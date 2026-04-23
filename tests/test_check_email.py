"""Tests for scripts/check_email.py — pure function tests only.

All Mail.app / IMAP / AppleScript functions are skipped.
Only pure parsers and classifiers are tested here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_email import (
    build_org_index,
    classify_email,
    extract_company_from_subject,
    normalize_org,
    parse_apple_date,
    triage_email,
)

# --- TestParseAppleDate ---


def test_parse_apple_date_apple_full_format():
    """Apple date format 'Month DD, YYYY HH:MM:SS AM'."""
    result = parse_apple_date("February 21, 2026 3:45:00 PM")
    assert result is not None
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 21


def test_parse_apple_date_with_day_of_week():
    """Day-of-week prefix is stripped before parsing."""
    result = parse_apple_date("Friday, February 21, 2026 at 3:45:00 PM")
    assert result is not None
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 21


def test_parse_apple_date_with_at_keyword():
    """'at' keyword before time is stripped."""
    result = parse_apple_date("February 21, 2026 at 10:30:00 AM")
    assert result is not None
    assert result.year == 2026


def test_parse_apple_date_24h_format():
    """24-hour format without AM/PM."""
    result = parse_apple_date("February 21, 2026 15:45:00")
    assert result is not None
    assert result.year == 2026


def test_parse_apple_date_invalid_returns_none():
    """Invalid date string returns None."""
    result = parse_apple_date("not a date at all")
    assert result is None


def test_parse_apple_date_empty_returns_none():
    """Empty string returns None."""
    result = parse_apple_date("")
    assert result is None


def test_parse_apple_date_none_raises_or_returns_none():
    """None input: function calls .strip() on None so it raises AttributeError.
    Documenting actual behavior (not a contract — callers should guard with str check).
    """
    import pytest
    with pytest.raises((AttributeError, TypeError)):
        parse_apple_date(None)


# --- TestClassifyEmail ---


def test_classify_email_rejection_from_body():
    """Body with rejection keyword → 'rejection'."""
    result = classify_email("Re: Your Application", "We are unfortunately unable to move forward.")
    assert result == "rejection"


def test_classify_email_rejection_keyword_not_moving_forward():
    result = classify_email("Update", "Thank you for applying. We are not moving forward with your application.")
    assert result == "rejection"


def test_classify_email_interview_from_body():
    """Body with interview keyword → 'interview'."""
    result = classify_email("Next Steps", "We would like to schedule an interview with you.")
    assert result == "interview"


def test_classify_email_confirmation_from_subject():
    """Subject matching ATS confirmation pattern → 'confirmation'."""
    result = classify_email("Thank you for applying to Anthropic", None)
    assert result == "confirmation"


def test_classify_email_unknown_subject_no_body():
    """No matching patterns → 'update'."""
    result = classify_email("Monthly Newsletter", None)
    assert result == "update"


def test_classify_email_case_insensitive_body():
    """Body matching is case-insensitive."""
    result = classify_email("Update", "Unfortunately we WILL NOT BE proceeding.")
    assert result == "rejection"


def test_classify_email_confirmation_takes_priority():
    """Confirmation pattern wins even if body has rejection words."""
    result = classify_email(
        "Thank you for applying to Acme",
        "Unfortunately we have many applicants."
    )
    # Confirmation is checked first
    assert result == "confirmation"


def test_classify_email_no_keywords_update():
    """No matching subject or body keywords → 'update'."""
    result = classify_email("Application Status", "We received your materials.")
    assert result == "update"


# --- TestTriageEmail ---


def test_triage_email_action_for_interview_request():
    result = triage_email(
        "Next Steps",
        "We would like to schedule an interview and would appreciate your availability.",
        "recruiter@example.com",
    )
    assert result == "ACTION"


def test_triage_email_track_for_confirmation():
    result = triage_email(
        "Thank you for applying to Anthropic",
        None,
        "no-reply@us.greenhouse-mail.io",
    )
    assert result == "TRACK"


def test_triage_email_skip_for_marketing_newsletter():
    result = triage_email(
        "Platform Newsletter Roundup",
        "View in browser or unsubscribe from these promotional emails.",
        "notifications@vendor.example",
    )
    assert result == "SKIP"


# --- TestNormalizeOrg ---


def test_normalize_org_lowercases():
    assert normalize_org("Anthropic") == "anthropic"


def test_normalize_org_strips_punctuation():
    assert normalize_org("Acme, Inc.") == "acmeinc"


def test_normalize_org_strips_spaces():
    assert normalize_org("Open AI") == "openai"


def test_normalize_org_handles_special_chars():
    """Special characters are removed."""
    result = normalize_org("X.AI Corp")
    assert result == "xaicorp"


def test_normalize_org_numbers_preserved():
    """Digits are preserved."""
    assert normalize_org("Company 42") == "company42"


def test_normalize_org_empty_string():
    assert normalize_org("") == ""


# --- TestBuildOrgIndex ---


def test_build_org_index_empty_entries():
    """Empty entry list → empty index."""
    result = build_org_index([])
    assert result == {}


def test_build_org_index_groups_by_normalized_org():
    """Entries normalized to the same key are grouped together."""
    # "Anthropic" and "Anthropic " (trailing space) both normalize identically
    entries = [
        {"id": "a", "target": {"organization": "Anthropic"}},
        {"id": "b", "target": {"organization": "Anthropic"}},
    ]
    index = build_org_index(entries)
    key = normalize_org("Anthropic")
    assert key in index
    assert len(index[key]) == 2


def test_build_org_index_multiple_orgs():
    """Different orgs each get their own bucket."""
    entries = [
        {"id": "a", "target": {"organization": "Anthropic"}},
        {"id": "b", "target": {"organization": "OpenAI"}},
    ]
    index = build_org_index(entries)
    assert len(index) == 2


def test_build_org_index_skips_missing_org():
    """Entries without organization are skipped."""
    entries = [
        {"id": "a", "target": {}},
        {"id": "b", "target": {"organization": "Acme"}},
    ]
    index = build_org_index(entries)
    assert len(index) == 1


def test_build_org_index_skips_non_dict_target():
    """Entries with non-dict target are skipped."""
    entries = [
        {"id": "a", "target": None},
        {"id": "b", "target": "string"},
    ]
    index = build_org_index(entries)
    assert index == {}


# --- TestExtractCompanyFromSubject ---


def test_extract_company_greenhouse_pattern():
    """Greenhouse ATS pattern extracts company name."""
    result = extract_company_from_subject("Thank you for applying to Anthropic")
    assert result == "Anthropic"


def test_extract_company_ashby_pattern():
    """Ashby ATS pattern extracts company name."""
    result = extract_company_from_subject("Thanks for applying to Cohere")
    assert result == "Cohere"


def test_extract_company_cloudflare_override():
    """Cloudflare subject uses company override → returns 'Cloudflare'."""
    result = extract_company_from_subject(
        "Application Received - Software Engineer at Cloudflare"
    )
    assert result == "Cloudflare"


def test_extract_company_no_match_returns_none():
    """Subject not matching any ATS pattern → None."""
    result = extract_company_from_subject("General newsletter subject")
    assert result is None


def test_extract_company_strips_trailing_punctuation():
    """Trailing '!' or '.' stripped from company name."""
    result = extract_company_from_subject("Thank you for applying to Acme!")
    assert result is not None
    assert not result.endswith("!")
