"""Tests for pipeline mode toggle functions (Tier 3G)."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import (
    get_mode_review_status,
    get_mode_thresholds,
    get_pipeline_mode,
)


def _mock_intel(mode="precision", review_date="2026-04-04", **extra):
    """Create mock market intelligence with precision_strategy."""
    strategy = {
        "mode": mode,
        "review_date": review_date,
        "revert_trigger": "0 interviews by review_date",
        "mode_thresholds": {
            "precision": {"auto_qualify_min": 9.0, "max_active": 10, "max_weekly_submissions": 2, "stale_days": 14, "stagnant_days": 30},
            "volume": {"auto_qualify_min": 7.0, "max_active": 30, "max_weekly_submissions": 10, "stale_days": 7, "stagnant_days": 14},
            "hybrid": {"auto_qualify_min": 8.0, "max_active": 15, "max_weekly_submissions": 5, "stale_days": 10, "stagnant_days": 21},
        },
    }
    strategy.update(extra)
    return {"precision_strategy": strategy}


class TestGetPipelineMode:
    def test_get_pipeline_mode_default(self):
        """Returns 'precision' when market intel has mode=precision."""
        with patch("pipeline_lib.load_market_intelligence", return_value=_mock_intel()):
            assert get_pipeline_mode() == "precision"

    def test_get_pipeline_mode_volume(self):
        """Returns 'volume' when configured."""
        with patch("pipeline_lib.load_market_intelligence", return_value=_mock_intel(mode="volume")):
            assert get_pipeline_mode() == "volume"

    def test_get_pipeline_mode_fallback(self):
        """Returns 'precision' when market intel is empty."""
        with patch("pipeline_lib.load_market_intelligence", return_value={}):
            assert get_pipeline_mode() == "precision"


class TestGetModeThresholds:
    def test_get_mode_thresholds_precision(self):
        """Returns precision thresholds when mode is precision."""
        with patch("pipeline_lib.load_market_intelligence", return_value=_mock_intel()):
            t = get_mode_thresholds()
            assert t["auto_qualify_min"] == 9.0
            assert t["max_active"] == 10
            assert t["stale_days"] == 14

    def test_get_mode_thresholds_volume(self):
        """Returns volume thresholds when mode is volume."""
        with patch("pipeline_lib.load_market_intelligence", return_value=_mock_intel(mode="volume")):
            t = get_mode_thresholds()
            assert t["auto_qualify_min"] == 7.0
            assert t["max_active"] == 30
            assert t["stale_days"] == 7


class TestGetModeReviewStatus:
    def test_get_mode_review_status_approaching(self):
        """When review date is in future, days_until_review > 0 and past_review is False."""
        with patch("pipeline_lib.load_market_intelligence", return_value=_mock_intel(review_date="2099-01-01")):
            status = get_mode_review_status()
            assert status["days_until_review"] > 0
            assert status["past_review"] is False
            assert status["mode"] == "precision"

    def test_get_mode_review_status_past(self):
        """When review date is in the past, past_review is True."""
        with patch("pipeline_lib.load_market_intelligence", return_value=_mock_intel(review_date="2020-01-01")):
            status = get_mode_review_status()
            assert status["days_until_review"] < 0
            assert status["past_review"] is True
