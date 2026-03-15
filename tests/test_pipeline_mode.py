"""Tests for pipeline_mode.py — mode switching between precision/volume/hybrid."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_mode import (
    MODE_DESCRIPTIONS,
    VALID_MODES,
    compare_modes,
    format_report,
    get_active_thresholds,
    get_current_mode,
    get_mode_thresholds,
    set_mode,
)


class TestGetCurrentMode:
    def test_reads_from_market_json(self):
        """Current mode reads from precision_strategy.mode."""
        mode = get_current_mode()
        assert mode in VALID_MODES

    def test_defaults_to_precision(self):
        """Empty market data defaults to precision."""
        assert get_current_mode({}) == "precision"


class TestGetModeThresholds:
    def test_returns_dict(self):
        thresholds = get_mode_thresholds()
        assert isinstance(thresholds, dict)
        assert "precision" in thresholds
        assert "volume" in thresholds
        assert "hybrid" in thresholds

    def test_precision_has_required_keys(self):
        thresholds = get_mode_thresholds()
        prec = thresholds.get("precision", {})
        assert "auto_qualify_min" in prec
        assert "max_active" in prec
        assert "stale_days" in prec


class TestGetActiveThresholds:
    def test_returns_current_mode_thresholds(self):
        thresholds = get_active_thresholds()
        assert isinstance(thresholds, dict)
        assert "auto_qualify_min" in thresholds


class TestSetMode:
    def test_invalid_mode_returns_error(self):
        result = set_mode("invalid_mode")
        assert result["status"] == "error"
        assert "Invalid mode" in result["error"]

    def test_same_mode_returns_no_change(self):
        current = get_current_mode()
        result = set_mode(current, dry_run=True)
        assert result["status"] == "no_change"

    def test_dry_run_does_not_write(self, tmp_path, monkeypatch):
        """Dry run computes changes but doesn't modify file."""
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
        monkeypatch.setattr("pipeline_mode.MARKET_JSON_PATH", market_path)

        result = set_mode("volume", dry_run=True)
        assert result["status"] == "dry_run"
        assert result["old_mode"] == "precision"
        assert result["new_mode"] == "volume"
        assert len(result["changes"]) >= 1

        # Verify file unchanged
        reloaded = json.loads(market_path.read_text())
        assert reloaded["precision_strategy"]["mode"] == "precision"

    def test_actual_switch(self, tmp_path, monkeypatch):
        """Non-dry-run switch actually updates the file."""
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
        monkeypatch.setattr("pipeline_mode.MARKET_JSON_PATH", market_path)

        result = set_mode("volume", dry_run=False)
        assert result["status"] == "switched"

        reloaded = json.loads(market_path.read_text())
        assert reloaded["precision_strategy"]["mode"] == "volume"


class TestCompareModes:
    def test_returns_all_modes(self):
        result = compare_modes()
        assert "current_mode" in result
        assert "modes" in result
        for mode in VALID_MODES:
            assert mode in result["modes"]

    def test_active_flag_set(self):
        result = compare_modes()
        current = result["current_mode"]
        assert result["modes"][current]["active"] is True
        other_modes = [m for m in VALID_MODES if m != current]
        for m in other_modes:
            assert result["modes"][m]["active"] is False


class TestConstants:
    def test_valid_modes_match_descriptions(self):
        for mode in VALID_MODES:
            assert mode in MODE_DESCRIPTIONS

    def test_three_modes(self):
        assert len(VALID_MODES) == 3


class TestFormatReport:
    def test_comparison_format(self):
        data = compare_modes()
        report = format_report(data)
        assert "PRECISION" in report
        assert "VOLUME" in report
        assert "HYBRID" in report

    def test_switch_format(self):
        data = {
            "status": "dry_run",
            "message": "Would switch precision → volume",
            "changes": {"auto_qualify_min": {"old": 9.0, "new": 7.0}},
        }
        report = format_report(data)
        assert "precision" in report
        assert "volume" in report
