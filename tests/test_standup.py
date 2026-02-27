"""Tests for scripts/standup.py pure computation functions."""

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from standup import (
    section_health,
    section_stale,
    section_plan,
    section_replenish,
    section_deferred,
    section_followup,
    section_jobs,
    section_opportunities,
    SECTIONS,
    STAGNATION_DAYS,
    URGENCY_DAYS,
    AT_RISK_DAYS,
    REPLENISH_THRESHOLD,
)


# --- Helpers ---

def _make_entry(
    entry_id="test-1",
    name="Test Entry",
    status="research",
    track="job",
    score=5.0,
    effort="quick",
    last_touched=None,
    deadline_date=None,
    deadline_type="hard",
    submitted_date=None,
    organization="Test Org",
):
    """Create a minimal pipeline entry dict for testing."""
    entry = {
        "id": entry_id,
        "name": name,
        "status": status,
        "track": track,
        "fit": {"score": score},
        "submission": {"effort_level": effort},
        "target": {"organization": organization},
        "timeline": {},
    }
    if last_touched:
        entry["last_touched"] = last_touched
    if deadline_date:
        entry["deadline"] = {"date": deadline_date, "type": deadline_type}
    if submitted_date:
        entry["timeline"]["submitted"] = submitted_date
    return entry


# --- section_health ---

class TestSectionHealth:
    def test_empty_entries(self, capsys):
        result = section_health([])
        assert result["total"] == 0
        assert result["actionable"] == 0
        assert result["submitted"] == 0
        assert result["days_since_last_submission"] is None

    def test_counts_by_status(self, capsys):
        entries = [
            _make_entry(status="research"),
            _make_entry(status="research"),
            _make_entry(status="qualified"),
            _make_entry(status="submitted"),
        ]
        result = section_health(entries)
        assert result["total"] == 4
        assert result["actionable"] == 3  # research + qualified
        assert result["submitted"] == 1

    def test_last_submission_date(self, capsys):
        today = date.today()
        entries = [
            _make_entry(submitted_date=(today - timedelta(days=5)).isoformat()),
            _make_entry(submitted_date=(today - timedelta(days=10)).isoformat()),
        ]
        result = section_health(entries)
        assert result["days_since_last_submission"] == 5
        assert result["submitted"] == 0  # status is still "research"

    def test_submitted_status_counts_as_submitted(self, capsys):
        entries = [
            _make_entry(status="submitted"),
            _make_entry(status="acknowledged"),
            _make_entry(status="interview"),
            _make_entry(status="research"),
        ]
        result = section_health(entries)
        assert result["submitted"] == 3

    def test_prints_header(self, capsys):
        section_health([_make_entry()])
        captured = capsys.readouterr()
        assert "PIPELINE HEALTH" in captured.out


# --- section_stale ---

class TestSectionStale:
    def test_no_stale_entries(self, capsys):
        today = date.today()
        entries = [
            _make_entry(
                status="qualified",
                last_touched=today.isoformat(),
            ),
        ]
        result = section_stale(entries)
        assert result["expired"] == 0
        assert result["at_risk"] == 0
        assert result["stagnant"] == 0

    def test_stagnant_entry(self, capsys):
        old_date = (date.today() - timedelta(days=STAGNATION_DAYS + 3)).isoformat()
        entries = [
            _make_entry(status="qualified", last_touched=old_date),
        ]
        result = section_stale(entries)
        assert result["stagnant"] == 1

    def test_expired_entry(self, capsys):
        past_deadline = (date.today() - timedelta(days=5)).isoformat()
        entries = [
            _make_entry(
                status="drafting",
                deadline_date=past_deadline,
                deadline_type="hard",
            ),
        ]
        result = section_stale(entries)
        assert result["expired"] == 1

    def test_at_risk_entry(self, capsys):
        soon = (date.today() + timedelta(days=AT_RISK_DAYS - 1)).isoformat()
        entries = [
            _make_entry(
                status="qualified",
                deadline_date=soon,
                deadline_type="hard",
            ),
        ]
        result = section_stale(entries)
        assert result["at_risk"] == 1

    def test_submitted_not_flagged_stagnant(self, capsys):
        old_date = (date.today() - timedelta(days=30)).isoformat()
        entries = [
            _make_entry(status="submitted", last_touched=old_date),
        ]
        result = section_stale(entries)
        assert result["stagnant"] == 0

    def test_submitted_not_flagged_expired(self, capsys):
        past_deadline = (date.today() - timedelta(days=5)).isoformat()
        entries = [
            _make_entry(
                status="submitted",
                deadline_date=past_deadline,
                deadline_type="hard",
            ),
        ]
        result = section_stale(entries)
        assert result["expired"] == 0


# --- section_plan ---

class TestSectionPlan:
    def test_empty_entries(self, capsys):
        result = section_plan([], 3.0)
        assert result["planned"] == 0
        assert result["used_minutes"] == 0

    def test_plans_within_budget(self, capsys):
        entries = [
            _make_entry(status="qualified", effort="quick", score=8.0),
            _make_entry(entry_id="test-2", status="qualified", effort="quick", score=6.0),
        ]
        result = section_plan(entries, 3.0)
        assert result["planned"] >= 1

    def test_urgent_entries_prioritized(self, capsys):
        soon = (date.today() + timedelta(days=5)).isoformat()
        entries = [
            _make_entry(
                entry_id="urgent-1",
                name="Urgent Entry",
                status="qualified",
                deadline_date=soon,
                deadline_type="hard",
                score=3.0,
            ),
            _make_entry(
                entry_id="scored-1",
                name="High Score",
                status="qualified",
                score=9.0,
            ),
        ]
        result = section_plan(entries, 3.0)
        captured = capsys.readouterr()
        assert "URGENT" in captured.out

    def test_expired_excluded_from_plan(self, capsys):
        past = (date.today() - timedelta(days=5)).isoformat()
        entries = [
            _make_entry(
                status="qualified",
                deadline_date=past,
                deadline_type="hard",
            ),
        ]
        result = section_plan(entries, 3.0)
        # Expired entries should not be planned
        assert result["planned"] == 0


# --- section_replenish ---

class TestSectionReplenish:
    def test_below_threshold(self, capsys):
        entries = [
            _make_entry(status="qualified"),
        ]
        section_replenish(entries)
        captured = capsys.readouterr()
        assert "Below threshold" in captured.out

    def test_above_threshold(self, capsys):
        entries = [
            _make_entry(entry_id=f"e-{i}", status="qualified")
            for i in range(REPLENISH_THRESHOLD + 1)
        ]
        section_replenish(entries)
        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_track_diversity(self, capsys):
        entries = [
            _make_entry(entry_id="j1", status="qualified", track="job"),
            _make_entry(entry_id="g1", status="qualified", track="grant"),
        ]
        section_replenish(entries)
        captured = capsys.readouterr()
        assert "job" in captured.out
        assert "grant" in captured.out

    def test_excludes_expired(self, capsys):
        past = (date.today() - timedelta(days=5)).isoformat()
        entries = [
            _make_entry(
                status="qualified",
                deadline_date=past,
                deadline_type="hard",
            ),
        ]
        section_replenish(entries)
        captured = capsys.readouterr()
        assert "Live actionable entries: 0" in captured.out


# --- section_deferred ---

class TestSectionDeferred:
    def test_no_deferred(self, capsys):
        entries = [_make_entry(status="research")]
        section_deferred(entries)
        captured = capsys.readouterr()
        assert "No deferred entries" in captured.out

    def test_deferred_with_resume_date(self, capsys):
        future = (date.today() + timedelta(days=10)).isoformat()
        entries = [{
            "id": "def-1",
            "name": "Deferred Thing",
            "status": "deferred",
            "deferral": {
                "reason": "portal_closed",
                "resume_date": future,
                "note": "Opens in March",
            },
        }]
        section_deferred(entries)
        captured = capsys.readouterr()
        assert "Deferred Thing" in captured.out
        assert "portal_closed" in captured.out
        assert "resumes in" in captured.out

    def test_deferred_past_resume_date(self, capsys):
        past = (date.today() - timedelta(days=3)).isoformat()
        entries = [{
            "id": "def-2",
            "name": "Overdue Deferred",
            "status": "deferred",
            "deferral": {
                "reason": "cycle_not_open",
                "resume_date": past,
            },
        }]
        section_deferred(entries)
        captured = capsys.readouterr()
        assert "PAST RESUME DATE" in captured.out


# --- section_jobs ---

class TestSectionJobs:
    def test_no_jobs(self, capsys):
        entries = [_make_entry(track="grant")]
        section_jobs(entries)
        captured = capsys.readouterr()
        assert "No job-track entries" in captured.out

    def test_job_entries_shown(self, capsys):
        entries = [
            _make_entry(entry_id="j1", name="Dev Role", status="qualified", track="job", score=7.5),
            _make_entry(entry_id="j2", name="PM Role", status="submitted", track="job", score=6.0),
        ]
        section_jobs(entries)
        captured = capsys.readouterr()
        assert "JOB PIPELINE" in captured.out
        assert "Dev Role" in captured.out
        assert "Total job entries: 2" in captured.out


# --- section_opportunities ---

# --- section_followup ---

class TestSectionFollowup:
    def test_section_followup_exists(self):
        """'followup' is in SECTIONS dict."""
        assert "followup" in SECTIONS

    def test_section_followup_runs(self, capsys):
        """section_followup([]) doesn't crash."""
        section_followup([])
        captured = capsys.readouterr()
        assert "FOLLOW-UP DASHBOARD" in captured.out

    def test_section_followup_shows_overdue(self, capsys):
        """Entry with overdue follow-up appears in output."""
        old_date = (date.today() - timedelta(days=25)).isoformat()
        entries = [
            _make_entry(
                entry_id="fu-1",
                name="Overdue Entry",
                status="submitted",
                submitted_date=old_date,
            ),
        ]
        section_followup(entries)
        captured = capsys.readouterr()
        assert "OVERDUE" in captured.out


# --- section_opportunities ---

class TestSectionOpportunities:
    def test_no_opportunities(self, capsys):
        entries = [_make_entry(track="job", status="qualified")]
        section_opportunities(entries)
        captured = capsys.readouterr()
        assert "No actionable non-job entries" in captured.out

    def test_shows_grants(self, capsys):
        entries = [
            _make_entry(entry_id="g1", name="Art Grant", status="qualified", track="grant", score=8.0),
        ]
        section_opportunities(entries)
        captured = capsys.readouterr()
        assert "OPPORTUNITY PIPELINE" in captured.out
        assert "Art Grant" in captured.out
