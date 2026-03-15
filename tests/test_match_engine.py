"""Tests for match_engine.py — auto-score, auto-qualify, rank matches."""

import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from match_engine import MatchResult, ScoredEntry, _log_match_result, match_and_rank


class TestDataclasses:
    def test_scored_entry_fields(self):
        """ScoredEntry has all required fields."""
        e = ScoredEntry(
            entry_id="test-id",
            composite_score=8.5,
            dimensions={"org_prestige": 7.0},
            text_match_score=0.65,
            identity_position="independent-engineer",
            organization="TestOrg",
        )
        assert e.composite_score == 8.5
        assert e.identity_position == "independent-engineer"

    def test_match_result_fields(self):
        """MatchResult has all required fields."""
        r = MatchResult(
            scored=[],
            qualified=[],
            top_matches=[],
            threshold_used=8.5,
            entries_scored=0,
        )
        assert r.threshold_used == 8.5

    def test_match_result_serializes(self):
        """MatchResult serializes to dict."""
        r = MatchResult(
            scored=[],
            qualified=[],
            top_matches=[],
            threshold_used=8.5,
            entries_scored=0,
        )
        d = asdict(r)
        assert "threshold_used" in d
        assert "entries_scored" in d

    def test_default_factory(self):
        """MatchResult defaults to empty lists."""
        r = MatchResult()
        assert r.scored == []
        assert r.qualified == []
        assert r.entries_scored == 0


class TestMatchAndRank:
    def test_dry_run_no_writes(self):
        """Dry run scores but does not advance entries."""
        with patch("match_engine._load_unscored_entries", return_value=[]):
            result = match_and_rank(dry_run=True)
            assert isinstance(result, MatchResult)
            assert result.qualified == []

    def test_scores_unscored_entries(self):
        """Scores entries that lack a composite score."""
        fake_entry = {
            "id": "test-co-engineer",
            "status": "research",
            "target": {"organization": "TestCo"},
            "identity_position": "independent-engineer",
        }
        scored = ScoredEntry(
            entry_id="test-co-engineer",
            composite_score=8.7,
            dimensions={},
            text_match_score=0.5,
            identity_position="independent-engineer",
            organization="TestCo",
        )
        with patch("match_engine._load_unscored_entries", return_value=[fake_entry]), \
             patch("match_engine._score_single", return_value=scored):
            result = match_and_rank(dry_run=True, top_n=5)
            assert result.entries_scored == 1
            assert len(result.scored) == 1

    def test_top_n_limits_output(self):
        """top_n parameter limits top_matches list."""
        entries = [
            {
                "id": f"entry-{i}",
                "status": "research",
                "target": {"organization": f"Org{i}"},
                "identity_position": "independent-engineer",
            }
            for i in range(20)
        ]
        scored_entries = [
            ScoredEntry(
                entry_id=f"entry-{i}",
                composite_score=9.0 - i * 0.1,
                dimensions={},
                text_match_score=0.5,
                identity_position="independent-engineer",
                organization=f"Org{i}",
            )
            for i in range(20)
        ]
        with patch("match_engine._load_unscored_entries", return_value=entries), \
             patch("match_engine._score_single", side_effect=scored_entries):
            result = match_and_rank(dry_run=True, top_n=5)
            assert len(result.top_matches) == 5

    def test_auto_qualify_promotes_above_threshold(self):
        """Entries above threshold are included in qualified list."""
        entry = {
            "id": "hot-co-engineer",
            "status": "research",
            "target": {"organization": "HotCo"},
            "identity_position": "independent-engineer",
        }
        scored = ScoredEntry(
            entry_id="hot-co-engineer",
            composite_score=9.1,
            dimensions={},
            text_match_score=0.8,
            identity_position="independent-engineer",
            organization="HotCo",
        )
        with patch("match_engine._load_unscored_entries", return_value=[entry]), \
             patch("match_engine._score_single", return_value=scored), \
             patch("match_engine._get_qualify_threshold", return_value=8.5):
            result = match_and_rank(dry_run=True, auto_qualify=True)
            assert "hot-co-engineer" in result.qualified

    def test_no_qualify_flag_skips_promotion(self):
        """auto_qualify=False skips qualification even for high scores."""
        entry = {
            "id": "hot-co-2",
            "status": "research",
            "target": {"organization": "HotCo2"},
            "identity_position": "independent-engineer",
        }
        scored = ScoredEntry(
            entry_id="hot-co-2",
            composite_score=9.5,
            dimensions={},
            text_match_score=0.9,
            identity_position="independent-engineer",
            organization="HotCo2",
        )
        with patch("match_engine._load_unscored_entries", return_value=[entry]), \
             patch("match_engine._score_single", return_value=scored):
            result = match_and_rank(dry_run=True, auto_qualify=False)
            assert result.qualified == []

    def test_sorts_by_score_descending(self):
        """Scored entries are sorted highest first."""
        entries = [
            {"id": f"e{i}", "status": "research", "target": {"organization": f"O{i}"}}
            for i in range(3)
        ]
        scores = [5.0, 9.0, 7.0]
        scored_list = [
            ScoredEntry(
                entry_id=f"e{i}",
                composite_score=scores[i],
                dimensions={},
                text_match_score=0.0,
                identity_position="independent-engineer",
                organization=f"O{i}",
            )
            for i in range(3)
        ]
        with patch("match_engine._load_unscored_entries", return_value=entries), \
             patch("match_engine._score_single", side_effect=scored_list):
            result = match_and_rank(dry_run=True)
            assert result.scored[0].composite_score == 9.0
            assert result.scored[-1].composite_score == 5.0

    def test_handles_score_failure(self):
        """Entries that fail scoring are skipped."""
        entries = [{"id": "bad", "status": "research", "target": {"organization": "X"}}]
        with patch("match_engine._load_unscored_entries", return_value=entries), \
             patch("match_engine._score_single", return_value=None):
            result = match_and_rank(dry_run=True)
            assert result.entries_scored == 0


class TestMatchHistory:
    def test_log_entry_format(self, tmp_path):
        """Match history log has expected fields."""
        log_path = tmp_path / "daily-matches.yaml"
        result = MatchResult(
            scored=[],
            qualified=["a"],
            top_matches=[],
            threshold_used=8.5,
            entries_scored=5,
        )
        _log_match_result(result, log_path)
        entries = yaml.safe_load(log_path.read_text())
        assert len(entries) == 1
        assert entries[0]["entries_scored"] == 5
        assert entries[0]["entries_qualified"] == 1

    def test_appends_to_existing(self, tmp_path):
        """Log appends to existing entries."""
        log_path = tmp_path / "daily-matches.yaml"
        log_path.write_text(yaml.dump([{"date": "2026-03-13"}]))
        result = MatchResult(entries_scored=3)
        _log_match_result(result, log_path)
        entries = yaml.safe_load(log_path.read_text())
        assert len(entries) == 2
