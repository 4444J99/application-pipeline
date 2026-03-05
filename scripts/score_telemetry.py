"""Telemetry helpers for score workflow command modes."""

from __future__ import annotations

from datetime import datetime

import yaml
from pipeline_lib import SIGNALS_DIR

TELEMETRY_PATH = SIGNALS_DIR / "score-telemetry.yaml"
MAX_RUNS = 500


def log_score_run(operation: str, payload: dict) -> None:
    """Append a structured telemetry record for score command operations."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "operation": operation,
        "payload": payload,
    }

    try:
        data = yaml.safe_load(TELEMETRY_PATH.read_text()) if TELEMETRY_PATH.exists() else {}
    except (OSError, yaml.YAMLError):
        data = {}

    if not isinstance(data, dict):
        data = {}
    runs = data.get("runs")
    if not isinstance(runs, list):
        runs = []
    runs.append(record)
    if len(runs) > MAX_RUNS:
        runs = runs[-MAX_RUNS:]
    data["runs"] = runs

    try:
        TELEMETRY_PATH.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    except OSError:
        # Telemetry should never block scoring operations.
        return
