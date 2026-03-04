"""Direct tests for scripts/score_network.py."""

import sys
from pathlib import Path

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
