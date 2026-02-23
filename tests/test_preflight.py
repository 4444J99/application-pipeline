"""Tests for scripts/preflight.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from preflight import check_entry


# --- Helpers ---


def _make_entry(**overrides) -> dict:
    """Create a test pipeline entry with sensible defaults."""
    future = (date.today() + timedelta(days=30)).isoformat()
    base = {
        "id": "test-entry",
        "name": "Test Entry",
        "track": "grant",
        "status": "staged",
        "target": {
            "organization": "Test Org",
            "application_url": "https://example.com/apply",
        },
        "deadline": {"date": future, "type": "hard"},
        "submission": {
            "effort_level": "quick",
            "blocks_used": {},
            "variant_ids": {},
            "materials_attached": [],
            "portfolio_url": "https://example.com/portfolio",
        },
    }
    base.update(overrides)
    return base


# --- check_entry ---


def test_check_entry_no_profile():
    """Flags when no profile exists for the entry."""
    entry = _make_entry(id="definitely-nonexistent-xyz")
    issues = check_entry(entry)
    assert any("no profile" in i for i in issues)


def test_check_entry_missing_portfolio_url():
    """Flags when portfolio_url is missing."""
    entry = _make_entry()
    entry["submission"]["portfolio_url"] = ""
    issues = check_entry(entry)
    assert any("portfolio_url" in i for i in issues)


def test_check_entry_missing_application_url():
    """Flags when application_url is missing."""
    entry = _make_entry()
    entry["target"]["application_url"] = ""
    issues = check_entry(entry)
    assert any("application_url" in i for i in issues)


def test_check_entry_expired_deadline():
    """Flags when deadline has passed."""
    past = (date.today() - timedelta(days=5)).isoformat()
    entry = _make_entry()
    entry["deadline"] = {"date": past, "type": "hard"}
    issues = check_entry(entry)
    assert any("expired" in i for i in issues)


def test_check_entry_rolling_deadline_ok():
    """Rolling deadline doesn't flag as expired."""
    entry = _make_entry()
    entry["deadline"] = {"date": None, "type": "rolling"}
    issues = check_entry(entry)
    assert not any("expired" in i for i in issues)


def test_check_entry_material_not_found():
    """Flags when a referenced material file doesn't exist."""
    entry = _make_entry()
    entry["submission"]["materials_attached"] = ["nonexistent/file.pdf"]
    issues = check_entry(entry)
    assert any("material not found" in i for i in issues)


def test_check_entry_real_artadia():
    """Integration test with real artadia-nyc entry (if available)."""
    from pipeline_lib import load_entry_by_id
    _, entry = load_entry_by_id("artadia-nyc")
    if entry is None:
        return  # skip if not available
    issues = check_entry(entry)
    # We expect artadia to have a profile and most fields — may still have issues
    assert not any("no profile" in i for i in issues)


def test_check_entry_mapped_profile():
    """Entries with profile ID mapping should find their profiles."""
    from pipeline_lib import load_entry_by_id
    _, entry = load_entry_by_id("creative-capital-2027")
    if entry is None:
        return  # skip if not available
    issues = check_entry(entry)
    assert not any("no profile" in i for i in issues)


def test_check_entry_all_ok():
    """Entry with no external dependencies passes basic structural checks."""
    # This tests structural checks only — profile/content checks depend on filesystem
    entry = _make_entry(id="definitely-nonexistent-xyz")
    issues = check_entry(entry)
    # Should have "no profile" but not structural failures
    structural = [i for i in issues if "portfolio_url" in i or "application_url" in i
                  or "expired" in i or "material not found" in i]
    assert len(structural) == 0
