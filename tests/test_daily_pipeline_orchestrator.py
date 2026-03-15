"""Tests for daily_pipeline_orchestrator.py — full 5-phase pipeline cycle."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from apply_engine import ApplyResult
from daily_pipeline_orchestrator import ALL_PHASES, run_daily_cycle
from match_engine import MatchResult
from material_builder import BuildResult
from outreach_engine import OutreachResult
from scan_orchestrator import ScanResult


def _mock_all_phases():
    """Return mock objects for all 5 phases."""
    return {
        "scan": ScanResult(new_entries=["a", "b"]),
        "match": MatchResult(
            scored=[], qualified=["a"], top_matches=[],
            threshold_used=8.5, entries_scored=2,
        ),
        "build": BuildResult(entries_processed=["a"]),
        "apply": ApplyResult(checked=[], submitted=["a"], skipped=[]),
        "outreach": OutreachResult(entries_processed=["a"], templates_generated=2),
    }


class TestAllPhases:
    def test_all_phases_defined(self):
        assert ALL_PHASES == ["scan", "match", "build", "apply", "outreach"]


class TestRunDailyCycle:
    def test_full_cycle_dry_run(self):
        """Full cycle dry run chains all five phases."""
        mocks = _mock_all_phases()
        with patch("daily_pipeline_orchestrator.scan_all", return_value=mocks["scan"]) as ms, \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=mocks["match"]) as mm, \
             patch("daily_pipeline_orchestrator.build_materials", return_value=mocks["build"]) as mb, \
             patch("daily_pipeline_orchestrator.apply_ready_entries", return_value=mocks["apply"]) as ma, \
             patch("daily_pipeline_orchestrator.prepare_outreach", return_value=mocks["outreach"]) as mo:
            result = run_daily_cycle(dry_run=True)
            for phase in ALL_PHASES:
                assert phase in result
            ms.assert_called_once()
            mm.assert_called_once()
            mb.assert_called_once()
            ma.assert_called_once()
            mo.assert_called_once()

    def test_scan_only_phase(self):
        """phases=['scan'] runs only scan."""
        scan_r = ScanResult(new_entries=[])
        with patch("daily_pipeline_orchestrator.scan_all", return_value=scan_r), \
             patch("daily_pipeline_orchestrator.match_and_rank") as mock_match, \
             patch("daily_pipeline_orchestrator.build_materials") as mock_build, \
             patch("daily_pipeline_orchestrator.apply_ready_entries") as mock_apply, \
             patch("daily_pipeline_orchestrator.prepare_outreach") as mock_outreach:
            result = run_daily_cycle(dry_run=True, phases=["scan"])
            assert "scan" in result
            assert "match" not in result
            assert "build" not in result
            assert "apply" not in result
            assert "outreach" not in result
            mock_match.assert_not_called()
            mock_build.assert_not_called()
            mock_apply.assert_not_called()
            mock_outreach.assert_not_called()

    def test_match_only_phase(self):
        """phases=['match'] runs only match."""
        match_r = MatchResult(
            scored=[], qualified=[], top_matches=[],
            threshold_used=8.5, entries_scored=0,
        )
        with patch("daily_pipeline_orchestrator.scan_all") as mock_scan, \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=match_r), \
             patch("daily_pipeline_orchestrator.build_materials") as mock_build:
            result = run_daily_cycle(dry_run=True, phases=["match"])
            assert "match" in result
            mock_scan.assert_not_called()
            mock_build.assert_not_called()

    def test_build_only_phase(self):
        """phases=['build'] runs only build."""
        build_r = BuildResult()
        with patch("daily_pipeline_orchestrator.scan_all") as mock_scan, \
             patch("daily_pipeline_orchestrator.match_and_rank") as mock_match, \
             patch("daily_pipeline_orchestrator.build_materials", return_value=build_r):
            result = run_daily_cycle(dry_run=True, phases=["build"])
            assert "build" in result
            mock_scan.assert_not_called()
            mock_match.assert_not_called()

    def test_apply_only_phase(self):
        """phases=['apply'] runs only apply."""
        apply_r = ApplyResult()
        with patch("daily_pipeline_orchestrator.scan_all") as mock_scan, \
             patch("daily_pipeline_orchestrator.apply_ready_entries", return_value=apply_r):
            result = run_daily_cycle(dry_run=True, phases=["apply"])
            assert "apply" in result
            mock_scan.assert_not_called()

    def test_outreach_only_phase(self):
        """phases=['outreach'] runs only outreach."""
        outreach_r = OutreachResult()
        with patch("daily_pipeline_orchestrator.scan_all") as mock_scan, \
             patch("daily_pipeline_orchestrator.prepare_outreach", return_value=outreach_r):
            result = run_daily_cycle(dry_run=True, phases=["outreach"])
            assert "outreach" in result
            mock_scan.assert_not_called()

    def test_scan_ids_passed_to_match(self):
        """Match receives scan's new entry IDs."""
        mocks = _mock_all_phases()
        with patch("daily_pipeline_orchestrator.scan_all", return_value=mocks["scan"]), \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=mocks["match"]) as mock_match, \
             patch("daily_pipeline_orchestrator.build_materials", return_value=mocks["build"]), \
             patch("daily_pipeline_orchestrator.apply_ready_entries", return_value=mocks["apply"]), \
             patch("daily_pipeline_orchestrator.prepare_outreach", return_value=mocks["outreach"]):
            run_daily_cycle(dry_run=True)
            call_kwargs = mock_match.call_args[1]
            assert call_kwargs["entry_ids"] == ["a", "b"]

    def test_match_qualified_passed_to_build(self):
        """Build receives match's qualified IDs."""
        mocks = _mock_all_phases()
        with patch("daily_pipeline_orchestrator.scan_all", return_value=mocks["scan"]), \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=mocks["match"]), \
             patch("daily_pipeline_orchestrator.build_materials", return_value=mocks["build"]) as mock_build, \
             patch("daily_pipeline_orchestrator.apply_ready_entries", return_value=mocks["apply"]), \
             patch("daily_pipeline_orchestrator.prepare_outreach", return_value=mocks["outreach"]):
            run_daily_cycle(dry_run=True)
            call_kwargs = mock_build.call_args[1]
            assert call_kwargs["entry_ids"] == ["a"]

    def test_json_serializable(self):
        """Result is JSON-serializable."""
        mocks = _mock_all_phases()
        with patch("daily_pipeline_orchestrator.scan_all", return_value=mocks["scan"]), \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=mocks["match"]), \
             patch("daily_pipeline_orchestrator.build_materials", return_value=mocks["build"]), \
             patch("daily_pipeline_orchestrator.apply_ready_entries", return_value=mocks["apply"]), \
             patch("daily_pipeline_orchestrator.prepare_outreach", return_value=mocks["outreach"]):
            result = run_daily_cycle(dry_run=True)
            serialized = json.dumps(result, default=str)
            assert len(serialized) > 0

    def test_none_phases_runs_all(self):
        """phases=None runs all five phases."""
        mocks = _mock_all_phases()
        with patch("daily_pipeline_orchestrator.scan_all", return_value=mocks["scan"]) as ms, \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=mocks["match"]) as mm, \
             patch("daily_pipeline_orchestrator.build_materials", return_value=mocks["build"]) as mb, \
             patch("daily_pipeline_orchestrator.apply_ready_entries", return_value=mocks["apply"]) as ma, \
             patch("daily_pipeline_orchestrator.prepare_outreach", return_value=mocks["outreach"]) as mo:
            result = run_daily_cycle(dry_run=True, phases=None)
            ms.assert_called_once()
            mm.assert_called_once()
            mb.assert_called_once()
            ma.assert_called_once()
            mo.assert_called_once()
            # 5 phase keys + auto_advance + followup_actions_logged
            assert len(result) >= 5
            for phase in ALL_PHASES:
                assert phase in result
