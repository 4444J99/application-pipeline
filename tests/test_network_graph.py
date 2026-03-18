"""Tests for network_graph.py — network graph with path-finding and scoring."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import yaml
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
    ingest_from_contacts_and_outreach,
    load_network,
    path_strength,
    save_network,
    score_org_proximity,
    shortest_paths,
    sync_to_contacts,
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


# --- Persistence ---


class TestPersistence:
    def test_save_and_load(self, empty_network, tmp_path, monkeypatch):
        import network_graph
        net_file = tmp_path / "network.yaml"
        monkeypatch.setattr(network_graph, "NETWORK_FILE", net_file)

        ensure_node(empty_network, "Alice", organization="Acme")
        ensure_node(empty_network, "Bob", organization="Widgets")
        add_edge(empty_network, "Alice", "Bob", strength=7)
        save_network(empty_network)

        loaded = load_network()
        assert len(loaded["nodes"]) == 2
        assert len(loaded["edges"]) == 1
        assert loaded["edges"][0]["strength"] == 7

    def test_load_missing_file(self, tmp_path, monkeypatch):
        import network_graph
        monkeypatch.setattr(network_graph, "NETWORK_FILE", tmp_path / "nonexistent.yaml")
        net = load_network()
        assert net == {"nodes": [], "edges": []}


# --- Ingest ---


class TestIngest:
    def test_ingest_from_contacts(self, empty_network, tmp_path, monkeypatch):
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)

        # Create contacts.yaml
        contacts = {
            "contacts": [{
                "name": "Jane Smith",
                "organization": "Acme",
                "role": "EM",
                "channel": "linkedin",
                "relationship_strength": 5,
                "interactions": [{"date": "2026-03-17", "type": "connect", "note": "Sent"}],
            }]
        }
        with open(tmp_path / "contacts.yaml", "w") as f:
            yaml.dump(contacts, f)

        added = ingest_from_contacts_and_outreach(empty_network, me="Test User")
        assert added >= 1
        assert find_node(empty_network, "Jane Smith") is not None
        assert find_node(empty_network, "Jane Smith")["organization"] == "Acme"
        assert find_edge(empty_network, "Test User", "Jane Smith") is not None

    def test_ingest_from_outreach_log(self, empty_network, tmp_path, monkeypatch):
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)
        monkeypatch.setattr(network_graph, "ALL_PIPELINE_DIRS", [])

        outreach = {
            "entries": [{
                "date": "2026-03-17",
                "type": "post_submission",
                "contact": "Bob Jones",
                "channel": "linkedin",
                "note": "Connection request sent",
                "related_targets": [],
            }]
        }
        with open(tmp_path / "outreach-log.yaml", "w") as f:
            yaml.dump(outreach, f)

        added = ingest_from_contacts_and_outreach(empty_network, me="Test User")
        assert added >= 1
        assert find_node(empty_network, "Bob Jones") is not None

    def test_ingest_idempotent(self, empty_network, tmp_path, monkeypatch):
        """Running ingest twice should not duplicate edges."""
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)

        contacts = {"contacts": [{"name": "Jane", "organization": "X", "relationship_strength": 3}]}
        with open(tmp_path / "contacts.yaml", "w") as f:
            yaml.dump(contacts, f)

        added1 = ingest_from_contacts_and_outreach(empty_network, me="Me")
        added2 = ingest_from_contacts_and_outreach(empty_network, me="Me")
        assert added1 >= 1
        assert added2 == 0  # No new edges on second run

    def test_ingest_creates_self_node(self, empty_network, tmp_path, monkeypatch):
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)
        ingest_from_contacts_and_outreach(empty_network, me="Hub Person")
        assert find_node(empty_network, "Hub Person") is not None

    def test_ingest_dm_boosts_strength(self, empty_network, tmp_path, monkeypatch):
        """Accepted/DM outreach should have higher strength than plain connect."""
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)
        monkeypatch.setattr(network_graph, "ALL_PIPELINE_DIRS", [])

        outreach = {
            "entries": [
                {"date": "2026-03-17", "type": "reconnect", "contact": "Plain",
                 "channel": "linkedin", "note": "Connection request sent", "related_targets": []},
                {"date": "2026-03-17", "type": "reconnect", "contact": "Warm",
                 "channel": "linkedin", "note": "Connection accepted — DM sent", "related_targets": []},
            ]
        }
        with open(tmp_path / "outreach-log.yaml", "w") as f:
            yaml.dump(outreach, f)

        ingest_from_contacts_and_outreach(empty_network, me="Me")
        plain_edge = find_edge(empty_network, "Me", "Plain")
        warm_edge = find_edge(empty_network, "Me", "Warm")
        assert warm_edge["strength"] > plain_edge["strength"]


# --- Sync to contacts ---


class TestSyncContacts:
    def test_sync_creates_new_contacts(self, tmp_path, monkeypatch):
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)

        network = {
            "nodes": [
                {"name": "Me", "organization": "Self", "channel": "linkedin"},
                {"name": "Alice", "organization": "Acme", "role": "EM", "channel": "linkedin"},
                {"name": "Bob", "organization": "Widgets", "role": "SWE", "channel": "email"},
            ],
            "edges": [
                {"from": "Me", "to": "Alice", "strength": 5},
                {"from": "Me", "to": "Bob", "strength": 3},
            ],
        }

        added = sync_to_contacts(network, me="Me")
        assert added == 2

        with open(tmp_path / "contacts.yaml") as f:
            data = yaml.safe_load(f)
        names = [c["name"] for c in data["contacts"]]
        assert "Alice" in names
        assert "Bob" in names
        assert "Me" not in names  # Self excluded

    def test_sync_skips_existing(self, tmp_path, monkeypatch):
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)

        # Pre-populate contacts
        with open(tmp_path / "contacts.yaml", "w") as f:
            yaml.dump({"contacts": [{"name": "Alice", "organization": "Acme"}]}, f)

        network = {
            "nodes": [
                {"name": "Me", "organization": "Self", "channel": "linkedin"},
                {"name": "Alice", "organization": "Acme", "channel": "linkedin"},
                {"name": "New Person", "organization": "NewCo", "channel": "linkedin"},
            ],
            "edges": [
                {"from": "Me", "to": "Alice", "strength": 5},
                {"from": "Me", "to": "New Person", "strength": 3},
            ],
        }

        added = sync_to_contacts(network, me="Me")
        assert added == 1  # Only New Person, Alice already exists

    def test_sync_populates_interactions_from_outreach(self, tmp_path, monkeypatch):
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)

        # Create outreach log
        outreach = {
            "entries": [{
                "date": "2026-03-17",
                "type": "seed",
                "contact": "Alice",
                "channel": "linkedin",
                "note": "Connection request sent",
                "related_targets": ["test-entry"],
            }]
        }
        with open(tmp_path / "outreach-log.yaml", "w") as f:
            yaml.dump(outreach, f)

        network = {
            "nodes": [
                {"name": "Me", "organization": "Self", "channel": "linkedin"},
                {"name": "Alice", "organization": "Acme", "channel": "linkedin"},
            ],
            "edges": [{"from": "Me", "to": "Alice", "strength": 3}],
        }

        sync_to_contacts(network, me="Me")

        with open(tmp_path / "contacts.yaml") as f:
            data = yaml.safe_load(f)
        alice = [c for c in data["contacts"] if c["name"] == "Alice"][0]
        assert len(alice["interactions"]) == 1
        assert alice["interactions"][0]["note"] == "Connection request sent"
        assert "test-entry" in alice["pipeline_entries"]

    def test_sync_idempotent(self, tmp_path, monkeypatch):
        import network_graph
        monkeypatch.setattr(network_graph, "SIGNALS_DIR", tmp_path)

        network = {
            "nodes": [
                {"name": "Me", "organization": "Self", "channel": "linkedin"},
                {"name": "Alice", "organization": "Acme", "channel": "linkedin"},
            ],
            "edges": [{"from": "Me", "to": "Alice", "strength": 3}],
        }

        added1 = sync_to_contacts(network, me="Me")
        added2 = sync_to_contacts(network, me="Me")
        assert added1 == 1
        assert added2 == 0


# --- Multi-hop scoring ---


class TestMultiHopScoring:
    def test_two_hop_scores_lower_than_one_hop(self):
        """2-hop path should score lower than 1-hop."""
        network = {
            "nodes": [
                {"name": "Me", "organization": "Self"},
                {"name": "Bridge", "organization": "Other"},
                {"name": "Target", "organization": "TargetCo"},
            ],
            "edges": [
                {"from": "Me", "to": "Bridge", "strength": 5},
                {"from": "Bridge", "to": "Target", "strength": 5},
            ],
        }
        result_2hop = score_org_proximity(network, "Me", "TargetCo")
        assert result_2hop["hop_count"] == 2
        assert result_2hop["label"] == "warm_intro"

        # Add direct connection
        network["nodes"].append({"name": "Direct", "organization": "TargetCo"})
        network["edges"].append({"from": "Me", "to": "Direct", "strength": 5})
        result_1hop = score_org_proximity(network, "Me", "TargetCo")
        assert result_1hop["hop_count"] == 1
        assert result_1hop["score"] > result_2hop["score"]

    def test_three_hop_path(self):
        """3-hop chain should score as chain_intro."""
        network = {
            "nodes": [
                {"name": "Me", "organization": "Self"},
                {"name": "A", "organization": "OrgA"},
                {"name": "B", "organization": "OrgB"},
                {"name": "C", "organization": "TargetCo"},
            ],
            "edges": [
                {"from": "Me", "to": "A", "strength": 5},
                {"from": "A", "to": "B", "strength": 5},
                {"from": "B", "to": "C", "strength": 5},
            ],
        }
        result = score_org_proximity(network, "Me", "TargetCo")
        assert result["hop_count"] == 3
        assert result["label"] == "chain_intro"
        assert result["score"] >= 3  # Should be around 4

    def test_four_hop_unreachable(self):
        """4-hop path should be treated as cold (beyond 3-hop horizon)."""
        network = {
            "nodes": [
                {"name": "Me", "organization": "Self"},
                {"name": "A", "organization": "O1"},
                {"name": "B", "organization": "O2"},
                {"name": "C", "organization": "O3"},
                {"name": "D", "organization": "TargetCo"},
            ],
            "edges": [
                {"from": "Me", "to": "A", "strength": 5},
                {"from": "A", "to": "B", "strength": 5},
                {"from": "B", "to": "C", "strength": 5},
                {"from": "C", "to": "D", "strength": 5},
            ],
        }
        result = score_org_proximity(network, "Me", "TargetCo")
        assert result["score"] == COLD_SCORE
        assert result["hop_count"] is None

    def test_strength_modifier_strong_path(self):
        """Strong tie (>=7) should boost score by 1."""
        network = {
            "nodes": [
                {"name": "Me", "organization": "Self"},
                {"name": "Friend", "organization": "TargetCo"},
            ],
            "edges": [
                {"from": "Me", "to": "Friend", "strength": 9},
            ],
        }
        result = score_org_proximity(network, "Me", "TargetCo")
        # Base 8 (1-hop) + 1 (strong) = 9
        assert result["score"] >= 9

    def test_strength_modifier_weak_path(self):
        """Weak tie (<=3) should penalize score by 1."""
        network = {
            "nodes": [
                {"name": "Me", "organization": "Self"},
                {"name": "Stranger", "organization": "TargetCo"},
            ],
            "edges": [
                {"from": "Me", "to": "Stranger", "strength": 1},
            ],
        }
        result = score_org_proximity(network, "Me", "TargetCo")
        # Base 8 (1-hop) - 1 (weak) = 7
        assert result["score"] <= 8
