"""Tests for generate_ratings.py — multi-model IRA rating session."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_ratings import (
    build_system_prompt,
    call_model,
    load_panel_config,
    load_personas,
    validate_response,
)


class TestPanelConfig:
    def test_panel_config_loads(self):
        """Panel config from rubric has required fields."""
        panel = load_panel_config()
        assert len(panel) >= 4
        for rater in panel:
            assert "rater_id" in rater
            assert "model" in rater
            assert "provider" in rater
            assert "persona" in rater
            assert "temperature" in rater

    def test_persona_prompts_load(self):
        """All personas referenced in panel exist in rater-personas.yaml."""
        panel = load_panel_config()
        personas = load_personas()
        for rater in panel:
            persona_key = rater["persona"]
            assert persona_key in personas, f"Missing persona: {persona_key}"
            assert "role" in personas[persona_key]
            assert "scoring_bias" in personas[persona_key]


class TestResponseValidation:
    def test_response_parsing_valid_json(self):
        """Valid model response parsed into rating schema."""
        response = {
            "architecture": {"score": 8.0, "confidence": "medium", "evidence": "test"},
            "documentation": {"score": 7.5, "confidence": "high", "evidence": "test"},
            "analytics_intelligence": {"score": 8.5, "confidence": "medium", "evidence": "test"},
            "sustainability": {"score": 7.0, "confidence": "medium", "evidence": "test"},
        }
        assert validate_response(response) is True

    def test_response_parsing_malformed(self):
        """Missing dimensions rejected."""
        response = {
            "architecture": {"score": 8.0, "confidence": "medium", "evidence": "test"},
            # Missing 3 dimensions
        }
        assert validate_response(response) is False

    def test_response_out_of_range(self):
        """Score outside 1.0-10.0 rejected."""
        response = {
            "architecture": {"score": 15.0, "confidence": "medium", "evidence": "test"},
            "documentation": {"score": 7.5, "confidence": "high", "evidence": "test"},
            "analytics_intelligence": {"score": 8.5, "confidence": "medium", "evidence": "test"},
            "sustainability": {"score": 7.0, "confidence": "medium", "evidence": "test"},
        }
        assert validate_response(response) is False
