#!/usr/bin/env python3
"""Tests for diagnose.py — diagnostic tool for system self-assessment."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from diagnose import (
    PROMPT_GENERATORS,
    compute_composite,
    format_human_report,
    format_json_output,
    load_rubric,
    measure_code_quality,
    measure_data_integrity,
    measure_operational_maturity,
    measure_test_coverage,
)


@pytest.fixture
def rubric():
    return load_rubric()


@pytest.fixture
def sample_scores():
    return {
        "test_coverage": {"score": 9.5, "confidence": "high", "evidence": "2100 tests; matrix strict pass"},
        "code_quality": {"score": 8.0, "confidence": "high", "evidence": "0 lint errors"},
        "data_integrity": {"score": 10.0, "confidence": "high", "evidence": "0 errors"},
        "operational_maturity": {"score": 7.0, "confidence": "medium", "evidence": "5 agents"},
    }


class TestLoadRubric:
    def test_rubric_loads(self, rubric):
        assert "dimensions" in rubric
        assert "version" in rubric

    def test_rubric_has_8_dimensions(self, rubric):
        assert len(rubric["dimensions"]) == 8

    def test_weights_sum_to_one(self, rubric):
        total = sum(d["weight"] for d in rubric["dimensions"].values())
        assert abs(total - 1.0) < 0.01

    def test_all_dimensions_have_scoring_guide(self, rubric):
        for key, dim in rubric["dimensions"].items():
            assert "scoring_guide" in dim, f"{key} missing scoring_guide"
            guide = dim["scoring_guide"]
            assert 1 in guide or "1" in guide, f"{key} missing anchor at 1"
            assert 10 in guide or "10" in guide, f"{key} missing anchor at 10"


class TestMeasureTestCoverage:
    def test_high_count_high_matrix(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            class R:
                pass
            r = R()
            if "pytest" in cmd:
                r.returncode = 0
                r.stdout = "2135 tests collected\n"
                r.stderr = ""
            else:
                r.returncode = 0
                r.stdout = "All 121/121 modules covered.\n"
                r.stderr = ""
            return r
        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        result = measure_test_coverage()
        assert result["score"] == 10.0
        assert result["confidence"] == "high"
        assert "2135" in result["evidence"]

    def test_low_count(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            class R:
                pass
            r = R()
            if "pytest" in cmd:
                r.returncode = 0
                r.stdout = "50 tests collected\n"
                r.stderr = ""
            else:
                r.returncode = 1
                r.stdout = "50/100"
                r.stderr = ""
            return r
        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        result = measure_test_coverage()
        assert result["score"] < 5.0

    def test_timeout_handled(self, monkeypatch):
        import subprocess as sp
        def mock_run(cmd, **kwargs):
            raise sp.TimeoutExpired(cmd, 120)
        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        result = measure_test_coverage()
        assert result["score"] >= 1.0

    def test_pytest_missing_uses_fallback_estimate(self, monkeypatch, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_sample.py").write_text(
            "def test_alpha():\n    assert True\n\n"
            "def test_beta():\n    assert True\n",
            encoding="utf-8",
        )

        monkeypatch.setattr("diagnose.TESTS_DIR", tests_dir)
        monkeypatch.setattr("diagnose._python_with_module", lambda _name: sys.executable)

        def mock_run(cmd, **kwargs):
            class R:
                pass
            r = R()
            if "-m" in cmd and "pytest" in cmd:
                r.returncode = 1
                r.stdout = ""
                r.stderr = "No module named pytest"
            else:
                r.returncode = 0
                r.stdout = "All 1/1 modules covered."
                r.stderr = ""
            return r

        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        result = measure_test_coverage()
        assert result["details"]["test_count"] == 2
        assert result["details"]["test_count_fallback_used"] is True
        assert result["confidence"] == "medium"


class TestMeasureCodeQuality:
    def test_zero_lint_errors(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            class R:
                returncode = 0
                stdout = "All checks passed!\n"
                stderr = ""
            return R()
        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        # Also need script files to count functions
        monkeypatch.setattr("diagnose.SCRIPTS_DIR", Path("/nonexistent"))
        result = measure_code_quality()
        assert result["score"] >= 7.0

    def test_many_lint_errors(self, monkeypatch):
        errors = "\n".join(f"scripts/foo.py:{i}:1: E501 line too long" for i in range(60))
        def mock_run(cmd, **kwargs):
            class R:
                returncode = 1
                stdout = errors
                stderr = ""
            return R()
        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        monkeypatch.setattr("diagnose.SCRIPTS_DIR", Path("/nonexistent"))
        result = measure_code_quality()
        assert result["score"] < 5.0

    def test_ruff_missing_sets_low_confidence(self, monkeypatch):
        monkeypatch.setattr("diagnose._python_with_module", lambda _name: sys.executable)

        def mock_run(cmd, **kwargs):
            class R:
                returncode = 1
                stdout = ""
                stderr = "No module named ruff"
            return R()

        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        monkeypatch.setattr("diagnose.SCRIPTS_DIR", Path("/nonexistent"))
        result = measure_code_quality()
        assert result["confidence"] == "low"
        assert result["details"]["ruff_unavailable"] is True

class TestShadowScripts:
    def test_finds_unmapped_scripts(self, tmp_path, monkeypatch):
        # Create a fake scripts dir
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text(
            'COMMANDS = {"mapped": ("mapped.py", [], "desc")}\n'
            'PARAM_COMMANDS = {}',
            encoding="utf-8",
        )
        (scripts_dir / "mapped.py").write_text("print('hi')", encoding="utf-8")
        (scripts_dir / "shadow.py").write_text("print('spooky')", encoding="utf-8")
        (scripts_dir / "_internal.py").write_text("print('hidden')", encoding="utf-8")

        monkeypatch.setattr("diagnose.SCRIPTS_DIR", scripts_dir)

        from diagnose import _get_shadow_scripts
        shadows = _get_shadow_scripts()

        # shadow.py is unmapped and not core infra
        assert "shadow.py" in shadows
        # mapped.py is mapped
        assert "mapped.py" not in shadows
        # _internal.py starts with _
        assert "_internal.py" not in shadows
        # run.py is core infra
        assert "run.py" not in shadows
        
        assert len(shadows) == 1

    def test_code_quality_penalizes_shadows(self, monkeypatch):
        monkeypatch.setattr("diagnose._python_with_module", lambda _name: sys.executable)
        monkeypatch.setattr("diagnose._get_shadow_scripts", lambda: ["shadow1.py", "shadow2.py"])

        def mock_run(cmd, **kwargs):
            class R:
                returncode = 0
                stdout = "All checks passed!\n"
                stderr = ""
            return R()
        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        # Mock SCRIPTS_DIR to avoid counting actual functions
        monkeypatch.setattr("diagnose.SCRIPTS_DIR", Path("/nonexistent"))

        from diagnose import measure_code_quality
        result = measure_code_quality()

        # Without shadows, 0 lint errors = 7.0 + hint_ratio*3.0.
        # Here hinted=0, total=0 -> ratio=0. Score would be 7.0.
        # 2 shadows = 0.4 penalty. Expected score = 6.6.
        assert result["score"] == 6.6
        assert "2 shadow scripts" in result["evidence"]
        assert result["details"]["shadow_scripts"] == ["shadow1.py", "shadow2.py"]


class TestMeasureDataIntegrity:
    def test_zero_errors(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            class R:
                returncode = 0
                stdout = "Validation passed\n"
                stderr = ""
            return R()
        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        result = measure_data_integrity()
        assert result["score"] == 10.0

    def test_some_errors(self, monkeypatch):
        call_count = [0]
        def mock_run(cmd, **kwargs):
            call_count[0] += 1
            class R:
                pass
            r = R()
            if call_count[0] == 1:
                r.returncode = 1
                r.stdout = "ERROR: missing field\nERROR: invalid status\n"
                r.stderr = ""
            else:
                r.returncode = 0
                r.stdout = ""
                r.stderr = ""
            return r
        monkeypatch.setattr("diagnose.subprocess.run", mock_run)
        result = measure_data_integrity()
        assert 7.0 <= result["score"] <= 10.0


class TestMeasureOperationalMaturity:
    def test_full_health(self, monkeypatch):
        mock_status = {
            "agents": [], "total": 6, "loaded_count": 6,
            "installed_count": 6, "healthy": True,
        }
        monkeypatch.setattr("diagnose.REPO_ROOT", Path("/tmp/fake"))
        import types
        fake_launchd = types.ModuleType("launchd_manager")
        fake_launchd.get_agent_status = lambda: mock_status
        monkeypatch.setitem(sys.modules, "launchd_manager", fake_launchd)
        result = measure_operational_maturity()
        assert result["score"] >= 5.0

    def test_no_agents(self, monkeypatch):
        monkeypatch.setattr("diagnose.REPO_ROOT", Path("/tmp/nonexistent"))
        # launchd_manager import will fail
        monkeypatch.delitem(sys.modules, "launchd_manager", raising=False)
        result = measure_operational_maturity()
        assert result["score"] >= 1.0


class TestComputeComposite:
    def test_weighted_sum(self, rubric, sample_scores):
        composite = compute_composite(sample_scores, rubric)
        # Manual: 0.15*9.5 + 0.10*8.0 + 0.15*10.0 + 0.15*7.0
        # = 1.425 + 0.8 + 1.5 + 1.05 = 4.775
        expected = round(0.15 * 9.5 + 0.10 * 8.0 + 0.15 * 10.0 + 0.15 * 7.0, 1)
        assert composite == expected

    def test_empty_scores(self, rubric):
        assert compute_composite({}, rubric) == 0.0

    def test_partial_scores(self, rubric):
        scores = {"test_coverage": {"score": 10.0}}
        composite = compute_composite(scores, rubric)
        assert composite == round(0.15 * 10.0, 1)


class TestFormatHumanReport:
    def test_contains_header(self, rubric, sample_scores):
        report = format_human_report(sample_scores, rubric)
        assert "DIAGNOSTIC SCORECARD" in report
        assert "COMPOSITE" in report

    def test_shows_unrated(self, rubric):
        scores = {"test_coverage": {"score": 9.0, "evidence": "test"}}
        report = format_human_report(scores, rubric)
        assert "not rated" in report


class TestFormatJsonOutput:
    def test_json_structure(self, rubric, sample_scores):
        output = format_json_output(sample_scores, rubric, rater_id="test-rater")
        assert output["rater_id"] == "test-rater"
        assert "timestamp" in output
        assert "rubric_version" in output
        assert "dimensions" in output
        assert "composite" in output
        assert isinstance(output["composite"], float)

    def test_json_serializable(self, rubric, sample_scores):
        output = format_json_output(sample_scores, rubric)
        serialized = json.dumps(output)
        parsed = json.loads(serialized)
        assert parsed["composite"] == output["composite"]


class TestPromptGenerators:
    def test_all_generators_return_strings(self):
        for name, gen in PROMPT_GENERATORS.items():
            result = gen()
            assert isinstance(result, str), f"{name} did not return str"
            assert len(result) > 100, f"{name} prompt too short"

    def test_architecture_prompt_mentions_scoring(self):
        prompt = PROMPT_GENERATORS["architecture"]()
        assert "1-10" in prompt or "scoring" in prompt.lower()

    def test_documentation_prompt_mentions_claude_md(self):
        prompt = PROMPT_GENERATORS["documentation"]()
        assert "CLAUDE.md" in prompt
