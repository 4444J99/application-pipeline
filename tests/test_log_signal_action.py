"""Tests for scripts/log_signal_action.py."""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import log_signal_action as signal_action_mod


def test_signal_actions_path_uses_env_override(tmp_path, monkeypatch):
    path = tmp_path / "custom-actions.yaml"
    monkeypatch.setenv(signal_action_mod.SIGNAL_ACTIONS_PATH_ENV, str(path))
    assert signal_action_mod._signal_actions_path() == path


def test_load_signal_actions_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv(signal_action_mod.SIGNAL_ACTIONS_PATH_ENV, str(tmp_path / "signal-actions.yaml"))
    assert signal_action_mod.load_signal_actions() == []


def test_log_action_persists_entry(tmp_path, monkeypatch):
    path = tmp_path / "signal-actions.yaml"
    monkeypatch.setenv(signal_action_mod.SIGNAL_ACTIONS_PATH_ENV, str(path))

    entry = signal_action_mod.log_action(
        signal_id="hyp-001",
        signal_type="hypothesis",
        description="Low conversion for portfolio language",
        triggered_action="Updated narrative block",
        entry_id="entry-1",
    )

    assert entry["signal_id"] == "hyp-001"
    actions = signal_action_mod.load_signal_actions()
    assert len(actions) == 1
    assert actions[0]["entry_id"] == "entry-1"
    assert path.exists()


def test_load_signal_actions_ignores_invalid_actions_shape(tmp_path, monkeypatch):
    path = tmp_path / "signal-actions.yaml"
    path.write_text(yaml.dump({"actions": {"not": "a-list"}}, sort_keys=False))
    monkeypatch.setenv(signal_action_mod.SIGNAL_ACTIONS_PATH_ENV, str(path))
    assert signal_action_mod.load_signal_actions() == []
