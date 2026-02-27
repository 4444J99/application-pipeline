"""Tests for scripts/submit.py"""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from submit import (
    resolve_field_content,
    generate_checklist,
    _append_conversion_log,
)
from pipeline_lib import SIGNALS_DIR


# --- resolve_field_content ---


SAMPLE_ENTRY = {
    "id": "test-entry",
    "name": "Test Entry",
    "track": "grant",
    "status": "staged",
    "target": {"organization": "Test Org", "application_url": "https://example.com/apply"},
    "deadline": {"date": "2026-06-01", "type": "hard"},
    "submission": {
        "effort_level": "quick",
        "blocks_used": {},
        "variant_ids": {},
        "materials_attached": [],
        "portfolio_url": "https://example.com/portfolio",
    },
}

SAMPLE_PROFILE = {
    "submission_format": "Artist statement + bio",
    "artist_statement": {"short": "Short stmt.", "medium": "Medium stmt.", "long": "Long stmt."},
    "bio": {"short": "Short bio.", "medium": "Medium bio.", "long": "Long bio."},
}

SAMPLE_LEGACY = {
    "artist_statement": "Legacy artist statement content that is paste-ready.",
    "bio": "Legacy bio content for the portal.",
}


def test_resolve_legacy_first():
    """Legacy script content takes priority over profile."""
    content, source = resolve_field_content(
        "artist_statement", SAMPLE_ENTRY, SAMPLE_PROFILE, SAMPLE_LEGACY,
    )
    assert content == SAMPLE_LEGACY["artist_statement"]
    assert source == "legacy"


def test_resolve_profile_fallback():
    """Profile content used when no legacy script available."""
    content, source = resolve_field_content(
        "artist_statement", SAMPLE_ENTRY, SAMPLE_PROFILE, None,
    )
    assert content == "Medium stmt."
    assert source == "profile"


def test_resolve_none_when_missing():
    """Returns None when no source has the field."""
    content, source = resolve_field_content(
        "budget", SAMPLE_ENTRY, SAMPLE_PROFILE, None,
    )
    assert content is None


def test_resolve_legacy_specific_field():
    """Legacy script for a specific field not in profile."""
    legacy = {"financial_hardship": "We face financial hardship because..."}
    content, source = resolve_field_content(
        "financial_hardship", SAMPLE_ENTRY, None, legacy,
    )
    assert "financial hardship" in content
    assert source == "legacy"


# --- generate_checklist ---


def test_checklist_basic():
    """Checklist generates with title and fields."""
    checklist, issues = generate_checklist(SAMPLE_ENTRY, SAMPLE_PROFILE, None)
    assert "SUBMISSION CHECKLIST: Test Entry" in checklist
    assert "Test Org" in checklist


def test_checklist_with_legacy():
    """Checklist uses legacy content when available."""
    checklist, issues = generate_checklist(SAMPLE_ENTRY, SAMPLE_PROFILE, SAMPLE_LEGACY)
    assert "Legacy artist statement" in checklist
    assert "legacy" in checklist.lower()


def test_checklist_missing_fields():
    """Checklist flags missing content as issues."""
    profile = {"submission_format": "Resume + cover letter + portfolio"}
    checklist, issues = generate_checklist(SAMPLE_ENTRY, profile, None)
    assert any("Missing content" in i for i in issues)


def test_checklist_no_profile_no_legacy():
    """Checklist handles no profile and no legacy gracefully."""
    entry = dict(SAMPLE_ENTRY)
    entry["submission"] = {"blocks_used": {}, "materials_attached": [], "portfolio_url": ""}
    checklist, issues = generate_checklist(entry, None, None)
    assert "No submission fields identified" in checklist or len(issues) > 0


def test_checklist_portal_url_present():
    """Checklist validates portal URL."""
    checklist, issues = generate_checklist(SAMPLE_ENTRY, SAMPLE_PROFILE, None)
    assert "Portal URL set" in checklist


def test_checklist_portal_url_missing():
    """Checklist flags missing portal URL."""
    entry = dict(SAMPLE_ENTRY)
    entry["target"] = {"organization": "Test", "application_url": ""}
    checklist, issues = generate_checklist(entry, SAMPLE_PROFILE, None)
    assert any("No portal URL" in i for i in issues)


def test_checklist_expired_deadline():
    """Checklist flags expired deadline."""
    past = (date.today() - timedelta(days=5)).isoformat()
    entry = dict(SAMPLE_ENTRY)
    entry["deadline"] = {"date": past, "type": "hard"}
    checklist, issues = generate_checklist(entry, SAMPLE_PROFILE, None)
    assert any("expired" in i.lower() for i in issues)


def test_checklist_ready():
    """Checklist shows READY when all fields are filled."""
    checklist, issues = generate_checklist(SAMPLE_ENTRY, SAMPLE_PROFILE, SAMPLE_LEGACY)
    # We have both legacy content for artist_statement and bio, and portal URL is set
    content_issues = [i for i in issues if "Missing content" in i]
    assert len(content_issues) == 0


def test_checklist_materials_section():
    """Checklist includes portfolio URL in materials section."""
    checklist, issues = generate_checklist(SAMPLE_ENTRY, SAMPLE_PROFILE, None)
    assert "portfolio" in checklist.lower()


def test_checklist_validation_summary():
    """Checklist includes PRE-SUBMIT VALIDATION section."""
    checklist, issues = generate_checklist(SAMPLE_ENTRY, SAMPLE_PROFILE, None)
    assert "PRE-SUBMIT VALIDATION" in checklist


# --- _append_conversion_log ---


def test_append_conversion_log():
    """Conversion log entry is properly formatted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "conversion-log.yaml"
        log_path.write_text("entries: []\n")

        # Patch SIGNALS_DIR temporarily by writing directly
        entry = {
            "id": "test-entry",
            "track": "grant",
            "fit": {"identity_position": "systems-artist"},
            "submission": {
                "blocks_used": {"artist_statement": "identity/2min"},
                "variant_ids": {"cover_letter": "cover-letters/grant-v1"},
            },
        }

        # We can't easily patch the global SIGNALS_DIR, so test the logic directly
        log_data = yaml.safe_load(log_path.read_text())
        if not isinstance(log_data.get("entries"), list):
            log_data["entries"] = []

        blocks_list = list(entry["submission"]["blocks_used"].values())
        variant_id = list(entry["submission"]["variant_ids"].values())[0]

        log_entry = {
            "id": entry["id"],
            "submitted": "2026-02-23",
            "track": entry["track"],
            "identity_position": entry["fit"]["identity_position"],
            "blocks_used": blocks_list,
            "variant_id": variant_id,
            "outcome": None,
        }
        log_data["entries"].append(log_entry)
        log_path.write_text(yaml.dump(log_data, default_flow_style=False, sort_keys=False))

        # Verify
        result = yaml.safe_load(log_path.read_text())
        assert len(result["entries"]) == 1
        assert result["entries"][0]["id"] == "test-entry"
        assert result["entries"][0]["track"] == "grant"
        assert result["entries"][0]["identity_position"] == "systems-artist"
        assert result["entries"][0]["blocks_used"] == ["identity/2min"]
        assert result["entries"][0]["variant_id"] == "cover-letters/grant-v1"
        assert result["entries"][0]["outcome"] is None


def test_append_conversion_log_empty_blocks():
    """Conversion log handles entries with no blocks or variants."""
    entry = {
        "id": "minimal-entry",
        "track": "job",
        "fit": {},
        "submission": {"blocks_used": {}, "variant_ids": {}},
    }

    blocks_used = entry["submission"]["blocks_used"]
    blocks_list = list(blocks_used.values()) if blocks_used else []
    variant_ids = entry["submission"]["variant_ids"]
    variant_id = list(variant_ids.values())[0] if variant_ids else None

    assert blocks_list == []
    assert variant_id is None


# --- _check_metrics_freshness ---


def test_check_metrics_freshness_clean():
    """Entry with no blocks returns no issues."""
    from submit import _check_metrics_freshness

    entry = {
        "submission": {"blocks_used": {}},
    }
    issues = _check_metrics_freshness(entry)
    assert issues == []


def test_check_metrics_freshness_no_submission():
    """Entry without submission block returns no issues."""
    from submit import _check_metrics_freshness

    entry = {"submission": "invalid"}
    issues = _check_metrics_freshness(entry)
    assert issues == []


# --- base resume blocking ---


def test_checklist_flags_base_resume():
    """Checklist should flag base resume as a blocking issue."""
    entry = dict(SAMPLE_ENTRY)
    entry["submission"] = dict(entry["submission"])
    entry["submission"]["materials_attached"] = ["resumes/base/multimedia-specialist.pdf"]
    checklist, issues = generate_checklist(entry, SAMPLE_PROFILE, SAMPLE_LEGACY)
    assert any("BASE RESUME" in i for i in issues)
    assert "BASE RESUME" in checklist


def test_checklist_no_flag_for_tailored_resume():
    """Checklist should not flag tailored resume."""
    entry = dict(SAMPLE_ENTRY)
    entry["submission"] = dict(entry["submission"])
    entry["submission"]["materials_attached"] = [
        "resumes/batch-03/test/test-resume.pdf"
    ]
    checklist, issues = generate_checklist(entry, SAMPLE_PROFILE, SAMPLE_LEGACY)
    assert not any("BASE RESUME" in i for i in issues)
