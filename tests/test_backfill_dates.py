"""Tests for scripts/backfill_dates.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from backfill_dates import backfill_entry, classify_freshness, find_backfill_candidates

# ---------------------------------------------------------------------------
# classify_freshness
# ---------------------------------------------------------------------------


def test_classify_freshness_unknown():
    assert classify_freshness(None) == "unknown"


def test_classify_freshness_fresh():
    assert classify_freshness(0) == "fresh (<=7d)"
    assert classify_freshness(7) == "fresh (<=7d)"


def test_classify_freshness_recent():
    assert classify_freshness(8) == "recent (8-30d)"
    assert classify_freshness(30) == "recent (8-30d)"


def test_classify_freshness_aging():
    assert classify_freshness(31) == "aging (31-90d)"
    assert classify_freshness(90) == "aging (31-90d)"


def test_classify_freshness_stale():
    assert classify_freshness(91) == "stale (>90d)"
    assert classify_freshness(365) == "stale (>90d)"


# ---------------------------------------------------------------------------
# find_backfill_candidates
# ---------------------------------------------------------------------------


def test_find_candidates_with_researched_no_dates():
    """Entry with researched but no posting_date/date_added is a candidate."""
    entries = [
        {"id": "needs-backfill", "timeline": {"researched": "2026-01-15"}},
    ]
    result = find_backfill_candidates(entries)
    assert len(result) == 1
    assert result[0]["id"] == "needs-backfill"


def test_find_candidates_skips_existing_posting_date():
    """Entry with posting_date is not a candidate."""
    entries = [
        {"id": "has-posting", "timeline": {"researched": "2026-01-15", "posting_date": "2026-01-10"}},
    ]
    result = find_backfill_candidates(entries)
    assert len(result) == 0


def test_find_candidates_skips_existing_date_added():
    """Entry with date_added is not a candidate."""
    entries = [
        {"id": "has-added", "timeline": {"researched": "2026-01-15", "date_added": "2026-01-15"}},
    ]
    result = find_backfill_candidates(entries)
    assert len(result) == 0


def test_find_candidates_skips_no_researched():
    """Entry without researched date is not a candidate."""
    entries = [
        {"id": "no-timeline", "timeline": {}},
        {"id": "no-researched", "timeline": {"notes": "some note"}},
    ]
    result = find_backfill_candidates(entries)
    assert len(result) == 0


def test_find_candidates_skips_no_timeline():
    """Entry without timeline section is not a candidate."""
    entries = [{"id": "empty"}]
    result = find_backfill_candidates(entries)
    assert len(result) == 0


# ---------------------------------------------------------------------------
# backfill_entry
# ---------------------------------------------------------------------------


def test_backfill_entry_dry_run(tmp_path):
    """Dry run returns True but does not modify the file."""
    yaml_content = """id: test-entry
timeline:
    researched: 2026-01-15
    posting_date: null
status: research
"""
    filepath = tmp_path / "test-entry.yaml"
    filepath.write_text(yaml_content)
    original = filepath.read_text()

    result = backfill_entry(filepath, dry_run=True)
    assert result is True
    assert filepath.read_text() == original


def test_backfill_entry_writes_date_added(tmp_path):
    """Execution mode inserts date_added into the timeline block."""
    yaml_content = """id: test-entry
timeline:
    researched: 2026-01-15
status: research
"""
    filepath = tmp_path / "test-entry.yaml"
    filepath.write_text(yaml_content)

    result = backfill_entry(filepath, dry_run=False)
    assert result is True

    updated = filepath.read_text()
    assert "date_added: 2026-01-15" in updated
