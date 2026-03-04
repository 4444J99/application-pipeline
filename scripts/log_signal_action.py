#!/usr/bin/env python3
"""Log signal-to-action connections for audit trail.

Records when a pipeline signal (hypothesis, score threshold, pattern)
triggers a concrete action, creating an auditable feedback loop.

Usage:
    python scripts/log_signal_action.py --signal-id hyp-001 --signal-type hypothesis \
        --description "Low management exp" --action "Added leadership block" \
        --entry-id anthropic-swe
    python scripts/log_signal_action.py --list
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR, atomic_write

SIGNAL_ACTIONS_PATH = SIGNALS_DIR / "signal-actions.yaml"

VALID_SIGNAL_TYPES = {"hypothesis", "score_threshold", "pattern", "agent_rule", "conversion_data", "network_change"}


def load_signal_actions() -> list[dict]:
    """Load signal-actions.yaml."""
    if not SIGNAL_ACTIONS_PATH.exists():
        return []
    with open(SIGNAL_ACTIONS_PATH) as f:
        data = yaml.safe_load(f) or {}
    actions = data.get("actions", [])
    return actions if isinstance(actions, list) else []


def save_signal_actions(actions: list[dict]) -> None:
    """Save signal-actions.yaml."""
    content = yaml.dump({"actions": actions}, default_flow_style=False, sort_keys=False)
    atomic_write(SIGNAL_ACTIONS_PATH, content)


def log_action(
    signal_id: str,
    signal_type: str,
    description: str,
    triggered_action: str,
    entry_id: str | None = None,
    responsible: str = "@4444J99",
) -> dict:
    """Add a new signal-action entry."""
    if signal_type not in VALID_SIGNAL_TYPES:
        print(f"Warning: signal_type '{signal_type}' not in {VALID_SIGNAL_TYPES}", file=sys.stderr)

    entry = {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "description": description,
        "triggered_action": triggered_action,
        "action_date": date.today().isoformat(),
        "responsible": responsible,
        "impact": "TBD",
    }
    if entry_id:
        entry["entry_id"] = entry_id

    actions = load_signal_actions()
    actions.append(entry)
    save_signal_actions(actions)
    return entry


def list_actions() -> None:
    """Print all signal-action entries."""
    actions = load_signal_actions()
    if not actions:
        print("No signal-action entries recorded.")
        return
    print(f"Signal-Action Audit Trail ({len(actions)} entries)")
    print("=" * 60)
    for a in actions:
        print(f"\n  Signal: {a.get('signal_id', '?')} ({a.get('signal_type', '?')})")
        print(f"  Description: {a.get('description', '?')}")
        print(f"  Action: {a.get('triggered_action', '?')}")
        print(f"  Date: {a.get('action_date', '?')} | Impact: {a.get('impact', 'TBD')}")
        if a.get("entry_id"):
            print(f"  Entry: {a['entry_id']}")


def main():
    parser = argparse.ArgumentParser(description="Log signal-to-action connections")
    parser.add_argument("--list", action="store_true", help="List all signal-action entries")
    parser.add_argument("--signal-id", help="Signal identifier (e.g., hyp-001)")
    parser.add_argument("--signal-type", choices=sorted(VALID_SIGNAL_TYPES), help="Type of signal")
    parser.add_argument("--description", help="What the signal observed")
    parser.add_argument("--action", help="What action was triggered")
    parser.add_argument("--entry-id", help="Pipeline entry ID (optional)")
    args = parser.parse_args()

    if args.list:
        list_actions()
        return

    if not all([args.signal_id, args.signal_type, args.description, args.action]):
        parser.error("--signal-id, --signal-type, --description, and --action are all required")

    entry = log_action(
        signal_id=args.signal_id,
        signal_type=args.signal_type,
        description=args.description,
        triggered_action=args.action,
        entry_id=args.entry_id,
    )
    print(f"Logged signal-action: {entry['signal_id']} -> {entry['triggered_action']}")


if __name__ == "__main__":
    main()
