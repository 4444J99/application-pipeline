import os
import sys
from unittest.mock import Mock

import pytest

# Ensure scripts dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

import run as run_module
from run import run_command


def test_run_standalone_command(monkeypatch):
    """Verify run_command calls subprocess.run correctly for standalone commands."""
    mock_run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(run_module.subprocess, "run", mock_run)

    with pytest.raises(SystemExit) as excinfo:
        run_command("standup")

    assert excinfo.value.code == 0
    args = mock_run.call_args[0][0]
    assert "standup.py" in args[1]


def test_run_parameterized_command(monkeypatch):
    """Verify run_command calls subprocess.run correctly for parameterized commands."""
    mock_run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(run_module.subprocess, "run", mock_run)

    with pytest.raises(SystemExit) as excinfo:
        run_command("score", "test-target")

    assert excinfo.value.code == 0
    args = mock_run.call_args[0][0]
    assert "score.py" in args[1]
    assert "--target" in args
    assert "test-target" in args

def test_run_unknown_command():
    """Verify run_command exits with 1 for unknown commands."""
    with pytest.raises(SystemExit) as excinfo:
        run_command("nonexistent-command")

    assert excinfo.value.code == 1


def test_run_missing_parameter():
    """Verify run_command exits with 1 when parameter is missing for PARAM_COMMANDS."""
    with pytest.raises(SystemExit) as excinfo:
        run_command("score")  # missing target-id

    assert excinfo.value.code == 1


def test_run_standalone_passthrough_args(monkeypatch):
    """Standalone commands should pass extra args through to the target script."""
    mock_run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(run_module.subprocess, "run", mock_run)

    with pytest.raises(SystemExit) as excinfo:
        run_command("batch", extra_args=["--yes", "--limit", "2"])

    assert excinfo.value.code == 0
    args = mock_run.call_args[0][0]
    assert "batch_submit.py" in args[1]
    assert "--yes" in args
    assert "--limit" in args
