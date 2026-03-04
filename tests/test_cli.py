import os
import sys

from typer.testing import CliRunner

# Ensure scripts dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from cli import app
from pipeline_api import ResultStatus, ValidationResult

runner = CliRunner()


def test_cli_help():
    """Verify help output works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Application Pipeline CLI" in result.output


def test_cli_commands_available():
    """Verify all expected commands are available."""
    result = runner.invoke(app, ["--help"])
    assert "score" in result.output
    assert "advance" in result.output
    assert "draft" in result.output
    assert "compose" in result.output
    assert "validate" in result.output
    assert "standup" in result.output


def test_cli_score_requires_args():
    """Verify score command requires --target, --all, or --auto-qualify."""
    result = runner.invoke(app, ["score"])
    assert result.exit_code != 0
    assert "Specify" in result.output or "error" in result.output.lower()


def test_cli_score_all_dry_run():
    """Verify score --all --dry-run is accepted and executes."""
    result = runner.invoke(app, ["score", "--all", "--dry-run"])
    assert result.exit_code == 0
    assert "batch" in result.output.lower() or "scored" in result.output.lower()


def test_cli_advance_requires_target():
    """Verify advance command requires target."""
    result = runner.invoke(app, ["advance"])
    assert result.exit_code != 0


def test_cli_standup_help():
    """Verify standup command help."""
    result = runner.invoke(app, ["standup", "--help"])
    assert result.exit_code == 0
    assert "Daily dashboard" in result.output


def test_cli_validate_handles_error_without_crash(monkeypatch):
    """Validate command should show errors cleanly instead of throwing AttributeError."""

    def _fake_validate(entry_id=None, entry_dict=None):
        return ValidationResult(
            status=ResultStatus.ERROR,
            entry_id=entry_id or "all",
            is_valid=False,
            errors=["synthetic validation error"],
            message="validation failed",
            error="synthetic validation error",
        )

    monkeypatch.setattr("cli.validate_entry", _fake_validate)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code != 0
    assert "synthetic validation error" in result.output
