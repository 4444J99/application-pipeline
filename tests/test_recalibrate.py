#!/usr/bin/env python3
"""Tests for recalibrate.py — quarterly rubric recalibration."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from recalibrate import run_proposal


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
