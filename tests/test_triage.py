#!/usr/bin/env python3
"""Tests for triage.py — pipeline triage automation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from triage import (
    format_triage_report,
    generate_triage_data,
    triage_org_cap,
    triage_staged_backlog,
)


def _entry(entry_id, status="staged", score=7.0, org="Acme Corp"):
    return {
        "id": entry_id,
        "status": status,
        "fit": {"score": score},
        "target": {"organization": org},
    }


class TestTriageStagedBacklog:
    def test_demotes_below_threshold(self):
        entries = [_entry("low-score", score=7.5), _entry("high-score", score=9.5)]
        actions = triage_staged_backlog(entries, min_score=9.0, dry_run=True)
        assert len(actions) == 1
        assert actions[0]["id"] == "low-score"
        assert actions[0]["applied"] is False

    def test_keeps_above_threshold(self):
        entries = [_entry("good", score=9.5)]
        actions = triage_staged_backlog(entries, min_score=9.0, dry_run=True)
        assert actions == []

    def test_ignores_non_staged(self):
        entries = [_entry("draft", status="drafting", score=5.0)]
        actions = triage_staged_backlog(entries, min_score=9.0, dry_run=True)
        assert actions == []

    def test_custom_threshold(self):
        entries = [_entry("mid", score=8.0)]
        actions = triage_staged_backlog(entries, min_score=8.5, dry_run=True)
        assert len(actions) == 1

    def test_zero_score_demoted(self):
        """get_score returns 0.0 for empty fit, which is below threshold."""
        entry = _entry("no-score")
        entry["fit"] = {}
        actions = triage_staged_backlog([entry], min_score=9.0, dry_run=True)
        assert len(actions) == 1
        assert actions[0]["score"] == 0.0


class TestTriageOrgCap:
    def test_defers_excess_entries(self):
        entries = [
            _entry("a1", status="qualified", score=9.0, org="BigCo"),
            _entry("a2", status="drafting", score=7.0, org="BigCo"),
        ]
        actions = triage_org_cap(entries, cap=1, dry_run=True)
        assert len(actions) == 1
        assert actions[0]["id"] == "a2"  # lower score deferred

    def test_no_violation(self):
        entries = [_entry("solo", status="qualified", score=8.0, org="SmallCo")]
        actions = triage_org_cap(entries, cap=1, dry_run=True)
        assert actions == []

    def test_ignores_closed_entries(self):
        entries = [
            _entry("a1", status="qualified", score=9.0, org="BigCo"),
            _entry("a2", status="withdrawn", score=7.0, org="BigCo"),
        ]
        actions = triage_org_cap(entries, cap=1, dry_run=True)
        assert actions == []

    def test_keeps_highest_scored(self):
        entries = [
            _entry("low", status="qualified", score=6.0, org="Corp"),
            _entry("mid", status="staged", score=8.0, org="Corp"),
            _entry("high", status="submitted", score=9.5, org="Corp"),
        ]
        actions = triage_org_cap(entries, cap=1, dry_run=True)
        deferred_ids = {a["id"] for a in actions}
        assert "high" not in deferred_ids
        assert len(deferred_ids) == 2


class TestFormatReport:
    def test_empty_report(self):
        report = format_triage_report([], [])
        assert "all entries meet threshold" in report
        assert "no violations" in report

    def test_with_actions(self):
        staged = [{"id": "x", "score": 7.0, "action": "demote", "applied": False}]
        report = format_triage_report(staged, [])
        assert "x" in report
        assert "DRY-RUN" in report


class TestGenerateTriageData:
    def test_returns_structured_data(self):
        entries = [_entry("test", score=5.0)]
        data = generate_triage_data(entries, min_score=9.0, dry_run=True)
        assert "staged_demotions" in data
        assert "org_cap_deferrals" in data
        assert "summary" in data
        assert data["summary"]["dry_run"] is True
