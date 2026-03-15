"""Tests for scripts/standup_constants.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from standup_constants import OUTREACH_BY_STATUS, PRACTICES_BY_CONTEXT, SECTIONS, build_next_status


def test_constants_have_expected_sections():
    assert "research" in OUTREACH_BY_STATUS
    assert "pre_deadline_week" in PRACTICES_BY_CONTEXT
    assert "health" in SECTIONS
    assert "jobfreshness" in SECTIONS


def test_build_next_status_filters_by_valid_transitions():
    transitions = {
        "research": {"qualified"},
        "qualified": {"drafting"},
        "drafting": {"staged"},
        "staged": {"submitted"},
        "submitted": {"acknowledged"},
    }
    next_map = build_next_status(transitions)
    assert next_map["research"] == "qualified"
    assert next_map["staged"] == "submitted"
    assert "submitted" not in next_map  # forward path stops at submitted


def test_section_names_are_nonempty_strings():
    for key, description in SECTIONS.items():
        assert isinstance(key, str) and len(key) > 0, "section key must be non-empty string"
        assert isinstance(description, str) and len(description) > 0, f"section '{key}' description must be non-empty"


def test_section_keys_are_unique():
    keys = list(SECTIONS.keys())
    assert len(keys) == len(set(keys)), "duplicate section keys found"

