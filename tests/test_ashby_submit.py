"""Tests for scripts/ashby_submit.py URL parsing and answer system."""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ashby_submit import (
    auto_fill_answers,
    build_field_submissions,
    field_type_label,
    get_custom_fields,
    generate_answer_template,
    is_standard_field,
    load_answers,
    merge_answers,
    parse_ashby_url,
    validate_answers,
)


# ---------------------------------------------------------------------------
# parse_ashby_url
# ---------------------------------------------------------------------------


def test_parse_ashby_url_valid():
    """parse_ashby_url extracts company and posting ID from a valid URL."""
    url = "https://jobs.ashbyhq.com/cohere/1fa01a03-9253-4f62-8f10-0fe368b38cb9"
    result = parse_ashby_url(url)
    assert result is not None
    company, posting_id = result
    assert company == "cohere"
    assert posting_id == "1fa01a03-9253-4f62-8f10-0fe368b38cb9"


def test_parse_ashby_url_invalid():
    """parse_ashby_url returns None for non-Ashby URLs."""
    assert parse_ashby_url("https://example.com/jobs/123") is None
    assert parse_ashby_url("https://lever.co/acme/abc") is None


def test_parse_ashby_url_empty():
    """parse_ashby_url returns None for empty string."""
    assert parse_ashby_url("") is None


# ---------------------------------------------------------------------------
# is_standard_field / get_custom_fields
# ---------------------------------------------------------------------------


def test_is_standard_field_system_fields():
    """is_standard_field identifies system fields."""
    assert is_standard_field({"path": "_systemfield_name", "type": "String"}) is True
    assert is_standard_field({"path": "_systemfield_email", "type": "Email"}) is True
    assert is_standard_field({"path": "_systemfield_phone", "type": "Phone"}) is True


def test_is_standard_field_file_type():
    """is_standard_field identifies file upload fields as standard."""
    assert is_standard_field({"path": "resume_field", "type": "File"}) is True


def test_is_standard_field_custom():
    """is_standard_field returns False for custom fields."""
    assert is_standard_field({"path": "custom_q1", "type": "String"}) is False


def test_get_custom_fields_filters():
    """get_custom_fields excludes standard fields."""
    fields = [
        {"path": "_systemfield_name", "type": "String", "title": "Name"},
        {"path": "_systemfield_email", "type": "Email", "title": "Email"},
        {"path": "resume_upload", "type": "File", "title": "Resume"},
        {"path": "custom_q1", "type": "String", "title": "Why us?"},
    ]
    result = get_custom_fields(fields)
    assert len(result) == 1
    assert result[0]["path"] == "custom_q1"


# ---------------------------------------------------------------------------
# field_type_label
# ---------------------------------------------------------------------------


def test_field_type_label_known_types():
    """field_type_label maps known Ashby types to readable labels."""
    assert field_type_label({"type": "String"}) == "text"
    assert field_type_label({"type": "LongText"}) == "textarea"
    assert field_type_label({"type": "ValueSelect"}) == "select"
    assert field_type_label({"type": "Boolean"}) == "boolean"


def test_field_type_label_unknown():
    """field_type_label passes through unrecognized types."""
    assert field_type_label({"type": "Custom"}) == "Custom"
    assert field_type_label({}) == "unknown"


# ---------------------------------------------------------------------------
# validate_answers
# ---------------------------------------------------------------------------


def test_validate_answers_required_missing():
    """validate_answers reports missing required fields."""
    fields = [
        {"path": "q1", "title": "Auth?", "isRequired": True, "type": "String"},
    ]
    errors = validate_answers(fields, {})
    assert len(errors) == 1
    assert "MISSING required" in errors[0]
    assert "Auth?" in errors[0]


def test_validate_answers_required_present():
    """validate_answers returns no errors when all required fields answered."""
    fields = [
        {"path": "q1", "title": "Auth?", "isRequired": True, "type": "String"},
    ]
    errors = validate_answers(fields, {"q1": "Yes"})
    assert errors == []


def test_validate_answers_fill_in_placeholder():
    """validate_answers treats 'FILL IN' as empty."""
    fields = [
        {"path": "q1", "title": "Location", "isRequired": True, "type": "String"},
    ]
    errors = validate_answers(fields, {"q1": "FILL IN"})
    assert len(errors) == 1
    assert "EMPTY required" in errors[0]


def test_validate_answers_optional_skipped():
    """validate_answers does not flag optional fields."""
    fields = [
        {"path": "q1", "title": "Optional?", "isRequired": False, "type": "String"},
    ]
    errors = validate_answers(fields, {})
    assert errors == []


# ---------------------------------------------------------------------------
# merge_answers
# ---------------------------------------------------------------------------


def test_merge_answers_file_takes_precedence():
    """merge_answers gives file answers precedence over auto-fill."""
    auto = {"q1": "auto", "q2": "auto-only"}
    file_ans = {"q1": "manual"}
    result = merge_answers(auto, file_ans)
    assert result["q1"] == "manual"
    assert result["q2"] == "auto-only"


def test_merge_answers_no_file():
    """merge_answers works when file answers are None."""
    result = merge_answers({"q1": "val"}, None)
    assert result == {"q1": "val"}


# ---------------------------------------------------------------------------
# auto_fill_answers
# ---------------------------------------------------------------------------


def test_auto_fill_portfolio_url():
    """auto_fill_answers maps portfolio fields to submission URL."""
    fields = [
        {"path": "portfolio_q", "title": "Portfolio URL", "type": "String"},
    ]
    config = {"linkedin": "", "pronouns": "", "location": "", "name_pronunciation": ""}
    entry = {"submission": {"portfolio_url": "https://example.com"}}
    result = auto_fill_answers(fields, config, entry)
    assert result.get("portfolio_q") == "https://example.com"


def test_auto_fill_location():
    """auto_fill_answers maps location fields to config value."""
    fields = [
        {"path": "loc_q", "title": "Where are you based?", "type": "String"},
    ]
    config = {"location": "NYC"}
    entry = {}
    result = auto_fill_answers(fields, config, entry)
    assert result.get("loc_q") == "NYC"


# ---------------------------------------------------------------------------
# generate_answer_template
# ---------------------------------------------------------------------------


def test_generate_answer_template_structure():
    """generate_answer_template produces YAML with header comments and entries."""
    fields = [
        {"path": "q1", "title": "Why us?", "isRequired": True, "type": "LongText"},
        {
            "path": "q2", "title": "Work auth?", "isRequired": True,
            "type": "ValueSelect",
            "selectableValues": [
                {"label": "Yes", "value": "yes"},
                {"label": "No", "value": "no"},
            ],
        },
    ]
    result = generate_answer_template(
        "test-entry", "Test Entry", "testco", "abc-123",
        fields, {},
    )
    assert "# Generated for: Test Entry" in result
    assert "q1" in result
    assert "q2" in result
    assert "FILL IN" in result
    assert "Options: Yes, No" in result


# ---------------------------------------------------------------------------
# build_field_submissions
# ---------------------------------------------------------------------------


def test_build_field_submissions_basic():
    """build_field_submissions includes standard and custom fields."""
    fields = [
        {"path": "_systemfield_name", "type": "String"},
        {"path": "custom_q", "title": "Why?", "type": "String"},
    ]
    config = {"first_name": "John", "last_name": "Doe", "email": "john@test.com"}
    entry = {}
    answers = {"custom_q": "Because reasons"}
    result = build_field_submissions(fields, config, entry, answers)
    paths = {s["path"] for s in result}
    assert "_systemfield_name" in paths
    assert "_systemfield_email" in paths
    assert "custom_q" in paths
    name_sub = next(s for s in result if s["path"] == "_systemfield_name")
    assert name_sub["value"] == "John Doe"


def test_build_field_submissions_select_resolution():
    """build_field_submissions resolves select values by label."""
    fields = [
        {
            "path": "auth_q", "title": "Work auth?", "type": "ValueSelect",
            "selectableValues": [
                {"label": "Yes", "value": "authorized_yes"},
                {"label": "No", "value": "authorized_no"},
            ],
        },
    ]
    config = {"first_name": "J", "last_name": "D", "email": "j@t.com"}
    answers = {"auth_q": "Yes"}
    result = build_field_submissions(fields, config, {}, answers)
    auth_sub = next(s for s in result if s["path"] == "auth_q")
    assert auth_sub["value"] == "authorized_yes"


# ---------------------------------------------------------------------------
# load_answers
# ---------------------------------------------------------------------------


def test_load_answers_filters_fill_in(tmp_path, monkeypatch):
    """load_answers strips 'FILL IN' placeholders and None values."""
    import ashby_submit

    answer_file = tmp_path / "test-entry.yaml"
    answer_file.write_text(
        'field_a: "real answer"\n'
        'field_b: "FILL IN"\n'
        "field_c: null\n"
        'field_d: "another answer"\n'
    )
    monkeypatch.setattr(ashby_submit, "ANSWERS_DIR", tmp_path)
    result = load_answers("test-entry")
    assert result == {"field_a": "real answer", "field_d": "another answer"}


def test_load_answers_missing_file(tmp_path, monkeypatch):
    """load_answers returns None when the answer file does not exist."""
    import ashby_submit

    monkeypatch.setattr(ashby_submit, "ANSWERS_DIR", tmp_path)
    assert load_answers("nonexistent-entry") is None
