import pytest
from typer.testing import CliRunner
import sys
import os
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from cli import app

runner = CliRunner()

def test_cli_help():
    """Verify help output works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Application Pipeline CLI" in result.output

def test_cli_standup_dry_run(mocker):
    """Verify standup command calls run_standup."""
    mock_run = mocker.patch("cli.run_standup")
    result = runner.invoke(app, ["standup", "--hours", "2.0"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(2.0, None, False, track_filter=None)

def test_cli_status_proxy(mocker):
    """Verify status command proxies to pipeline_status.main."""
    mock_main = mocker.patch("cli.status_main")
    result = runner.invoke(app, ["status", "--upcoming", "14"])
    assert result.exit_code == 0
    mock_main.assert_called_once()

def test_cli_score_proxy(mocker):
    """Verify score command proxies to score.main."""
    mock_main = mocker.patch("cli.score_main")
    result = runner.invoke(app, ["score", "test-target", "--dry-run"])
    assert result.exit_code == 0
    mock_main.assert_called_once()

def test_cli_advance_proxy(mocker):
    """Verify advance command proxies to advance.main."""
    mock_main = mocker.patch("cli.advance_main")
    result = runner.invoke(app, ["advance", "test-target", "--to", "staged"])
    assert result.exit_code == 0
    mock_main.assert_called_once()
