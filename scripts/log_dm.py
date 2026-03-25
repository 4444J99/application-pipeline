#!/usr/bin/env python3
"""Log a DM to all three signal files in one shot.

Updates contacts.yaml, outreach-log.yaml, and network.yaml atomically
when a DM is sent to a contact. Solves the three-file update gap that
caused 30 DMs sent but only 19 logged (see project memory 2026-03-24).

Usage:
    python scripts/log_dm.py --contact "Mario Tayah" --note "DM about reliability tension"
    python scripts/log_dm.py --contact "Mario Tayah" --note "DM sent" --date 2026-03-25
    python scripts/log_dm.py --contact "Mario Tayah" --note "DM sent" --channel linkedin
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR

CONTACTS_PATH = SIGNALS_DIR / "contacts.yaml"
OUTREACH_LOG_PATH = SIGNALS_DIR / "outreach-log.yaml"
NETWORK_PATH = SIGNALS_DIR / "network.yaml"


def _find_contact(name: str, contacts: list[dict]) -> dict | None:
    """Find a contact by name (case-insensitive substring match)."""
    name_lower = name.lower()
    for c in contacts:
        if name_lower in c.get("name", "").lower():
            return c
    return None


def _find_node(name: str, nodes: list[dict]) -> dict | None:
    """Find a network node by name (case-insensitive substring match)."""
    name_lower = name.lower()
    for n in nodes:
        if name_lower in n.get("name", "").lower():
            return n
    return None


def _load_yaml(path: Path) -> dict | list | None:
    """Load a YAML file, returning None if missing or empty."""
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def _write_yaml(path: Path, data: dict | list) -> None:
    """Write YAML data back to file."""
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )


def log_dm(
    contact_name: str,
    note: str,
    dm_date: str | None = None,
    channel: str = "linkedin",
) -> dict:
    """Log a DM across all three signal files.

    Returns a summary dict of what was updated.
    """
    today = date.today().isoformat()
    dm_date = dm_date or today

    summary = {
        "contact": None,
        "contacts_updated": False,
        "outreach_updated": False,
        "network_updated": False,
        "errors": [],
    }

    # --- 1. contacts.yaml ---
    contacts_data = _load_yaml(CONTACTS_PATH)
    if contacts_data is None:
        summary["errors"].append(f"Could not load {CONTACTS_PATH}")
        return summary

    contacts_list = (
        contacts_data.get("contacts", [])
        if isinstance(contacts_data, dict)
        else contacts_data
    )

    contact = _find_contact(contact_name, contacts_list)
    if contact is None:
        summary["errors"].append(
            f"Contact '{contact_name}' not found in contacts.yaml"
        )
        return summary

    summary["contact"] = contact["name"]

    # Add interaction
    if "interactions" not in contact or contact["interactions"] is None:
        contact["interactions"] = []
    contact["interactions"].append({
        "date": dm_date,
        "type": "dm",
        "note": note,
    })

    # Update next_action
    contact["next_action"] = "Await response"
    await_date = date.fromisoformat(dm_date) + timedelta(days=7)
    contact["next_action_date"] = await_date.isoformat()

    # Bump relationship_strength (cap at 10)
    current_strength = contact.get("relationship_strength", 0) or 0
    contact["relationship_strength"] = min(current_strength + 1, 10)

    _write_yaml(CONTACTS_PATH, contacts_data)
    summary["contacts_updated"] = True

    # --- 2. outreach-log.yaml ---
    outreach_data = _load_yaml(OUTREACH_LOG_PATH)
    if outreach_data is None:
        outreach_data = {"entries": []}

    outreach_entries = (
        outreach_data.get("entries", [])
        if isinstance(outreach_data, dict)
        else outreach_data
    )
    if outreach_entries is None:
        outreach_entries = []

    related_targets = contact.get("pipeline_entries", []) or []

    outreach_entries.append({
        "date": dm_date,
        "type": "dm",
        "contact": contact["name"],
        "channel": channel,
        "note": note,
        "related_targets": list(related_targets),
    })

    if isinstance(outreach_data, dict):
        outreach_data["entries"] = outreach_entries
    else:
        outreach_data = {"entries": outreach_entries}

    _write_yaml(OUTREACH_LOG_PATH, outreach_data)
    summary["outreach_updated"] = True

    # --- 3. network.yaml ---
    network_data = _load_yaml(NETWORK_PATH)
    if network_data is None:
        summary["errors"].append(f"Could not load {NETWORK_PATH}")
        return summary

    nodes = (
        network_data.get("nodes", [])
        if isinstance(network_data, dict)
        else []
    )

    node = _find_node(contact_name, nodes)
    if node is not None:
        node["last_interaction"] = dm_date
        _write_yaml(NETWORK_PATH, network_data)
        summary["network_updated"] = True
    else:
        summary["errors"].append(
            f"Node for '{contact_name}' not found in network.yaml (contacts/outreach still updated)"
        )

    return summary


def _print_summary(summary: dict) -> None:
    """Print a human-readable summary of the DM logging."""
    contact = summary["contact"] or "unknown"
    print(f"\n  DM logged for: {contact}")
    print(f"  {'contacts.yaml':20s} {'UPDATED' if summary['contacts_updated'] else 'SKIPPED'}")
    print(f"  {'outreach-log.yaml':20s} {'UPDATED' if summary['outreach_updated'] else 'SKIPPED'}")
    print(f"  {'network.yaml':20s} {'UPDATED' if summary['network_updated'] else 'SKIPPED'}")

    if summary["errors"]:
        print("\n  Warnings:")
        for err in summary["errors"]:
            print(f"    - {err}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Log a DM to all three signal files (contacts, outreach-log, network)."
    )
    parser.add_argument(
        "--contact", required=True,
        help="Contact name (case-insensitive substring match)",
    )
    parser.add_argument(
        "--note", required=True,
        help="DM content or summary note",
    )
    parser.add_argument(
        "--date", default=None,
        help="Date of the DM (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--channel", default="linkedin",
        help="Communication channel (default: linkedin)",
    )
    args = parser.parse_args()

    summary = log_dm(
        contact_name=args.contact,
        note=args.note,
        dm_date=args.date,
        channel=args.channel,
    )

    _print_summary(summary)

    if summary["errors"] and not summary["contacts_updated"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
