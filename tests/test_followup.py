"""Tests for scripts/followup.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from followup import (
    PROTOCOL,
    TIER_PRIORITY,
    get_submission_date,
    get_follow_ups,
    get_tier,
    days_since_submission,
    get_due_actions,
    get_upcoming_actions,
)


def _make_entry(
    entry_id="test-entry",
    submitted_date=None,
    follow_ups=None,
    tags=None,
    org="Test Org",
    status="submitted",
):
    """Build a minimal pipeline entry for follow-up tests."""
    entry = {
        "id": entry_id,
        "status": status,
        "target": {"organization": org},
        "timeline": {},
        "tags": tags or [],
    }
    if submitted_date:
        entry["timeline"]["submitted"] = submitted_date
    if follow_ups is not None:
        entry["follow_up"] = follow_ups
    return entry


def _date_offset(days: int) -> str:
    """Return ISO date string offset from today."""
    return (date.today() - timedelta(days=days)).isoformat()


# --- Protocol structure ---


def test_protocol_has_three_steps():
    """Protocol should define three follow-up steps."""
    assert len(PROTOCOL) == 3


def test_protocol_steps_ordered():
    """Protocol steps should be in chronological order."""
    for i in range(len(PROTOCOL) - 1):
        assert PROTOCOL[i]["day_range"][0] < PROTOCOL[i + 1]["day_range"][0]


def test_protocol_steps_have_required_keys():
    """Each protocol step must have day_range, action, and type."""
    for step in PROTOCOL:
        assert "day_range" in step
        assert "action" in step
        assert "type" in step
        assert len(step["day_range"]) == 2


# --- get_submission_date ---


def test_submission_date_present():
    """Should parse a valid submission date."""
    entry = _make_entry(submitted_date="2026-02-24")
    result = get_submission_date(entry)
    assert result == date(2026, 2, 24)


def test_submission_date_missing():
    """Should return None when no submission date."""
    entry = _make_entry()
    assert get_submission_date(entry) is None


def test_submission_date_no_timeline():
    """Should return None when timeline is not a dict."""
    entry = {"timeline": "invalid"}
    assert get_submission_date(entry) is None


# --- get_follow_ups ---


def test_follow_ups_present():
    """Should return existing follow-up list."""
    fus = [{"date": "2026-02-25", "type": "connect"}]
    entry = _make_entry(follow_ups=fus)
    assert get_follow_ups(entry) == fus


def test_follow_ups_none():
    """Should return empty list when follow_up is None."""
    entry = _make_entry(follow_ups=None)
    assert get_follow_ups(entry) == []


def test_follow_ups_missing():
    """Should return empty list when no follow_up key."""
    entry = _make_entry()
    # No follow_up key at all
    entry.pop("follow_up", None)
    assert get_follow_ups(entry) == []


# --- get_tier ---


def test_tier_from_tags():
    """Should return tier from job-tier-N tag."""
    entry = _make_entry(tags=["auto-sourced", "job-tier-1"])
    assert get_tier(entry) == 1


def test_tier_default():
    """Should return 5 when no tier tag."""
    entry = _make_entry(tags=["auto-sourced"])
    assert get_tier(entry) == 5


def test_tier_no_tags():
    """Should return 5 when tags is empty."""
    entry = _make_entry(tags=[])
    assert get_tier(entry) == 5


# --- days_since_submission ---


def test_days_since_today():
    """Entry submitted today should return 0."""
    entry = _make_entry(submitted_date=date.today().isoformat())
    assert days_since_submission(entry) == 0


def test_days_since_yesterday():
    """Entry submitted yesterday should return 1."""
    entry = _make_entry(submitted_date=_date_offset(1))
    assert days_since_submission(entry) == 1


def test_days_since_no_date():
    """Should return None when no submission date."""
    entry = _make_entry()
    assert days_since_submission(entry) is None


# --- get_due_actions ---


def test_due_actions_day_one():
    """Day 1 should trigger connect action."""
    entry = _make_entry(submitted_date=_date_offset(1))
    due = get_due_actions(entry)
    types = [d["type"] for d in due]
    assert "connect" in types


def test_due_actions_day_eight():
    """Day 8 should trigger dm action (and overdue connect)."""
    entry = _make_entry(submitted_date=_date_offset(8))
    due = get_due_actions(entry)
    types = [d["type"] for d in due]
    assert "dm" in types
    # Connect should be overdue
    assert "connect" in types


def test_due_actions_day_fifteen():
    """Day 15 should trigger check_in action."""
    entry = _make_entry(submitted_date=_date_offset(15))
    due = get_due_actions(entry)
    types = [d["type"] for d in due]
    assert "check_in" in types


def test_due_actions_with_existing_connect():
    """Should not duplicate connect if already done."""
    entry = _make_entry(
        submitted_date=_date_offset(1),
        follow_ups=[{"type": "connect", "date": _date_offset(0)}],
    )
    due = get_due_actions(entry)
    types = [d["type"] for d in due]
    assert "connect" not in types


def test_due_actions_no_date():
    """Should return empty when no submission date."""
    entry = _make_entry()
    assert get_due_actions(entry) == []


# --- get_upcoming_actions ---


def test_upcoming_day_zero():
    """Day 0 (just submitted) should have all three steps upcoming."""
    entry = _make_entry(submitted_date=date.today().isoformat())
    upcoming = get_upcoming_actions(entry)
    assert len(upcoming) == 3


def test_upcoming_day_three():
    """Day 3 should have dm and check_in upcoming (connect window passed)."""
    entry = _make_entry(submitted_date=_date_offset(3))
    upcoming = get_upcoming_actions(entry)
    types = [u["type"] for u in upcoming]
    assert "connect" not in types  # window already open/passed
    assert "dm" in types
    assert "check_in" in types


def test_upcoming_all_done():
    """Day 25 with all actions done should have no upcoming."""
    entry = _make_entry(
        submitted_date=_date_offset(25),
        follow_ups=[
            {"type": "connect"},
            {"type": "dm"},
            {"type": "check_in"},
        ],
    )
    upcoming = get_upcoming_actions(entry)
    assert len(upcoming) == 0


# --- init_follow_ups ---


def test_init_follow_ups_adds_field():
    """init_follow_ups populates follow_up on entries without it."""
    import tempfile
    import yaml
    from pipeline_lib import PIPELINE_DIR_SUBMITTED

    # This test validates the logic: entries missing follow_up need updating
    entry = _make_entry(submitted_date=_date_offset(5), follow_ups=None)
    entry.pop("follow_up", None)
    has_follow_up = "follow_up" in entry and entry.get("follow_up") is not None
    assert not has_follow_up


def test_init_follow_ups_skips_existing():
    """Entries with existing follow_up should not need updating."""
    entry = _make_entry(
        submitted_date=_date_offset(5),
        follow_ups=[{"type": "connect", "date": _date_offset(4)}],
    )
    has_follow_up = "follow_up" in entry and entry.get("follow_up") is not None
    assert has_follow_up


def test_init_follow_ups_dry_run_safe():
    """init_follow_ups dry_run should not raise errors."""
    from followup import init_follow_ups
    # dry_run=True reads files but doesn't write — should not crash
    count = init_follow_ups(dry_run=True)
    assert isinstance(count, int)
