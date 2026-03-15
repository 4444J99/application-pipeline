"""Tests for newly added CLI commands."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_followup_help():
    result = runner.invoke(app, ["followup", "--help"])
    assert result.exit_code == 0
    assert "follow-up" in result.output.lower() or "overdue" in result.output.lower()


def test_cli_enrich_requires_target_or_all():
    result = runner.invoke(app, ["enrich"])
    assert result.exit_code != 0


def test_cli_triage_help():
    result = runner.invoke(app, ["triage", "--help"])
    assert result.exit_code == 0
    assert "min-score" in result.output


def test_cli_hygiene_help():
    result = runner.invoke(app, ["hygiene", "--help"])
    assert result.exit_code == 0


def test_cli_diagnose_help():
    result = runner.invoke(app, ["diagnose", "--help"])
    assert result.exit_code == 0
    assert "diagnostic" in result.output.lower() or "scorecard" in result.output.lower()


def test_cli_scan_help():
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "scan" in result.output.lower()


def test_cli_match_help():
    result = runner.invoke(app, ["match", "--help"])
    assert result.exit_code == 0
    assert "score" in result.output.lower() or "match" in result.output.lower()


def test_cli_build_help():
    result = runner.invoke(app, ["build", "--help"])
    assert result.exit_code == 0
    assert "material" in result.output.lower() or "llm" in result.output.lower()


def test_cli_cycle_help():
    result = runner.invoke(app, ["cycle", "--help"])
    assert result.exit_code == 0
    assert "scan" in result.output.lower() or "cycle" in result.output.lower()


def test_cli_apply_help():
    result = runner.invoke(app, ["apply", "--help"])
    assert result.exit_code == 0
    assert "readiness" in result.output.lower() or "submit" in result.output.lower()


def test_cli_outreach_prep_help():
    result = runner.invoke(app, ["outreach-prep", "--help"])
    assert result.exit_code == 0
    assert "outreach" in result.output.lower() or "template" in result.output.lower()
