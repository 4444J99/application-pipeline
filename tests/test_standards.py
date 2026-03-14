"""Tests for the hierarchical standards validation framework."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from standards import (
    BoardReport,
    CourseRegulator,
    DepartmentRegulator,
    FederalRegulator,
    GateResult,
    LevelReport,
    NationalRegulator,
    StandardsBoard,
    UniversityRegulator,
    _run_gate,
    _run_subprocess_gate,
)

# ---------------------------------------------------------------------------
# GateResult
# ---------------------------------------------------------------------------


class TestGateResult:
    """GateResult data class — fields, CI bounds, serialisation."""

    def test_fields(self):
        """Constructor stores gate, passed, score, evidence."""
        g = GateResult(gate="rubric", passed=True, score=0.85, evidence="all dims covered")
        assert g.gate == "rubric"
        assert g.passed is True
        assert g.score == 0.85
        assert g.evidence == "all dims covered"
        assert g.ci_lower is None
        assert g.ci_upper is None

    def test_with_ci(self):
        """CI bounds are stored when provided."""
        g = GateResult(gate="agreement", passed=True, score=0.72, evidence="ICC=0.72",
                       ci_lower=0.61, ci_upper=0.83)
        assert g.ci_lower == 0.61
        assert g.ci_upper == 0.83

    def test_to_dict(self):
        """to_dict includes CI keys only when set."""
        g_no_ci = GateResult(gate="schema", passed=False, score=0.0, evidence="missing fields")
        d = g_no_ci.to_dict()
        assert d == {"gate": "schema", "passed": False, "score": 0.0, "evidence": "missing fields"}
        assert "ci_lower" not in d
        assert "ci_upper" not in d

        g_with_ci = GateResult(gate="agreement", passed=True, score=0.8, evidence="ok",
                               ci_lower=0.7, ci_upper=0.9)
        d2 = g_with_ci.to_dict()
        assert d2["ci_lower"] == 0.7
        assert d2["ci_upper"] == 0.9


# ---------------------------------------------------------------------------
# LevelReport
# ---------------------------------------------------------------------------


class TestLevelReport:
    """LevelReport quorum logic and serialisation."""

    def _make_gates(self, passed_flags: list[bool]) -> list[GateResult]:
        return [
            GateResult(gate=f"gate_{i}", passed=p, score=1.0 if p else 0.0, evidence="")
            for i, p in enumerate(passed_flags)
        ]

    def test_quorum_3_of_3_passes(self):
        """All three gates passing → level passes."""
        lr = LevelReport(level=2, name="Department", gates=self._make_gates([True, True, True]))
        assert lr.passed is True
        assert lr.quorum == "3/3"

    def test_quorum_2_of_3_passes(self):
        """Exactly two gates passing meets the ≥2/3 quorum threshold."""
        lr = LevelReport(level=2, name="Department", gates=self._make_gates([True, True, False]))
        assert lr.passed is True
        assert lr.quorum == "2/3"

    def test_quorum_1_of_3_fails(self):
        """Only one gate passing does not meet quorum."""
        lr = LevelReport(level=2, name="Department", gates=self._make_gates([True, False, False]))
        assert lr.passed is False
        assert lr.quorum == "1/3"

    def test_quorum_0_of_3_fails(self):
        """Zero gates passing fails the level."""
        lr = LevelReport(level=2, name="Department", gates=self._make_gates([False, False, False]))
        assert lr.passed is False
        assert lr.quorum == "0/3"

    def test_to_dict(self):
        """to_dict returns level, name, gates list, passed, quorum."""
        lr = LevelReport(level=1, name="Course", gates=self._make_gates([True, False, True]))
        d = lr.to_dict()
        assert d["level"] == 1
        assert d["name"] == "Course"
        assert d["passed"] is True
        assert d["quorum"] == "2/3"
        assert len(d["gates"]) == 3
        assert all("gate" in g for g in d["gates"])


# ---------------------------------------------------------------------------
# BoardReport
# ---------------------------------------------------------------------------


class TestBoardReport:
    """BoardReport aggregation over multiple LevelReports."""

    def _passing_level(self, level: int) -> LevelReport:
        gates = [GateResult(gate=f"g{i}", passed=True, score=1.0, evidence="ok") for i in range(3)]
        return LevelReport(level=level, name=f"Level{level}", gates=gates)

    def _failing_level(self, level: int) -> LevelReport:
        gates = [GateResult(gate=f"g{i}", passed=False, score=0.0, evidence="fail") for i in range(3)]
        return LevelReport(level=level, name=f"Level{level}", gates=gates)

    def test_all_passing(self):
        """All levels passing → board passes."""
        report = BoardReport(level_reports=[self._passing_level(i) for i in range(1, 5)])
        assert report.passed is True
        assert report.levels_passed == 4
        assert report.levels_total == 4

    def test_partial_failure(self):
        """One failing level → board fails."""
        report = BoardReport(level_reports=[
            self._passing_level(1),
            self._failing_level(2),
            self._passing_level(3),
        ])
        assert report.passed is False
        assert report.levels_passed == 2
        assert report.levels_total == 3

    def test_to_dict(self):
        """to_dict nests level_reports and exposes passed, levels_passed, levels_total."""
        report = BoardReport(level_reports=[self._passing_level(1)])
        d = report.to_dict()
        assert "level_reports" in d
        assert len(d["level_reports"]) == 1
        assert d["passed"] is True
        assert d["levels_passed"] == 1
        assert d["levels_total"] == 1


# ---------------------------------------------------------------------------
# _run_gate helper
# ---------------------------------------------------------------------------


class TestRunGate:
    """_run_gate wraps a callable with exception safety."""

    def test_success(self):
        """A validator returning a GateResult passes it through unchanged."""
        def good_validator():
            return GateResult(gate="rubric", passed=True, score=0.9, evidence="all good")

        result = _run_gate("rubric", good_validator)
        assert result.gate == "rubric"
        assert result.passed is True
        assert result.score == 0.9

    def test_exception_wraps_to_failure(self):
        """An exception from the validator is caught and wrapped into a failing GateResult."""
        def bad_validator():
            raise RuntimeError("something went wrong")

        result = _run_gate("rubric", bad_validator)
        assert result.gate == "rubric"
        assert result.passed is False
        assert result.score == 0.0
        assert "RuntimeError" in result.evidence or "something went wrong" in result.evidence


# ---------------------------------------------------------------------------
# _run_subprocess_gate helper
# ---------------------------------------------------------------------------


class TestRunSubprocessGate:
    """_run_subprocess_gate executes a subprocess and maps exit code to GateResult."""

    def test_success(self, tmp_path):
        """Exit code 0 → passed=True, score=1.0."""
        script = tmp_path / "ok.py"
        script.write_text("import sys; sys.exit(0)\n")
        result = _run_subprocess_gate("ok", [sys.executable, str(script)])
        assert result.gate == "ok"
        assert result.passed is True
        assert result.score == 1.0

    def test_failure(self, tmp_path):
        """Non-zero exit code → passed=False, score=0.0."""
        script = tmp_path / "fail.py"
        script.write_text("import sys; sys.exit(1)\n")
        result = _run_subprocess_gate("fail", [sys.executable, str(script)])
        assert result.gate == "fail"
        assert result.passed is False
        assert result.score == 0.0


# ---------------------------------------------------------------------------
# Stub regulators — verify gate names and stub behaviour
# ---------------------------------------------------------------------------


class TestStubRegulators:
    """All stub regulators return the correct gate names and always fail."""

    def _check_regulator(self, reg: object, expected_level: int, expected_gates: list[str]):
        report = reg.evaluate()
        assert isinstance(report, LevelReport)
        assert report.level == expected_level
        gate_names = [g.gate for g in report.gates]
        assert gate_names == expected_gates
        assert all(not g.passed for g in report.gates), "Stub gates should all fail"
        assert not report.passed

    def test_course_regulator(self):
        self._check_regulator(CourseRegulator(), 1, ["rubric", "evidence", "historical"])

    def test_department_regulator(self):
        self._check_regulator(DepartmentRegulator(), 2, ["schema", "rubric", "wiring"])

    def test_university_regulator(self):
        self._check_regulator(UniversityRegulator(), 3, ["diagnostic", "integrity", "agreement"])

    def test_national_regulator(self):
        self._check_regulator(NationalRegulator(), 4, ["outcome", "recalibration", "hypothesis"])

    def test_federal_regulator(self):
        self._check_regulator(FederalRegulator(), 5, ["source_quality", "benchmark", "temporal"])


# ---------------------------------------------------------------------------
# StandardsBoard
# ---------------------------------------------------------------------------


class TestStandardsBoard:
    """StandardsBoard orchestrates regulators with gated and run-all modes."""

    def test_full_audit_gated_stops_on_failure(self):
        """gated=True stops at the first failing level (stubs all fail → stops after level 2)."""
        board = StandardsBoard()
        report = board.full_audit(gated=True)
        # All stubs fail, so cascade stops after the first system regulator (Department, level 2)
        assert report.levels_total == 1
        assert not report.passed
        assert report.level_reports[0].level == 2

    def test_full_audit_run_all_continues_past_failure(self):
        """gated=False runs all 4 system-level regulators regardless of failures."""
        board = StandardsBoard()
        report = board.full_audit(gated=False)
        assert report.levels_total == 4
        assert not report.passed
        assert report.levels_passed == 0

    def test_check_level_returns_level_report(self):
        """check_level delegates to the correct regulator and returns a LevelReport."""
        board = StandardsBoard()
        for level in range(1, 6):
            report = board.check_level(level)
            assert isinstance(report, LevelReport)
            assert report.level == level

    def test_check_level_invalid_raises(self):
        """check_level raises ValueError for an out-of-range level."""
        board = StandardsBoard()
        try:
            board.check_level(99)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "99" in str(e)

    def test_check_entry_delegates_to_course(self):
        """check_entry returns a Level 1 Course report."""
        board = StandardsBoard()
        entry = {"id": "test-entry", "status": "drafting"}
        report = board.check_entry(entry)
        assert isinstance(report, LevelReport)
        assert report.level == 1
