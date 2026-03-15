"""Tests for external_validator.py — external validation of scoring inputs."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from external_validator import (
    DIVERGENCE_THRESHOLD_PCT,
    ORG_GITHUB_HANDLES,
    SKILL_KEYWORDS,
    SOC_MAPPING,
    _bls_series_id,
    _calibrate_mode_thresholds,
    _calibrate_salary_breakpoints,
    _calibrate_skill_signals,
    _pct_divergence,
    calibrate_thresholds,
    compare_against_scoring,
    format_calibration_report,
    format_report,
    load_cache,
    save_cache,
)


class TestBLSSeriesID:
    def test_series_id_format(self):
        """BLS series ID has correct prefix and length."""
        sid = _bls_series_id("15-1252", "04")
        assert sid.startswith("OEUM")
        assert "151252" in sid
        assert sid.endswith("04")

    def test_series_id_strips_hyphens(self):
        """SOC code hyphens are stripped in series ID."""
        sid = _bls_series_id("15-1252", "12")
        assert "-" not in sid

    def test_all_soc_mappings_produce_valid_ids(self):
        """Every SOC mapping produces a series ID."""
        for role_key, cfg in SOC_MAPPING.items():
            for label, dt_code in cfg["datatypes"].items():
                sid = _bls_series_id(cfg["soc"], dt_code)
                assert len(sid) > 20, f"Short series ID for {role_key}/{label}"


class TestDivergence:
    def test_zero_divergence(self):
        assert _pct_divergence(100, 100) == 0.0

    def test_positive_divergence(self):
        d = _pct_divergence(130, 100)
        assert d == pytest.approx(30.0)

    def test_external_zero_returns_zero(self):
        assert _pct_divergence(100, 0) == 0.0

    def test_threshold_constant_is_positive(self):
        assert DIVERGENCE_THRESHOLD_PCT > 0


class TestCompareAgainstScoring:
    def test_comparison_with_empty_cache(self):
        """Empty cache produces valid structure with no data."""
        result = compare_against_scoring({})
        assert "salary_divergence" in result
        assert "skill_rank_changes" in result
        assert "org_outliers" in result
        assert "summary" in result

    def test_comparison_with_salary_data(self, tmp_path, monkeypatch):
        """Salary comparison detects divergence."""
        # Mock market JSON
        market = {
            "salary_benchmarks": {
                "senior_engineer": {"min": 200000, "max": 400000},
            },
            "skills_signals": {"hot_2026": [], "cooling_2026": []},
        }
        market_path = tmp_path / "market-intelligence-2026.json"
        market_path.write_text(json.dumps(market))
        monkeypatch.setattr("external_validator.MARKET_JSON_PATH", market_path)

        cache = {
            "salary_benchmarks": {
                "software_engineer": {
                    "bls_soc_code": "15-1252",
                    "annual_p10": 84000,
                    "annual_p90": 208000,
                    "annual_median": 136000,
                },
            },
        }

        result = compare_against_scoring(cache)
        assert len(result["salary_divergence"]) >= 1
        # $200K min vs $84K p10 = >100% divergence → flagged
        senior = [s for s in result["salary_divergence"] if s["role"] == "senior_engineer"]
        assert len(senior) == 1
        assert senior[0]["divergent"] is True

    def test_comparison_with_matching_salaries(self, tmp_path, monkeypatch):
        """No divergence when pipeline matches BLS closely."""
        market = {
            "salary_benchmarks": {
                "senior_engineer": {"min": 90000, "max": 200000},
            },
            "skills_signals": {"hot_2026": [], "cooling_2026": []},
        }
        market_path = tmp_path / "market-intelligence-2026.json"
        market_path.write_text(json.dumps(market))
        monkeypatch.setattr("external_validator.MARKET_JSON_PATH", market_path)

        cache = {
            "salary_benchmarks": {
                "software_engineer": {
                    "bls_soc_code": "15-1252",
                    "annual_p10": 84000,
                    "annual_p90": 208000,
                    "annual_median": 136000,
                },
            },
        }

        result = compare_against_scoring(cache)
        senior = [s for s in result["salary_divergence"] if s["role"] == "senior_engineer"]
        assert len(senior) == 1
        assert senior[0]["divergent"] is False

    def test_skill_demand_no_issue_when_empty(self):
        """No skill issues when cache has no skill data."""
        result = compare_against_scoring({"skill_demand": {}})
        assert result["skill_rank_changes"] == []

    def test_org_outlier_detection(self, monkeypatch):
        """Flags high-prestige orgs with minimal GitHub presence."""
        import score_constants

        monkeypatch.setattr(score_constants, "HIGH_PRESTIGE", {"TestOrg": 9})

        cache = {
            "org_signals": {
                "TestOrg": {
                    "github_handle": "testorg",
                    "github_public_repos": 2,
                    "github_followers": 10,
                },
            },
        }

        result = compare_against_scoring(cache)
        assert len(result["org_outliers"]) == 1
        assert result["org_outliers"][0]["org"] == "TestOrg"


class TestCacheIO:
    def test_save_and_load(self, tmp_path, monkeypatch):
        """Cache round-trips through save/load."""
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr("external_validator.CACHE_PATH", cache_path)

        data = {"last_refresh": "2026-03-14", "salary_benchmarks": {"test": 1}}
        save_cache(data)
        loaded = load_cache()
        assert loaded == data

    def test_load_missing_returns_none(self, tmp_path, monkeypatch):
        """Missing cache file returns None."""
        monkeypatch.setattr("external_validator.CACHE_PATH", tmp_path / "nope.json")
        assert load_cache() is None


class TestFormatReport:
    def test_report_is_string(self):
        """format_report produces a non-empty string."""
        comparison = {
            "salary_divergence": [],
            "skill_rank_changes": [],
            "org_outliers": [],
            "summary": {"total_checks": 0, "divergent": 0, "ok": 0, "no_data": 0},
        }
        report = format_report(comparison)
        assert "EXTERNAL VALIDATION REPORT" in report
        assert "SALARY BENCHMARKS" in report


class TestConstants:
    def test_soc_mapping_has_required_fields(self):
        """Every SOC mapping has soc, bls_title, and datatypes."""
        for role, cfg in SOC_MAPPING.items():
            assert "soc" in cfg, f"Missing soc for {role}"
            assert "bls_title" in cfg, f"Missing bls_title for {role}"
            assert "datatypes" in cfg, f"Missing datatypes for {role}"
            assert len(cfg["datatypes"]) >= 2

    def test_skill_keywords_non_empty(self):
        assert len(SKILL_KEYWORDS) >= 10

    def test_org_handles_non_empty(self):
        assert len(ORG_GITHUB_HANDLES) >= 5


class TestCLI:
    def test_main_compare_only_no_cache(self, tmp_path, monkeypatch, capsys):
        """--compare-only with no cache exits with error."""
        monkeypatch.setattr("external_validator.CACHE_PATH", tmp_path / "nope.json")
        monkeypatch.setattr("sys.argv", ["external_validator.py", "--compare-only"])

        from external_validator import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_fetch_only(self, tmp_path, monkeypatch):
        """--fetch-only calls refresh_cache."""
        monkeypatch.setattr("external_validator.CACHE_PATH", tmp_path / "cache.json")
        monkeypatch.setattr("sys.argv", ["external_validator.py", "--fetch-only"])

        refreshed = {"called": False}

        def fake_refresh():
            refreshed["called"] = True
            return {"last_refresh": "test"}

        monkeypatch.setattr("external_validator.refresh_cache", fake_refresh)

        from external_validator import main

        main()
        assert refreshed["called"]


class TestCalibrateSalaryBreakpoints:
    def test_proposes_changes_when_bls_differs(self):
        """Salary breakpoints shift when BLS data diverges >10%."""
        cache = {
            "salary_benchmarks": {
                "software_engineer": {
                    "bls_soc_code": "15-1252",
                    "bls_title": "Software Developers",
                    "annual_p10": 75000,
                    "annual_median": 130000,
                    "annual_p90": 200000,
                    "fetched": "2026-03-14",
                },
            },
        }
        result = _calibrate_salary_breakpoints(cache)
        # p90 (200K) is >10% different from current tier_9 (150K)
        assert result["has_changes"] is True
        assert "tier_9" in result["changes"]
        assert result["changes"]["tier_9"]["proposed"] == 200000

    def test_no_changes_when_aligned(self):
        """No changes when BLS matches current breakpoints."""
        cache = {
            "salary_benchmarks": {
                "software_engineer": {
                    "annual_p10": 50000,
                    "annual_median": 100000,
                    "annual_p90": 150000,
                    "fetched": "2026-03-14",
                },
            },
        }
        result = _calibrate_salary_breakpoints(cache)
        assert result["has_changes"] is False

    def test_handles_missing_data(self):
        """Returns no changes when BLS data is missing."""
        result = _calibrate_salary_breakpoints({})
        assert result["has_changes"] is False


class TestCalibrateModeThresholds:
    def test_proposes_precision_adjustment(self, tmp_path, monkeypatch):
        """Proposes lowering auto_qualify_min when external data validates."""
        market = {
            "precision_strategy": {
                "mode": "precision",
                "mode_thresholds": {
                    "precision": {"auto_qualify_min": 9.0, "max_active": 10},
                    "volume": {"auto_qualify_min": 7.0, "max_active": 30},
                    "hybrid": {"auto_qualify_min": 8.0, "max_active": 15},
                },
            },
        }
        market_path = tmp_path / "market.json"
        market_path.write_text(json.dumps(market))
        monkeypatch.setattr("external_validator.MARKET_JSON_PATH", market_path)

        cache = {
            "salary_benchmarks": {
                "software_engineer": {
                    "annual_p10": 50000,
                    "annual_median": 100000,
                    "annual_p90": 150000,
                    "fetched": "2026-03-14",
                },
            },
            "skill_demand": {"python": {"posting_count": 50}},
        }
        result = _calibrate_mode_thresholds(cache)
        assert result["has_changes"] is True
        assert "precision" in result["proposed_changes"]
        proposed = result["proposed_changes"]["precision"]["auto_qualify_min"]["proposed"]
        assert proposed < 9.0  # Must be lower than unattainable 9.0
        assert proposed >= 5.0  # But not absurdly low

    def test_no_changes_without_market_json(self, tmp_path, monkeypatch):
        """Returns no changes when market JSON is missing."""
        monkeypatch.setattr("external_validator.MARKET_JSON_PATH", tmp_path / "nope.json")
        result = _calibrate_mode_thresholds({})
        assert result["has_changes"] is False


class TestCalibrateSkillSignals:
    def test_detects_misclassified_skill(self, tmp_path, monkeypatch):
        """Flags cooling skill with more postings than hot median."""
        market = {
            "skills_signals": {
                "hot_2026": ["kubernetes", "terraform"],
                "cooling_2026": ["react"],
            },
        }
        market_path = tmp_path / "market.json"
        market_path.write_text(json.dumps(market))
        monkeypatch.setattr("external_validator.MARKET_JSON_PATH", market_path)

        cache = {
            "skill_demand": {
                "kubernetes": {"posting_count": 30},
                "terraform": {"posting_count": 20},
                "react": {"posting_count": 50},  # cooling but 50 > hot median of 25
            },
        }
        result = _calibrate_skill_signals(cache)
        assert result["has_changes"] is True
        assert len(result["misclassified"]) == 1
        assert result["misclassified"][0]["skill"] == "react"


class TestCalibrateThresholds:
    def test_dry_run_does_not_write(self, tmp_path, monkeypatch):
        """Dry run proposes changes without modifying files."""
        cache_path = tmp_path / "cache.json"
        cache = {
            "last_refresh": "2026-03-14",
            "salary_benchmarks": {
                "software_engineer": {
                    "annual_p10": 75000,
                    "annual_median": 130000,
                    "annual_p90": 200000,
                    "fetched": "2026-03-14",
                },
            },
            "skill_demand": {"python": {"posting_count": 50}},
            "org_signals": {},
        }
        cache_path.write_text(json.dumps(cache))
        monkeypatch.setattr("external_validator.CACHE_PATH", cache_path)

        market = {
            "precision_strategy": {
                "mode": "precision",
                "mode_thresholds": {
                    "precision": {"auto_qualify_min": 9.0},
                    "volume": {"auto_qualify_min": 7.0},
                    "hybrid": {"auto_qualify_min": 8.0},
                },
            },
        }
        market_path = tmp_path / "market.json"
        market_path.write_text(json.dumps(market))
        monkeypatch.setattr("external_validator.MARKET_JSON_PATH", market_path)

        result = calibrate_thresholds(dry_run=True)
        assert result["status"] == "dry_run"
        assert result["total_changes"] >= 1

        # Verify market JSON unchanged
        reloaded = json.loads(market_path.read_text())
        assert reloaded["precision_strategy"]["mode_thresholds"]["precision"]["auto_qualify_min"] == 9.0

    def test_no_cache_returns_error(self, tmp_path, monkeypatch):
        """Returns error when no cache exists."""
        monkeypatch.setattr("external_validator.CACHE_PATH", tmp_path / "nope.json")
        result = calibrate_thresholds()
        assert result["status"] == "error"


class TestFormatCalibrationReport:
    def test_report_has_sections(self):
        """Calibration report includes all sections."""
        result = {
            "status": "dry_run",
            "cache_date": "2026-03-14",
            "total_changes": 1,
            "proposals": {
                "salary_breakpoints": {"has_changes": False, "reason": "within tolerance"},
                "benefits_cliffs": {"validation_notes": []},
                "mode_thresholds": {"has_changes": False, "reason": "aligned"},
                "skill_weights": {"misclassified": []},
            },
        }
        report = format_calibration_report(result)
        assert "EXTERNAL CALIBRATION REPORT" in report
        assert "SALARY SCORING BREAKPOINTS" in report
        assert "MODE THRESHOLD CALIBRATION" in report
        assert "SKILL SIGNAL VALIDATION" in report
