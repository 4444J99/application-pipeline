"""Tests for cultivate.py relationship cultivation workflow."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from cultivate import get_cultivation_candidates, suggest_actions


def _make_entry(entry_id="test", status="qualified", network_score=1, composite=7.5,
                org="Test Corp", **overrides):
    """Create a minimal entry for cultivation testing."""
    entry = {
        "id": entry_id,
        "name": f"Test {entry_id}",
        "status": status,
        "track": "job",
        "target": {"organization": org, "application_url": "https://example.com"},
        "fit": {
            "composite": composite,
            "identity_position": "independent-engineer",
            "dimensions": {"network_proximity": network_score},
        },
        "network": {"relationship_strength": "cold"} if network_score <= 1 else {},
    }
    entry.update(overrides)
    return entry


class TestCandidatesFiltering:
    """Test get_cultivation_candidates filtering."""

    def test_candidates_filters_reachable_only(self):
        """Only entries where network can push score above threshold should appear."""
        # Entry with very low non-network dims -> unreachable even with internal
        low_entry = _make_entry("low", composite=3.0)
        # Entry with moderate dims -> reachable with warm
        moderate_entry = _make_entry("moderate", composite=8.0)

        all_entries = [low_entry, moderate_entry]

        # Mock analyze_reachability to control results
        def mock_reachability(entry, all_e, threshold):
            eid = entry.get("id")
            if eid == "low":
                return {
                    "entry_id": "low",
                    "current_composite": 3.0,
                    "current_network": 1,
                    "threshold": threshold,
                    "scenarios": [],
                    "reachable_with": None,
                }
            return {
                "entry_id": "moderate",
                "current_composite": 8.0,
                "current_network": 1,
                "threshold": threshold,
                "scenarios": [
                    {"level": "warm", "network_score": 7, "composite": 9.2, "delta": 1.2, "crosses_threshold": True},
                ],
                "reachable_with": "warm",
            }

        with patch("cultivate.analyze_reachability", side_effect=mock_reachability):
            candidates = get_cultivation_candidates(all_entries, all_entries, threshold=9.0)

        ids = [c["entry_id"] for c in candidates]
        assert "moderate" in ids
        assert "low" not in ids

    def test_candidates_sorted_by_gap(self):
        """Candidates should be sorted by composite descending (closest to threshold first)."""
        entries = [
            _make_entry("far", composite=6.0),
            _make_entry("close", composite=8.5),
            _make_entry("mid", composite=7.5),
        ]

        def mock_reachability(entry, all_e, threshold):
            eid = entry.get("id")
            composite = {"far": 6.0, "close": 8.5, "mid": 7.5}[eid]
            return {
                "entry_id": eid,
                "current_composite": composite,
                "current_network": 1,
                "threshold": threshold,
                "scenarios": [
                    {"level": "warm", "network_score": 7, "composite": composite + 1.5,
                     "delta": 1.5, "crosses_threshold": composite + 1.5 >= threshold},
                ],
                "reachable_with": "warm",
            }

        with patch("cultivate.analyze_reachability", side_effect=mock_reachability):
            candidates = get_cultivation_candidates(entries, entries, threshold=9.0)

        ids = [c["entry_id"] for c in candidates]
        assert ids[0] == "close"  # highest composite first


class TestSuggestActions:
    """Test suggest_actions score delta inclusion."""

    def test_suggest_actions_includes_score_delta(self):
        """Suggestions should include concrete score delta values."""
        candidate = {
            "scenarios": [
                {"level": "acquaintance", "network_score": 4, "composite": 8.3,
                 "delta": 0.8, "crosses_threshold": False},
                {"level": "warm", "network_score": 7, "composite": 9.1,
                 "delta": 1.6, "crosses_threshold": True},
            ],
            "reachable_with": "warm",
        }
        suggestions = suggest_actions(candidate)
        assert len(suggestions) >= 2
        # Check that score deltas appear in suggestions
        assert "+0.8" in suggestions[0]
        assert "+1.6" in suggestions[1]
        # Check that UNLOCKS marker appears
        assert "UNLOCKS" in suggestions[1]
