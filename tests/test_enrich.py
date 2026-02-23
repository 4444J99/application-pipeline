"""Tests for scripts/enrich.py"""

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from enrich import (
    enrich_materials, enrich_variant, find_matching_variant, detect_gaps,
    COVER_LETTER_MAP, DEFAULT_RESUME, RESUME_TRACKS, GRANT_TEMPLATE_TRACKS,
)
from pipeline_lib import MATERIALS_DIR, VARIANTS_DIR


def _make_temp_yaml(content: str) -> Path:
    """Write content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


SAMPLE_GRANT = """id: test-grant
name: Test Grant
track: grant
status: staged
outcome: null
submission:
  effort_level: standard
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_GRANT_WITH_MATERIALS = """id: test-grant
name: Test Grant
track: grant
status: staged
outcome: null
submission:
  effort_level: standard
  blocks_used: {}
  variant_ids: {}
  materials_attached:
    - resumes/multimedia-specialist.pdf
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_JOB = """id: anthropic-fde
name: Anthropic FDE
track: job
status: qualified
outcome: null
submission:
  effort_level: complex
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_WRITING = """id: test-writing
name: Test Writing Submission
track: writing
status: qualified
outcome: null
submission:
  effort_level: quick
  blocks_used: {}
  variant_ids: {}
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""

SAMPLE_WITH_VARIANTS = """id: test-entry
name: Test Entry
track: job
status: qualified
outcome: null
submission:
  effort_level: standard
  blocks_used: {}
  variant_ids:
    cover_letter: cover-letters/existing
  materials_attached: []
  portfolio_url: https://example.com
last_touched: "2026-01-15"
"""


# --- enrich_materials ---


def test_enrich_materials_replaces_empty_list():
    filepath = _make_temp_yaml(SAMPLE_GRANT)
    try:
        result = enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": []},
        })
        assert result is True
        content = filepath.read_text()
        assert DEFAULT_RESUME in content
        assert "materials_attached: []" not in content
    finally:
        filepath.unlink()


def test_enrich_materials_preserves_existing():
    filepath = _make_temp_yaml(SAMPLE_GRANT_WITH_MATERIALS)
    try:
        result = enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": ["resumes/multimedia-specialist.pdf"]},
        })
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_materials_skips_writing_track():
    filepath = _make_temp_yaml(SAMPLE_WRITING)
    try:
        result = enrich_materials(filepath, {
            "track": "writing",
            "submission": {"materials_attached": []},
        })
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_materials_skips_consulting_track():
    filepath = _make_temp_yaml(SAMPLE_WRITING)
    try:
        result = enrich_materials(filepath, {
            "track": "consulting",
            "submission": {"materials_attached": []},
        })
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_materials_updates_last_touched():
    filepath = _make_temp_yaml(SAMPLE_GRANT)
    try:
        enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": []},
        })
        content = filepath.read_text()
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_enrich_materials_dry_run():
    filepath = _make_temp_yaml(SAMPLE_GRANT)
    try:
        result = enrich_materials(filepath, {
            "track": "grant",
            "submission": {"materials_attached": []},
        }, dry_run=True)
        assert result is True
        # File should be unchanged
        content = filepath.read_text()
        assert "materials_attached: []" in content
    finally:
        filepath.unlink()


# --- enrich_variant ---


def test_enrich_variant_replaces_empty_dict():
    filepath = _make_temp_yaml(SAMPLE_JOB)
    try:
        result = enrich_variant(filepath, {
            "submission": {"variant_ids": {}},
        }, "cover-letters/anthropic-fde-custom-agents")
        assert result is True
        content = filepath.read_text()
        assert "anthropic-fde-custom-agents" in content
        assert "variant_ids: {}" not in content
    finally:
        filepath.unlink()


def test_enrich_variant_preserves_existing():
    filepath = _make_temp_yaml(SAMPLE_WITH_VARIANTS)
    try:
        result = enrich_variant(filepath, {
            "submission": {"variant_ids": {"cover_letter": "cover-letters/existing"}},
        }, "cover-letters/new-one")
        assert result is False
    finally:
        filepath.unlink()


def test_enrich_variant_updates_last_touched():
    filepath = _make_temp_yaml(SAMPLE_JOB)
    try:
        enrich_variant(filepath, {
            "submission": {"variant_ids": {}},
        }, "cover-letters/test")
        content = filepath.read_text()
        assert date.today().isoformat() in content
    finally:
        filepath.unlink()


def test_enrich_variant_dry_run():
    filepath = _make_temp_yaml(SAMPLE_JOB)
    try:
        result = enrich_variant(filepath, {
            "submission": {"variant_ids": {}},
        }, "cover-letters/test", dry_run=True)
        assert result is True
        content = filepath.read_text()
        assert "variant_ids: {}" in content
    finally:
        filepath.unlink()


# --- find_matching_variant ---


def test_find_matching_variant_known():
    assert find_matching_variant("anthropic-fde") == "cover-letters/anthropic-fde-custom-agents"
    assert find_matching_variant("huggingface-dev-advocate") == "cover-letters/huggingface-dev-advocate-hub-enterprise"
    assert find_matching_variant("openai-se-evals") == "cover-letters/openai-se-applied-evals"
    assert find_matching_variant("together-ai") == "cover-letters/together-ai-lead-dx-documentation"


def test_find_matching_variant_unknown():
    assert find_matching_variant("artadia-nyc") is None
    assert find_matching_variant("nonexistent") is None


# --- File existence checks ---


def test_cover_letter_map_files_exist():
    """All mapped variant files should exist on disk."""
    for entry_id, variant_path in COVER_LETTER_MAP.items():
        full_path = VARIANTS_DIR / f"{variant_path}.md"
        assert full_path.exists(), f"Missing variant: {full_path} (for {entry_id})"


def test_default_resume_exists():
    """The default resume file should exist on disk."""
    full_path = MATERIALS_DIR / DEFAULT_RESUME
    assert full_path.exists(), f"Missing resume: {full_path}"


# --- detect_gaps ---


def test_detect_gaps_materials():
    entry = {
        "id": "test",
        "track": "grant",
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    gaps = detect_gaps(entry)
    assert "materials" in gaps


def test_detect_gaps_no_materials_for_writing():
    entry = {
        "id": "test",
        "track": "writing",
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    gaps = detect_gaps(entry)
    assert "materials" not in gaps


def test_detect_gaps_variants_for_mapped_entry():
    entry = {
        "id": "anthropic-fde",
        "track": "job",
        "submission": {"materials_attached": [], "variant_ids": {}},
    }
    gaps = detect_gaps(entry)
    assert "variants" in gaps


def test_detect_gaps_no_variant_gap_when_populated():
    entry = {
        "id": "anthropic-fde",
        "track": "job",
        "submission": {
            "materials_attached": ["resumes/multimedia-specialist.pdf"],
            "variant_ids": {"cover_letter": "cover-letters/existing"},
        },
    }
    gaps = detect_gaps(entry)
    assert "variants" not in gaps


def test_resume_tracks_complete():
    """Ensure RESUME_TRACKS covers expected tracks."""
    expected = {"job", "fellowship", "grant", "residency", "prize", "program"}
    assert RESUME_TRACKS == expected


def test_grant_template_tracks():
    """Ensure GRANT_TEMPLATE_TRACKS covers expected tracks."""
    expected = {"grant", "residency", "prize"}
    assert GRANT_TEMPLATE_TRACKS == expected
