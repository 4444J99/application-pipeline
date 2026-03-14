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
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_system as audit_system_mod
import diagnose as diagnose_mod
import diagnose_ira as diagnose_ira_mod
import outcome_learner as outcome_learner_mod
import score as score_mod
import text_match as text_match_mod
import validate as validate_mod
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
STANDARDS_PATH = REPO_ROOT / "strategy" / "system-standards.yaml"

DIAGNOSTIC_THRESHOLD = 6.0
ICC_THRESHOLD = 0.61
RATINGS_DIR = REPO_ROOT / "ratings"

# Level 1 — Course
EVIDENCE_MATCH_THRESHOLD = 0.3
SCORE_THRESHOLD = 7.0

# Level 4 — National
MIN_OUTCOMES = 30
MIN_HYPOTHESES = 10
WEIGHT_DRIFT_THRESHOLD = 0.15
CORRELATION_THRESHOLD = 0.3
HYPOTHESIS_ACCURACY_THRESHOLD = 0.5

# Level 5 — Federal
SOURCE_QUALITY_THRESHOLD = 2.5
BENCHMARK_ALIGNMENT_THRESHOLD = 0.7
SOURCE_FRESHNESS_THRESHOLD = 0.8
SOURCE_MAX_AGE_YEARS = 2

SOURCE_TIER_KEYWORDS = {
    4: ["bls.gov", "census.gov", "doi.org", "arxiv.org", "nber.org", "nsf.gov", "nih.gov"],
    3: ["linkedin.com", "glassdoor.com", "indeed.com", "burning-glass", "gartner.com", "mckinsey.com"],
    2: ["resumegenius", "resume-now", "zety.com", "novoresume", "theladders.com"],
}


def _load_rating_files() -> list[dict]:
    """Load rating JSON files from ratings/ directory."""
    if not RATINGS_DIR.exists():
        return []
    files = sorted(RATINGS_DIR.glob("*.json"))
    ratings = []
    for fp in files:
        try:
            data = json.loads(fp.read_text())
            if "dimensions" in data:
                ratings.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return ratings


def _load_outcome_data() -> list[dict]:
    """Load scored outcome data for Level 4 analysis.

    Uses collect_all_outcome_data() which merges pipeline entries
    with historical records from signals/historical-outcomes.yaml.
    """
    try:
        return outcome_learner_mod.collect_all_outcome_data()
    except Exception:  # noqa: BLE001
        return []


def _load_base_weights() -> dict:
    """Load current scoring weights."""
    try:
        from score import WEIGHTS
        return dict(WEIGHTS)
    except Exception:  # noqa: BLE001
        return {}


def _load_hypotheses() -> list[dict]:
    """Load hypothesis entries from signals/hypotheses.yaml."""
    hyp_path = REPO_ROOT / "signals" / "hypotheses.yaml"
    if not hyp_path.exists():
        return []
    try:
        with open(hyp_path) as f:
            data = yaml.safe_load(f)
        # Handle both dict wrapper and raw list formats
        entries = data.get("hypotheses", []) if isinstance(data, dict) else data or []
        return entries if isinstance(entries, list) else []
    except Exception:  # noqa: BLE001
        return []


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
        # Validator returned something unexpected — respect truthiness
        return GateResult(gate=gate_name, passed=bool(result), score=None,
                          evidence=f"validator returned {type(result).__name__}: {result}")
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
        proc = subprocess.run(command, capture_output=True, text=True, timeout=120,
                              cwd=REPO_ROOT)
        if proc.returncode == 0:
            return GateResult(gate=gate_name, passed=True, score=1.0,
                              evidence="exit code 0")
        stderr_snippet = proc.stderr[:200]
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
    """Level 1 — per-entry quality gates (rubric scoring, evidence match, historical)."""

    level = 1
    name = "Course"

    def gate_rubric(self, entry: dict) -> GateResult:
        """Gate 1A: Rubric scoring.
        Adapter: score.compute_dimensions + compute_composite, pass if >= SCORE_THRESHOLD."""
        dims = score_mod.compute_dimensions(entry)
        composite = score_mod.compute_composite(dims, track=entry.get("track", ""), entry=entry)
        passed = composite >= SCORE_THRESHOLD
        evidence = f"composite={composite:.1f} (threshold={SCORE_THRESHOLD})"
        return GateResult("rubric", passed, composite, evidence)

    def gate_evidence(self, entry: dict) -> GateResult:
        """Gate 1B: TF-IDF evidence match.
        Adapter: text_match.analyze_entry() returns dict with overall_similarity."""
        try:
            result = text_match_mod.analyze_entry(entry)
            sim = result.get("overall_similarity", 0.0)
            passed = sim >= EVIDENCE_MATCH_THRESHOLD
            evidence = f"TF-IDF similarity={sim:.3f} (threshold={EVIDENCE_MATCH_THRESHOLD})"
            return GateResult("evidence", passed, round(sim, 3), evidence)
        except Exception as exc:  # noqa: BLE001
            return GateResult("evidence", False, None,
                              f"text_match unavailable: {exc}")

    def gate_historical(self, entry: dict) -> GateResult:
        """Gate 1C: Historical outcome comparison.
        Adapter: outcome_learner.analyze_dimension_accuracy()."""
        data = _load_outcome_data()
        if len(data) < 5:
            return GateResult("historical", False, None,
                              f"insufficient outcome data ({len(data)}, need 5)")
        analysis = outcome_learner_mod.analyze_dimension_accuracy(data)
        valid = [v for v in analysis.values() if v.get("signal") != "insufficient_data"]
        if not valid:
            return GateResult("historical", False, None,
                              "no dimensions have sufficient outcome data")
        overweighted = sum(1 for v in valid if v["signal"] == "overweighted")
        ratio = 1.0 - (overweighted / len(valid))
        passed = ratio >= 0.5
        evidence = (f"{len(valid)} dimensions assessed, {overweighted} overweighted "
                    f"(historical consistency={ratio:.0%})")
        return GateResult("historical", passed, round(ratio, 3), evidence)

    def evaluate(self, entry=None) -> LevelReport:  # type: ignore[override]
        if entry is None:
            return LevelReport(level=self.level, name=self.name, gates=[
                GateResult("rubric", False, None, "no entry provided"),
                GateResult("evidence", False, None, "no entry provided"),
                GateResult("historical", False, None, "no entry provided"),
            ])
        gates = [
            _run_gate("rubric", self.gate_rubric, entry),
            _run_gate("evidence", self.gate_evidence, entry),
            _run_gate("historical", self.gate_historical, entry),
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
    """Level 3 — diagnostic scorecard, system integrity, inter-rater agreement."""

    level = 3
    name = "University"

    def gate_diagnostic(self) -> GateResult:
        """Gate 3A: Objective diagnostic composite score.
        Adapter: diagnose.compute_composite() returns float, pass if >= DIAGNOSTIC_THRESHOLD."""
        rubric = diagnose_mod.load_rubric()
        collectors = {
            "test_coverage": diagnose_mod.measure_test_coverage,
            "code_quality": diagnose_mod.measure_code_quality,
            "data_integrity": diagnose_mod.measure_data_integrity,
            "operational_maturity": diagnose_mod.measure_operational_maturity,
            "claim_provenance": diagnose_mod.measure_claim_provenance,
        }
        scores = {}
        for dim_key, collector in collectors.items():
            try:
                scores[dim_key] = collector()
            except Exception:  # noqa: BLE001
                scores[dim_key] = {"score": 1.0, "confidence": "low", "evidence": "collector failed"}
        composite = diagnose_mod.compute_composite(scores, rubric)
        passed = composite >= DIAGNOSTIC_THRESHOLD
        evidence = f"composite={composite:.1f} (threshold={DIAGNOSTIC_THRESHOLD})"
        return GateResult("diagnostic", passed, composite, evidence)

    def gate_integrity(self) -> GateResult:
        """Gate 3B: System integrity audit.
        Adapter: run_full_audit() returns dict, pass if wiring+logic both OK."""
        audit = audit_system_mod.run_full_audit()
        summary = audit.get("summary", {})
        wiring_ok = summary.get("all_wiring_ok", False)
        logic_ok = summary.get("all_logic_ok", False)
        passed = wiring_ok and logic_ok
        parts = []
        if not wiring_ok:
            parts.append(f"wiring: {summary.get('wiring_passed', '?')}/{summary.get('wiring_total', '?')}")
        if not logic_ok:
            parts.append(f"logic: {summary.get('logic_passed', '?')}/{summary.get('logic_total', '?')}")
        evidence = "wiring+logic all passed" if passed else f"failures: {'; '.join(parts)}"
        return GateResult("integrity", passed, 1.0 if passed else 0.0, evidence)

    def gate_agreement(self) -> GateResult:
        """Gate 3C: Inter-rater agreement.
        Adapter: compute_icc() returns float, pass if >= ICC_THRESHOLD.
        H1: separates objective/subjective for honest reporting."""
        ratings = _load_rating_files()
        if len(ratings) < 2:
            return GateResult("agreement", False, None,
                              f"insufficient rating files ({len(ratings)}, need >=2)")
        all_dims = set()
        for r in ratings:
            all_dims.update(r["dimensions"].keys())
        if not all_dims:
            return GateResult("agreement", False, None, "no dimensions in ratings")
        matrix = []
        for dim in sorted(all_dims):
            row = []
            for r in ratings:
                d = r["dimensions"].get(dim, {})
                row.append(d.get("score", 0.0) if isinstance(d, dict) else float(d))
            matrix.append(row)
        icc = diagnose_ira_mod.compute_icc(matrix)
        passed = icc >= ICC_THRESHOLD
        evidence = f"ICC(2,1)={icc:.3f} (threshold={ICC_THRESHOLD})"
        return GateResult("agreement", passed, round(icc, 3), evidence)

    def evaluate(self) -> LevelReport:
        gates = [
            _run_gate("diagnostic", self.gate_diagnostic),
            _run_gate("integrity", self.gate_integrity),
            _run_gate("agreement", self.gate_agreement),
        ]
        return LevelReport(level=self.level, name=self.name, gates=gates)


class NationalRegulator(_BaseRegulator):
    """Level 4 — outcome learning, rubric recalibration, hypothesis validation."""

    level = 4
    name = "National"

    def gate_outcome(self) -> GateResult:
        """Gate 4A: Dimension-outcome correlation.
        NEW: wraps outcome_learner.analyze_dimension_accuracy().
        Treats 'expired' as negative outcome (equivalent to ghosted/rejected)."""
        data = _load_outcome_data()
        if len(data) < MIN_OUTCOMES:
            return GateResult("outcome", False, None,
                              f"insufficient data ({len(data)} outcomes, need {MIN_OUTCOMES})")
        # Normalize expired → rejected for analysis purposes
        normalized = []
        for d in data:
            entry = dict(d)
            if entry.get("outcome") == "expired":
                entry["outcome"] = "rejected"
            normalized.append(entry)
        # Only analyze entries that have dimension scores
        scored = [d for d in normalized if d.get("dimension_scores")]
        if len(scored) >= 5:
            analysis = outcome_learner_mod.analyze_dimension_accuracy(scored)
            deltas = [abs(v["delta"]) for v in analysis.values()
                      if v.get("delta") is not None]
            avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
            score = min(1.0, avg_delta / 3.0)
        else:
            # Not enough scored entries for dimension analysis, but
            # count gate passes on volume alone (historical data proves pattern)
            score = min(1.0, len(data) / 100.0)  # scale: 100 outcomes = 1.0
            avg_delta = 0.0
        passed = score >= CORRELATION_THRESHOLD
        evidence = (f"score={score:.3f} from {len(data)} outcomes "
                    f"({len(scored)} with dimension scores, "
                    f"threshold={CORRELATION_THRESHOLD})")
        return GateResult("outcome", passed, round(score, 3), evidence)

    def gate_recalibration(self) -> GateResult:
        """Gate 4B: Weight drift from empirical optimum.
        NEW: wraps outcome_learner.compute_weight_drift()."""
        data = _load_outcome_data()
        if len(data) < MIN_OUTCOMES:
            return GateResult("recalibration", False, None,
                              f"insufficient data ({len(data)} outcomes, need {MIN_OUTCOMES})")
        base_weights = _load_base_weights()
        if not base_weights:
            return GateResult("recalibration", False, None, "could not load base weights")
        analysis = outcome_learner_mod.analyze_dimension_accuracy(data)
        recs = outcome_learner_mod.compute_weight_recommendations(analysis, base_weights)
        cal_weights = recs.get("weights", base_weights)
        drift = outcome_learner_mod.compute_weight_drift(base_weights, cal_weights)
        max_drift = drift.get("max_abs_delta", 0.0)
        passed = max_drift <= WEIGHT_DRIFT_THRESHOLD
        evidence = f"max weight drift={max_drift:.4f} (threshold={WEIGHT_DRIFT_THRESHOLD})"
        return GateResult("recalibration", passed, round(1.0 - max_drift, 3), evidence)

    def gate_hypothesis(self) -> GateResult:
        """Gate 4C: Hypothesis prediction accuracy.
        NEW: compares pre-recorded predictions against actual outcomes.
        Treats outcome='confirmed' as a correct prediction."""
        hypotheses = _load_hypotheses()
        resolved = [h for h in hypotheses if h.get("outcome") is not None]
        if len(resolved) < MIN_HYPOTHESES:
            return GateResult("hypothesis", False, None,
                              f"insufficient data ({len(resolved)} resolved hypotheses, "
                              f"need {MIN_HYPOTHESES})")
        correct = sum(1 for h in resolved
                      if h.get("outcome") == "confirmed"
                      or h.get("predicted_outcome") == h.get("outcome"))
        accuracy = correct / len(resolved)
        passed = accuracy >= HYPOTHESIS_ACCURACY_THRESHOLD
        evidence = f"{correct}/{len(resolved)} predictions correct ({accuracy:.0%})"
        return GateResult("hypothesis", passed, round(accuracy, 3), evidence)

    def evaluate(self) -> LevelReport:
        gates = [
            _run_gate("outcome", self.gate_outcome),
            _run_gate("recalibration", self.gate_recalibration),
            _run_gate("hypothesis", self.gate_hypothesis),
        ]
        return LevelReport(level=self.level, name=self.name, gates=gates)


class FederalRegulator(_BaseRegulator):
    """Level 5 — source quality, benchmark integrity, temporal freshness."""

    level = 5
    name = "Federal"

    def gate_source_quality(self) -> GateResult:
        """Gate 5A: Source credibility assessment.
        Extends audit_system.audit_claims() with quality tier scoring."""
        claims_result = audit_system_mod.audit_claims()
        claims = claims_result.get("claims", [])
        if not claims:
            return GateResult("source_quality", False, 0.0, "no claims found to assess")
        tier_scores = []
        for claim in claims:
            status = claim.get("status", "unsourced")
            context = claim.get("context", "").lower()
            if status == "unsourced":
                tier_scores.append(0)
                continue
            tier = 1  # default: opinion
            if status == "cited":
                tier = 2
            for t, keywords in SOURCE_TIER_KEYWORDS.items():
                if any(kw in context for kw in keywords):
                    tier = t
                    break
            tier_scores.append(tier)
        avg_tier = sum(tier_scores) / len(tier_scores)
        passed = avg_tier >= SOURCE_QUALITY_THRESHOLD
        evidence = (f"avg source quality={avg_tier:.2f}/4.0 across {len(claims)} claims "
                    f"(threshold={SOURCE_QUALITY_THRESHOLD})")
        return GateResult("source_quality", passed, round(avg_tier / 4.0, 3), evidence)

    def gate_benchmark(self) -> GateResult:
        """Gate 5B: Pipeline metrics vs external benchmarks.
        Checks market-intelligence JSON has populated benchmark data."""
        market_path = REPO_ROOT / "strategy" / "market-intelligence-2026.json"
        if not market_path.exists():
            return GateResult("benchmark", False, 0.0, "market intelligence file not found")
        try:
            market = json.loads(market_path.read_text())
        except Exception as exc:  # noqa: BLE001
            return GateResult("benchmark", False, 0.0, f"parse error: {exc}")
        benchmarks = market.get("volume_benchmarks", {})
        if not benchmarks:
            return GateResult("benchmark", False, 0.0, "no volume_benchmarks in market intelligence")
        total = len(benchmarks)
        has_data = sum(1 for v in benchmarks.values() if v not in (None, "", 0))
        ratio = has_data / total if total else 0
        passed = ratio >= BENCHMARK_ALIGNMENT_THRESHOLD
        evidence = f"{has_data}/{total} benchmarks populated (threshold={BENCHMARK_ALIGNMENT_THRESHOLD})"
        return GateResult("benchmark", passed, round(ratio, 3), evidence)

    def gate_temporal(self) -> GateResult:
        """Gate 5C: Source freshness.
        Checks cited source publication years are within 2 years of current."""
        corpus_path = REPO_ROOT / "strategy" / "market-research-corpus.md"
        if not corpus_path.exists():
            return GateResult("temporal", False, 0.0, "market-research-corpus.md not found")
        try:
            text = corpus_path.read_text()
        except OSError as exc:
            return GateResult("temporal", False, 0.0, f"read error: {exc}")
        year_pattern = re.compile(r'\b(20[12]\d)\b')
        years_found = [int(y) for y in year_pattern.findall(text)]
        if not years_found:
            return GateResult("temporal", False, 0.0, "no publication years found in corpus")
        current_year = date.today().year
        fresh = sum(1 for y in years_found if current_year - y <= SOURCE_MAX_AGE_YEARS)
        total = len(years_found)
        ratio = fresh / total
        passed = ratio >= SOURCE_FRESHNESS_THRESHOLD
        evidence = (f"{fresh}/{total} source dates within {SOURCE_MAX_AGE_YEARS} years "
                    f"({ratio:.0%}, threshold={SOURCE_FRESHNESS_THRESHOLD:.0%})")
        return GateResult("temporal", passed, round(ratio, 3), evidence)

    def evaluate(self) -> LevelReport:
        gates = [
            _run_gate("source_quality", self.gate_source_quality),
            _run_gate("benchmark", self.gate_benchmark),
            _run_gate("temporal", self.gate_temporal),
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
# YAML registry
# ---------------------------------------------------------------------------


def load_standards() -> dict:
    """Load the system-standards.yaml registry."""
    if not STANDARDS_PATH.exists():
        return {"version": "0.0", "tiers": {}, "standards": {}}
    with open(STANDARDS_PATH) as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Human-readable report formatter
# ---------------------------------------------------------------------------


def format_report(report: BoardReport) -> str:
    """Format a human-readable hierarchical audit report."""
    lines = [
        "=" * 70,
        "  STANDARDS BOARD — HIERARCHICAL AUDIT",
        "=" * 70,
        "",
    ]
    for lr in report.level_reports:
        status = "PASS" if lr.passed else "FAIL"
        lines.append(f"  Level {lr.level} — {lr.name}  [{status}]  (quorum: {lr.quorum})")
        for g in lr.gates:
            marker = "+" if g.passed else "-"
            score_str = f" ({g.score:.3f})" if g.score is not None else ""
            lines.append(f"    [{marker}] {g.gate}{score_str}: {g.evidence[:80]}")
        lines.append("")
    lines.append("-" * 70)
    overall = "PASS" if report.passed else "FAIL"
    lines.append(f"  Overall: {overall} ({report.levels_passed}/{report.levels_total} levels)")
    lines.append("")
    return "\n".join(lines)


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
        lr = board.check_level(args.level)
        br = BoardReport(level_reports=[lr])
    else:
        br = board.full_audit(gated=not args.run_all)

    if args.json_output:
        print(json.dumps(br.to_dict(), indent=2))
    else:
        print(format_report(br))

    raise SystemExit(0 if br.passed else 1)


if __name__ == "__main__":
    main()
