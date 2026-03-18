"""Tests for network_graph.py — network graph with path-finding and scoring."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from network_graph import (
    COLD_SCORE,
    HOP_SCORE,
    add_edge,
    all_paths_to_org,
    build_adjacency,
    ensure_node,
    find_edge,
    find_node,
    get_org_members,
    path_strength,
    score_org_proximity,
    shortest_paths,
)


@pytest.fixture
def empty_network():
    return {"nodes": [], "edges": []}


@pytest.fixture
def simple_network():
    """A -> B(OrgX) -> C(OrgY), A -> D(OrgY)"""
    return {
        "nodes": [
            {"name": "A", "organization": "Self", "role": "", "degree": 0,
             "channel": "linkedin", "last_interaction": "", "tags": []},
            {"name": "B", "organization": "OrgX", "role": "EM",  "degree": 1,
             "channel": "linkedin", "last_interaction": "", "tags": []},
            {"name": "C", "organization": "OrgY", "role": "SWE", "degree": 1,
             "channel": "linkedin", "last_interaction": "", "tags": []},
            {"name": "D", "organization": "OrgY", "role": "PM",  "degree": 1,
             "channel": "linkedin", "last_interaction": "", "tags": []},
        ],
        "edges": [
            {"from": "A", "to": "B", "strength": 5, "relationship_type": "professional", "created": "2026-01-01"},
            {"from": "B", "to": "C", "strength": 7, "relationship_type": "professional", "created": "2026-01-01"},
            {"from": "A", "to": "D", "strength": 3, "relationship_type": "seed", "created": "2026-01-01"},
        ],
    }


# --- Node operations ---


class TestNodeOperations:
    def test_ensure_node_creates(self, empty_network):
        node = ensure_node(empty_network, "Alice", organization="Acme")
        assert node["name"] == "Alice"
        assert node["organization"] == "Acme"
        assert len(empty_network["nodes"]) == 1

    def test_ensure_node_finds_existing(self, empty_network):
        ensure_node(empty_network, "Alice", organization="Acme")
        node = ensure_node(empty_network, "Alice", role="EM")
        assert node["organization"] == "Acme"
        assert node["role"] == "EM"
        assert len(empty_network["nodes"]) == 1

    def test_find_node_case_insensitive(self, empty_network):
        ensure_node(empty_network, "Alice")
        assert find_node(empty_network, "alice") is not None
        assert find_node(empty_network, "ALICE") is not None

    def test_find_node_missing(self, empty_network):
        assert find_node(empty_network, "Nobody") is None


# --- Edge operations ---


class TestEdgeOperations:
    def test_add_edge(self, empty_network):
        ensure_node(empty_network, "A")
        ensure_node(empty_network, "B")
        edge = add_edge(empty_network, "A", "B", strength=5)
        assert edge["strength"] == 5
        assert len(empty_network["edges"]) == 1

    def test_add_edge_clamps_strength(self, empty_network):
        ensure_node(empty_network, "A")
        ensure_node(empty_network, "B")
        edge = add_edge(empty_network, "A", "B", strength=15)
        assert edge["strength"] == 10

    def test_add_edge_updates_existing(self, empty_network):
        ensure_node(empty_network, "A")
        ensure_node(empty_network, "B")
        add_edge(empty_network, "A", "B", strength=3)
        add_edge(empty_network, "A", "B", strength=7)
        assert len(empty_network["edges"]) == 1
        assert empty_network["edges"][0]["strength"] == 7

    def test_find_edge_undirected(self, empty_network):
        ensure_node(empty_network, "A")
        ensure_node(empty_network, "B")
        add_edge(empty_network, "A", "B", strength=5)
        assert find_edge(empty_network, "A", "B") is not None
        assert find_edge(empty_network, "B", "A") is not None

    def test_find_edge_missing(self, empty_network):
        assert find_edge(empty_network, "A", "B") is None


# --- Graph operations ---


class TestGraphOperations:
    def test_build_adjacency(self, simple_network):
        adj = build_adjacency(simple_network)
        assert "A" in adj
        assert len(adj["A"]) == 2  # B and D
        assert len(adj["B"]) == 2  # A and C

    def test_get_org_members(self, simple_network):
        members = get_org_members(simple_network, "OrgY")
        assert set(members) == {"C", "D"}

    def test_get_org_members_case_insensitive(self, simple_network):
        members = get_org_members(simple_network, "orgy")
        assert set(members) == {"C", "D"}

    def test_get_org_members_empty(self, simple_network):
        assert get_org_members(simple_network, "NoSuchOrg") == []


# --- Path finding ---


class TestPathFinding:
    def test_shortest_path_direct(self, simple_network):
        paths = shortest_paths(simple_network, "A", "OrgX")
        assert len(paths) == 1
        assert paths[0] == ["A", "B"]

    def test_shortest_path_two_hop(self, simple_network):
        paths = shortest_paths(simple_network, "A", "OrgY")
        # A->D is 1 hop (shortest), A->B->C is 2 hops
        assert any(len(p) == 2 for p in paths)  # 1-hop path exists

    def test_shortest_path_no_path(self, simple_network):
        paths = shortest_paths(simple_network, "A", "NoSuchOrg")
        assert paths == []

    def test_all_paths_to_org(self, simple_network):
        paths = all_paths_to_org(simple_network, "A", "OrgY")
        assert len(paths) == 2  # A->D and A->B->C
        assert any(p == ["A", "D"] for p in paths)
        assert any(p == ["A", "B", "C"] for p in paths)

    def test_all_paths_respects_max_hops(self, simple_network):
        paths = all_paths_to_org(simple_network, "A", "OrgY", max_hops=1)
        # Only A->D (1 hop); A->B->C is 2 hops
        assert all(len(p) <= 2 for p in paths)

    def test_path_strength_single_edge(self, simple_network):
        ps = path_strength(simple_network, ["A", "B"])
        assert ps == 5.0

    def test_path_strength_multi_edge(self, simple_network):
        # A->B (5) -> C (7), harmonic mean = 2 / (1/5 + 1/7) = 2 / 0.343 ≈ 5.83
        ps = path_strength(simple_network, ["A", "B", "C"])
        assert 5.8 <= ps <= 5.9

    def test_path_strength_empty_path(self, simple_network):
        assert path_strength(simple_network, ["A"]) == 10.0


# --- Scoring ---


class TestScoring:
    def test_score_direct_connection(self, simple_network):
        result = score_org_proximity(simple_network, "A", "OrgX")
        assert result["hop_count"] == 1
        assert result["label"] == "direct_connection"
        assert result["score"] == HOP_SCORE[1]  # 8, no redundancy

    def test_score_with_redundancy(self, simple_network):
        result = score_org_proximity(simple_network, "A", "OrgY")
        assert result["independent_paths"] == 2
        assert result["score"] >= HOP_SCORE[1]  # At least base for 1-hop

    def test_score_cold(self, simple_network):
        result = score_org_proximity(simple_network, "A", "NoSuchOrg")
        assert result["score"] == COLD_SCORE
        assert result["label"] == "cold"
        assert result["hop_count"] is None

    def test_score_bounded_1_10(self, simple_network):
        result = score_org_proximity(simple_network, "A", "OrgY")
        assert 1 <= result["score"] <= 10

    def test_score_insider_density(self, simple_network):
        result = score_org_proximity(simple_network, "A", "OrgY")
        assert result["insider_density"] == 2  # C and D


# --- Hop score decay ---


class TestHopDecay:
    def test_hop_scores_decrease(self):
        """Scores must strictly decrease with more hops."""
        assert HOP_SCORE[0] > HOP_SCORE[1] > HOP_SCORE[2] > HOP_SCORE[3] > COLD_SCORE

    def test_cold_is_minimum(self):
        assert COLD_SCORE == 1
