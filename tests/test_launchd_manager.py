"""Tests for scripts/launchd_manager.py."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import launchd_manager as launchd_mod


def _make_plists(tmp_path):
    launchd_dir = tmp_path / "launchd"
    launchd_dir.mkdir()
    alpha = launchd_dir / "com.4jp.pipeline.alpha.plist"
    beta = launchd_dir / "com.4jp.pipeline.beta.plist"
    alpha.write_text("<plist/>")
    beta.write_text("<plist/>")
    return [alpha, beta]


def test_install_agents_dry_run_prints_actions(tmp_path, monkeypatch, capsys):
    plists = _make_plists(tmp_path)
    monkeypatch.setattr(launchd_mod, "_ensure_macos", lambda: None)
    monkeypatch.setattr(launchd_mod, "_plist_paths", lambda: plists)
    monkeypatch.setattr(launchd_mod, "USER_LAUNCH_AGENTS", tmp_path / "agents")
    monkeypatch.setattr(launchd_mod, "LOG_DIR", tmp_path / "logs")

    launchd_mod.install_agents(kickstart=True, dry_run=True)
    output = capsys.readouterr().out
    assert "launchctl bootstrap" in output
    assert "launchctl kickstart -k" in output


def test_show_status_reports_install_and_load_counts(tmp_path, monkeypatch, capsys):
    plists = _make_plists(tmp_path)
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / plists[0].name).write_text("installed")

    monkeypatch.setattr(launchd_mod, "_ensure_macos", lambda: None)
    monkeypatch.setattr(launchd_mod, "_plist_paths", lambda: plists)
    monkeypatch.setattr(launchd_mod, "USER_LAUNCH_AGENTS", agents_dir)

    def fake_run(cmd, check=True):  # noqa: ARG001
        label = cmd[-1]
        return SimpleNamespace(returncode=0 if label.endswith("com.4jp.pipeline.alpha") else 1)

    monkeypatch.setattr(launchd_mod, "_run", fake_run)
    launchd_mod.show_status()
    output = capsys.readouterr().out
    assert "Installed: 1/2 | Loaded: 1/2" in output


def test_main_rejects_install_and_uninstall_flags(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["launchd_manager.py", "--install", "--uninstall"])
    with pytest.raises(SystemExit) as exc:
        launchd_mod.main()
    assert exc.value.code == 1
