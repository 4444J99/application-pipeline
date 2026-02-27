"""Tests for scripts/hygiene.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from hygiene import (
    STALE_ROLLING_DAYS,
    check_gate,
    check_stale_rolling,
)


def _make_entry(
    entry_id="test-entry",
    track="job",
    status="qualified",
    application_url="https://example.com/apply",
    portal="greenhouse",
    location_class="us-remote",
    score=7.0,
    identity_position="independent-engineer",
    deadline_date=None,
    deadline_type="rolling",
    last_touched=None,
):
    """Build a minimal pipeline entry for hygiene tests."""
    entry = {
        "id": entry_id,
        "name": f"Test {entry_id}",
        "track": track,
        "status": status,
        "target": {
            "application_url": application_url,
            "portal": portal,
            "location_class": location_class,
        },
        "fit": {
            "score": score,
            "identity_position": identity_position,
        },
        "deadline": {
            "date": deadline_date,
            "type": deadline_type,
        },
    }
    if last_touched:
        entry["last_touched"] = last_touched
    return entry


# --- check_gate ---


def test_check_gate_job_requires_url():
    """Job without application_url fails gate."""
    entry = _make_entry(track="job", application_url="")
    issues = check_gate(entry)
    assert any("application URL" in i for i in issues)


def test_check_gate_grant_requires_deadline():
    """Grant without deadline.date (non-rolling) fails gate."""
    entry = _make_entry(track="grant", deadline_type="hard", deadline_date=None)
    # Grants don't require application_url but do need deadline
    issues = check_gate(entry)
    assert any("deadline" in i.lower() for i in issues)


def test_check_gate_valid_entry_passes():
    """Well-formed job entry passes all gates."""
    entry = _make_entry()
    issues = check_gate(entry)
    assert issues == []


def test_check_gate_missing_score_fails():
    """Entry without fit score fails universal gate."""
    entry = _make_entry(score=0)
    issues = check_gate(entry)
    assert any("score" in i.lower() for i in issues)


def test_check_gate_missing_identity_fails():
    """Entry without identity_position fails universal gate."""
    entry = _make_entry(identity_position="")
    issues = check_gate(entry)
    assert any("identity_position" in i for i in issues)


# --- check_stale_rolling ---


def test_check_stale_rolling():
    """Entry with rolling deadline + old last_touched flagged."""
    old_date = (date.today() - timedelta(days=STALE_ROLLING_DAYS + 10)).isoformat()
    entry = _make_entry(last_touched=old_date)
    stale = check_stale_rolling([entry])
    assert len(stale) == 1
    assert stale[0]["id"] == "test-entry"


def test_check_stale_rolling_recent():
    """Recent rolling entry not flagged."""
    recent = (date.today() - timedelta(days=5)).isoformat()
    entry = _make_entry(last_touched=recent)
    stale = check_stale_rolling([entry])
    assert len(stale) == 0
