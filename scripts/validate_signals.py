#!/usr/bin/env python3
"""Validate schema integrity of signal YAML files.

Checks signals/signal-actions.yaml, signals/conversion-log.yaml,
signals/hypotheses.yaml, and signals/agent-actions.yaml against
their expected schemas.

Usage:
    python scripts/validate_signals.py              # Report only (always exit 0)
    python scripts/validate_signals.py --strict     # Exit non-zero on any error
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SIGNAL_TYPES = {"hypothesis", "score_threshold", "pattern", "agent_rule", "conversion_data", "network_change"}
OUTCOMES = {None, "null", "rejected", "acknowledged", "withdrawn", "expired", "accepted"}
AGENT_MODES = {"plan", "execute"}


def _load_yaml(path: Path) -> dict | list | None:
    """Load a YAML file, returning None if missing or empty."""
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def _check_str(entry: dict, key: str, errors: list[str], label: str) -> None:
    """Assert a required string field exists."""
    val = entry.get(key)
    if val is None or not isinstance(val, str) or not val.strip():
        errors.append(f"{label}: missing or empty required field '{key}'")


def validate_signal_actions(errors: list[str]) -> int:
    """Validate signals/signal-actions.yaml. Returns entry count."""
    path = SIGNALS_DIR / "signal-actions.yaml"
    data = _load_yaml(path)
    if data is None:
        errors.append(f"{path}: file missing or empty")
        return 0
    if not isinstance(data, dict) or "actions" not in data:
        errors.append(f"{path}: missing top-level 'actions' key")
        return 0
    actions = data["actions"]
    if not isinstance(actions, list):
        errors.append(f"{path}: 'actions' must be a list")
        return 0

    for i, entry in enumerate(actions):
        label = f"{path} [action {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        _check_str(entry, "signal_id", errors, label)
        _check_str(entry, "description", errors, label)
        _check_str(entry, "triggered_action", errors, label)

        # signal_type must be from allowed set
        st = entry.get("signal_type")
        if not isinstance(st, str) or st not in SIGNAL_TYPES:
            errors.append(f"{label}: signal_type '{st}' not in {sorted(SIGNAL_TYPES)}")

        # action_date must be YYYY-MM-DD
        ad = str(entry.get("action_date", ""))
        if not DATE_RE.match(ad):
            errors.append(f"{label}: action_date '{ad}' is not YYYY-MM-DD format")

    return len(actions)


def validate_conversion_log(errors: list[str]) -> int:
    """Validate signals/conversion-log.yaml. Returns entry count."""
    path = SIGNALS_DIR / "conversion-log.yaml"
    data = _load_yaml(path)
    if data is None:
        errors.append(f"{path}: file missing or empty")
        return 0
    if not isinstance(data, dict) or "entries" not in data:
        errors.append(f"{path}: missing top-level 'entries' key")
        return 0
    entries = data["entries"]
    if not isinstance(entries, list):
        errors.append(f"{path}: 'entries' must be a list")
        return 0

    for i, entry in enumerate(entries):
        label = f"{path} [entry {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        _check_str(entry, "id", errors, label)
        _check_str(entry, "track", errors, label)

        # submitted must be a date string
        sub = str(entry.get("submitted", ""))
        if not DATE_RE.match(sub):
            errors.append(f"{label}: submitted '{sub}' is not YYYY-MM-DD format")

        # outcome is optional but validated when present and non-null
        outcome = entry.get("outcome")
        if outcome is not None and str(outcome) != "null" and outcome not in OUTCOMES:
            errors.append(f"{label}: outcome '{outcome}' not in {sorted(o for o in OUTCOMES if o)}")

    return len(entries)


def validate_hypotheses(errors: list[str]) -> int:
    """Validate signals/hypotheses.yaml. Returns entry count."""
    path = SIGNALS_DIR / "hypotheses.yaml"
    data = _load_yaml(path)
    if data is None:
        errors.append(f"{path}: file missing or empty")
        return 0
    if not isinstance(data, dict) or "hypotheses" not in data:
        errors.append(f"{path}: missing top-level 'hypotheses' key")
        return 0
    hypotheses = data["hypotheses"]
    if not isinstance(hypotheses, list):
        errors.append(f"{path}: 'hypotheses' must be a list")
        return 0

    for i, entry in enumerate(hypotheses):
        label = f"{path} [hypothesis {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        # id field: accept either 'id' or 'entry_id' as the identifier
        eid = entry.get("id") or entry.get("entry_id")
        if not eid or not isinstance(eid, str) or not eid.strip():
            errors.append(f"{label}: missing or empty required field 'id' (or 'entry_id')")
        _check_str(entry, "category", errors, label)

    return len(hypotheses)


def validate_agent_actions(errors: list[str]) -> int:
    """Validate signals/agent-actions.yaml. Returns entry count."""
    path = SIGNALS_DIR / "agent-actions.yaml"
    data = _load_yaml(path)
    if data is None:
        errors.append(f"{path}: file missing or empty")
        return 0
    if not isinstance(data, dict) or "runs" not in data:
        errors.append(f"{path}: missing top-level 'runs' key")
        return 0
    runs = data["runs"]
    if not isinstance(runs, list):
        errors.append(f"{path}: 'runs' must be a list")
        return 0

    for i, entry in enumerate(runs):
        label = f"{path} [run {i}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not a mapping")
            continue
        _check_str(entry, "timestamp", errors, label)

        mode = entry.get("mode")
        if not isinstance(mode, str) or mode not in AGENT_MODES:
            errors.append(f"{label}: mode '{mode}' not in {sorted(AGENT_MODES)}")

    return len(runs)


def validate_all_signals() -> tuple[list[str], dict]:
    """Validate all signal YAML files.

    Returns:
        (errors, stats) where errors is a list of error messages and
        stats maps file basename to validated entry count.
    """
    errors: list[str] = []
    stats: dict[str, int] = {}

    stats["signal-actions"] = validate_signal_actions(errors)
    stats["conversion-log"] = validate_conversion_log(errors)
    stats["hypotheses"] = validate_hypotheses(errors)
    stats["agent-actions"] = validate_agent_actions(errors)

    return errors, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate signal YAML schema integrity")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on any error")
    args = parser.parse_args()

    errors, stats = validate_all_signals()

    total_entries = sum(stats.values())
    print("Signal Validation Report")
    print("=" * 50)
    for name, count in stats.items():
        print(f"  {name}: {count} entries validated")
    print(f"  Total: {total_entries} entries")
    print(f"  Errors: {len(errors)}")

    if errors:
        print()
        for err in errors:
            print(f"  ERROR: {err}")

    if args.strict and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
