"""Tests for scripts/archive_research.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_RESEARCH_POOL,
    load_entries,
)


def test_research_pool_dir_exists():
    """The research_pool directory must exist."""
    assert PIPELINE_DIR_RESEARCH_POOL.exists(), (
        "pipeline/research_pool/ does not exist — create it or run archive_research.py"
    )


def test_get_research_entries_only_research():
    """get_research_entries should only return entries with status=research."""
    from archive_research import get_research_entries

    entries = get_research_entries()
    for e in entries:
        assert e.get("status") == "research", (
            f"Non-research entry returned: {e.get('id')} has status={e.get('status')}"
        )


def test_get_research_entries_only_from_active():
    """get_research_entries should only scan active/ directory."""
    from archive_research import get_research_entries

    entries = get_research_entries()
    for e in entries:
        assert e.get("_dir") == "active", (
            f"Entry from wrong dir: {e.get('id')} in {e.get('_dir')}"
        )


def test_report_does_not_crash():
    """report() should run without errors even if there are no research entries."""
    from archive_research import report

    entries = []
    report(entries)  # Should not raise


def test_restore_nonexistent_returns_false():
    """Restoring a nonexistent entry should return False."""
    from archive_research import restore

    result = restore("definitely-nonexistent-entry-xyz-999")
    assert result is False


def test_pool_entries_have_research_status():
    """All entries in research_pool/ should have status=research."""
    pool_entries = load_entries(dirs=[PIPELINE_DIR_RESEARCH_POOL])
    for e in pool_entries:
        assert e.get("status") == "research", (
            f"Pool entry {e.get('id')} has status={e.get('status')} (expected research)"
        )


def test_active_has_no_research_after_archive():
    """After archival, active/ should have few or no research entries.

    This test validates that either:
    1. archive_research.py has been run (0 research entries in active/), or
    2. it hasn't been run yet (>0 research entries in active/)

    It does NOT fail — it documents the current state.
    """
    active_entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    research_in_active = [e for e in active_entries if e.get("status") == "research"]
    non_research_in_active = len(active_entries) - len(research_in_active)

    # If pool has entries, active should be mostly clean
    pool_entries = load_entries(dirs=[PIPELINE_DIR_RESEARCH_POOL])
    if pool_entries:
        assert len(research_in_active) <= 5, (
            f"research_pool/ has {len(pool_entries)} entries but active/ has "
            f"{len(research_in_active)} research entries — consider running "
            f"archive_research.py --yes"
        )
        if research_in_active:
            import warnings
            warnings.warn(
                f"{len(research_in_active)} research entries in active/ "
                f"(may be intentionally kept for active work)"
            )
