"""Integration tests: cross-script pipeline chain verification.

Exercises the state machine by creating temporary YAML entries and
running multiple scripts in sequence, verifying the entry progresses
correctly with all fields populated.
"""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import (
    update_yaml_field, ensure_yaml_field, update_last_touched,
    VALID_TRANSITIONS,
)
from advance import can_advance, advance_entry
from score import compute_dimensions, compute_composite
from enrich import enrich_materials, select_resume, detect_gaps


# --- Helpers ---


def _make_temp_yaml(content: str) -> Path:
    """Write content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def _date_offset(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


INTEGRATION_ENTRY = f"""id: integration-test
name: Integration Test Grant
track: grant
status: qualified
outcome: null
target:
  organization: Test Foundation
  url: https://example.com
  application_url: https://example.com/apply
  portal: web
deadline:
  date: '{_date_offset(30)}'
  type: hard
amount:
  value: 10000
  currency: USD
  type: lump_sum
  benefits_cliff_note: null
fit:
  score: 6.0
  identity_position: systems-artist
  framing: "Test framing for integration test"
  lead_organs:
  - I
submission:
  effort_level: standard
  blocks_used: {{}}
  variant_ids: {{}}
  materials_attached: []
  portfolio_url: https://example.com/portfolio
timeline:
  researched: '{_date_offset(-10)}'
  qualified: '{_date_offset(-5)}'
  materials_ready: null
  submitted: null
  acknowledged: null
  interview: null
  outcome_date: null
last_touched: "{_date_offset(-5)}"
"""


# --- update_yaml_field tests ---


def test_update_yaml_field_top_level():
    """update_yaml_field should replace a top-level field value."""
    content = "id: test\nstatus: qualified\ntrack: grant\n"
    result = update_yaml_field(content, "status", "drafting")
    assert "status: drafting" in result
    data = yaml.safe_load(result)
    assert data["status"] == "drafting"


def test_update_yaml_field_nested():
    """update_yaml_field with nested=True matches indented fields."""
    content = "fit:\n  score: 5.0\n  framing: test\n"
    result = update_yaml_field(content, "score", "7.2", nested=True)
    assert "score: 7.2" in result
    data = yaml.safe_load(result)
    assert data["fit"]["score"] == 7.2


def test_update_yaml_field_raises_on_missing():
    """update_yaml_field raises ValueError when field not found."""
    content = "id: test\nstatus: qualified\n"
    try:
        update_yaml_field(content, "nonexistent", "value")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_update_yaml_field_preserves_other_fields():
    """Updating one field should not corrupt others."""
    content = INTEGRATION_ENTRY
    result = update_yaml_field(content, "status", "drafting")
    data = yaml.safe_load(result)
    assert data["status"] == "drafting"
    assert data["id"] == "integration-test"
    assert data["track"] == "grant"
    assert data["fit"]["score"] == 6.0


def test_ensure_yaml_field_existing():
    """ensure_yaml_field updates an existing field."""
    content = "id: test\nstatus: qualified\n"
    result = ensure_yaml_field(content, "status", "drafting")
    assert "status: drafting" in result


def test_ensure_yaml_field_missing():
    """ensure_yaml_field appends a missing field."""
    content = "id: test\nstatus: qualified\n"
    result = ensure_yaml_field(content, "last_touched", '"2026-02-24"')
    assert "last_touched:" in result
    data = yaml.safe_load(result)
    assert data["last_touched"] == "2026-02-24"


def test_update_last_touched():
    """update_last_touched sets last_touched to today."""
    content = 'id: test\nlast_touched: "2026-01-01"\n'
    result = update_last_touched(content)
    data = yaml.safe_load(result)
    assert data["last_touched"] == date.today().isoformat()


# --- Cross-script integration tests ---


def test_score_then_advance():
    """Score an entry, then advance it — verify both changes persist."""
    filepath = _make_temp_yaml(INTEGRATION_ENTRY)
    try:
        # Score the entry
        data = yaml.safe_load(filepath.read_text())
        dims = compute_dimensions(data)
        composite = compute_composite(dims)
        assert 1.0 <= composite <= 10.0

        # Advance qualified → drafting
        assert can_advance("qualified", "drafting") is True
        advance_entry(filepath, "integration-test", "drafting")

        # Verify both the original fit.score and the new status
        updated = yaml.safe_load(filepath.read_text())
        assert updated["status"] == "drafting"
        assert updated["fit"]["score"] == 6.0
        assert updated["last_touched"] == date.today().isoformat()
    finally:
        filepath.unlink()


def test_advance_then_advance_staged():
    """Advance qualified → drafting → staged through two steps."""
    filepath = _make_temp_yaml(INTEGRATION_ENTRY)
    try:
        # Step 1: qualified → drafting
        advance_entry(filepath, "integration-test", "drafting")
        data = yaml.safe_load(filepath.read_text())
        assert data["status"] == "drafting"

        # Step 2: drafting → staged
        advance_entry(filepath, "integration-test", "staged")
        data = yaml.safe_load(filepath.read_text())
        assert data["status"] == "staged"
        assert data["timeline"]["materials_ready"] == date.today().isoformat()
    finally:
        filepath.unlink()


def test_enrich_materials_on_grant():
    """Enriching a grant entry wires the identity-matched resume."""
    filepath = _make_temp_yaml(INTEGRATION_ENTRY)
    try:
        data = yaml.safe_load(filepath.read_text())

        # Verify the entry has empty materials
        assert data["submission"]["materials_attached"] == []

        # Select resume based on identity
        resume = select_resume(data)
        assert "systems-artist" in resume

        # Enrich materials
        result = enrich_materials(filepath, data)
        assert result is True

        # Verify the materials were wired
        updated = yaml.safe_load(filepath.read_text())
        assert len(updated["submission"]["materials_attached"]) == 1
        assert "systems-artist" in updated["submission"]["materials_attached"][0]
    finally:
        filepath.unlink()


def test_full_pipeline_chain():
    """Exercise the full chain: enrich → advance → verify."""
    filepath = _make_temp_yaml(INTEGRATION_ENTRY)
    try:
        data = yaml.safe_load(filepath.read_text())

        # Step 1: Detect initial gaps
        gaps = detect_gaps(data)
        assert "materials" in gaps

        # Step 2: Enrich materials
        enrich_materials(filepath, data)

        # Step 3: Advance to drafting
        advance_entry(filepath, "integration-test", "drafting")

        # Step 4: Advance to staged
        advance_entry(filepath, "integration-test", "staged")

        # Step 5: Verify final state
        final = yaml.safe_load(filepath.read_text())
        assert final["status"] == "staged"
        assert len(final["submission"]["materials_attached"]) >= 1
        assert final["timeline"]["materials_ready"] == date.today().isoformat()
        assert final["last_touched"] == date.today().isoformat()

        # The YAML should still be valid
        filepath.read_text()  # should not raise
        yaml.safe_load(filepath.read_text())  # should parse cleanly
    finally:
        filepath.unlink()


def test_valid_transitions_consistency():
    """VALID_TRANSITIONS imported from pipeline_lib is consistent."""
    # Every status in the transition map should have a set
    for status, targets in VALID_TRANSITIONS.items():
        assert isinstance(targets, set), f"{status} doesn't map to a set"

    # outcome should be terminal
    assert VALID_TRANSITIONS["outcome"] == set()

    # Forward chain should be possible
    assert "qualified" in VALID_TRANSITIONS["research"]
    assert "drafting" in VALID_TRANSITIONS["qualified"]
    assert "staged" in VALID_TRANSITIONS["drafting"]
    assert "submitted" in VALID_TRANSITIONS["staged"]


def test_yaml_integrity_after_multiple_updates():
    """Multiple sequential updates should not corrupt the YAML."""
    filepath = _make_temp_yaml(INTEGRATION_ENTRY)
    try:
        content = filepath.read_text()

        # Apply multiple updates
        content = update_yaml_field(content, "status", "drafting")
        content = update_last_touched(content)
        content = update_yaml_field(content, "score", "7.5", nested=True)

        # Write and re-read
        filepath.write_text(content)
        data = yaml.safe_load(filepath.read_text())

        assert data["status"] == "drafting"
        assert data["fit"]["score"] == 7.5
        assert data["last_touched"] == date.today().isoformat()
        assert data["id"] == "integration-test"
        assert data["track"] == "grant"
    finally:
        filepath.unlink()
