#!/usr/bin/env python3
"""Tests for recalibrate.py — quarterly rubric recalibration."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from recalibrate import _load_rubric_text, apply_proposal, run_proposal


class TestRunProposal:
    def test_insufficient_data_returns_none(self):
        with patch("recalibrate.recalibrate_weights", return_value=None):
            result = run_proposal()
        assert result is None

    def test_proposal_with_data(self, capsys):
        suggested = {
            "identity_alignment": 0.15,
            "financial_alignment": 0.10,
            "mission_fit": 0.15,
            "strategic_value": 0.10,
            "effort_to_value": 0.10,
            "deadline_feasibility": 0.10,
            "evidence_match": 0.10,
            "portal_friction": 0.10,
            "network_proximity": 0.10,
        }
        with patch("recalibrate.recalibrate_weights", return_value=suggested):
            result = run_proposal()
        assert result == suggested
        output = capsys.readouterr().out
        assert "RECALIBRATION PROPOSAL" in output


class TestHelpers:
    def test_load_rubric_text_returns_nonempty_string(self):
        text = _load_rubric_text()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_apply_proposal_writes_yaml_file(self, tmp_path, monkeypatch):
        rubric_path = tmp_path / "scoring-rubric.yaml"
        rubric_path.write_text(
            "weights:\n  identity_alignment: 0.12\n  financial_alignment: 0.10\n"
        )
        monkeypatch.setattr("recalibrate.RUBRIC_PATH", rubric_path)

        suggested = {"identity_alignment": 0.15, "financial_alignment": 0.08}
        apply_proposal(suggested)

        import yaml

        data = yaml.safe_load(rubric_path.read_text())
        assert data["weights"] == suggested
        assert "weights_previous" in data

    def test_run_proposal_insufficient_data_prints_message(self, capsys):
        with patch("recalibrate.recalibrate_weights", return_value=None):
            result = run_proposal()
        assert result is None
        output = capsys.readouterr().out
        assert "INSUFFICIENT DATA" in output
