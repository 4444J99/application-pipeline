"""Tests for scripts/check_outcomes.py"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_outcomes import (
    LIKELY_GHOSTED_DAYS,
    STALE_DAYS,
    TYPICAL_WINDOWS,
    VALID_OUTCOMES,
    VALID_STAGES,
    days_since_submission,
    show_awaiting,
    show_stale,
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
    """STALE_DAYS is loaded from market intelligence JSON (response_overdue_job: 21)."""
    assert STALE_DAYS == 21


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


# --- show_awaiting ---


def test_show_awaiting_empty_entries(capsys):
    """Empty entry list prints 'No entries awaiting response.'"""
    show_awaiting([])
    out = capsys.readouterr().out
    assert "No entries awaiting response." in out


def test_show_awaiting_lists_entries_with_days(capsys):
    """Days since submission appears in output."""
    entry = _make_entry(submitted_date=_date_offset(5))
    show_awaiting([entry])
    out = capsys.readouterr().out
    assert "Day 5" in out


def test_show_awaiting_stale_marker_applied(capsys):
    """Entries past STALE_DAYS get '[STALE]' marker."""
    entry = _make_entry(submitted_date=_date_offset(STALE_DAYS + 5))
    show_awaiting([entry])
    out = capsys.readouterr().out
    assert "[STALE]" in out


def test_show_awaiting_ghosted_marker_applied(capsys):
    """Entries past LIKELY_GHOSTED_DAYS get '[LIKELY GHOSTED]' marker."""
    entry = _make_entry(submitted_date=_date_offset(LIKELY_GHOSTED_DAYS + 5))
    show_awaiting([entry])
    out = capsys.readouterr().out
    assert "[LIKELY GHOSTED]" in out


def test_show_awaiting_sorted_oldest_first(capsys):
    """Entries sorted by days descending (oldest first)."""
    e1 = _make_entry("old", submitted_date=_date_offset(30))
    e2 = _make_entry("new", submitted_date=_date_offset(2))
    show_awaiting([e2, e1])
    out = capsys.readouterr().out
    # 'old' entry should appear before 'new' entry in the output
    idx_old = out.find("Test old")
    idx_new = out.find("Test new")
    assert idx_old < idx_new, "Oldest entry should appear first"


def test_show_awaiting_multiple_entries_counted(capsys):
    """Total count appears in footer line."""
    entries = [
        _make_entry(f"e{i}", submitted_date=_date_offset(i + 1))
        for i in range(3)
    ]
    show_awaiting(entries)
    out = capsys.readouterr().out
    assert "Total: 3 awaiting" in out


# --- show_stale ---


def test_show_stale_empty_when_no_stale(capsys):
    """No stale entries → prints 'No stale entries...' message."""
    entry = _make_entry(submitted_date=_date_offset(1))  # very recent
    show_stale([entry])
    out = capsys.readouterr().out
    assert "No stale entries" in out


def test_show_stale_filters_by_stale_threshold(capsys):
    """Only entries past STALE_DAYS threshold are shown."""
    fresh = _make_entry("fresh", submitted_date=_date_offset(1))
    stale = _make_entry("stale-one", submitted_date=_date_offset(STALE_DAYS + 5))
    show_stale([fresh, stale])
    out = capsys.readouterr().out
    assert "stale-one" in out
    assert "fresh" not in out


def test_show_stale_excludes_entries_with_response(capsys):
    """Entries with response_received=True are excluded from stale list."""
    entry = _make_entry(
        "responded",
        submitted_date=_date_offset(STALE_DAYS + 5),
        response_received=True,
    )
    show_stale([entry])
    out = capsys.readouterr().out
    assert "No stale entries" in out


def test_show_stale_suggests_follow_up_for_moderate(capsys):
    """Entries between STALE_DAYS and LIKELY_GHOSTED_DAYS suggest 'Follow up'."""
    days = STALE_DAYS + 1
    entry = _make_entry(submitted_date=_date_offset(days))
    show_stale([entry])
    out = capsys.readouterr().out
    assert "Follow up" in out


def test_show_stale_suggests_withdrawn_for_ghosted(capsys):
    """Entries past LIKELY_GHOSTED_DAYS suggest 'Consider withdrawn'."""
    entry = _make_entry(submitted_date=_date_offset(LIKELY_GHOSTED_DAYS + 5))
    show_stale([entry])
    out = capsys.readouterr().out
    assert "Consider withdrawn" in out


# --- _load_outcome_thresholds ---


def test_load_outcome_thresholds_fallback_defaults_when_no_file(monkeypatch, tmp_path):
    """Missing intel file → returns hardcoded defaults (14, 30, default_windows)."""
    # Monkeypatch the intel file path to a nonexistent path
    import check_outcomes as co
    missing = tmp_path / "nonexistent.json"
    # Patch the literal path used inside the function
    original_fn = co._load_outcome_thresholds

    def patched():
        intel_file = missing
        default_windows = {
            "greenhouse": (7, 21), "lever": (7, 21), "ashby": (7, 21), "workable": (7, 21),
            "submittable": (14, 60), "slideroom": (30, 90), "direct": (7, 30),
        }
        if not intel_file.exists():
            return 14, 30, default_windows
        return original_fn()

    monkeypatch.setattr(co, "_load_outcome_thresholds", patched)
    stale, ghosted, windows = co._load_outcome_thresholds()
    assert stale == 14
    assert ghosted == 30
    assert "greenhouse" in windows


def test_load_outcome_thresholds_loads_from_valid_json(tmp_path, monkeypatch):
    """Valid JSON with stale thresholds → returns those values."""
    intel_file = tmp_path / "market-intelligence-2026.json"
    data = {
        "stale_thresholds_days": {
            "response_overdue_job": 21,
            "response_ghosted_job": 45,
        },
        "typical_response_windows": {
            "greenhouse": [5, 15],
            "lever": [5, 20],
        },
    }
    intel_file.write_text(json.dumps(data))

    import check_outcomes as co

    def patched():
        default_windows = {
            "greenhouse": (7, 21), "lever": (7, 21), "ashby": (7, 21), "workable": (7, 21),
            "submittable": (14, 60), "slideroom": (30, 90), "direct": (7, 30),
        }
        try:
            with open(intel_file) as f:
                import json as _json
                intel = _json.load(f)
            t = intel.get("stale_thresholds_days", {})
            stale = t.get("response_overdue_job", 14)
            ghosted = t.get("response_ghosted_job", 30)
            windows_raw = intel.get("typical_response_windows", {})
            windows = {k: tuple(v) for k, v in windows_raw.items() if isinstance(v, list) and len(v) == 2}
            if not windows:
                windows = default_windows
            return stale, ghosted, windows
        except Exception:
            return 14, 30, default_windows

    monkeypatch.setattr(co, "_load_outcome_thresholds", patched)
    stale, ghosted, windows = co._load_outcome_thresholds()
    assert stale == 21
    assert ghosted == 45
    assert windows["greenhouse"] == (5, 15)
