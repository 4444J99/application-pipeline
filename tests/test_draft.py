"""Tests for scripts/draft.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from draft import (
    parse_submission_format,
    get_profile_content,
    assemble_draft,
    build_portal_fields,
)
from pipeline_lib import load_profile, PROFILES_DIR


# --- parse_submission_format ---


def test_parse_format_submittable():
    result = parse_submission_format(
        "Artist statement + bio + work samples + resume (Submittable)"
    )
    assert result["platform"] == "submittable"
    field_names = [f["name"] for f in result["fields"]]
    assert "artist_statement" in field_names
    assert "bio" in field_names
    assert "work_samples" in field_names
    assert "resume" in field_names


def test_parse_format_short_application():
    result = parse_submission_format(
        "Short application: project description (~300 words)"
    )
    assert result["platform"] is None
    assert len(result["fields"]) >= 1
    pf = result["fields"][0]
    assert pf["name"] == "project_description"
    assert pf["word_limit"] == 300


def test_parse_format_slideroom():
    result = parse_submission_format(
        "Artist statement + project proposal + work samples + bio (SlideRoom)"
    )
    assert result["platform"] == "slideroom"
    field_names = [f["name"] for f in result["fields"]]
    assert "artist_statement" in field_names
    assert "bio" in field_names


def test_parse_format_direct_outreach():
    result = parse_submission_format(
        "Direct outreach + platform registration (Toptal, Contra)"
    )
    assert result["fields"] == []


def test_parse_format_empty():
    result = parse_submission_format("")
    assert result["platform"] is None
    assert result["fields"] == []


def test_parse_format_pitch_email():
    result = parse_submission_format(
        "Pitch email: 2-3 paragraph pitch + writing samples"
    )
    field_names = [f["name"] for f in result["fields"]]
    assert "writing_sample" in field_names


def test_parse_format_resume_cover():
    result = parse_submission_format("Resume + cover letter + portfolio")
    field_names = [f["name"] for f in result["fields"]]
    assert "resume" in field_names
    assert "cover_letter" in field_names
    assert "portfolio" in field_names


def test_parse_format_complex():
    result = parse_submission_format(
        "6 short-answer questions + 500-word project description + "
        "work samples + bio + resume"
    )
    field_names = [f["name"] for f in result["fields"]]
    assert "project_description" in field_names
    assert "work_samples" in field_names
    assert "bio" in field_names
    assert "resume" in field_names


def test_parse_format_preserves_raw():
    raw = "Artist statement + bio"
    result = parse_submission_format(raw)
    assert result["raw"] == raw


# --- get_profile_content ---


SAMPLE_PROFILE = {
    "artist_statement": {
        "short": "Short statement.",
        "medium": "Medium statement with more detail.",
        "long": "Long statement with full depth and context.",
    },
    "bio": {
        "short": "Short bio.",
        "medium": "Medium bio.",
        "long": "Long bio.",
    },
    "identity_narrative": "A narrative about the project.",
    "work_samples": [
        {"name": "Sample 1", "url": "https://example.com/1", "description": "Desc 1"},
        {"name": "Sample 2", "url": "https://example.com/2", "description": "Desc 2"},
    ],
    "evidence_highlights": ["Point one.", "Point two."],
    "differentiators": ["Diff one.", "Diff two."],
}


def test_profile_artist_statement_short():
    result = get_profile_content(SAMPLE_PROFILE, "artist_statement", "short")
    assert result == "Short statement."


def test_profile_artist_statement_medium():
    result = get_profile_content(SAMPLE_PROFILE, "artist_statement", "medium")
    assert result == "Medium statement with more detail."


def test_profile_artist_statement_long():
    result = get_profile_content(SAMPLE_PROFILE, "artist_statement", "long")
    assert result == "Long statement with full depth and context."


def test_profile_bio_medium():
    result = get_profile_content(SAMPLE_PROFILE, "bio", "medium")
    assert result == "Medium bio."


def test_profile_project_description():
    result = get_profile_content(SAMPLE_PROFILE, "project_description")
    assert "narrative" in result.lower()


def test_profile_work_samples():
    result = get_profile_content(SAMPLE_PROFILE, "work_samples")
    assert "Sample 1" in result
    assert "Sample 2" in result
    assert "https://example.com/1" in result


def test_profile_evidence_highlights():
    result = get_profile_content(SAMPLE_PROFILE, "evidence_highlights")
    assert "Point one." in result


def test_profile_differentiators():
    result = get_profile_content(SAMPLE_PROFILE, "differentiators")
    assert "Diff one." in result


def test_profile_unknown_section():
    result = get_profile_content(SAMPLE_PROFILE, "nonexistent_field")
    assert result is None


def test_profile_writing_sample_returns_none():
    result = get_profile_content(SAMPLE_PROFILE, "writing_sample")
    assert result is None


# --- load_profile ---


def test_load_profile_existing():
    if not PROFILES_DIR.exists():
        return  # skip if no profiles dir
    profile = load_profile("artadia-nyc")
    assert profile is not None
    assert profile["target_id"] == "artadia-nyc"
    assert "artist_statement" in profile


def test_load_profile_nonexistent():
    profile = load_profile("definitely-does-not-exist-xyz")
    assert profile is None


# --- assemble_draft ---


def test_assemble_draft_basic():
    entry = {
        "id": "test-entry",
        "name": "Test Entry",
        "track": "grant",
        "status": "qualified",
        "target": {"organization": "Test Org"},
        "deadline": {"date": "2026-06-01", "type": "hard"},
        "submission": {"blocks_used": {}, "variant_ids": {}},
    }
    profile = {
        "submission_format": "Artist statement + bio",
        "artist_statement": {"medium": "My art statement."},
        "bio": {"medium": "My bio."},
    }
    doc, warnings = assemble_draft(entry, profile)
    assert "# Draft: Test Entry" in doc
    assert "## Artist Statement" in doc
    assert "My art statement." in doc
    assert "## Bio" in doc
    assert "My bio." in doc


def test_assemble_draft_no_profile():
    entry = {
        "id": "test-entry",
        "name": "Test Entry",
        "track": "grant",
        "status": "qualified",
        "target": {"organization": "Test Org"},
        "submission": {"blocks_used": {}},
    }
    doc, warnings = assemble_draft(entry, None)
    assert "No profile found" in doc
    assert len(warnings) > 0


def test_assemble_draft_missing_section():
    entry = {
        "id": "test-entry",
        "name": "Test Entry",
        "track": "grant",
        "status": "qualified",
        "target": {"organization": "Test Org"},
        "submission": {"blocks_used": {}},
    }
    profile = {
        "submission_format": "Resume + cover letter",
        "artist_statement": {"medium": "Irrelevant."},
    }
    doc, warnings = assemble_draft(entry, profile)
    assert "MISSING" in doc
    assert any("Missing content" in w for w in warnings)


def test_assemble_draft_word_count():
    entry = {
        "id": "test-entry",
        "name": "Test Entry",
        "track": "grant",
        "status": "qualified",
        "target": {"organization": "Test Org"},
        "submission": {"blocks_used": {}},
    }
    profile = {
        "submission_format": "Short application: project description (~300 words)",
        "identity_narrative": "Word " * 400,
    }
    doc, warnings = assemble_draft(entry, profile)
    assert "OVER LIMIT" in doc
    assert any("exceeds" in w for w in warnings)


# --- build_portal_fields ---


def test_build_portal_fields_submittable():
    profile = {
        "submission_format": "Artist statement + bio + work samples + resume (Submittable)",
    }
    pf = build_portal_fields(profile)
    assert pf["platform"] == "submittable"
    assert len(pf["fields"]) >= 4
    field_names = [f["name"] for f in pf["fields"]]
    assert "artist_statement" in field_names


def test_build_portal_fields_with_limit():
    profile = {
        "submission_format": "Short application: project description (~300 words)",
    }
    pf = build_portal_fields(profile)
    assert len(pf["fields"]) >= 1
    assert pf["fields"][0]["word_limit"] == 300


def test_build_portal_fields_empty():
    profile = {"submission_format": ""}
    pf = build_portal_fields(profile)
    assert pf.get("fields") is None or pf.get("fields") == []
