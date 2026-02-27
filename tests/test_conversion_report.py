"""Tests for scripts/conversion_report.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from conversion_report import analyze_by_dimension


def _make_entry(
    entry_id="test-entry",
    track="job",
    status="research",
    outcome=None,
    score=5.0,
    identity_position="independent-engineer",
):
    """Build a minimal pipeline entry for conversion report tests."""
    entry = {
        "id": entry_id,
        "track": track,
        "status": status,
        "fit": {"score": score, "identity_position": identity_position},
        "conversion": {},
    }
    if outcome:
        entry["outcome"] = outcome
    return entry


# --- analyze_by_dimension ---


def test_analyze_by_dimension_grouping():
    """Groups entries by extract_fn correctly."""
    entries = [
        _make_entry(entry_id="e1", track="job"),
        _make_entry(entry_id="e2", track="grant"),
        _make_entry(entry_id="e3", track="job"),
    ]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    assert "job" in groups
    assert "grant" in groups
    assert groups["job"]["total"] == 2
    assert groups["grant"]["total"] == 1


def test_analyze_by_dimension_counts():
    """Counts submitted/accepted/rejected correctly."""
    entries = [
        _make_entry(entry_id="e1", status="submitted"),
        _make_entry(entry_id="e2", status="outcome", outcome="accepted"),
        _make_entry(entry_id="e3", status="outcome", outcome="rejected"),
        _make_entry(entry_id="e4", status="research"),
    ]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    job = groups["job"]
    assert job["total"] == 4
    assert job["submitted"] == 3  # submitted + 2 outcome
    assert job["accepted"] == 1
    assert job["rejected"] == 1


def test_analyze_by_dimension_none_key():
    """Entries where extract_fn returns None are skipped."""
    entries = [
        _make_entry(entry_id="e1", identity_position="educator"),
        _make_entry(entry_id="e2"),
    ]
    groups = analyze_by_dimension(
        entries, "position",
        lambda e: e.get("fit", {}).get("missing_field"),
    )
    assert groups == {}


def test_analyze_by_dimension_pending():
    """Submitted entries without outcome counted as pending."""
    entries = [
        _make_entry(entry_id="e1", status="submitted"),
        _make_entry(entry_id="e2", status="acknowledged"),
    ]
    groups = analyze_by_dimension(entries, "track", lambda e: e.get("track"))
    assert groups["job"]["pending"] == 2
