"""Tests for scripts/answer_questions.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from answer_questions import (
    build_answer_prompt,
    find_fill_in_fields,
    try_auto_answer,
)


def _make_entry(
    entry_id="test-entry",
    name="Test Role",
    org="Test Corp",
    portal="greenhouse",
    framing="systems builder",
):
    """Build a minimal pipeline entry for answer question tests."""
    return {
        "id": entry_id,
        "name": name,
        "target": {"organization": org, "portal": portal},
        "fit": {"framing": framing},
        "submission": {"variant_ids": {}},
    }


# --- find_fill_in_fields ---


def test_find_fill_in_fields():
    """Parses FILL IN fields from YAML text."""
    answers = {"q1": "FILL IN", "q2": "answered already"}
    raw_text = "# Label for Q1\nq1: FILL IN\n# Label for Q2\nq2: answered already\n"
    fields = find_fill_in_fields(answers, raw_text)
    assert len(fields) == 1
    assert fields[0]["key"] == "q1"
    assert fields[0]["label"] == "Label for Q1"


# --- build_answer_prompt ---


def test_generate_answer_prompt():
    """Prompt includes question text and identity context."""
    entry = _make_entry(name="Dev Advocate", org="Acme")
    fill_fields = [
        {"key": "q1", "label": "Why do you want to work here?", "type_info": "text"},
    ]
    prompt = build_answer_prompt(entry, fill_fields, "My cover letter text")
    assert isinstance(prompt, str)
    assert "Acme" in prompt
    assert "Dev Advocate" in prompt
    assert "Why do you want to work here?" in prompt
    assert "My cover letter text" in prompt


# --- try_auto_answer ---


def test_auto_answer_matches_pattern():
    """Auto-answer matches work authorization pattern."""
    config = {"default_answers": {"work_authorization": "Yes, authorized"}}
    result = try_auto_answer("Are you authorized to work in the US?", config)
    assert result == "Yes, authorized"


def test_auto_answer_no_match():
    """Auto-answer returns None for unrecognized question."""
    config = {"default_answers": {"work_authorization": "Yes"}}
    result = try_auto_answer("What is your favorite color?", config)
    assert result is None


def test_auto_answer_empty_config():
    """Auto-answer handles empty config gracefully."""
    result = try_auto_answer("salary expectations", {})
    assert result is None
