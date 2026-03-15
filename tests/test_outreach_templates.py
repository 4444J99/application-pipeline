"""Tests for outreach_templates.py — personalized outreach message generation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from outreach_templates import (
    VALID_TYPES,
    _identity_position,
    _org_name,
    _role_title,
    _track,
    format_report,
    generate_all_templates,
    generate_cold_email,
    generate_connect_note,
    generate_followup,
)  # noqa: I001 — private helpers imported for direct testing

# --- Fixtures ---

@pytest.fixture
def job_entry():
    return {
        "id": "test-job-entry",
        "track": "job",
        "identity_position": "independent-engineer",
        "target": {
            "organization": "Acme Corp",
            "title": "Senior Platform Engineer",
        },
    }


@pytest.fixture
def grant_entry():
    return {
        "id": "test-grant-entry",
        "track": "grant",
        "identity_position": "systems-artist",
        "target": {
            "organization": "Creative Capital",
            "title": "Emerging Artist Grant 2027",
        },
    }


@pytest.fixture
def residency_entry():
    return {
        "id": "test-residency-entry",
        "track": "residency",
        "identity_position": "creative-technologist",
        "target": {
            "organization": "Eyebeam",
            "title": "Technology Residency",
        },
    }


@pytest.fixture
def minimal_entry():
    """Entry with minimal fields — tests fallback behavior."""
    return {"id": "minimal-entry"}


# --- Helper Tests ---

class TestHelpers:
    def test_org_name_from_organization(self, job_entry):
        assert _org_name(job_entry) == "Acme Corp"

    def test_org_name_from_company_fallback(self):
        entry = {"target": {"company": "FallbackCo"}}
        assert _org_name(entry) == "FallbackCo"

    def test_org_name_default(self, minimal_entry):
        assert _org_name(minimal_entry) == "the organization"

    def test_role_title(self, job_entry):
        assert _role_title(job_entry) == "Senior Platform Engineer"

    def test_role_title_from_name_fallback(self):
        entry = {"target": {"name": "Fellowship Program"}}
        assert _role_title(entry) == "Fellowship Program"

    def test_role_title_default(self, minimal_entry):
        assert _role_title(minimal_entry) == "the role"

    def test_identity_position(self, job_entry):
        assert _identity_position(job_entry) == "independent-engineer"

    def test_identity_position_default(self, minimal_entry):
        assert _identity_position(minimal_entry) == "independent-engineer"

    def test_track(self, job_entry):
        assert _track(job_entry) == "job"

    def test_track_default(self, minimal_entry):
        assert _track(minimal_entry) == "job"


# --- Connect Note Tests ---

class TestGenerateConnectNote:
    def test_returns_dict_with_required_keys(self, job_entry):
        result = generate_connect_note(job_entry)
        assert result["type"] == "connect"
        assert result["platform"] == "linkedin"
        assert result["max_chars"] == 300
        assert "template" in result
        assert "char_count" in result
        assert result["entry_id"] == "test-job-entry"
        assert result["org"] == "Acme Corp"

    def test_linkedin_char_limit(self, job_entry):
        result = generate_connect_note(job_entry)
        assert result["char_count"] <= 300
        assert len(result["template"]) <= 300

    def test_job_template_mentions_org(self, job_entry):
        result = generate_connect_note(job_entry)
        assert "Acme Corp" in result["template"]

    def test_grant_template_differs_from_job(self, grant_entry):
        result = generate_connect_note(grant_entry)
        assert "template" in result
        # Grant templates mention exploring programs or mission
        assert any(w in result["template"].lower() for w in ["program", "mission", "exploring"])

    def test_residency_uses_grant_template(self, residency_entry):
        result = generate_connect_note(residency_entry)
        # Residency follows grant/fellowship path
        assert "template" in result

    def test_truncation_at_300_chars(self):
        """Long org/role names get truncated to 300 chars."""
        entry = {
            "id": "long-name",
            "track": "job",
            "identity_position": "independent-engineer",
            "target": {
                "organization": "A" * 200,
                "title": "B" * 200,
            },
        }
        result = generate_connect_note(entry)
        assert len(result["template"]) <= 300


# --- Cold Email Tests ---

class TestGenerateColdEmail:
    def test_returns_dict_with_required_keys(self, job_entry):
        result = generate_cold_email(job_entry)
        assert result["type"] == "email"
        assert "subject" in result
        assert "template" in result
        assert result["entry_id"] == "test-job-entry"
        assert result["org"] == "Acme Corp"
        assert "word_count" in result

    def test_job_subject_includes_role_and_org(self, job_entry):
        result = generate_cold_email(job_entry)
        assert "Acme Corp" in result["subject"]

    def test_grant_subject_mentions_artistic_practice(self, grant_entry):
        result = generate_cold_email(grant_entry)
        assert "artistic practice" in result["subject"].lower() or "systems engineering" in result["subject"].lower()

    def test_independent_engineer_evidence(self, job_entry):
        result = generate_cold_email(job_entry)
        assert "infrastructure" in result["template"].lower() or "pipeline" in result["template"].lower()

    def test_systems_artist_evidence(self, grant_entry):
        result = generate_cold_email(grant_entry)
        assert "governance" in result["template"].lower() or "ORGANVM" in result["template"]

    def test_unknown_position_fallback(self):
        entry = {
            "id": "unknown-pos",
            "track": "job",
            "identity_position": "unknown-position",
            "target": {"organization": "TestOrg", "title": "TestRole"},
        }
        result = generate_cold_email(entry)
        assert "software" in result["template"].lower()

    def test_word_count_positive(self, job_entry):
        result = generate_cold_email(job_entry)
        assert result["word_count"] > 0


# --- Follow-up Tests ---

class TestGenerateFollowup:
    def test_returns_dict_with_required_keys(self, job_entry):
        result = generate_followup(job_entry)
        assert result["type"] == "followup"
        assert "template" in result
        assert result["entry_id"] == "test-job-entry"
        assert result["timing"] == "Day 7-10 after submission"

    def test_job_followup_mentions_org(self, job_entry):
        result = generate_followup(job_entry)
        assert "Acme Corp" in result["template"]

    def test_grant_followup_differs(self, grant_entry):
        result = generate_followup(grant_entry)
        assert "Creative Capital" in result["template"]
        # Grant follow-ups are softer in tone
        assert "additional materials" in result["template"].lower()

    def test_word_count_reasonable(self, job_entry):
        result = generate_followup(job_entry)
        assert 10 < result["word_count"] < 200


# --- All Templates Tests ---

class TestGenerateAllTemplates:
    def test_returns_all_three_types(self, job_entry):
        result = generate_all_templates(job_entry)
        assert "templates" in result
        assert "connect" in result["templates"]
        assert "email" in result["templates"]
        assert "followup" in result["templates"]

    def test_metadata_fields(self, job_entry):
        result = generate_all_templates(job_entry)
        assert result["entry_id"] == "test-job-entry"
        assert result["org"] == "Acme Corp"
        assert result["role"] == "Senior Platform Engineer"
        assert result["track"] == "job"
        assert result["identity_position"] == "independent-engineer"


# --- Format Report Tests ---

class TestFormatReport:
    def test_all_templates_format(self, job_entry):
        data = generate_all_templates(job_entry)
        report = format_report(data)
        assert "CONNECT" in report
        assert "EMAIL" in report
        assert "FOLLOWUP" in report
        assert "Acme Corp" in report

    def test_single_template_format(self, job_entry):
        data = generate_connect_note(job_entry)
        # Wrap single template for format_report
        wrapped = {
            "entry_id": job_entry["id"],
            "org": _org_name(job_entry),
            "role": _role_title(job_entry),
            "track": _track(job_entry),
            "identity_position": _identity_position(job_entry),
            "templates": {data["type"]: data},
        }
        report = format_report(wrapped)
        assert "CONNECT" in report
        assert "LinkedIn" in report or "linkedin" in report


# --- Constants Tests ---

class TestConstants:
    def test_valid_types(self):
        assert VALID_TYPES == {"connect", "email", "followup"}

    def test_all_identity_positions_have_email_evidence(self):
        """Every canonical identity position produces a non-fallback email."""
        positions = [
            "independent-engineer",
            "systems-artist",
            "educator",
            "creative-technologist",
            "community-practitioner",
        ]
        for pos in positions:
            entry = {
                "id": f"test-{pos}",
                "track": "job",
                "identity_position": pos,
                "target": {"organization": "TestOrg", "title": "TestRole"},
            }
            result = generate_cold_email(entry)
            # Should not use the generic fallback
            assert "large-scale software systems" not in result["template"]
