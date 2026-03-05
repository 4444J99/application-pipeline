#!/usr/bin/env python3
"""Tests for retrospective.py — monthly retrospective prompt generator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from retrospective import build_prompt, format_prompt


def _make_entries():
    from datetime import date

    today = date.today().isoformat()
    return [
        {
            "id": "test-1",
            "status": "submitted",
            "track": "grant",
            "last_touched": today,
            "fit": {"composite": 9.2},
            "timeline": {"submitted": today},
        },
        {
            "id": "test-2",
            "status": "outcome",
            "outcome": "rejected",
            "track": "job",
            "last_touched": today,
            "fit": {"composite": 7.5},
            "timeline": {"submitted": today},
        },
    ]


class TestBuildPrompt:
    def test_returns_data_and_questions(self):
        result = build_prompt(_make_entries(), lookback_days=30)
        assert "data" in result
        assert "questions" in result
        assert len(result["questions"]) >= 5

    def test_counts_entries(self):
        result = build_prompt(_make_entries(), lookback_days=30)
        assert result["data"]["entries_touched"] == 2

    def test_includes_rejection_question(self):
        result = build_prompt(_make_entries(), lookback_days=30)
        questions_text = " ".join(result["questions"])
        assert "rejection" in questions_text.lower()

    def test_empty_entries(self):
        result = build_prompt([], lookback_days=30)
        assert result["data"]["entries_touched"] == 0


class TestFormatPrompt:
    def test_contains_header(self):
        result = build_prompt(_make_entries(), lookback_days=30)
        text = format_prompt(result)
        assert "MONTHLY RETROSPECTIVE" in text
        assert "REFLECTION QUESTIONS" in text
