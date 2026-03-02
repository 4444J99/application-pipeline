"""Tests for scripts/browser_submit.py — pure logic only.

All Playwright browser-interaction functions require a live browser and
cannot be unit tested. This file covers only the two pure functions:
resolve_portal and find_staged_job_entries.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from browser_submit import find_staged_job_entries, resolve_portal

# --- TestResolvePortal ---


def test_resolve_portal_greenhouse():
    entry = {"target": {"portal": "greenhouse"}}
    assert resolve_portal(entry) == "greenhouse"


def test_resolve_portal_ashby():
    entry = {"target": {"portal": "ashby"}}
    assert resolve_portal(entry) == "ashby"


def test_resolve_portal_lever():
    entry = {"target": {"portal": "lever"}}
    assert resolve_portal(entry) == "lever"


def test_resolve_portal_missing_portal_defaults_to_custom():
    """Missing portal key defaults to 'custom'."""
    entry = {"target": {}}
    assert resolve_portal(entry) == "custom"


def test_resolve_portal_missing_target_defaults_to_custom():
    """Missing target key entirely defaults to 'custom'."""
    entry = {}
    assert resolve_portal(entry) == "custom"


# --- TestFindStagedJobEntries ---


def _make_entry(entry_id, status, track, portal="greenhouse"):
    return {
        "id": entry_id,
        "status": status,
        "track": track,
        "target": {"portal": portal},
    }


def test_find_staged_job_entries_filters_staged(monkeypatch):
    """Only entries with status='staged' are returned."""
    entries = [
        _make_entry("a", "staged", "job"),
        _make_entry("b", "qualified", "job"),
        _make_entry("c", "submitted", "job"),
    ]
    import browser_submit as bs
    monkeypatch.setattr(bs, "load_entries", lambda dirs, include_filepath: entries)
    result = find_staged_job_entries()
    assert len(result) == 1
    assert result[0]["id"] == "a"


def test_find_staged_job_entries_filters_track_job(monkeypatch):
    """Only entries with track='job' are returned."""
    entries = [
        _make_entry("a", "staged", "job"),
        _make_entry("b", "staged", "grant"),
        _make_entry("c", "staged", "residency"),
    ]
    import browser_submit as bs
    monkeypatch.setattr(bs, "load_entries", lambda dirs, include_filepath: entries)
    result = find_staged_job_entries()
    assert len(result) == 1
    assert result[0]["id"] == "a"


def test_find_staged_job_entries_with_portal_filter(monkeypatch):
    """portal_filter restricts by portal type."""
    entries = [
        _make_entry("a", "staged", "job", portal="greenhouse"),
        _make_entry("b", "staged", "job", portal="ashby"),
    ]
    import browser_submit as bs
    monkeypatch.setattr(bs, "load_entries", lambda dirs, include_filepath: entries)
    result = find_staged_job_entries(portal_filter="greenhouse")
    assert len(result) == 1
    assert result[0]["id"] == "a"


def test_find_staged_job_entries_empty_when_no_staged(monkeypatch):
    """No staged entries → empty list."""
    entries = [
        _make_entry("a", "qualified", "job"),
        _make_entry("b", "drafting", "job"),
    ]
    import browser_submit as bs
    monkeypatch.setattr(bs, "load_entries", lambda dirs, include_filepath: entries)
    result = find_staged_job_entries()
    assert result == []


# --- resolve_portal: additional cases ---


def test_resolve_portal_workable():
    entry = {"target": {"portal": "workable"}}
    assert resolve_portal(entry) == "workable"


def test_resolve_portal_custom():
    entry = {"target": {"portal": "custom"}}
    assert resolve_portal(entry) == "custom"


def test_resolve_portal_none_value():
    """portal=None returns None (key exists but value is None)."""
    entry = {"target": {"portal": None}}
    assert resolve_portal(entry) is None


# --- find_staged_job_entries: additional cases ---


def test_find_staged_job_entries_multiple_staged(monkeypatch):
    """Multiple staged job entries all returned."""
    entries = [
        _make_entry("a", "staged", "job"),
        _make_entry("b", "staged", "job"),
        _make_entry("c", "staged", "job"),
    ]
    import browser_submit as bs
    monkeypatch.setattr(bs, "load_entries", lambda dirs, include_filepath: entries)
    result = find_staged_job_entries()
    assert len(result) == 3


def test_find_staged_job_entries_mixed_portals(monkeypatch):
    """Without portal filter, all portal types returned."""
    entries = [
        _make_entry("a", "staged", "job", portal="greenhouse"),
        _make_entry("b", "staged", "job", portal="ashby"),
        _make_entry("c", "staged", "job", portal="lever"),
    ]
    import browser_submit as bs
    monkeypatch.setattr(bs, "load_entries", lambda dirs, include_filepath: entries)
    result = find_staged_job_entries()
    assert len(result) == 3


def test_find_staged_job_entries_portal_filter_no_match(monkeypatch):
    """Portal filter with no matching entries returns empty."""
    entries = [
        _make_entry("a", "staged", "job", portal="greenhouse"),
    ]
    import browser_submit as bs
    monkeypatch.setattr(bs, "load_entries", lambda dirs, include_filepath: entries)
    result = find_staged_job_entries(portal_filter="ashby")
    assert result == []


def test_find_staged_job_entries_empty_pipeline(monkeypatch):
    """Empty pipeline returns empty list."""
    import browser_submit as bs
    monkeypatch.setattr(bs, "load_entries", lambda dirs, include_filepath: [])
    result = find_staged_job_entries()
    assert result == []


# --- _make_entry helper validation ---


def test_make_entry_structure():
    """Helper creates well-formed entries."""
    entry = _make_entry("test-id", "staged", "job", "greenhouse")
    assert entry["id"] == "test-id"
    assert entry["status"] == "staged"
    assert entry["track"] == "job"
    assert entry["target"]["portal"] == "greenhouse"
