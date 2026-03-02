"""Tests for scripts/hygiene.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from hygiene import (
    DEFAULT_FOCUS_LIMIT,
    GATE_CHECKS,
    STALE_ROLLING_DAYS,
    check_gate,
    check_stale_rolling,
    run_auto_expire,
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


# --- check_gate: additional cases ---


def test_check_gate_grant_rolling_passes():
    """Grant with rolling deadline passes gate."""
    entry = _make_entry(track="grant", deadline_type="rolling")
    issues = check_gate(entry)
    # Only universal issues, no deadline issue
    deadline_issues = [i for i in issues if "deadline" in i.lower()]
    assert deadline_issues == []


def test_check_gate_residency_requires_deadline():
    """Residency without deadline fails gate."""
    entry = _make_entry(track="residency", deadline_type="hard", deadline_date=None)
    issues = check_gate(entry)
    assert any("deadline" in i.lower() for i in issues)


def test_check_gate_fellowship_requires_deadline():
    """Fellowship without deadline fails gate."""
    entry = _make_entry(track="fellowship", deadline_type="hard", deadline_date=None)
    issues = check_gate(entry)
    assert any("deadline" in i.lower() for i in issues)


def test_check_gate_job_missing_portal():
    """Job without portal type fails gate."""
    entry = _make_entry(track="job")
    entry["target"]["portal"] = ""
    issues = check_gate(entry)
    assert any("portal" in i.lower() for i in issues)


def test_check_gate_job_missing_location():
    """Job without location_class fails gate."""
    entry = _make_entry(track="job")
    entry["target"]["location_class"] = ""
    issues = check_gate(entry)
    assert any("location" in i.lower() for i in issues)


def test_check_gate_unknown_track_universal_only():
    """Unknown track only gets universal gate checks."""
    entry = _make_entry(track="unknown_track", score=7.0, identity_position="educator")
    issues = check_gate(entry)
    assert issues == []


def test_check_gate_missing_fit_dict():
    """Entry with fit as non-dict fails universal gates."""
    entry = _make_entry()
    entry["fit"] = "not a dict"
    issues = check_gate(entry)
    assert any("score" in i.lower() for i in issues)
    assert any("identity_position" in i for i in issues)


# --- check_stale_rolling: additional cases ---


def test_check_stale_rolling_non_rolling_ignored():
    """Non-rolling deadline entries not flagged even if stale."""
    old_date = (date.today() - timedelta(days=STALE_ROLLING_DAYS + 10)).isoformat()
    entry = _make_entry(last_touched=old_date, deadline_type="hard")
    stale = check_stale_rolling([entry])
    assert len(stale) == 0


def test_check_stale_rolling_submitted_ignored():
    """Submitted entries not flagged (not actionable)."""
    old_date = (date.today() - timedelta(days=STALE_ROLLING_DAYS + 10)).isoformat()
    entry = _make_entry(status="submitted", last_touched=old_date)
    stale = check_stale_rolling([entry])
    assert len(stale) == 0


def test_check_stale_rolling_no_last_touched():
    """Entry without last_touched not flagged."""
    entry = _make_entry()
    stale = check_stale_rolling([entry])
    assert len(stale) == 0


def test_check_stale_rolling_returns_correct_fields():
    """Stale result has expected fields."""
    old_date = (date.today() - timedelta(days=STALE_ROLLING_DAYS + 5)).isoformat()
    entry = _make_entry(entry_id="stale-test", last_touched=old_date)
    stale = check_stale_rolling([entry])
    assert len(stale) == 1
    assert stale[0]["id"] == "stale-test"
    assert "days_stale" in stale[0]
    assert "last_touched" in stale[0]
    assert stale[0]["days_stale"] > STALE_ROLLING_DAYS


# --- run_auto_expire ---


def test_run_auto_expire_dry_run(capsys):
    """Dry run reports expired entries but doesn't modify."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    entry = _make_entry(
        entry_id="expired-test",
        status="qualified",
        deadline_date=yesterday,
        deadline_type="hard",
    )
    expired = run_auto_expire([entry], dry_run=True)
    assert len(expired) == 1
    assert expired[0]["id"] == "expired-test"
    out = capsys.readouterr().out
    assert "dry-run" in out.lower() or "Dry run" in out


def test_run_auto_expire_ignores_submitted(capsys):
    """Submitted entries not expired."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    entry = _make_entry(status="submitted", deadline_date=yesterday, deadline_type="hard")
    expired = run_auto_expire([entry], dry_run=True)
    assert len(expired) == 0


def test_run_auto_expire_ignores_rolling(capsys):
    """Rolling deadline entries not expired."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    entry = _make_entry(deadline_date=yesterday, deadline_type="rolling")
    expired = run_auto_expire([entry], dry_run=True)
    assert len(expired) == 0


def test_run_auto_expire_ignores_future_deadline(capsys):
    """Future deadline entries not expired."""
    future = (date.today() + timedelta(days=30)).isoformat()
    entry = _make_entry(deadline_date=future, deadline_type="hard")
    expired = run_auto_expire([entry], dry_run=True)
    assert len(expired) == 0


# --- Constants ---


def test_gate_checks_has_job():
    """GATE_CHECKS includes job track."""
    assert "job" in GATE_CHECKS


def test_gate_checks_has_grant():
    """GATE_CHECKS includes grant track."""
    assert "grant" in GATE_CHECKS


def test_stale_rolling_days_positive():
    """STALE_ROLLING_DAYS is a positive integer."""
    assert isinstance(STALE_ROLLING_DAYS, int)
    assert STALE_ROLLING_DAYS > 0


def test_default_focus_limit():
    """DEFAULT_FOCUS_LIMIT is 3."""
    assert DEFAULT_FOCUS_LIMIT == 3
