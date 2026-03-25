#!/usr/bin/env python3
"""Reconcile outreach — ingest LinkedIn DM history and backfill signal files.

Parses pasted LinkedIn message history, diffs against existing logged data,
and backfills outreach-log.yaml, contacts.yaml, and network.yaml in one pass.

Usage:
    python scripts/reconcile_outreach.py --file dm-history.txt
    python scripts/reconcile_outreach.py --file dm-history.txt --yes
    python scripts/reconcile_outreach.py --file dm-history.txt --json
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTACTS_PATH = SIGNALS_DIR / "contacts.yaml"
OUTREACH_LOG_PATH = SIGNALS_DIR / "outreach-log.yaml"
NETWORK_PATH = SIGNALS_DIR / "network.yaml"

# Date patterns in LinkedIn message history
DATE_PATTERNS = [
    r"(\d{1,2}:\d{2}\s*[AP]M)",  # "8:03 PM" — today
    r"(Mar\s+\d{1,2})",  # "Mar 23"
    r"(Feb\s+\d{1,2})",
    r"(Jan\s+\d{1,2})",
    r"(Dec\s+\d{1,2},\s*\d{4})",  # "Dec 27, 2025"
    r"(Oct\s+\d{1,2},\s*\d{4})",
    r"(TODAY)",
]

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


@dataclass
class ParsedDM:
    """A DM parsed from LinkedIn message history."""

    contact_name: str
    date_str: str
    date_iso: str
    message_text: str
    direction: str = "outbound"  # outbound | inbound
    is_response: bool = False


@dataclass
class ReconcileResult:
    """Result of reconciliation."""

    parsed: list[ParsedDM] = field(default_factory=list)
    already_logged: list[str] = field(default_factory=list)
    new_to_log: list[ParsedDM] = field(default_factory=list)
    contacts_updated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_date(date_str: str, reference_year: int = 2026) -> str:
    """Convert LinkedIn date format to ISO date."""
    date_str = date_str.strip()

    # "TODAY" or time-only (e.g., "8:03 PM") → today
    if date_str.upper() == "TODAY" or re.match(r"\d{1,2}:\d{2}", date_str):
        return str(date.today())

    # "Mar 23" → 2026-03-23
    m = re.match(r"(\w{3})\s+(\d{1,2})$", date_str)
    if m:
        month_str, day = m.group(1).lower(), int(m.group(2))
        month = MONTH_MAP.get(month_str, 1)
        return f"{reference_year}-{month:02d}-{day:02d}"

    # "Dec 27, 2025" → 2025-12-27
    m = re.match(r"(\w{3})\s+(\d{1,2}),\s*(\d{4})", date_str)
    if m:
        month_str, day, year = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        month = MONTH_MAP.get(month_str, 1)
        return f"{year}-{month:02d}-{day:02d}"

    return str(date.today())


def parse_linkedin_history(text: str) -> list[ParsedDM]:
    """Parse pasted LinkedIn DM history into structured records."""
    dms = []

    # Split into conversation blocks
    # Each block starts with a contact name followed by status/role info and a date
    # Pattern: "Name\n...role/status...\nDate\n...messages..."

    # Strategy: find "You:" messages and attribute them to the nearest contact header
    lines = text.split("\n")
    current_contact = None
    current_date_str = ""
    current_date_iso = ""
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines and boilerplate
        if not line or line.startswith("Open the options") or line.startswith("Sponsored"):
            i += 1
            continue

        # Detect date lines
        date_match = None
        for pattern in DATE_PATTERNS:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                date_match = m.group(1)
                break

        if date_match and not line.startswith("You:"):
            # Check if this is a standalone date line (like "Mar 23" or "8:07 PM")
            stripped = line.replace(date_match, "").strip()
            if len(stripped) < 5:  # It's primarily a date line
                current_date_str = date_match
                current_date_iso = _parse_date(date_match)
                i += 1
                continue

        # Detect "You:" messages (outbound DMs)
        if line.startswith("You:"):
            message = line[4:].strip()
            # Collect continuation lines
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line or next_line.startswith("You:") or next_line.startswith("Open the"):
                    break
                # Check if next line is a new contact header or date
                is_new_section = False
                for p in DATE_PATTERNS:
                    if re.search(p, next_line, re.IGNORECASE):
                        is_new_section = True
                        break
                if is_new_section:
                    break
                message += " " + next_line
                j += 1

            if current_contact and message:
                dms.append(ParsedDM(
                    contact_name=current_contact,
                    date_str=current_date_str,
                    date_iso=current_date_iso,
                    message_text=message.strip(),
                    direction="outbound",
                ))
            i = j
            continue

        # Detect inbound messages (contact name followed by ": message")
        if current_contact and ":" in line and not line.startswith("You"):
            parts = line.split(":", 1)
            sender = parts[0].strip()
            msg = parts[1].strip() if len(parts) > 1 else ""
            if sender.lower() in current_contact.lower() or current_contact.lower() in sender.lower():
                if msg:
                    dms.append(ParsedDM(
                        contact_name=current_contact,
                        date_str=current_date_str,
                        date_iso=current_date_iso,
                        message_text=msg,
                        direction="inbound",
                        is_response=True,
                    ))
                i += 1
                continue

        # Detect contact headers — a line that looks like a name
        # (capitalized words, no special prefixes, not a known boilerplate line)
        if re.match(r"^[A-Z\U0001f600-\U0001f64f]", line) and len(line) < 80:
            # Skip known boilerplate
            skip_patterns = [
                "Open the options", "Sponsored", "Status is", "InMail",
                "View Anthony", "Anthony James Padavano",
            ]
            if not any(sp.lower() in line.lower() for sp in skip_patterns):
                # Clean emoji and status indicators
                clean = re.sub(r"[\U0001f600-\U0001f64f\U0001f900-\U0001f9ff]", "", line).strip()
                clean = re.sub(r"Status is \w+", "", clean).strip()
                # Check if it looks like a name (2-4 words, starts with caps)
                words = clean.split()
                if 1 <= len(words) <= 5 and words[0][0].isupper():
                    # Avoid picking up role descriptions
                    role_indicators = [
                        "building", "helping", "head of", "senior", "staff",
                        "co-ceo", "hedge", "public figure", "songwriter",
                    ]
                    if not any(ri in clean.lower() for ri in role_indicators):
                        current_contact = clean
                        i += 1
                        continue

        i += 1

    return dms


def _load_yaml_safe(path: Path) -> dict | list:
    """Load YAML safely, handling both dict and list roots."""
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _get_outreach_entries(data) -> list:
    """Extract entries list from outreach-log data."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "entries" in data:
        return data["entries"]
    return []


def _get_contacts(data) -> list:
    """Extract contacts list."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "contacts" in data:
        return data["contacts"]
    return []


def _is_already_logged(dm: ParsedDM, existing_entries: list) -> bool:
    """Check if a DM is already in the outreach log."""
    for entry in existing_entries:
        contact = entry.get("contact", "")
        entry_date = str(entry.get("date", ""))
        entry_type = entry.get("type", "")

        if (contact.lower() == dm.contact_name.lower()
                and entry_date == dm.date_iso
                and entry_type in ("dm", "dm_sent")):
            return True
    return False


def _find_contact(name: str, contacts: list) -> dict | None:
    """Find a contact by name."""
    name_lower = name.lower()
    for c in contacts:
        if name_lower in c.get("name", "").lower():
            return c
    return None


def reconcile(
    parsed_dms: list[ParsedDM],
    dry_run: bool = True,
) -> ReconcileResult:
    """Diff parsed DMs against existing data and backfill gaps."""
    result = ReconcileResult(parsed=parsed_dms)

    # Load existing data
    outreach_data = _load_yaml_safe(OUTREACH_LOG_PATH)
    outreach_entries = _get_outreach_entries(outreach_data)
    contacts_data = _load_yaml_safe(CONTACTS_PATH)
    contacts_list = _get_contacts(contacts_data)
    network_data = _load_yaml_safe(NETWORK_PATH)

    new_outreach_entries = []
    contacts_to_update = {}  # name → list of interactions to add

    for dm in parsed_dms:
        if dm.direction != "outbound":
            # Log inbound responses separately
            continue

        if _is_already_logged(dm, outreach_entries):
            result.already_logged.append(f"{dm.contact_name} ({dm.date_iso})")
            continue

        result.new_to_log.append(dm)

        # Prepare outreach-log entry
        note_preview = dm.message_text[:100] + ("..." if len(dm.message_text) > 100 else "")
        new_outreach_entries.append({
            "date": dm.date_iso,
            "type": "dm",
            "contact": dm.contact_name,
            "channel": "linkedin",
            "note": f"DM sent (reconciled from LinkedIn history). {note_preview}",
            "related_targets": [],
        })

        # Prepare contacts.yaml update
        if dm.contact_name not in contacts_to_update:
            contacts_to_update[dm.contact_name] = []
        contacts_to_update[dm.contact_name].append({
            "date": dm.date_iso,
            "type": "dm",
            "note": f"DM sent. {note_preview}",
        })

    if dry_run:
        return result

    # Write outreach-log
    if new_outreach_entries:
        outreach_entries.extend(new_outreach_entries)
        if isinstance(outreach_data, dict) and "entries" in outreach_data:
            outreach_data["entries"] = outreach_entries
        else:
            outreach_data = outreach_entries
        OUTREACH_LOG_PATH.write_text(
            yaml.dump(outreach_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        )

    # Update contacts.yaml
    for name, interactions in contacts_to_update.items():
        contact = _find_contact(name, contacts_list)
        if contact:
            existing_interactions = contact.get("interactions", [])
            for interaction in interactions:
                # Check if already exists
                already = any(
                    i.get("date") == interaction["date"] and i.get("type") == "dm"
                    for i in existing_interactions
                )
                if not already:
                    existing_interactions.append(interaction)
                    result.contacts_updated.append(f"{name} ({interaction['date']})")
            contact["interactions"] = existing_interactions
            # Update next_action if it was "DM if accepted" or similar
            next_action = contact.get("next_action", "")
            if "DM" in next_action and "Await" not in next_action:
                contact["next_action"] = "Await response"
                contact["next_action_date"] = str(
                    date.fromisoformat(interactions[-1]["date"]).replace(day=min(
                        date.fromisoformat(interactions[-1]["date"]).day + 7, 28
                    ))
                )

    if contacts_to_update:
        if isinstance(contacts_data, dict):
            contacts_data["contacts"] = contacts_list
        else:
            contacts_data = contacts_list
        CONTACTS_PATH.write_text(
            yaml.dump(contacts_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        )

    # Update network.yaml last_interaction dates
    nodes = network_data.get("nodes", []) if isinstance(network_data, dict) else []
    if not nodes and isinstance(network_data, list):
        # network.yaml might be a flat list of nodes + edges
        # Find the nodes section
        nodes = [n for n in network_data if isinstance(n, dict) and "name" in n and "organization" in n]

    for name in contacts_to_update:
        for node in nodes:
            if node.get("name", "").lower() == name.lower():
                latest_date = max(i["date"] for i in contacts_to_update[name])
                current = node.get("last_interaction", "")
                if latest_date > current:
                    node["last_interaction"] = latest_date
                break

    if contacts_to_update and nodes:
        NETWORK_PATH.write_text(
            yaml.dump(network_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        )

    return result


def _format_report(result: ReconcileResult) -> str:
    """Format reconciliation report."""
    lines = [
        "=" * 60,
        "OUTREACH RECONCILIATION REPORT",
        "=" * 60,
        "",
        f"  Parsed DMs:      {len(result.parsed)}",
        f"  Outbound:        {sum(1 for d in result.parsed if d.direction == 'outbound')}",
        f"  Inbound:         {sum(1 for d in result.parsed if d.direction == 'inbound')}",
        f"  Already logged:  {len(result.already_logged)}",
        f"  NEW to backfill: {len(result.new_to_log)}",
        f"  Contacts updated:{len(result.contacts_updated)}",
        "",
    ]

    if result.new_to_log:
        lines.append("  NEW DMs to backfill:")
        lines.append("  " + "-" * 56)
        for dm in result.new_to_log:
            lines.append(f"  [{dm.date_iso}] {dm.contact_name}")
            lines.append(f"    {dm.message_text[:80]}...")
            lines.append("")

    if result.already_logged:
        lines.append(f"  Already logged ({len(result.already_logged)}):")
        for item in result.already_logged:
            lines.append(f"    {item}")
        lines.append("")

    if result.errors:
        lines.append(f"  Errors ({len(result.errors)}):")
        for e in result.errors:
            lines.append(f"    {e}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Reconcile LinkedIn DM history with pipeline signals")
    parser.add_argument("--file", required=True, help="Path to pasted LinkedIn DM history text file")
    parser.add_argument("--yes", action="store_true", help="Execute (write to signal files)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    history_path = Path(args.file)
    if not history_path.exists():
        print(f"File not found: {history_path}", file=sys.stderr)
        sys.exit(1)

    text = history_path.read_text()
    parsed = parse_linkedin_history(text)

    if not parsed:
        print("No DMs parsed from the input file.")
        sys.exit(0)

    result = reconcile(parsed, dry_run=not args.yes)

    mode = "EXECUTED" if args.yes else "DRY-RUN"
    print(f"\n  [{mode}]")

    if args.json:
        import json
        print(json.dumps({
            "parsed": len(result.parsed),
            "already_logged": result.already_logged,
            "new_to_log": [{"contact": d.contact_name, "date": d.date_iso} for d in result.new_to_log],
            "contacts_updated": result.contacts_updated,
        }, indent=2))
    else:
        print(_format_report(result))


if __name__ == "__main__":
    main()
