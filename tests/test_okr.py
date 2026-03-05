#!/usr/bin/env python3
"""Tests for okr.py — quarterly OKR tracker."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from okr import compute_actuals, compute_progress, format_report, quarter_elapsed_pct


def _make_entry(entry_id, status="submitted", outcome=None, submitted_date="2026-04-15",
                score=8.5, follow_ups=None, outcome_date=None):
    entry = {
        "id": entry_id,
        "status": status,
        "outcome": outcome,
        "fit": {"composite": score},
        "timeline": {"submitted": submitted_date},
        "follow_up": follow_ups or [],
    }
    if outcome_date:
        entry["timeline"]["outcome_date"] = outcome_date
    return entry


class TestComputeActuals:
    def test_counts_submissions_in_period(self):
        entries = [
            _make_entry("e1", submitted_date="2026-04-10"),
            _make_entry("e2", submitted_date="2026-05-01"),
            _make_entry("e3", submitted_date="2026-01-01"),  # outside period
        ]
        actuals = compute_actuals(entries, "2026-04-01", "2026-06-30")
        assert actuals["submissions"] == 2

    def test_counts_network_actions(self):
        entries = [
            _make_entry("e1", follow_ups=[
                {"date": "2026-04-10", "channel": "linkedin"},
                {"date": "2026-05-01", "channel": "email"},
            ]),
        ]
        actuals = compute_actuals(entries, "2026-04-01", "2026-06-30")
        assert actuals["network_actions"] == 2

    def test_empty_entries(self):
        actuals = compute_actuals([], "2026-04-01", "2026-06-30")
        assert actuals["submissions"] == 0
        assert actuals["conversion_rate"] == 0.0

    def test_outcomes_collected(self):
        entries = [
            _make_entry("e1", status="outcome", outcome="rejected",
                        outcome_date="2026-05-15"),
            _make_entry("e2", status="outcome", outcome="accepted",
                        outcome_date="2026-01-15"),  # outside period
        ]
        actuals = compute_actuals(entries, "2026-04-01", "2026-06-30")
        assert actuals["outcomes_collected"] == 1


class TestComputeProgress:
    def test_on_track(self):
        targets = {"objectives": {"submissions": {"target": 10, "description": "Test"}}}
        actuals = {"submissions": 8}
        progress = compute_progress(targets, actuals)
        assert progress[0]["progress_pct"] == 80.0
        assert progress[0]["status"] == "ON_TRACK"

    def test_behind(self):
        targets = {"objectives": {"submissions": {"target": 10, "description": "Test"}}}
        actuals = {"submissions": 2}
        progress = compute_progress(targets, actuals)
        assert progress[0]["status"] == "BEHIND"

    def test_at_risk(self):
        targets = {"objectives": {"submissions": {"target": 10, "description": "Test"}}}
        actuals = {"submissions": 5}
        progress = compute_progress(targets, actuals)
        assert progress[0]["status"] == "AT_RISK"


class TestQuarterElapsed:
    def test_midpoint(self):
        pct = quarter_elapsed_pct("2026-01-01", "2026-04-01")
        # ~90 day quarter, depends on today — just verify it's a number
        assert 0 <= pct <= 100

    def test_past_quarter(self):
        pct = quarter_elapsed_pct("2025-01-01", "2025-03-31")
        assert pct == 100.0


class TestFormatReport:
    def test_contains_header(self):
        targets = {
            "quarter": "Q2-2026",
            "period_start": "2026-04-01",
            "period_end": "2026-06-30",
            "objectives": {"submissions": {"target": 10, "description": "Total subs"}},
        }
        progress = [{"key": "submissions", "description": "Total subs",
                      "target": 10, "actual": 5, "progress_pct": 50.0, "status": "AT_RISK"}]
        report = format_report(targets, progress, 50.0)
        assert "QUARTERLY OKR PROGRESS" in report
        assert "Q2-2026" in report
        assert "AT RISK" in report
