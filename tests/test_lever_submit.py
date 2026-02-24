"""Tests for scripts/lever_submit.py URL parsing and answer system."""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lever_submit import (
    auto_fill_answers,
    get_custom_questions,
    generate_answer_template,
    load_answers,
    merge_answers,
    parse_lever_url,
    validate_answers,
)


# ---------------------------------------------------------------------------
# parse_lever_url
# ---------------------------------------------------------------------------


def test_parse_lever_url_valid_us():
    """parse_lever_url extracts company and posting ID from a US URL."""
    url = "https://jobs.lever.co/acmecorp/abc12345-def6-7890-abcd-ef1234567890"
    result = parse_lever_url(url)
    assert result is not None
    company, posting_id, is_eu = result
    assert company == "acmecorp"
    assert posting_id == "abc12345-def6-7890-abcd-ef1234567890"
    assert is_eu is False


def test_parse_lever_url_valid_eu():
    """parse_lever_url extracts company and posting ID from an EU URL."""
    url = "https://jobs.eu.lever.co/eurocompany/aaa11111-bbb2-3333-cccc-dddddddddddd"
    result = parse_lever_url(url)
    assert result is not None
    company, posting_id, is_eu = result
    assert company == "eurocompany"
    assert posting_id == "aaa11111-bbb2-3333-cccc-dddddddddddd"
    assert is_eu is True


def test_parse_lever_url_invalid():
    """parse_lever_url returns None for non-Lever URLs."""
    assert parse_lever_url("https://example.com/jobs/123") is None
    assert parse_lever_url("https://greenhouse.io/acme/123") is None


def test_parse_lever_url_empty():
    """parse_lever_url returns None for empty string."""
    assert parse_lever_url("") is None


# ---------------------------------------------------------------------------
# get_custom_questions
# ---------------------------------------------------------------------------


def test_get_custom_questions_filters_empty():
    """get_custom_questions skips questions with empty text."""
    questions = [
        {"text": ""},
        {"text": "Why do you want this role?", "required": True},
    ]
    result = get_custom_questions(questions)
    assert len(result) == 1
    assert result[0]["text"] == "Why do you want this role?"


def test_get_custom_questions_empty_input():
    """get_custom_questions returns empty list for empty input."""
    assert get_custom_questions([]) == []


# ---------------------------------------------------------------------------
# validate_answers
# ---------------------------------------------------------------------------


def test_validate_answers_required_missing():
    """validate_answers reports missing required questions."""
    questions = [
        {"text": "Are you authorized to work?", "required": True},
    ]
    errors = validate_answers(questions, {})
    assert len(errors) == 1
    assert "MISSING required" in errors[0]


def test_validate_answers_required_present():
    """validate_answers returns no errors when all required answered."""
    questions = [
        {"text": "Are you authorized to work?", "required": True},
    ]
    errors = validate_answers(questions, {"Are you authorized to work?": "Yes"})
    assert errors == []


def test_validate_answers_fill_in_placeholder():
    """validate_answers treats 'FILL IN' as empty."""
    questions = [
        {"text": "Location", "required": True},
    ]
    errors = validate_answers(questions, {"Location": "FILL IN"})
    assert len(errors) == 1
    assert "EMPTY required" in errors[0]


def test_validate_answers_optional_skipped():
    """validate_answers does not flag optional questions."""
    questions = [
        {"text": "Anything else?", "required": False},
    ]
    errors = validate_answers(questions, {})
    assert errors == []


# ---------------------------------------------------------------------------
# merge_answers
# ---------------------------------------------------------------------------


def test_merge_answers_file_takes_precedence():
    """merge_answers gives file answers precedence over auto-fill."""
    auto = {"q1": "auto-value", "q2": "auto-only"}
    file_ans = {"q1": "manual-override"}
    result = merge_answers(auto, file_ans)
    assert result["q1"] == "manual-override"
    assert result["q2"] == "auto-only"


def test_merge_answers_no_file():
    """merge_answers works when file answers are None."""
    auto = {"q1": "value"}
    result = merge_answers(auto, None)
    assert result == {"q1": "value"}


# ---------------------------------------------------------------------------
# auto_fill_answers
# ---------------------------------------------------------------------------


def test_auto_fill_portfolio_url():
    """auto_fill_answers maps portfolio questions to submission URL."""
    questions = [
        {"text": "Personal Website or Portfolio URL", "required": False},
    ]
    config = {"linkedin": "", "pronouns": "", "location": "", "name_pronunciation": ""}
    entry = {"submission": {"portfolio_url": "https://example.com/portfolio"}}
    result = auto_fill_answers(questions, config, entry)
    assert result.get("Personal Website or Portfolio URL") == "https://example.com/portfolio"


def test_auto_fill_location():
    """auto_fill_answers maps location questions to config value."""
    questions = [
        {"text": "Where are you located?", "required": False},
    ]
    config = {"location": "New York, NY"}
    entry = {}
    result = auto_fill_answers(questions, config, entry)
    assert result.get("Where are you located?") == "New York, NY"


# ---------------------------------------------------------------------------
# generate_answer_template
# ---------------------------------------------------------------------------


def test_generate_answer_template_structure():
    """generate_answer_template produces YAML with header comments and entries."""
    questions = [
        {"text": "Why this role?", "required": True},
        {"text": "Anything else?", "required": False},
    ]
    auto_filled = {}
    result = generate_answer_template(
        "test-entry", "Test Entry", "testco", "abc-123",
        questions, auto_filled,
    )
    assert "# Generated for: Test Entry" in result
    assert "# Posting: testco/abc-123" in result
    assert "Why this role?" in result
    assert "FILL IN" in result
    assert "Required" in result


# ---------------------------------------------------------------------------
# load_answers
# ---------------------------------------------------------------------------


def test_load_answers_filters_fill_in(tmp_path, monkeypatch):
    """load_answers strips 'FILL IN' placeholders and None values."""
    import lever_submit

    answer_file = tmp_path / "test-entry.yaml"
    answer_file.write_text(
        '"question one": "real answer"\n'
        '"question two": "FILL IN"\n'
        '"question three": null\n'
        '"question four": "another answer"\n'
    )
    monkeypatch.setattr(lever_submit, "ANSWERS_DIR", tmp_path)
    result = load_answers("test-entry")
    assert result == {"question one": "real answer", "question four": "another answer"}


def test_load_answers_missing_file(tmp_path, monkeypatch):
    """load_answers returns None when the answer file does not exist."""
    import lever_submit

    monkeypatch.setattr(lever_submit, "ANSWERS_DIR", tmp_path)
    assert load_answers("nonexistent-entry") is None
