"""Tests for shared dynamic answer resolution utilities in scripts/ats_base.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ats_base import (
    auto_fill_answer,
    build_normalized_answer_index,
    clean_answer_mapping,
    find_dynamic_answer,
    load_answers_yaml,
    match_default_answer,
    normalize_text,
    resolve_select_value,
)


def test_normalize_text_collapses_punctuation_and_case():
    assert normalize_text("  Work Authorization? (US)  ") == "work authorization us"


def test_match_default_answer_from_config():
    config = {"default_answers": {"work_authorization": "Yes, fully authorized"}}
    answer = match_default_answer("Are you legally authorized to work in the US?", config)
    assert answer == "Yes, fully authorized"


def test_auto_fill_answer_falls_back_to_default_answers():
    config = {"default_answers": {"visa_sponsorship": "No sponsorship required"}}
    answer = auto_fill_answer("Will you require visa sponsorship?", config, portfolio_url="")
    assert answer == "No sponsorship required"


def test_auto_fill_answer_prefers_default_over_generic_location_match():
    config = {
        "location": "New York City",
        "default_answers": {"visa_sponsorship": "No"},
    }
    label = "Will you now or in the future require sponsorship for a visa to remain in your current location?"
    answer = auto_fill_answer(label, config, portfolio_url="")
    assert answer == "No"


def test_auto_fill_answer_privacy_acknowledgement():
    config = {}
    answer = auto_fill_answer("Please review and acknowledge the candidate privacy policy", config, portfolio_url="")
    assert answer == "Acknowledge/Confirm"


def test_find_dynamic_answer_prefixed_label_and_normalized_alias():
    answers = {
        "label::Are you authorized to work in the U.S.": "Yes",
    }
    index = build_normalized_answer_index(answers)
    value = find_dynamic_answer(
        answers,
        field_key="question_12345",
        label="Are you authorized to work in the US?",
        normalized_index=index,
    )
    assert value == "Yes"


def test_resolve_select_value_supports_short_yes_no_alias():
    options = [
        {"label": "Yes - Authorized", "value": 1},
        {"label": "No - Need Sponsorship", "value": 0},
    ]
    assert resolve_select_value("yes", options) == 1
    assert resolve_select_value("no", options) == 0


def test_clean_answer_mapping_filters_placeholders():
    raw = {
        "a": "ok",
        "b": "FILL IN",
        "c": None,
        "d": "   ",
    }
    assert clean_answer_mapping(raw) == {"a": "ok"}


def test_load_answers_yaml_parse_error_returns_none(tmp_path, capsys):
    path = tmp_path / "bad.yaml"
    path.write_text("field: [not closed")
    result = load_answers_yaml(path)
    captured = capsys.readouterr()
    assert result is None
    assert "Could not parse answer file" in captured.err
