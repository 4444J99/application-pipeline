#!/usr/bin/env python3
"""Hierarchical standards validation framework.

Five-level oversight architecture with triad regulators (3 gates per level,
≥2/3 quorum). Wraps existing validators and adds new Level 4-5 assessment
gates. Designed for meta-ORGANVM portability — data classes and orchestration
are organ-agnostic; gate implementations are organ-specific.

Usage:
    python scripts/standards.py                  # Full hierarchical audit
    python scripts/standards.py --level 2        # Single level
    python scripts/standards.py --json           # Machine-readable output
    python scripts/standards.py --run-all        # Run all levels (no cascade stop)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_system as audit_system_mod
import validate as validate_mod

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    """Outcome of a single gate within a regulatory body."""

    gate: str
    passed: bool
    score: float | None
    evidence: str
    ci_lower: float | None = None   # 95% CI lower bound (H2)
    ci_upper: float | None = None   # 95% CI upper bound (H2)

    def to_dict(self) -> dict:
        d = {
            "gate": self.gate,
            "passed": self.passed,
            "score": self.score,
            "evidence": self.evidence,
        }
        if self.ci_lower is not None:
            d["ci_lower"] = self.ci_lower
        if self.ci_upper is not None:
            d["ci_upper"] = self.ci_upper
        return d


@dataclass
class LevelReport:
    """Outcome of one regulatory body (one level, three gates, quorum rule)."""

    level: int
    name: str
    gates: list[GateResult]

    @property
    def passed(self) -> bool:
        return sum(1 for g in self.gates if g.passed) >= 2

    @property
    def quorum(self) -> str:
        n = sum(1 for g in self.gates if g.passed)
        return f"{n}/{len(self.gates)}"

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "name": self.name,
            "gates": [g.to_dict() for g in self.gates],
            "passed": self.passed,
            "quorum": self.quorum,
        }


@dataclass
class BoardReport:
    """Outcome of the full hierarchical audit."""

    level_reports: list[LevelReport]

    @property
    def passed(self) -> bool:
        return all(lr.passed for lr in self.level_reports)

    @property
    def levels_passed(self) -> int:
        return sum(1 for lr in self.level_reports if lr.passed)

    @property
    def levels_total(self) -> int:
        return len(self.level_reports)

    def to_dict(self) -> dict:
        return {
            "level_reports": [lr.to_dict() for lr in self.level_reports],
            "passed": self.passed,
            "levels_passed": self.levels_passed,
            "levels_total": self.levels_total,
        }


# ---------------------------------------------------------------------------
# Gate Execution Helpers
# ---------------------------------------------------------------------------


def _run_gate(gate_name: str, validator_fn, *args) -> GateResult:
    """Call validator_fn with exception safety.

    If the function returns a GateResult, pass it through unchanged.
    If it raises, wrap the exception into a failing GateResult.
    """
    try:
        result = validator_fn(*args)
        if isinstance(result, GateResult):
            return result
        # Validator returned something unexpected — treat as a pass with a note
        return GateResult(gate=gate_name, passed=True, score=1.0,
                          evidence=f"validator returned {type(result).__name__}")
    except Exception as exc:  # noqa: BLE001
        return GateResult(
            gate=gate_name,
            passed=False,
            score=0.0,
            evidence=f"{type(exc).__name__}: {exc}",
        )


def _run_subprocess_gate(gate_name: str, command: list[str]) -> GateResult:
    """Run a subprocess and map exit code to a GateResult.

    Returns passed=True / score=1.0 on exit code 0.
    Returns passed=False / score=0.0 on non-zero exit.
    Handles TimeoutExpired by returning a failing gate.
    """
    try:
        proc = subprocess.run(command, capture_output=True, timeout=120)
        if proc.returncode == 0:
            return GateResult(gate=gate_name, passed=True, score=1.0,
                              evidence="exit code 0")
        stderr_snippet = proc.stderr.decode(errors="replace")[:200]
        return GateResult(gate=gate_name, passed=False, score=0.0,
                          evidence=f"exit code {proc.returncode}: {stderr_snippet}")
    except subprocess.TimeoutExpired:
        return GateResult(gate=gate_name, passed=False, score=0.0,
                          evidence="subprocess timed out after 120s")
    except Exception as exc:  # noqa: BLE001
        return GateResult(gate=gate_name, passed=False, score=0.0,
                          evidence=f"{type(exc).__name__}: {exc}")


def _get_pipeline_files() -> list[Path]:
    """Get all pipeline YAML files for schema validation."""
    from pipeline_lib import ALL_PIPELINE_DIRS_WITH_POOL
    files = []
    for d in ALL_PIPELINE_DIRS_WITH_POOL:
        if d.exists():
            files.extend(sorted(d.glob("*.yaml")))
    return [f for f in files if not f.name.startswith("_")]


# ---------------------------------------------------------------------------
# Stub Regulators
# ---------------------------------------------------------------------------


class _BaseRegulator:
    """Abstract base for all regulatory bodies."""

    level: int = 0
    name: str = ""

    def evaluate(self, *args) -> LevelReport:
        raise NotImplementedError


class CourseRegulator(_BaseRegulator):
    """Level 1 — per-entry quality gates (rubric coverage, evidence, history)."""

    level = 1
    name = "Course"

    def evaluate(self, entry=None) -> LevelReport:  # type: ignore[override]
        gates = [
            GateResult("rubric", False, None, "not yet implemented"),
            GateResult("evidence", False, None, "not yet implemented"),
            GateResult("historical", False, None, "not yet implemented"),
        ]
        return LevelReport(level=self.level, name=self.name, gates=gates)


class DepartmentRegulator(_BaseRegulator):
    """Level 2 — schema enforcement, rubric integrity, cross-reference wiring."""

    level = 2
    name = "Department"

    def gate_schema(self) -> GateResult:
        """Gate 2A: Entry schema validation.
        Adapter: validate.validate_entry(filepath) returns list[str] — empty = pass."""
        files = _get_pipeline_files()
        if not files:
            return GateResult("schema", False, 0.0, "no pipeline YAML files found")
        error_count = 0
        all_errors = []
        for fp in files:
            errors = validate_mod.validate_entry(fp)
            if errors:
                error_count += 1
                all_errors.extend(f"{fp.name}: {e}" for e in errors[:3])
        total = len(files)
        passed = error_count == 0
        ratio = (total - error_count) / total if total else 0
        evidence = (f"{total} entries validated, 0 errors" if passed
                    else f"{error_count} entries with errors: {'; '.join(all_errors[:5])}")
        return GateResult("schema", passed, round(ratio, 3), evidence)

    def gate_rubric(self) -> GateResult:
        """Gate 2B: Scoring rubric integrity.
        Adapter: validate.validate_scoring_rubric() returns list[str] — empty = pass."""
        errors = validate_mod.validate_scoring_rubric()
        passed = len(errors) == 0
        evidence = ("rubric validation passed" if passed
                    else f"{len(errors)} errors: {'; '.join(errors[:5])}")
        return GateResult("rubric", passed, 1.0 if passed else 0.0, evidence)

    def gate_wiring(self) -> GateResult:
        """Gate 2C: Cross-reference wiring integrity.
        Adapter: audit_system.audit_wiring() returns dict with summary.passed/total."""
        result = audit_system_mod.audit_wiring()
        summary = result.get("summary", {})
        passed_count = summary.get("passed", 0)
        total = summary.get("total", 1)
        ratio = passed_count / total if total else 0
        passed = passed_count == total
        evidence = (f"all {total} wiring checks passed" if passed
                    else f"{passed_count}/{total} wiring checks passed")
        return GateResult("wiring", passed, round(ratio, 3), evidence)

    def evaluate(self) -> LevelReport:
        gates = [
            _run_gate("schema", self.gate_schema),
            _run_gate("rubric", self.gate_rubric),
            _run_gate("wiring", self.gate_wiring),
        ]
        return LevelReport(level=self.level, name=self.name, gates=gates)


class UniversityRegulator(_BaseRegulator):
    """Level 3 — diagnostic scorecard, data integrity, inter-rater agreement."""

    level = 3
    name = "University"

    def evaluate(self) -> LevelReport:  # type: ignore[override]
        gates = [
            GateResult("diagnostic", False, None, "not yet implemented"),
            GateResult("integrity", False, None, "not yet implemented"),
            GateResult("agreement", False, None, "not yet implemented"),
        ]
        return LevelReport(level=self.level, name=self.name, gates=gates)


class NationalRegulator(_BaseRegulator):
    """Level 4 — outcome learning, rubric recalibration, hypothesis validation."""

    level = 4
    name = "National"

    def evaluate(self) -> LevelReport:  # type: ignore[override]
        gates = [
            GateResult("outcome", False, None, "not yet implemented"),
            GateResult("recalibration", False, None, "not yet implemented"),
            GateResult("hypothesis", False, None, "not yet implemented"),
        ]
        return LevelReport(level=self.level, name=self.name, gates=gates)


class FederalRegulator(_BaseRegulator):
    """Level 5 — source quality, benchmark integrity, temporal freshness."""

    level = 5
    name = "Federal"

    def evaluate(self) -> LevelReport:  # type: ignore[override]
        gates = [
            GateResult("source_quality", False, None, "not yet implemented"),
            GateResult("benchmark", False, None, "not yet implemented"),
            GateResult("temporal", False, None, "not yet implemented"),
        ]
        return LevelReport(level=self.level, name=self.name, gates=gates)


# ---------------------------------------------------------------------------
# Standards Board
# ---------------------------------------------------------------------------


class StandardsBoard:
    """Orchestrates all regulatory bodies in hierarchical order.

    System-level audit runs: Department → University → National → Federal.
    Course (Level 1) is per-entry and invoked separately via check_entry().
    """

    def __init__(self):
        self.course = CourseRegulator()
        self.department = DepartmentRegulator()
        self.university = UniversityRegulator()
        self.national = NationalRegulator()
        self.federal = FederalRegulator()
        self._system_regulators = [
            self.department,
            self.university,
            self.national,
            self.federal,
        ]

    def full_audit(self, gated: bool = True) -> BoardReport:
        """Run all system-level regulators.

        If gated=True, stop at the first failing level (cascade stop).
        If gated=False, run all levels regardless of failures.
        """
        reports: list[LevelReport] = []
        for regulator in self._system_regulators:
            report = regulator.evaluate()
            reports.append(report)
            if gated and not report.passed:
                break
        return BoardReport(level_reports=reports)

    def check_level(self, level: int) -> LevelReport:
        """Run a single level's regulator and return its LevelReport."""
        mapping = {
            1: self.course,
            2: self.department,
            3: self.university,
            4: self.national,
            5: self.federal,
        }
        regulator = mapping.get(level)
        if regulator is None:
            raise ValueError(f"Invalid level: {level}. Must be 1-5.")
        return regulator.evaluate()

    def check_entry(self, entry: dict) -> LevelReport:
        """Run the Course (Level 1) regulator for a single pipeline entry."""
        return self.course.evaluate(entry)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hierarchical standards validation framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--level", type=int, choices=range(1, 6), metavar="LEVEL",
                        help="Run a single level (1-5)")
    parser.add_argument("--run-all", action="store_true",
                        help="Run all levels without cascade stop")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Machine-readable JSON output")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    board = StandardsBoard()

    if args.level:
        report = board.check_level(args.level)
        if args.json_output:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            status = "PASS" if report.passed else "FAIL"
            print(f"Level {report.level} ({report.name}): {status} [{report.quorum}]")
            for gate in report.gates:
                mark = "+" if gate.passed else "-"
                print(f"  [{mark}] {gate.gate}: {gate.evidence}")
    else:
        board_report = board.full_audit(gated=not args.run_all)
        if args.json_output:
            print(json.dumps(board_report.to_dict(), indent=2))
        else:
            status = "PASS" if board_report.passed else "FAIL"
            print(f"Standards Board: {status} ({board_report.levels_passed}/{board_report.levels_total} levels)")
            for lr in board_report.level_reports:
                level_status = "PASS" if lr.passed else "FAIL"
                print(f"  Level {lr.level} ({lr.name}): {level_status} [{lr.quorum}]")
                for gate in lr.gates:
                    mark = "+" if gate.passed else "-"
                    print(f"    [{mark}] {gate.gate}: {gate.evidence}")


if __name__ == "__main__":
    main()
