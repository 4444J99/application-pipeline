#!/usr/bin/env python3
"""Tests for interview_prep.py — interview preparation generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from interview_prep import (
    STAR_QUESTIONS,
    generate_prep,
)


class TestStarQuestions:
    def test_all_positions_have_questions(self):
        positions = [
            "independent-engineer", "systems-artist", "educator",
            "creative-technologist", "community-practitioner",
        ]
        for pos in positions:
            assert pos in STAR_QUESTIONS
            assert len(STAR_QUESTIONS[pos]) >= 3

    def test_questions_are_strings(self):
        for pos, questions in STAR_QUESTIONS.items():
            for q in questions:
                assert isinstance(q, str)
                assert q.endswith(".")


class TestGeneratePrep:
    def test_entry_not_found(self):
        prep = generate_prep("nonexistent-entry-12345")
        assert "not found" in prep.lower()

    def test_prep_contains_sections(self, monkeypatch):
        """Mock load_entry_by_id to test prep generation."""
        import interview_prep as mod

        mock_entry = {
            "id": "test-role",
            "name": "Test Role",
            "status": "interview",
            "track": "job",
            "fit": {"score": 9.0, "identity_position": "independent-engineer"},
            "target": {"organization": "TestCo", "application_url": "https://example.com"},
            "amount": {"value": "150000", "type": "salary"},
        }

        monkeypatch.setattr(mod, "load_entry_by_id", lambda eid: (Path("/fake"), mock_entry))
        # Stub out org_intel and skills_gap imports that would fail
        monkeypatch.setattr(mod, "_load_org_intel", lambda org: None)
        monkeypatch.setattr(mod, "_load_skills_gap", lambda entry: None)
        monkeypatch.setattr(mod, "_get_blocks_content", lambda entry: [])

        prep = generate_prep("test-role")
        assert "# Interview Prep: Test Role" in prep
        assert "## Role Overview" in prep
        assert "## STAR Question Bank" in prep
        assert "## Key Metrics to Reference" in prep
        assert "103 repositories" in prep
        assert "TestCo" in prep
