"""Tests for scripts/score_telemetry.py."""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_telemetry


def test_log_score_run_appends_records(tmp_path, monkeypatch):
    telemetry_file = tmp_path / "score-telemetry.yaml"
    monkeypatch.setattr(score_telemetry, "SIGNALS_DIR", tmp_path)
    monkeypatch.setattr(score_telemetry, "TELEMETRY_PATH", telemetry_file)

    score_telemetry.log_score_run("auto_qualify", {"moved": 3})
    score_telemetry.log_score_run("reachable", {"reachable": 8})

    data = yaml.safe_load(telemetry_file.read_text())
    assert isinstance(data, dict)
    runs = data.get("runs")
    assert isinstance(runs, list)
    assert len(runs) == 2
    assert runs[0]["operation"] == "auto_qualify"
    assert runs[1]["operation"] == "reachable"
