"""Tests for scripts/campaign.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from campaign import classify_urgency, get_campaign_entries, detect_gaps, is_effort_feasible


def _make_entry(
    entry_id="test",
    name="Test Entry",
    status="staged",
    track="grant",
    deadline_date=None,
    deadline_type="hard",
    materials=None,
    variant_ids=None,
    portal_fields=None,
):
    """Build a minimal pipeline entry dict for testing."""
    entry = {
        "id": entry_id,
        "name": name,
        "status": status,
        "track": track,
        "deadline": {
            "date": deadline_date,
            "type": deadline_type,
        },
        "submission": {
            "effort_level": "standard",
            "materials_attached": materials or [],
            "variant_ids": variant_ids or {},
        },
    }
    if portal_fields is not None:
        entry["portal_fields"] = portal_fields
    return entry


def _date_offset(days: int) -> str:
    """Return an ISO date string offset from today."""
    return (date.today() + timedelta(days=days)).isoformat()


# --- classify_urgency ---


def test_urgency_critical_expired():
    entry = _make_entry(deadline_date=_date_offset(-2))
    assert classify_urgency(entry) == "critical"


def test_urgency_critical_imminent():
    entry = _make_entry(deadline_date=_date_offset(1))
    assert classify_urgency(entry) == "critical"


def test_urgency_critical_boundary():
    entry = _make_entry(deadline_date=_date_offset(3))
    assert classify_urgency(entry) == "critical"


def test_urgency_urgent():
    entry = _make_entry(deadline_date=_date_offset(5))
    assert classify_urgency(entry) == "urgent"


def test_urgency_urgent_boundary():
    entry = _make_entry(deadline_date=_date_offset(7))
    assert classify_urgency(entry) == "urgent"


def test_urgency_upcoming():
    entry = _make_entry(deadline_date=_date_offset(10))
    assert classify_urgency(entry) == "upcoming"


def test_urgency_upcoming_boundary():
    entry = _make_entry(deadline_date=_date_offset(14))
    assert classify_urgency(entry) == "upcoming"


def test_urgency_ready_far():
    entry = _make_entry(deadline_date=_date_offset(30))
    assert classify_urgency(entry) == "ready"


def test_urgency_ready_rolling():
    entry = _make_entry(deadline_date=None, deadline_type="rolling")
    assert classify_urgency(entry) == "ready"


# --- get_campaign_entries ---


def test_campaign_entries_filters_by_deadline():
    entries = [
        _make_entry(entry_id="soon", deadline_date=_date_offset(5), status="staged"),
        _make_entry(entry_id="far", deadline_date=_date_offset(60), status="staged"),
    ]
    result = get_campaign_entries(entries, days_ahead=14)
    ids = [e["id"] for e in result]
    assert "soon" in ids
    assert "far" not in ids


def test_campaign_entries_includes_staged_rolling():
    entries = [
        _make_entry(
            entry_id="rolling-one",
            deadline_date=None,
            deadline_type="rolling",
            status="staged",
        ),
    ]
    result = get_campaign_entries(entries, days_ahead=14)
    ids = [e["id"] for e in result]
    assert "rolling-one" in ids


def test_campaign_entries_sorted_by_deadline():
    entries = [
        _make_entry(entry_id="later", deadline_date=_date_offset(10), status="staged"),
        _make_entry(entry_id="sooner", deadline_date=_date_offset(3), status="staged"),
    ]
    result = get_campaign_entries(entries, days_ahead=14)
    assert result[0]["id"] == "sooner"
    assert result[1]["id"] == "later"


def test_campaign_entries_excludes_submitted():
    entries = [
        _make_entry(entry_id="done", deadline_date=_date_offset(5), status="submitted"),
        _make_entry(entry_id="active", deadline_date=_date_offset(5), status="staged"),
    ]
    result = get_campaign_entries(entries, days_ahead=14)
    ids = [e["id"] for e in result]
    assert "done" not in ids
    assert "active" in ids


def test_campaign_entries_excludes_research():
    entries = [
        _make_entry(entry_id="early", deadline_date=_date_offset(5), status="research"),
    ]
    result = get_campaign_entries(entries, days_ahead=14)
    assert len(result) == 0


def test_campaign_entries_excludes_long_expired():
    entries = [
        _make_entry(entry_id="old", deadline_date=_date_offset(-10), status="staged"),
    ]
    result = get_campaign_entries(entries, days_ahead=14)
    assert len(result) == 0


def test_campaign_entries_includes_recently_expired():
    entries = [
        _make_entry(entry_id="recent", deadline_date=_date_offset(-3), status="staged"),
    ]
    result = get_campaign_entries(entries, days_ahead=14)
    ids = [e["id"] for e in result]
    assert "recent" in ids


def test_campaign_entries_includes_qualified():
    entries = [
        _make_entry(entry_id="qual", deadline_date=_date_offset(5), status="qualified"),
    ]
    result = get_campaign_entries(entries, days_ahead=14)
    ids = [e["id"] for e in result]
    assert "qual" in ids


# --- detect_gaps (from enrich, tested for campaign context) ---


def test_detect_gaps_materials():
    entry = _make_entry(track="grant", materials=[])
    gaps = detect_gaps(entry)
    assert "materials" in gaps


def test_detect_gaps_no_materials_gap_when_populated():
    entry = _make_entry(track="grant", materials=["resumes/multimedia-specialist.pdf"])
    gaps = detect_gaps(entry)
    assert "materials" not in gaps


def test_detect_gaps_portal_requires_profile():
    """Portal gap only detected if profile exists with submission_format."""
    entry = _make_entry(entry_id="nonexistent-profile-xyz")
    gaps = detect_gaps(entry)
    # No profile → no portal_fields gap flagged
    assert "portal_fields" not in gaps


# --- is_effort_feasible ---


def _make_effort_entry(deadline_days, effort_level="standard", deadline_type="hard"):
    """Build an entry for effort-feasibility testing."""
    entry = _make_entry(
        deadline_date=_date_offset(deadline_days) if deadline_days is not None else None,
        deadline_type=deadline_type,
    )
    entry["submission"]["effort_level"] = effort_level
    return entry


def test_feasible_quick_with_time():
    """Quick effort (30 min) with 3 days left is feasible."""
    entry = _make_effort_entry(3, "quick")
    assert is_effort_feasible(entry) is True


def test_infeasible_complex_tight_deadline():
    """Complex effort (720 min / 12h) with 1 day left (360 min available) is infeasible."""
    entry = _make_effort_entry(1, "complex")
    assert is_effort_feasible(entry) is False


def test_feasible_complex_plenty_of_time():
    """Complex effort (720 min) with 7 days left (2520 min available) is feasible."""
    entry = _make_effort_entry(7, "complex")
    assert is_effort_feasible(entry) is True


def test_infeasible_deep_zero_days():
    """Deep effort (270 min) due today (0 days, 0 min available) is infeasible."""
    entry = _make_effort_entry(0, "deep")
    assert is_effort_feasible(entry) is False


def test_infeasible_expired():
    """Expired deadline is always infeasible."""
    entry = _make_effort_entry(-2, "quick")
    assert is_effort_feasible(entry) is False


def test_feasible_rolling():
    """Rolling deadline is always feasible."""
    entry = _make_effort_entry(None, "complex", deadline_type="rolling")
    assert is_effort_feasible(entry) is True


def test_feasible_standard_one_day():
    """Standard effort (90 min) with 1 day (360 min) is feasible."""
    entry = _make_effort_entry(1, "standard")
    assert is_effort_feasible(entry) is True
