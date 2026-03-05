"""Parity checks between dispatcher commands and API surface."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pipeline_api
from run import COMMANDS, PARAM_COMMANDS


def test_pipeline_api_exports_core_operations():
    """Core pipeline operations should remain available in the API layer."""
    expected = [
        "score_entry",
        "advance_entry",
        "draft_entry",
        "compose_entry",
        "validate_entry",
    ]
    for name in expected:
        assert hasattr(pipeline_api, name), f"pipeline_api missing {name}"


def test_run_param_command_parity_with_core_scripts():
    """Parameterized dispatcher commands should route to expected scripts."""
    expected = {
        "score": "score.py",
        "advance": "advance.py",
        "draft": "draft.py",
        "compose": "compose.py",
    }
    for command, script in expected.items():
        assert command in PARAM_COMMANDS, f"run.py missing param command '{command}'"
        mapped_script, _args, _desc = PARAM_COMMANDS[command]
        assert mapped_script == script


def test_run_standalone_validate_command_parity():
    """Validation remains available as a top-level dispatcher command."""
    assert "validate" in COMMANDS
    script, _args, _desc = COMMANDS["validate"]
    assert script == "validate.py"
