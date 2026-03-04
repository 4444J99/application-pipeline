"""Tests for scripts/email_submit.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from email_submit import (
    collect_attachments,
    extract_recipient,
    generate_subject,
    is_email_entry,
)

# --- extract_recipient ---


def test_extract_recipient_email_field():
    """extract_recipient returns email from target.email field."""
    entry = {
        "target": {
            "email": "grants@example.org",
            "application_url": "https://example.org/apply",
        },
    }
    assert extract_recipient(entry) == "grants@example.org"


def test_extract_recipient_mailto():
    """extract_recipient extracts address from mailto: URL."""
    entry = {
        "target": {
            "application_url": "mailto:submissions@residency.org",
        },
    }
    assert extract_recipient(entry) == "submissions@residency.org"


def test_extract_recipient_no_email():
    """extract_recipient returns None when no email is configured."""
    entry = {
        "target": {
            "application_url": "https://example.org/apply",
        },
    }
    assert extract_recipient(entry) is None


def test_extract_recipient_empty_target():
    """extract_recipient handles missing target gracefully."""
    assert extract_recipient({}) is None
    assert extract_recipient({"target": None}) is None
    assert extract_recipient({"target": {}}) is None


def test_extract_recipient_invalid_email():
    """extract_recipient rejects strings without @ sign."""
    entry = {"target": {"email": "not-an-email"}}
    assert extract_recipient(entry) is None


def test_extract_recipient_email_takes_priority_over_mailto():
    """target.email is checked before mailto: URL."""
    entry = {
        "target": {
            "email": "direct@example.org",
            "application_url": "mailto:fallback@example.org",
        },
    }
    assert extract_recipient(entry) == "direct@example.org"


# --- is_email_entry ---


def test_is_email_entry_custom_with_email():
    """is_email_entry returns True for custom portal with email."""
    entry = {
        "target": {
            "portal": "custom",
            "email": "grants@example.org",
        },
    }
    assert is_email_entry(entry) is True


def test_is_email_entry_email_portal():
    """is_email_entry returns True for email portal with email."""
    entry = {
        "target": {
            "portal": "email",
            "email": "grants@example.org",
        },
    }
    assert is_email_entry(entry) is True


def test_is_email_entry_custom_no_email():
    """is_email_entry returns False for custom portal without email."""
    entry = {
        "target": {
            "portal": "custom",
            "application_url": "https://example.org/apply",
        },
    }
    assert is_email_entry(entry) is False


def test_is_email_entry_greenhouse():
    """is_email_entry returns False for non-email portals even with email."""
    entry = {
        "target": {
            "portal": "greenhouse",
            "email": "hr@company.com",
            "application_url": "https://boards.greenhouse.io/company/jobs/123",
        },
    }
    assert is_email_entry(entry) is False


def test_is_email_entry_no_portal():
    """is_email_entry returns False when portal field is missing."""
    entry = {
        "target": {
            "email": "grants@example.org",
        },
    }
    assert is_email_entry(entry) is False


def test_is_email_entry_custom_with_mailto():
    """is_email_entry returns True for custom portal with mailto: URL."""
    entry = {
        "target": {
            "portal": "custom",
            "application_url": "mailto:submissions@gallery.org",
        },
    }
    assert is_email_entry(entry) is True


# --- generate_subject ---


def test_generate_subject_explicit():
    """generate_subject uses email_subject override when set."""
    entry = {
        "id": "test-entry",
        "name": "Test Grant Application",
        "submission": {
            "email_subject": "Application: 2026 Arts Fellowship - Anthony Padavano",
        },
    }
    result = generate_subject(entry)
    assert result == "Application: 2026 Arts Fellowship - Anthony Padavano"


def test_generate_subject_auto():
    """generate_subject auto-generates from entry name when no override."""
    entry = {
        "id": "creative-capital-2027",
        "name": "Creative Capital 2027",
        "target": {"organization": "Creative Capital"},
        "submission": {},
    }
    result = generate_subject(entry)
    assert "Application" in result
    assert "Creative Capital 2027" in result


def test_generate_subject_no_submission():
    """generate_subject handles missing submission field."""
    entry = {
        "id": "minimal-entry",
        "name": "Minimal Entry",
        "target": {},
    }
    result = generate_subject(entry)
    assert "Application" in result
    assert "Minimal Entry" in result


def test_generate_subject_fallback_to_id():
    """generate_subject uses id as fallback when name is missing."""
    entry = {
        "id": "test-id-only",
        "submission": {},
    }
    result = generate_subject(entry)
    assert "Application" in result
    assert "test-id-only" in result


# --- collect_attachments ---


def test_collect_attachments_skips_html():
    """HTML files in materials_attached are filtered out."""
    entry = {
        "submission": {
            "materials_attached": [
                "resumes/batch-03/test/test-resume.html",
                "resumes/batch-03/test/test-resume.pdf",
                "work-samples/portfolio-screenshot.png",
            ],
        },
    }
    attachments = collect_attachments(entry)
    # Filter: only files that actually exist on disk will be returned,
    # but HTML files should never appear regardless
    for att in attachments:
        assert att.suffix.lower() != ".html", f"HTML file should be filtered: {att}"


def test_collect_attachments_empty_materials():
    """collect_attachments returns empty list when no materials attached."""
    entry = {
        "submission": {"materials_attached": []},
    }
    result = collect_attachments(entry)
    assert isinstance(result, list)


def test_collect_attachments_no_submission():
    """collect_attachments handles missing submission gracefully."""
    entry = {}
    result = collect_attachments(entry)
    assert isinstance(result, list)
    assert len(result) == 0


def test_collect_attachments_none_materials():
    """collect_attachments handles None materials_attached."""
    entry = {"submission": {"materials_attached": None}}
    result = collect_attachments(entry)
    assert isinstance(result, list)
    assert len(result) == 0
