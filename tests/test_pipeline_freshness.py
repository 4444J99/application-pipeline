"""Tests for scripts/pipeline_freshness.py."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pipeline_freshness
from pipeline_freshness import (
    compute_freshness_score,
    get_entry_era,
    get_freshness_tier,
    get_posting_age_hours,
)


def test_get_entry_era_volume_and_precision():
    assert get_entry_era({"timeline": {"submitted": "2026-03-03"}}) == "volume"
    assert get_entry_era({"timeline": {"submitted": "2026-03-04"}}) == "precision"


def test_get_posting_age_hours_date_only():
    entry = {"timeline": {"posting_date": (date.today() - timedelta(days=2)).isoformat()}}
    assert get_posting_age_hours(entry) == 48.0


def test_get_freshness_tier_non_job_returns_none():
    assert get_freshness_tier({"track": "grant", "timeline": {"posting_date": date.today().isoformat()}}) is None


def test_compute_freshness_score_stale_clamps_to_zero():
    entry = {
        "track": "job",
        "timeline": {"posting_date": (date.today() - timedelta(days=10)).isoformat()},
    }
    assert compute_freshness_score(entry) == 0.0


def test_get_freshness_tier_respects_custom_thresholds(monkeypatch):
    monkeypatch.setattr(
        pipeline_freshness,
        "load_market_intelligence",
        lambda: {"job_posting_freshness_hours": {"fresh": 1, "warm": 2, "stale": 3}},
    )
    entry = {"track": "job", "timeline": {"posting_date": date.today().isoformat()}}
    assert get_freshness_tier(entry) == "hot"
