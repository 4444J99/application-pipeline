"""Tests for scripts/greenhouse_submit.py custom question answer system."""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from greenhouse_submit import (
    auto_fill_answers,
    field_type_label,
    generate_answer_template,
    get_custom_questions,
    load_answers,
    merge_answers,
    parse_greenhouse_url,
    resolve_select_value,
    validate_answers,
)


# ---------------------------------------------------------------------------
# parse_greenhouse_url
# ---------------------------------------------------------------------------


def test_parse_greenhouse_url_valid():
    """parse_greenhouse_url extracts board token and job ID from a valid URL."""
    url = "https://job-boards.greenhouse.io/acmecorp/jobs/4567890"
    result = parse_greenhouse_url(url)
    assert result == ("acmecorp", "4567890")


def test_parse_greenhouse_url_with_query_params():
    """parse_greenhouse_url handles URLs with trailing query params."""
    url = "https://job-boards.greenhouse.io/acmecorp/jobs/123456?gh_jid=123456"
    result = parse_greenhouse_url(url)
    assert result == ("acmecorp", "123456")


def test_parse_greenhouse_url_invalid():
    """parse_greenhouse_url returns None for non-Greenhouse URLs."""
    assert parse_greenhouse_url("https://example.com/jobs/123") is None
    assert parse_greenhouse_url("https://lever.co/acme/jobs/abc") is None


def test_parse_greenhouse_url_empty():
    """parse_greenhouse_url returns None for empty string."""
    assert parse_greenhouse_url("") is None


# ---------------------------------------------------------------------------
# resolve_select_value
# ---------------------------------------------------------------------------


def test_resolve_select_value_match_by_label():
    """resolve_select_value returns integer value when label matches."""
    values = [
        {"label": "Yes", "value": 1},
        {"label": "No", "value": 0},
    ]
    assert resolve_select_value("Yes", values) == 1
    assert resolve_select_value("No", values) == 0


def test_resolve_select_value_case_insensitive():
    """resolve_select_value matches labels case-insensitively."""
    values = [{"label": "Remote", "value": 42}]
    assert resolve_select_value("remote", values) == 42


def test_resolve_select_value_match_by_value():
    """resolve_select_value falls back to matching against the value itself."""
    values = [
        {"label": "Option A", "value": 10},
        {"label": "Option B", "value": 20},
    ]
    assert resolve_select_value("10", values) == 10


def test_resolve_select_value_no_match():
    """resolve_select_value returns None when nothing matches."""
    values = [{"label": "Yes", "value": 1}]
    assert resolve_select_value("Maybe", values) is None


def test_resolve_select_value_empty_values():
    """resolve_select_value returns the original string when values list is empty."""
    assert resolve_select_value("anything", []) == "anything"


# ---------------------------------------------------------------------------
# get_custom_questions
# ---------------------------------------------------------------------------


def test_get_custom_questions_filters_standard():
    """get_custom_questions excludes questions whose fields are all standard."""
    questions = [
        {
            "label": "First Name",
            "required": True,
            "fields": [{"name": "first_name", "type": "input_text"}],
        },
        {
            "label": "Email",
            "required": True,
            "fields": [{"name": "email", "type": "input_text"}],
        },
        {
            "label": "How did you hear about us?",
            "required": False,
            "fields": [{"name": "question_12345", "type": "input_text"}],
        },
    ]
    result = get_custom_questions(questions)
    assert len(result) == 1
    assert result[0]["label"] == "How did you hear about us?"


def test_get_custom_questions_empty_input():
    """get_custom_questions returns empty list for empty input."""
    assert get_custom_questions([]) == []


# ---------------------------------------------------------------------------
# field_type_label
# ---------------------------------------------------------------------------


def test_field_type_label_known_types():
    """field_type_label maps known Greenhouse types to readable labels."""
    assert field_type_label({"type": "input_text"}) == "text"
    assert field_type_label({"type": "textarea"}) == "textarea"
    assert field_type_label({"type": "multi_value_single_select"}) == "select"
    assert field_type_label({"type": "input_file"}) == "file"


def test_field_type_label_unknown_type():
    """field_type_label passes through unrecognized types as-is."""
    assert field_type_label({"type": "checkbox"}) == "checkbox"
    assert field_type_label({}) == "unknown"


# ---------------------------------------------------------------------------
# validate_answers
# ---------------------------------------------------------------------------


def test_validate_answers_required_missing():
    """validate_answers reports missing required fields."""
    questions = [
        {
            "label": "Pronouns",
            "required": True,
            "fields": [{"name": "question_001", "type": "input_text"}],
        },
    ]
    errors = validate_answers(questions, {})
    assert len(errors) == 1
    assert "MISSING required" in errors[0]
    assert "Pronouns" in errors[0]


def test_validate_answers_required_present():
    """validate_answers returns no errors when all required fields are answered."""
    questions = [
        {
            "label": "Pronouns",
            "required": True,
            "fields": [{"name": "question_001", "type": "input_text"}],
        },
    ]
    errors = validate_answers(questions, {"question_001": "they/them"})
    assert errors == []


def test_validate_answers_fill_in_placeholder():
    """validate_answers treats 'FILL IN' as empty."""
    questions = [
        {
            "label": "Location",
            "required": True,
            "fields": [{"name": "question_002", "type": "input_text"}],
        },
    ]
    errors = validate_answers(questions, {"question_002": "FILL IN"})
    assert len(errors) == 1
    assert "EMPTY required" in errors[0]


def test_validate_answers_optional_skipped():
    """validate_answers does not flag optional questions as missing."""
    questions = [
        {
            "label": "Favorite color",
            "required": False,
            "fields": [{"name": "question_003", "type": "input_text"}],
        },
    ]
    errors = validate_answers(questions, {})
    assert errors == []


# ---------------------------------------------------------------------------
# merge_answers
# ---------------------------------------------------------------------------


def test_merge_answers_file_takes_precedence():
    """merge_answers gives file answers precedence over auto-fill."""
    auto = {"field_a": "auto-value", "field_b": "auto-only"}
    file_ans = {"field_a": "manual-override"}
    result = merge_answers(auto, file_ans)
    assert result["field_a"] == "manual-override"
    assert result["field_b"] == "auto-only"


def test_merge_answers_no_file():
    """merge_answers works when file answers are None."""
    auto = {"field_x": "value"}
    result = merge_answers(auto, None)
    assert result == {"field_x": "value"}


# ---------------------------------------------------------------------------
# auto_fill_answers
# ---------------------------------------------------------------------------


def test_auto_fill_portfolio_url():
    """auto_fill_answers maps portfolio/website questions to submission URL."""
    questions = [
        {
            "label": "Personal Website or Portfolio URL",
            "required": False,
            "fields": [{"name": "question_web", "type": "input_text"}],
        },
    ]
    config = {"linkedin": "", "pronouns": "", "location": "", "name_pronunciation": ""}
    entry = {"submission": {"portfolio_url": "https://example.com/portfolio"}}
    result = auto_fill_answers(questions, config, entry)
    assert result.get("question_web") == "https://example.com/portfolio"


def test_auto_fill_linkedin():
    """auto_fill_answers maps LinkedIn questions to config value."""
    questions = [
        {
            "label": "LinkedIn Profile",
            "required": False,
            "fields": [{"name": "question_li", "type": "input_text"}],
        },
    ]
    config = {"linkedin": "https://linkedin.com/in/test"}
    entry = {}
    result = auto_fill_answers(questions, config, entry)
    assert result.get("question_li") == "https://linkedin.com/in/test"


def test_auto_fill_pronouns():
    """auto_fill_answers maps pronoun questions to config value."""
    questions = [
        {
            "label": "What are your pronouns?",
            "required": False,
            "fields": [{"name": "question_pn", "type": "input_text"}],
        },
    ]
    config = {"pronouns": "they/them"}
    entry = {}
    result = auto_fill_answers(questions, config, entry)
    assert result.get("question_pn") == "they/them"


def test_auto_fill_location():
    """auto_fill_answers maps location questions to config value."""
    questions = [
        {
            "label": "Where are you located?",
            "required": False,
            "fields": [{"name": "question_loc", "type": "input_text"}],
        },
    ]
    config = {"location": "New York, NY"}
    entry = {}
    result = auto_fill_answers(questions, config, entry)
    assert result.get("question_loc") == "New York, NY"


# ---------------------------------------------------------------------------
# generate_answer_template
# ---------------------------------------------------------------------------


def test_generate_answer_template_structure():
    """generate_answer_template produces YAML with header comments and field entries."""
    questions = [
        {
            "label": "Why do you want this role?",
            "required": True,
            "fields": [{"name": "question_why", "type": "textarea"}],
        },
        {
            "label": "Work authorization",
            "required": True,
            "fields": [
                {
                    "name": "question_auth",
                    "type": "multi_value_single_select",
                    "values": [
                        {"label": "Yes", "value": 1},
                        {"label": "No", "value": 0},
                    ],
                },
            ],
        },
    ]
    auto_filled = {}
    result = generate_answer_template(
        "test-entry", "Test Entry", "testboard", "99999",
        questions, auto_filled,
    )
    assert "# Generated for: Test Entry" in result
    assert "# Job: testboard/99999" in result
    assert "question_why" in result
    assert "question_auth" in result
    assert "FILL IN" in result
    assert "Required" in result
    assert "Options: Yes, No" in result


def test_generate_answer_template_auto_filled():
    """generate_answer_template uses auto-filled values instead of FILL IN."""
    questions = [
        {
            "label": "LinkedIn",
            "required": False,
            "fields": [{"name": "question_li", "type": "input_text"}],
        },
    ]
    auto_filled = {"question_li": "https://linkedin.com/in/test"}
    result = generate_answer_template(
        "test-entry", "Test Entry", "board", "111",
        questions, auto_filled,
    )
    assert "https://linkedin.com/in/test" in result
    # Should not show FILL IN for auto-filled fields
    lines = result.split("\n")
    li_line = [l for l in lines if l.startswith("question_li:")][0]
    assert "FILL IN" not in li_line


# ---------------------------------------------------------------------------
# load_answers
# ---------------------------------------------------------------------------


def test_load_answers_filters_fill_in(tmp_path, monkeypatch):
    """load_answers strips 'FILL IN' placeholders and None values."""
    import greenhouse_submit

    answer_file = tmp_path / "test-entry.yaml"
    answer_file.write_text(
        'field_a: "real answer"\n'
        'field_b: "FILL IN"\n'
        "field_c: null\n"
        'field_d: "another answer"\n'
    )
    monkeypatch.setattr(greenhouse_submit, "ANSWERS_DIR", tmp_path)
    result = load_answers("test-entry")
    assert result == {"field_a": "real answer", "field_d": "another answer"}


def test_load_answers_missing_file(tmp_path, monkeypatch):
    """load_answers returns None when the answer file does not exist."""
    import greenhouse_submit

    monkeypatch.setattr(greenhouse_submit, "ANSWERS_DIR", tmp_path)
    assert load_answers("nonexistent-entry") is None
