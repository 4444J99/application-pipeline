# tests/test_outcome_learner_historical.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pytest
import yaml


class TestLoadHistoricalOutcomes:
    """Test loading historical outcomes from YAML."""

    def test_loads_from_file(self, tmp_path, monkeypatch):
        data = {
            "metadata": {"total_records": 2},
            "entries": [
                {"company": "A", "title": "Dev", "applied_date": "2024-11-20",
                 "channel": "linkedin-easy-apply", "portal": "linkedin",
                 "outcome": "expired", "outcome_reason": "no_response"},
                {"company": "B", "title": "PM", "applied_date": "2024-12-01",
                 "channel": "applyall-blast", "portal": "greenhouse",
                 "outcome": "expired", "outcome_reason": "no_response"},
            ],
        }
        outfile = tmp_path / "historical-outcomes.yaml"
        with open(outfile, "w") as f:
            yaml.dump(data, f)

        import outcome_learner
        monkeypatch.setattr(outcome_learner, "HISTORICAL_OUTCOMES_PATH", outfile)
        records = outcome_learner.load_historical_outcomes()
        assert len(records) == 2
        assert records[0]["outcome"] == "expired"
        assert records[0]["channel"] == "linkedin-easy-apply"

    def test_returns_empty_if_no_file(self, tmp_path, monkeypatch):
        import outcome_learner
        monkeypatch.setattr(outcome_learner, "HISTORICAL_OUTCOMES_PATH",
                            tmp_path / "nonexistent.yaml")
        records = outcome_learner.load_historical_outcomes()
        assert records == []


class TestCollectAllOutcomeData:
    """Test combined outcome data collection."""

    def test_merges_pipeline_and_historical(self, tmp_path, monkeypatch):
        # Mock pipeline data
        import outcome_learner
        monkeypatch.setattr(outcome_learner, "collect_outcome_data",
                            lambda: [{"entry_id": "pipe-1", "outcome": "rejected",
                                     "composite_score": 7.5, "dimension_scores": {},
                                     "track": "job", "identity_position": "independent-engineer"}])
        historical = tmp_path / "hist.yaml"
        with open(historical, "w") as f:
            yaml.dump({"entries": [
                {"company": "A", "title": "Dev", "applied_date": "2024-11-20",
                 "channel": "linkedin-easy-apply", "portal": "linkedin",
                 "outcome": "expired", "outcome_reason": "no_response"},
            ]}, f)
        monkeypatch.setattr(outcome_learner, "HISTORICAL_OUTCOMES_PATH", historical)

        combined = outcome_learner.collect_all_outcome_data()
        assert len(combined) == 2
        # Pipeline records have composite_score, historical don't
        assert combined[0].get("composite_score") is not None
        assert combined[1].get("composite_score") is None
