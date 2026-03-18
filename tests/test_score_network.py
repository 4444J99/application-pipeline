"""Direct tests for scripts/score_network.py."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_network


def test_days_since_missing():
    assert score_network._days_since(None) is None


def test_score_network_referral_channel_min_8():
    score = score_network.score_network_proximity(
        {
            "id": "t1",
            "target": {"organization": "Test Corp"},
            "conversion": {"channel": "referral"},
            "follow_up": [],
            "outreach": [],
        }
    )
    assert score >= 8


def test_score_network_relationship_strength_internal():
    score = score_network.score_network_proximity(
        {
            "id": "t2",
            "target": {"organization": "Test Corp"},
            "network": {"relationship_strength": "internal"},
            "follow_up": [],
            "outreach": [],
        }
    )
    assert score == 10


# --- Graph integration tests ---


def test_score_from_graph_fallback_env_guard():
    """PIPELINE_METRICS_SOURCE=fallback should skip graph and return 1."""
    entry = {"target": {"organization": "Cloudflare"}}
    with patch.dict(os.environ, {"PIPELINE_METRICS_SOURCE": "fallback"}):
        assert score_network._score_from_graph(entry) == 1


def test_score_from_graph_no_org():
    """Entry without organization should return 1."""
    assert score_network._score_from_graph({"target": {}}) == 1
    assert score_network._score_from_graph({}) == 1


def test_score_from_graph_empty_network():
    """Empty network should return 1."""
    with patch.dict(os.environ, {}, clear=False):
        # Remove fallback guard if set
        os.environ.pop("PIPELINE_METRICS_SOURCE", None)
        mock_network = {"nodes": [], "edges": []}
        with patch("score_network.network_graph_module.load_network", return_value=mock_network) if hasattr(score_network, "network_graph_module") else patch("network_graph.load_network", return_value=mock_network):
            result = score_network._score_from_graph({"target": {"organization": "NoSuchOrg"}})
            assert result == 1


def test_score_from_graph_with_mocked_network():
    """Graph with a direct connection should boost score."""
    mock_network = {
        "nodes": [
            {"name": "Anthony Padavano", "organization": "ORGANVM"},
            {"name": "Test Person", "organization": "TargetCo"},
        ],
        "edges": [
            {"from": "Anthony Padavano", "to": "Test Person", "strength": 5,
             "relationship_type": "professional", "created": "2026-03-17"},
        ],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PIPELINE_METRICS_SOURCE", None)

        import network_graph
        with patch.object(network_graph, "load_network", return_value=mock_network):
            result = score_network._score_from_graph({"target": {"organization": "TargetCo"}})
            # 1-hop direct connection should score >= 7
            assert result >= 7


def test_score_from_graph_import_failure():
    """If network_graph import fails, should return 1 (graceful degradation)."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PIPELINE_METRICS_SOURCE", None)
        with patch.dict("sys.modules", {"network_graph": None}):
            result = score_network._score_from_graph({"target": {"organization": "Whatever"}})
            assert result == 1


def test_score_network_max_of_entry_and_graph():
    """Final score should be max(entry_score, graph_score)."""
    # Entry with cold network (score 1 from entry signals)
    entry = {
        "id": "t3",
        "target": {"organization": "TargetCo"},
        "network": {"relationship_strength": "cold"},
        "follow_up": [],
        "outreach": [],
        "conversion": {},
    }
    mock_network = {
        "nodes": [
            {"name": "Anthony Padavano", "organization": "ORGANVM"},
            {"name": "Contact A", "organization": "TargetCo"},
        ],
        "edges": [
            {"from": "Anthony Padavano", "to": "Contact A", "strength": 5,
             "relationship_type": "professional", "created": "2026-03-17"},
        ],
    }
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PIPELINE_METRICS_SOURCE", None)
        import network_graph
        with patch.object(network_graph, "load_network", return_value=mock_network):
            score = score_network.score_network_proximity(entry)
            # Entry signals = 1 (cold), graph = ~8 (1-hop). max() should pick graph.
            assert score >= 7


def test_score_bounded_1_10():
    """Score must always be in [1, 10]."""
    entry = {
        "id": "t4",
        "target": {"organization": "X"},
        "network": {"relationship_strength": "internal"},
        "conversion": {"channel": "referral"},
        "follow_up": [],
        "outreach": [],
    }
    score = score_network.score_network_proximity(entry)
    assert 1 <= score <= 10
