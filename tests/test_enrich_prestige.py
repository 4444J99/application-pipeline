"""Tests for scripts/enrich_prestige.py."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import enrich_prestige


def test_stars_to_prestige_boost_large():
    assert enrich_prestige._stars_to_prestige_boost(600, 15000) == 2


def test_stars_to_prestige_boost_medium():
    assert enrich_prestige._stars_to_prestige_boost(200, 5000) == 1


def test_stars_to_prestige_boost_small():
    assert enrich_prestige._stars_to_prestige_boost(10, 50) == 0


def test_stars_to_prestige_boost_boundary():
    # Medium tier uses > 100 repos and > 2000 followers
    assert enrich_prestige._stars_to_prestige_boost(100, 2000) == 0
    assert enrich_prestige._stars_to_prestige_boost(101, 2001) == 1
    # High tier uses > 500 repos and > 10000 followers
    assert enrich_prestige._stars_to_prestige_boost(500, 10000) == 1  # meets medium, not high
    assert enrich_prestige._stars_to_prestige_boost(501, 10001) == 2


def test_enrich_prestige_no_fetch():
    """Without GitHub fetch, returns static prestige only."""
    result = enrich_prestige.enrich_prestige(fetch_github=False)
    assert len(result) > 0
    # All sources should be manual
    for company, info in result.items():
        assert info["source"] == "manual"
        assert info["github_repos"] is None


def test_enrich_prestige_with_fetch(monkeypatch):
    """With GitHub fetch, enriches known companies."""

    def fake_fetch(org):
        return {"public_repos": 300, "followers": 5000}

    monkeypatch.setattr(enrich_prestige, "_fetch_github_org", fake_fetch)
    monkeypatch.setattr(enrich_prestige, "RATE_DELAY", 0)

    result = enrich_prestige.enrich_prestige(fetch_github=True)
    # Anthropic should be enriched
    anthropic = result.get("Anthropic", {})
    assert anthropic["github_repos"] == 300
    assert anthropic["github_followers"] == 5000
    assert anthropic["source"] == "manual+github"


def test_enrich_prestige_fetch_failure(monkeypatch):
    """Failed GitHub fetch should not crash — company keeps static score."""

    def fake_fetch(org):
        return None

    monkeypatch.setattr(enrich_prestige, "_fetch_github_org", fake_fetch)
    monkeypatch.setattr(enrich_prestige, "RATE_DELAY", 0)

    result = enrich_prestige.enrich_prestige(fetch_github=True)
    anthropic = result.get("Anthropic", {})
    assert anthropic["source"] == "manual"
    assert anthropic["github_repos"] is None


def test_enrich_prestige_score_capped_at_10(monkeypatch):
    """Score + boost should never exceed 10."""

    def fake_fetch(org):
        return {"public_repos": 1000, "followers": 50000}

    monkeypatch.setattr(enrich_prestige, "_fetch_github_org", fake_fetch)
    monkeypatch.setattr(enrich_prestige, "RATE_DELAY", 0)

    result = enrich_prestige.enrich_prestige(fetch_github=True)
    for info in result.values():
        assert info["score"] <= 10


def test_write_cache(tmp_path):
    data = {"TestCo": {"score": 7, "source": "manual", "github_repos": None, "github_followers": None}}
    cache_path = tmp_path / "cache.json"
    enrich_prestige.write_cache(data, path=cache_path)
    assert cache_path.exists()
    loaded = json.loads(cache_path.read_text())
    assert "generated" in loaded
    assert loaded["companies"]["TestCo"]["score"] == 7


def test_load_cache_fresh(tmp_path):
    cache_path = tmp_path / "cache.json"
    cache_data = {
        "generated": datetime.now(UTC).isoformat(),
        "companies": {"TestCo": {"score": 7}},
    }
    cache_path.write_text(json.dumps(cache_data))
    result = enrich_prestige.load_cache(path=cache_path)
    assert result is not None
    assert result["TestCo"]["score"] == 7


def test_load_cache_stale(tmp_path):
    cache_path = tmp_path / "cache.json"
    old_date = datetime.now(UTC) - timedelta(days=10)
    cache_data = {
        "generated": old_date.isoformat(),
        "companies": {"TestCo": {"score": 7}},
    }
    cache_path.write_text(json.dumps(cache_data))
    result = enrich_prestige.load_cache(path=cache_path)
    assert result is None


def test_load_cache_missing(tmp_path):
    result = enrich_prestige.load_cache(path=tmp_path / "nonexistent.json")
    assert result is None


def test_load_cache_malformed(tmp_path):
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("not json")
    result = enrich_prestige.load_cache(path=cache_path)
    assert result is None
