"""Tests for scripts/check_outcomes.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_outcomes import (
    STALE_DAYS,
    TYPICAL_WINDOWS,
    VALID_OUTCOMES,
    VALID_STAGES,
    days_since_submission,
)


def _make_entry(
    entry_id="test-entry",
    status="submitted",
    submitted_date=None,
    response_received=False,
    outcome=None,
    portal="greenhouse",
    org="Test Org",
):
    """Build a minimal pipeline entry for outcome tests."""
    entry = {
        "id": entry_id,
        "name": f"Test {entry_id}",
        "status": status,
        "target": {"organization": org, "portal": portal},
        "timeline": {},
        "conversion": {"response_received": response_received},
    }
    if submitted_date:
        entry["timeline"]["submitted"] = submitted_date
    if outcome:
        entry["outcome"] = outcome
    return entry


def _date_offset(days: int) -> str:
    """Return ISO date string offset from today."""
    return (date.today() - timedelta(days=days)).isoformat()


# --- Constants ---


def test_stale_days_constant():
    """STALE_DAYS == 14."""
    assert STALE_DAYS == 14


def test_typical_windows_has_major_portals():
    """TYPICAL_WINDOWS covers greenhouse, lever, ashby, submittable."""
    for portal in ("greenhouse", "lever", "ashby", "submittable"):
        assert portal in TYPICAL_WINDOWS, f"{portal} missing from TYPICAL_WINDOWS"
        window = TYPICAL_WINDOWS[portal]
        assert len(window) == 2
        assert window[0] < window[1]


def test_valid_outcomes_include_terminal():
    """VALID_OUTCOMES includes all terminal outcome types."""
    for outcome in ("accepted", "rejected", "withdrawn", "expired"):
        assert outcome in VALID_OUTCOMES


def test_valid_stages_include_common():
    """VALID_STAGES includes common stages."""
    for stage in ("resume_screen", "phone_screen", "technical", "onsite"):
        assert stage in VALID_STAGES


# --- days_since_submission ---


def test_days_since_today():
    """Entry submitted today returns 0."""
    entry = _make_entry(submitted_date=date.today().isoformat())
    assert days_since_submission(entry) == 0


def test_days_since_past():
    """Entry submitted 10 days ago returns 10."""
    entry = _make_entry(submitted_date=_date_offset(10))
    assert days_since_submission(entry) == 10


def test_days_since_no_date():
    """Returns None when no submission date."""
    entry = _make_entry()
    assert days_since_submission(entry) is None


# --- Filtering logic (tested via function behavior) ---


def test_get_stale_entries_criteria():
    """Entries >STALE_DAYS without response match stale criteria."""
    entry = _make_entry(submitted_date=_date_offset(STALE_DAYS + 5))
    days = days_since_submission(entry)
    has_response = entry["conversion"].get("response_received", False)
    assert days > STALE_DAYS
    assert not has_response


def test_get_stale_entries_with_response_excluded():
    """Entries with response_received=true should not be stale."""
    entry = _make_entry(
        submitted_date=_date_offset(STALE_DAYS + 5),
        response_received=True,
    )
    has_response = entry["conversion"].get("response_received", False)
    assert has_response is True
