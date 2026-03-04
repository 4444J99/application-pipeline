"""Tests for scripts/pipeline_market.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_market import build_market_intelligence_loader


def test_loader_uses_defaults_when_file_missing(tmp_path):
    load_market_intelligence, get_portal_scores, get_strategic_base, _, _ = build_market_intelligence_loader(tmp_path)

    assert load_market_intelligence() == {}
    assert isinstance(get_portal_scores(), dict)
    assert isinstance(get_strategic_base(), dict)
    assert "email" in get_portal_scores()


def test_loader_reads_market_intel_when_present(tmp_path):
    strategy = tmp_path / "strategy"
    strategy.mkdir(parents=True, exist_ok=True)
    payload = {
        "portal_friction_scores": {"custom_portal": 3},
        "track_benchmarks": {"job": {"acceptance_rate": 0.03}},
    }
    (strategy / "market-intelligence-2026.json").write_text(json.dumps(payload))

    load_market_intelligence, get_portal_scores, get_strategic_base, _, _ = build_market_intelligence_loader(tmp_path)

    intel = load_market_intelligence()
    assert intel["portal_friction_scores"]["custom_portal"] == 3
    assert get_portal_scores()["custom_portal"] == 3
    assert get_strategic_base()["job"] == 7

