"""Tests for scripts/velocity.py pure computation functions."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from velocity import compute_velocity, format_report


# --- Helpers ---

def _make_entry(
    entry_id="test-1",
    status="research",
    track="job",
    effort="quick",
    last_touched=None,
    submitted_date=None,
    qualified_date=None,
    researched_date=None,
    outcome=None,
    deadline_date=None,
    deadline_type="hard",
):
    entry = {
        "id": entry_id,
        "status": status,
        "track": track,
        "submission": {"effort_level": effort},
        "timeline": {},
    }
    if last_touched:
        entry["last_touched"] = last_touched
    if submitted_date:
        entry["timeline"]["submitted"] = submitted_date
    if qualified_date:
        entry["timeline"]["qualified"] = qualified_date
    if researched_date:
        entry["timeline"]["researched"] = researched_date
    if outcome:
        entry["outcome"] = outcome
    if deadline_date:
        entry["deadline"] = {"date": deadline_date, "type": deadline_type}
    return entry


# --- compute_velocity ---

class TestComputeVelocity:
    def test_empty_entries(self):
        metrics = compute_velocity([])
        assert metrics["total_submitted"] == 0
        assert metrics["last_submission"] is None
        assert metrics["days_since_last"] is None
        assert metrics["submitted_last_7d"] == 0
        assert metrics["submitted_last_30d"] == 0

    def test_submission_tracking(self):
        today = date.today()
        entries = [
            _make_entry(submitted_date=(today - timedelta(days=3)).isoformat()),
            _make_entry(entry_id="t2", submitted_date=(today - timedelta(days=20)).isoformat()),
        ]
        metrics = compute_velocity(entries)
        assert metrics["total_submitted"] == 2
        assert metrics["days_since_last"] == 3
        assert metrics["submitted_last_7d"] == 1
        assert metrics["submitted_last_30d"] == 2

    def test_status_distribution(self):
        entries = [
            _make_entry(status="research"),
            _make_entry(entry_id="t2", status="research"),
            _make_entry(entry_id="t3", status="qualified"),
        ]
        metrics = compute_velocity(entries)
        assert metrics["status_distribution"]["research"] == 2
        assert metrics["status_distribution"]["qualified"] == 1

    def test_effort_distribution_actionable_only(self):
        entries = [
            _make_entry(status="qualified", effort="quick"),
            _make_entry(entry_id="t2", status="qualified", effort="deep"),
            _make_entry(entry_id="t3", status="submitted", effort="quick"),  # not actionable
        ]
        metrics = compute_velocity(entries)
        assert metrics["effort_distribution"].get("quick", 0) == 1
        assert metrics["effort_distribution"].get("deep", 0) == 1

    def test_staleness_distribution(self):
        today = date.today()
        entries = [
            _make_entry(status="qualified", last_touched=today.isoformat()),
            _make_entry(entry_id="t2", status="qualified",
                        last_touched=(today - timedelta(days=10)).isoformat()),
            _make_entry(entry_id="t3", status="qualified"),  # never touched
        ]
        metrics = compute_velocity(entries)
        staleness = metrics["staleness_distribution"]
        assert staleness["0-7d"] == 1
        assert staleness["8-14d"] == 1
        assert staleness["never"] == 1

    def test_conversion_funnel(self):
        entries = [
            _make_entry(researched_date="2026-01-01"),
            _make_entry(entry_id="t2", researched_date="2026-01-01",
                        qualified_date="2026-01-05"),
            _make_entry(entry_id="t3", researched_date="2026-01-01",
                        submitted_date="2026-01-10"),
        ]
        metrics = compute_velocity(entries)
        assert metrics["funnel"]["researched"] == 3
        assert metrics["funnel"]["qualified"] == 1
        assert metrics["funnel"]["submitted"] == 1

    def test_outcome_breakdown(self):
        entries = [
            _make_entry(outcome="withdrawn"),
            _make_entry(entry_id="t2", outcome="withdrawn"),
            _make_entry(entry_id="t3", outcome="expired"),
        ]
        metrics = compute_velocity(entries)
        assert metrics["outcomes"]["withdrawn"] == 2
        assert metrics["outcomes"]["expired"] == 1

    def test_track_distribution(self):
        entries = [
            _make_entry(track="job"),
            _make_entry(entry_id="t2", track="grant"),
            _make_entry(entry_id="t3", track="job"),
        ]
        metrics = compute_velocity(entries)
        assert metrics["track_distribution"]["job"] == 2
        assert metrics["track_distribution"]["grant"] == 1

    def test_deadline_pressure(self):
        today = date.today()
        entries = [
            _make_entry(
                status="qualified",
                deadline_date=(today + timedelta(days=5)).isoformat(),
                deadline_type="hard",
            ),
            _make_entry(
                entry_id="t2",
                status="qualified",
                deadline_date=(today + timedelta(days=20)).isoformat(),
                deadline_type="hard",
            ),
            _make_entry(
                entry_id="t3",
                status="qualified",
                deadline_date=(today + timedelta(days=5)).isoformat(),
                deadline_type="rolling",  # not counted
            ),
        ]
        metrics = compute_velocity(entries)
        assert metrics["deadline_pressure"]["this_week"] == 1
        assert metrics["deadline_pressure"]["next_month"] == 1


# --- format_report ---

class TestFormatReport:
    def test_produces_markdown(self):
        metrics = compute_velocity([])
        report = format_report(metrics)
        assert report.startswith("# Pipeline Velocity Report")
        assert "## Submission Velocity" in report

    def test_includes_all_sections(self):
        entries = [
            _make_entry(
                status="qualified",
                last_touched=date.today().isoformat(),
                researched_date="2026-01-01",
            ),
        ]
        metrics = compute_velocity(entries)
        report = format_report(metrics)
        assert "## Status Distribution" in report
        assert "## Effort Distribution" in report
        assert "## Staleness" in report
        assert "## Conversion Funnel" in report
        assert "## Deadline Pressure" in report

    def test_never_submitted_message(self):
        metrics = compute_velocity([])
        report = format_report(metrics)
        assert "**NEVER**" in report

    def test_with_submissions(self):
        today = date.today()
        entries = [
            _make_entry(submitted_date=(today - timedelta(days=2)).isoformat()),
        ]
        metrics = compute_velocity(entries)
        report = format_report(metrics)
        assert "Total submitted: 1" in report
