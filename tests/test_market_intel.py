"""Tests for scripts/market_intel.py"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from market_intel import (
    check_staleness,
    fmt_currency,
    fmt_days,
    fmt_pct,
    load_intel,
)

# --- TestFmtPct ---


def test_fmt_pct_none():
    assert fmt_pct(None) == "N/A"


def test_fmt_pct_zero():
    assert fmt_pct(0.0) == "0.0%"


def test_fmt_pct_one():
    assert fmt_pct(1.0) == "100.0%"


def test_fmt_pct_decimal():
    """0.0821 → '8.2%'"""
    assert fmt_pct(0.0821) == "8.2%"


def test_fmt_pct_half():
    assert fmt_pct(0.5) == "50.0%"


def test_fmt_pct_small():
    """0.01 → '1.0%'"""
    assert fmt_pct(0.01) == "1.0%"


# --- TestFmtDays ---


def test_fmt_days_none():
    assert fmt_days(None) == "N/A"


def test_fmt_days_value():
    assert fmt_days(14) == "14d"


def test_fmt_days_zero():
    assert fmt_days(0) == "0d"


def test_fmt_days_large():
    assert fmt_days(90) == "90d"


# --- TestFmtCurrency ---


def test_fmt_currency_none():
    assert fmt_currency(None) == "N/A"


def test_fmt_currency_thousands():
    assert fmt_currency(150000) == "$150,000 USD"


def test_fmt_currency_small():
    """Values < 1000 use simple $ format."""
    assert fmt_currency(500) == "$500 USD"


def test_fmt_currency_exactly_1000():
    """1000 is exactly at boundary (>= 1000)."""
    assert fmt_currency(1000) == "$1,000 USD"


def test_fmt_currency_custom_currency():
    assert fmt_currency(20000, "EUR") == "$20,000 EUR"


def test_fmt_currency_zero():
    assert fmt_currency(0) == "$0 USD"


# --- TestCheckStaleness ---


def test_check_staleness_no_meta_returns_true():
    """Empty intel dict → stale."""
    assert check_staleness({}) is True


def test_check_staleness_no_last_updated():
    """meta exists but no last_updated → stale."""
    intel = {"meta": {"version": "1.0"}}
    assert check_staleness(intel) is True


def test_check_staleness_recent_date_not_stale():
    """Yesterday's date → not stale."""
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    intel = {"meta": {"last_updated": yesterday}}
    assert check_staleness(intel) is False


def test_check_staleness_old_date_stale():
    """91 days ago → stale (default threshold 90)."""
    old = (date.today() - timedelta(days=91)).strftime("%Y-%m-%d")
    intel = {"meta": {"last_updated": old}}
    assert check_staleness(intel) is True


def test_check_staleness_exactly_90_days_not_stale():
    """Exactly 90 days ago → not stale (threshold is >90)."""
    d = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    intel = {"meta": {"last_updated": d}}
    assert check_staleness(intel) is False


def test_check_staleness_invalid_date_returns_true():
    """Invalid date string → stale."""
    intel = {"meta": {"last_updated": "not-a-date"}}
    assert check_staleness(intel) is True


def test_check_staleness_custom_threshold():
    """Custom stale_thresholds_days.intelligence_staleness is respected."""
    d = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
    intel = {
        "meta": {"last_updated": d},
        "stale_thresholds_days": {"intelligence_staleness": 5},
    }
    assert check_staleness(intel) is True


def test_check_staleness_recent_with_custom_high_threshold():
    """High threshold → recent-ish date still not stale."""
    d = (date.today() - timedelta(days=50)).strftime("%Y-%m-%d")
    intel = {
        "meta": {"last_updated": d},
        "stale_thresholds_days": {"intelligence_staleness": 180},
    }
    assert check_staleness(intel) is False


# --- TestLoadIntel ---


def test_load_intel_missing_file_returns_empty(monkeypatch, tmp_path):
    """INTEL_FILE missing → returns {}."""
    import market_intel as mi
    monkeypatch.setattr(mi, "INTEL_FILE", tmp_path / "nonexistent.json")
    result = load_intel()
    assert result == {}


def test_load_intel_valid_json(tmp_path, monkeypatch):
    """Valid JSON file is loaded correctly."""
    import market_intel as mi
    intel_file = tmp_path / "market-intelligence-2026.json"
    data = {"meta": {"version": "2026.1"}, "market_conditions": {}}
    intel_file.write_text(json.dumps(data))
    monkeypatch.setattr(mi, "INTEL_FILE", intel_file)
    result = load_intel()
    assert result["meta"]["version"] == "2026.1"
