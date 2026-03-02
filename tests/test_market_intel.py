"""Tests for scripts/market_intel.py"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from market_intel import (
    _REQUIRED_INTEL_KEYS,
    check_staleness,
    fmt_currency,
    fmt_days,
    fmt_pct,
    load_intel,
    section_differentiation,
    section_funding,
    section_meta,
    section_startup,
    validate_intel_schema,
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


# --- Required Intel Keys (v2: 13 sections) ---


def test_required_intel_keys_count():
    """All 13 sections (7 original + 6 new) are in _REQUIRED_INTEL_KEYS."""
    assert len(_REQUIRED_INTEL_KEYS) == 13


def test_required_intel_keys_original_seven():
    """Original 7 keys present."""
    original = ["meta", "market_conditions", "track_benchmarks", "portal_friction_scores",
                 "skills_signals", "follow_up_protocol", "stale_thresholds_days"]
    for key in original:
        assert key in _REQUIRED_INTEL_KEYS, f"missing original key: {key}"


def test_required_intel_keys_new_six():
    """6 new keys from v2 JSON present."""
    new_keys = ["startup_funding_landscape", "non_dilutive_funding", "startup_mechanics",
                "differentiation_signals", "alternative_funding", "meta_strategy"]
    for key in new_keys:
        assert key in _REQUIRED_INTEL_KEYS, f"missing new key: {key}"


def test_required_intel_keys_all_expect_dict():
    """All required keys expect dict type."""
    for key, expected_type in _REQUIRED_INTEL_KEYS.items():
        assert expected_type is dict, f"key {key} expects {expected_type}, should be dict"


# --- Schema Validation ---


def test_validate_catches_missing_new_keys():
    """Schema validation flags missing new sections."""
    minimal = {"meta": {}, "market_conditions": {}, "track_benchmarks": {},
               "portal_friction_scores": {}, "skills_signals": {},
               "follow_up_protocol": {}, "stale_thresholds_days": {}}
    issues = validate_intel_schema(minimal)
    assert len(issues) == 6  # 6 new keys missing
    for issue in issues:
        assert "missing required key" in issue


def test_validate_passes_full_schema():
    """Full schema with all 13 keys produces no issues."""
    full = {k: {} for k in _REQUIRED_INTEL_KEYS}
    issues = validate_intel_schema(full)
    assert len(issues) == 0


# --- New Display Sections (smoke tests — don't crash on empty data) ---


def test_section_startup_empty_intel(capsys):
    """section_startup doesn't crash on empty intel."""
    section_startup({})
    captured = capsys.readouterr()
    assert "STARTUP FUNDING LANDSCAPE" in captured.out


def test_section_funding_empty_intel(capsys):
    """section_funding doesn't crash on empty intel."""
    section_funding({})
    captured = capsys.readouterr()
    assert "NON-DILUTIVE" in captured.out


def test_section_differentiation_empty_intel(capsys):
    """section_differentiation doesn't crash on empty intel."""
    section_differentiation({})
    captured = capsys.readouterr()
    assert "DIFFERENTIATION SIGNALS" in captured.out


def test_section_meta_empty_intel(capsys):
    """section_meta doesn't crash on empty intel."""
    section_meta({})
    captured = capsys.readouterr()
    assert "META STRATEGY" in captured.out
