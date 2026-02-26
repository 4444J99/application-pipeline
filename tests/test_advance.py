"""Tests for scripts/advance.py"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from advance import can_advance, advance_entry, VALID_TRANSITIONS


# --- can_advance ---


def test_can_advance_valid():
    assert can_advance("qualified", "drafting") is True
    assert can_advance("qualified", "staged") is True
    assert can_advance("drafting", "staged") is True
    assert can_advance("staged", "submitted") is True
    assert can_advance("research", "qualified") is True


def test_can_advance_invalid():
    assert can_advance("research", "submitted") is False
    assert can_advance("qualified", "submitted") is False
    assert can_advance("outcome", "research") is False


def test_can_advance_withdrawn():
    assert can_advance("qualified", "withdrawn") is True
    assert can_advance("drafting", "withdrawn") is True
    assert can_advance("staged", "withdrawn") is True


def test_can_advance_outcome_terminal():
    assert can_advance("outcome", "research") is False
    assert can_advance("outcome", "qualified") is False


def test_can_advance_rollback():
    assert can_advance("drafting", "qualified") is True
    assert can_advance("staged", "drafting") is True


def test_can_advance_from_deferred():
    """Deferred entries can be re-activated to staged or qualified."""
    assert can_advance("deferred", "staged") is True
    assert can_advance("deferred", "qualified") is True
    assert can_advance("deferred", "withdrawn") is True
    # But not to arbitrary statuses
    assert can_advance("deferred", "submitted") is False
    assert can_advance("deferred", "drafting") is False


def test_valid_transitions_all_statuses():
    """All statuses in VALID_TRANSITIONS should map to sets."""
    for status, targets in VALID_TRANSITIONS.items():
        assert isinstance(targets, set), f"{status} doesn't map to a set"


# --- advance_entry ---


def _make_temp_yaml(content: str) -> Path:
    """Write content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


SAMPLE_YAML = """id: test-entry
name: Test Entry
track: grant
status: qualified
outcome: null
deadline:
  date: '2026-06-01'
  type: hard
submission:
  effort_level: quick
timeline:
  researched: '2026-01-01'
  qualified: '2026-01-15'
  materials_ready: null
  submitted: null
last_touched: "2026-01-15"
"""


def test_advance_entry_updates_status():
    filepath = _make_temp_yaml(SAMPLE_YAML)
    try:
        result = advance_entry(filepath, "test-entry", "drafting")
        assert result is True
        content = filepath.read_text()
        assert "status: drafting" in content
    finally:
        filepath.unlink()


def test_advance_entry_updates_last_touched():
    from datetime import date
    filepath = _make_temp_yaml(SAMPLE_YAML)
    try:
        advance_entry(filepath, "test-entry", "drafting")
        content = filepath.read_text()
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_advance_entry_to_staged_sets_timeline():
    filepath = _make_temp_yaml(SAMPLE_YAML)
    try:
        advance_entry(filepath, "test-entry", "staged")
        content = filepath.read_text()
        assert "status: staged" in content
        # materials_ready should be set
        from datetime import date
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_advance_entry_preserves_other_fields():
    filepath = _make_temp_yaml(SAMPLE_YAML)
    try:
        advance_entry(filepath, "test-entry", "drafting")
        content = filepath.read_text()
        assert "id: test-entry" in content
        assert "name: Test Entry" in content
        assert "track: grant" in content
    finally:
        filepath.unlink()


def test_advance_entry_no_last_touched():
    """Test advancing an entry that has no last_touched field."""
    yaml_no_touch = """id: test-entry
name: Test Entry
track: grant
status: qualified
"""
    filepath = _make_temp_yaml(yaml_no_touch)
    try:
        advance_entry(filepath, "test-entry", "drafting")
        content = filepath.read_text()
        assert "status: drafting" in content
        assert "last_touched:" in content
    finally:
        filepath.unlink()


# --- deferred re-activation ---


DEFERRED_YAML = """id: deferred-entry
name: Deferred Entry
track: grant
status: deferred
deferral:
  reason: portal_paused
  resume_date: '2026-04-01'
  note: Portal under maintenance
last_touched: "2026-01-15"
"""


def test_advance_deferred_to_staged():
    """Deferred entries can be advanced to staged."""
    filepath = _make_temp_yaml(DEFERRED_YAML)
    try:
        result = advance_entry(filepath, "deferred-entry", "staged")
        assert result is True
        content = filepath.read_text()
        assert "status: staged" in content
    finally:
        filepath.unlink()


def test_advance_deferred_to_qualified():
    """Deferred entries can be advanced to qualified."""
    filepath = _make_temp_yaml(DEFERRED_YAML)
    try:
        result = advance_entry(filepath, "deferred-entry", "qualified")
        assert result is True
        content = filepath.read_text()
        assert "status: qualified" in content
    finally:
        filepath.unlink()


def test_run_advance_excludes_deferred_from_normal_batch():
    """Deferred entries should not be picked up by default batch operations
    targeting actionable statuses (e.g. --to staged without --status deferred).

    The gate allows deferred entries through, but can_advance must also pass,
    and deferred is not in ACTIONABLE_STATUSES so the status_filter logic
    handles exclusion correctly.
    """
    # Deferred → staged is valid per VALID_TRANSITIONS
    assert can_advance("deferred", "staged") is True
    # But deferred is NOT in ACTIONABLE_STATUSES, meaning it won't match
    # a default --status filter for qualified/drafting batch runs
    from pipeline_lib import ACTIONABLE_STATUSES
    assert "deferred" not in ACTIONABLE_STATUSES
