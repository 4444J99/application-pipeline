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


def test_log_score_run_creates_file_if_absent(tmp_path, monkeypatch):
    telemetry_file = tmp_path / "score-telemetry.yaml"
    monkeypatch.setattr(score_telemetry, "SIGNALS_DIR", tmp_path)
    monkeypatch.setattr(score_telemetry, "TELEMETRY_PATH", telemetry_file)

    assert not telemetry_file.exists()
    score_telemetry.log_score_run("test_op", {"key": "value"})
    assert telemetry_file.exists()

    data = yaml.safe_load(telemetry_file.read_text())
    assert len(data["runs"]) == 1
    assert data["runs"][0]["operation"] == "test_op"


def test_log_score_run_empty_payload(tmp_path, monkeypatch):
    telemetry_file = tmp_path / "score-telemetry.yaml"
    monkeypatch.setattr(score_telemetry, "SIGNALS_DIR", tmp_path)
    monkeypatch.setattr(score_telemetry, "TELEMETRY_PATH", telemetry_file)

    score_telemetry.log_score_run("empty_test", {})
    data = yaml.safe_load(telemetry_file.read_text())
    assert data["runs"][0]["payload"] == {}


def test_log_score_run_timestamps_increase(tmp_path, monkeypatch):
    telemetry_file = tmp_path / "score-telemetry.yaml"
    monkeypatch.setattr(score_telemetry, "SIGNALS_DIR", tmp_path)
    monkeypatch.setattr(score_telemetry, "TELEMETRY_PATH", telemetry_file)

    score_telemetry.log_score_run("first", {"n": 1})
    score_telemetry.log_score_run("second", {"n": 2})

    data = yaml.safe_load(telemetry_file.read_text())
    assert data["runs"][0]["timestamp"] <= data["runs"][1]["timestamp"]
