"""Tests for the network_proximity scoring dimension."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from score import score_network_proximity


def _make_entry(**overrides):
    """Create a minimal pipeline entry for testing."""
    entry = {
        "id": "test-entry",
        "name": "Test Entry",
        "track": "job",
        "status": "qualified",
        "target": {"organization": "Test Corp"},
        "conversion": {},
        "follow_up": [],
        "outreach": [],
    }
    entry.update(overrides)
    return entry


class TestNetworkProximityDefaults:
    """Test default/cold scoring."""

    def test_cold_entry_scores_1(self):
        entry = _make_entry()
        assert score_network_proximity(entry) == 1

    def test_no_network_field_scores_1(self):
        entry = _make_entry()
        entry.pop("network", None)
        assert score_network_proximity(entry) == 1

    def test_empty_network_field_scores_1(self):
        entry = _make_entry(network={})
        assert score_network_proximity(entry) == 1


class TestRelationshipStrength:
    """Test network.relationship_strength signal."""

    def test_invalid_enum_defaults_to_cold(self):
        entry = _make_entry(network={"relationship_strength": "best_friend"})
        assert score_network_proximity(entry) == 1

    def test_cold(self):
        entry = _make_entry(network={"relationship_strength": "cold"})
        assert score_network_proximity(entry) == 1

    def test_acquaintance(self):
        entry = _make_entry(network={"relationship_strength": "acquaintance"})
        assert score_network_proximity(entry) == 4

    def test_warm(self):
        entry = _make_entry(network={"relationship_strength": "warm"})
        assert score_network_proximity(entry) == 7

    def test_strong(self):
        entry = _make_entry(network={"relationship_strength": "strong"})
        assert score_network_proximity(entry) == 9

    def test_internal(self):
        entry = _make_entry(network={"relationship_strength": "internal"})
        assert score_network_proximity(entry) == 10


class TestReferralChannel:
    """Test conversion.channel == 'referral' signal."""

    def test_referral_channel_min_8(self):
        entry = _make_entry(conversion={"channel": "referral"})
        assert score_network_proximity(entry) >= 8

    def test_direct_channel_no_boost(self):
        entry = _make_entry(conversion={"channel": "direct"})
        assert score_network_proximity(entry) == 1


class TestFollowUpResponses:
    """Test follow_up with responses signal."""

    def test_replied_follow_up_min_7(self):
        entry = _make_entry(follow_up=[
            {"date": "2026-03-01", "channel": "linkedin", "response": "replied"}
        ])
        assert score_network_proximity(entry) >= 7

    def test_referred_follow_up_min_7(self):
        entry = _make_entry(follow_up=[
            {"date": "2026-03-01", "channel": "email", "response": "referred"}
        ])
        assert score_network_proximity(entry) >= 7

    def test_no_response_no_boost(self):
        entry = _make_entry(follow_up=[
            {"date": "2026-03-01", "channel": "linkedin", "response": "none"}
        ])
        assert score_network_proximity(entry) == 1

    def test_ignored_no_boost(self):
        entry = _make_entry(follow_up=[
            {"date": "2026-03-01", "channel": "linkedin", "response": "ignored"}
        ])
        assert score_network_proximity(entry) == 1


class TestOutreachActions:
    """Test outreach actions completed signal."""

    def test_two_done_outreach_min_5(self):
        entry = _make_entry(outreach=[
            {"type": "warm_contact", "status": "done"},
            {"type": "info_session", "status": "done"},
        ])
        assert score_network_proximity(entry) >= 5

    def test_one_done_outreach_min_4(self):
        entry = _make_entry(outreach=[
            {"type": "warm_contact", "status": "done"},
        ])
        assert score_network_proximity(entry) >= 4

    def test_planned_outreach_no_boost(self):
        entry = _make_entry(outreach=[
            {"type": "warm_contact", "status": "planned"},
        ])
        assert score_network_proximity(entry) == 1


class TestMutualConnections:
    """Test network.mutual_connections signal."""

    def test_five_or_more_mutual_connections_min_5(self):
        entry = _make_entry(network={"mutual_connections": 5})
        assert score_network_proximity(entry) >= 5

    def test_many_mutual_connections_min_5(self):
        entry = _make_entry(network={"mutual_connections": 20})
        assert score_network_proximity(entry) >= 5

    def test_four_mutual_connections_no_boost(self):
        entry = _make_entry(network={"mutual_connections": 4})
        assert score_network_proximity(entry) == 1

    def test_zero_mutual_connections_no_boost(self):
        entry = _make_entry(network={"mutual_connections": 0})
        assert score_network_proximity(entry) == 1

    def test_missing_mutual_connections_no_boost(self):
        entry = _make_entry(network={})
        assert score_network_proximity(entry) == 1

    def test_non_numeric_mutual_connections_no_boost(self):
        entry = _make_entry(network={"mutual_connections": "many"})
        assert score_network_proximity(entry) == 1


class TestOrgDensity:
    """Test organization density signal."""

    def test_multiple_entries_same_org(self):
        entry = _make_entry(id="e1", target={"organization": "Anthropic"})
        others = [
            _make_entry(id="e2", target={"organization": "Anthropic"}),
            _make_entry(id="e3", target={"organization": "Anthropic"}),
            _make_entry(id="e4", target={"organization": "Anthropic"}),
        ]
        assert score_network_proximity(entry, all_entries=[entry] + others) >= 4

    def test_one_other_entry_same_org(self):
        entry = _make_entry(id="e1", target={"organization": "Anthropic"})
        others = [
            _make_entry(id="e2", target={"organization": "Anthropic"}),
        ]
        assert score_network_proximity(entry, all_entries=[entry] + others) >= 3

    def test_no_other_entries_same_org(self):
        entry = _make_entry(id="e1", target={"organization": "Anthropic"})
        others = [
            _make_entry(id="e2", target={"organization": "Google"}),
        ]
        assert score_network_proximity(entry, all_entries=[entry] + others) == 1


class TestSignalPrecedence:
    """Highest signal wins."""

    def test_strong_relationship_beats_org_density(self):
        entry = _make_entry(
            id="e1",
            network={"relationship_strength": "strong"},
            target={"organization": "Anthropic"},
        )
        others = [_make_entry(id="e2", target={"organization": "Anthropic"})]
        score = score_network_proximity(entry, all_entries=[entry] + others)
        assert score == 9

    def test_internal_is_max(self):
        entry = _make_entry(network={"relationship_strength": "internal"})
        assert score_network_proximity(entry) == 10

    def test_score_clamped_to_10(self):
        """Even with all signals active, score should not exceed 10."""
        entry = _make_entry(
            network={"relationship_strength": "internal"},
            conversion={"channel": "referral"},
            follow_up=[{"response": "replied"}],
            outreach=[{"status": "done"}, {"status": "done"}],
        )
        assert score_network_proximity(entry) <= 10
