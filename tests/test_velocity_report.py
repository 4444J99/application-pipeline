"""Tests for scripts/velocity_report.py."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import velocity_report as report_mod


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):  # noqa: ARG003
        return cls(2026, 3, 1, 10, 0, 0)


def test_filter_by_date_range_keeps_recent_and_ignores_invalid(monkeypatch):
    monkeypatch.setattr(report_mod, "datetime", _FixedDateTime)
    entries = [
        {"submission_date": "2026-02-20"},
        {"submission_date": "2025-10-20"},
        {"submission_date": "not-a-date"},
        {},
    ]

    filtered = report_mod.filter_by_date_range(entries, months=1)
    assert filtered == [{"submission_date": "2026-02-20"}]


def test_calculate_metrics_computes_core_breakdowns():
    entries = [
        {
            "submission_date": "2026-02-20",
            "outcome": "accepted",
            "composition_method": "manual",
            "identity_position": "systems-artist",
            "target": {"portal": "greenhouse"},
        },
        {
            "submission_date": "2026-02-21",
            "outcome": "rejected",
            "composition_method": "manual",
            "identity_position": "systems-artist",
            "target": {"portal": "ashby"},
        },
    ]
    metrics = report_mod.calculate_metrics(entries)
    assert metrics["total_submissions"] == 2
    assert metrics["conversions"] == 1
    assert metrics["conversion_rate"] == 0.5
    assert metrics["by_composition_method"]["manual"]["submissions"] == 2


def test_calculate_hypothesis_accuracy_uses_validated_subset():
    hypotheses = [
        {"predicted_outcome": "accepted", "actual_outcome": "accepted"},
        {"predicted_outcome": "rejected", "actual_outcome": "accepted"},
        {"predicted_outcome": "accepted"},
    ]
    stats = report_mod.calculate_hypothesis_accuracy(hypotheses)
    assert stats == {"accuracy": 0.5, "total": 2, "correct": 1}


def test_generate_report_includes_expected_sections(monkeypatch):
    monkeypatch.setattr(report_mod, "datetime", _FixedDateTime)
    entries = [{"submission_date": "2026-02-20", "outcome": "accepted", "target": {"portal": "greenhouse"}}]
    report = report_mod.generate_report(entries, hypotheses=[], months=1)
    assert "# Monthly Velocity Report" in report
    assert "## Summary" in report
    assert "## Hypothesis Validation" in report


def test_load_conversion_log_supports_dict_shape(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()
    path = signals / "conversion-log.yaml"
    path.write_text("entries:\n  - submission_date: '2026-02-20'\n    outcome: accepted\n")
    monkeypatch.setattr(report_mod, "SIGNALS_DIR", signals)
    data = report_mod.load_conversion_log()
    assert isinstance(data, list)
    assert data[0]["outcome"] == "accepted"


def test_load_hypotheses_supports_dict_shape(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()
    path = signals / "hypotheses.yaml"
    path.write_text("hypotheses:\n  - predicted_outcome: accepted\n    actual_outcome: accepted\n")
    monkeypatch.setattr(report_mod, "SIGNALS_DIR", signals)
    data = report_mod.load_hypotheses()
    assert isinstance(data, list)
    assert data[0]["predicted_outcome"] == "accepted"
