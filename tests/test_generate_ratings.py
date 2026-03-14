"""Tests for generate_ratings.py — multi-model IRA rating session."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_ratings import (
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


class TestAPIIntegration:
    def test_call_anthropic_formats_request(self, monkeypatch):
        """Anthropic API call builds correct message structure."""
        captured = {}

        import generate_ratings

        def fake_anthropic(model, system_prompt, user_prompt, temperature):
            captured.update({"model": model, "system": system_prompt, "user": user_prompt, "temperature": temperature})
            return {
                "architecture": {"score": 8.0, "confidence": "high", "evidence": "test"},
                "documentation": {"score": 7.0, "confidence": "high", "evidence": "test"},
                "analytics_intelligence": {"score": 8.5, "confidence": "high", "evidence": "test"},
                "sustainability": {"score": 7.5, "confidence": "high", "evidence": "test"},
            }

        monkeypatch.setattr(generate_ratings, "_call_anthropic", fake_anthropic)
        result = call_model("anthropic", "claude-opus-4-6", "sys", "user", 0.7)
        assert captured["model"] == "claude-opus-4-6"
        assert captured["temperature"] == 0.7
        assert "architecture" in result

    def test_call_google_formats_request(self, monkeypatch):
        """Google API call builds correct message structure."""
        captured = {}

        import generate_ratings

        def fake_google(model, system_prompt, user_prompt, temperature):
            captured.update({"model": model, "temperature": temperature})
            return {
                "architecture": {"score": 7.5, "confidence": "high", "evidence": "test"},
                "documentation": {"score": 8.0, "confidence": "high", "evidence": "test"},
                "analytics_intelligence": {"score": 7.0, "confidence": "high", "evidence": "test"},
                "sustainability": {"score": 6.5, "confidence": "high", "evidence": "test"},
            }

        monkeypatch.setattr(generate_ratings, "_call_google", fake_google)
        result = call_model("google", "gemini-2.0-flash", "sys", "user", 0.7)
        assert captured["model"] == "gemini-2.0-flash"
        assert "architecture" in result


class TestDryRun:
    def test_dry_run_no_api_calls(self, monkeypatch):
        """--dry-run prints prompts without making any API calls."""
        api_called = {"count": 0}

        import generate_ratings

        def fake_call(*args, **kwargs):
            api_called["count"] += 1
            return {}

        monkeypatch.setattr(generate_ratings, "call_model", fake_call)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        monkeypatch.setenv("GOOGLE_API_KEY", "fake")
        result = generate_ratings.generate_ratings(dry_run=True)

        assert result["status"] == "dry_run"
        assert api_called["count"] == 0
        assert len(result["raters"]) >= 4


class TestAPIKeyCheck:
    def test_missing_api_key_error(self, monkeypatch):
        """Clear error when ANTHROPIC_API_KEY is missing."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        import generate_ratings

        result = generate_ratings.generate_ratings()

        assert result["status"] == "error"
        assert "API_KEY" in result["error"]


class TestObjectiveSharing:
    def test_objective_scores_shared(self, tmp_path, monkeypatch):
        """Objective ground truth injected into all rater outputs identically."""
        import generate_ratings
        from diagnose import OBJECTIVE_DIMENSIONS

        # Mock ratings dir to tmp
        monkeypatch.setattr(generate_ratings, "RATINGS_DIR", tmp_path / "ratings")

        # Mock collectors to return known values
        fake_objective = {
            "test_coverage": {"score": 10.0, "evidence": "fake"},
            "code_quality": {"score": 9.0, "evidence": "fake"},
            "data_integrity": {"score": 10.0, "evidence": "fake"},
            "operational_maturity": {"score": 8.0, "evidence": "fake"},
            "claim_provenance": {"score": 5.0, "evidence": "fake"},
        }
        monkeypatch.setattr(generate_ratings, "COLLECTORS", {k: (lambda v=v: v) for k, v in fake_objective.items()})

        # Mock prompt generators
        monkeypatch.setattr(
            generate_ratings,
            "PROMPT_GENERATORS",
            {d: (lambda: "fake evidence") for d in ["architecture", "documentation", "analytics_intelligence", "sustainability"]},
        )

        # Mock model calls to return valid subjective scores
        call_count = {"n": 0}

        def fake_call(provider, model, system_prompt, user_prompt, temperature):
            call_count["n"] += 1
            return {
                "architecture": {"score": 7.0 + call_count["n"], "confidence": "high", "evidence": "t"},
                "documentation": {"score": 6.0 + call_count["n"], "confidence": "high", "evidence": "t"},
                "analytics_intelligence": {"score": 8.0, "confidence": "high", "evidence": "t"},
                "sustainability": {"score": 7.0, "confidence": "high", "evidence": "t"},
            }

        monkeypatch.setattr(generate_ratings, "call_model", fake_call)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        monkeypatch.setenv("GOOGLE_API_KEY", "fake")

        result = generate_ratings.generate_ratings()
        assert result["status"] == "success"

        # Check that all rating files have identical objective scores
        ratings_dir = tmp_path / "ratings"
        rating_files = list(ratings_dir.glob("*.json"))
        assert len(rating_files) >= 2

        for rf in rating_files:
            data = json.loads(rf.read_text())
            for obj_dim in OBJECTIVE_DIMENSIONS:
                assert data["dimensions"][obj_dim]["score"] == fake_objective[obj_dim]["score"]
