#!/usr/bin/env python3
"""Lightweight relationship CRM for the application pipeline.

Tracks contacts, interactions, and relationship strength across organizations.
Cross-references with pipeline entries to identify coverage gaps and suggest
network_proximity scores.

Storage: signals/contacts.yaml

Usage:
    python scripts/crm.py                      # Dashboard: contacts by org, overdue actions, strength distribution
    python scripts/crm.py --add --name "Jane Smith" --org "Anthropic" --role "EM" --channel linkedin
    python scripts/crm.py --log --name "Jane Smith" --type dm --note "Discussed Agent SDK role"
    python scripts/crm.py --due                # Contacts with overdue next_action_date
    python scripts/crm.py --org Anthropic      # All contacts at an org
    python scripts/crm.py --link --name "Jane Smith" --entry anthropic-se-claude-code
    python scripts/crm.py --stats              # Relationship strength distribution, interactions/week, orgs covered
"""

import argparse
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    SIGNALS_DIR,
    atomic_write,
    load_entries,
)

CONTACTS_FILE = SIGNALS_DIR / "contacts.yaml"

VALID_CHANNELS = {"linkedin", "email", "twitter", "referral", "event", "slack", "phone"}
VALID_INTERACTION_TYPES = {"connect", "dm", "email", "call", "meeting", "referral_ask", "intro", "coffee"}


# --- Data access ---


def load_contacts() -> list[dict]:
    """Load all contacts from signals/contacts.yaml."""
    if not CONTACTS_FILE.exists():
        return []
    with open(CONTACTS_FILE) as f:
        data = yaml.safe_load(f) or {}
    contacts = data.get("contacts", [])
    if not isinstance(contacts, list):
        return []
    return contacts


def save_contacts(contacts: list[dict]) -> None:
    """Save contacts list to signals/contacts.yaml atomically."""
    content = yaml.dump(
        {"contacts": contacts},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    atomic_write(CONTACTS_FILE, content)


def find_contact(contacts: list[dict], name: str) -> dict | None:
    """Find a contact by name (case-insensitive)."""
    name_lower = name.lower()
    for contact in contacts:
        if contact.get("name", "").lower() == name_lower:
            return contact
    return None


# --- Mutations ---


def add_contact(
    name: str,
    organization: str,
    role: str = "",
    channel: str = "linkedin",
    tags: list[str] | None = None,
) -> dict:
    """Add a new contact. Returns the created contact dict.

    Raises ValueError if the contact already exists or channel is invalid.
    """
    if channel not in VALID_CHANNELS:
        raise ValueError(f"Invalid channel '{channel}'. Valid: {', '.join(sorted(VALID_CHANNELS))}")

    contacts = load_contacts()
    if find_contact(contacts, name) is not None:
        raise ValueError(f"Contact '{name}' already exists. Use --log to add interactions.")

    contact = {
        "name": name,
        "organization": organization,
        "role": role,
        "channel": channel,
        "relationship_strength": 1,
        "interactions": [],
        "pipeline_entries": [],
        "tags": tags or [],
        "next_action": "",
        "next_action_date": "",
    }
    contacts.append(contact)
    save_contacts(contacts)
    return contact


def log_interaction(
    name: str,
    interaction_type: str = "dm",
    note: str = "",
    bump_strength: bool = True,
) -> dict:
    """Log an interaction for an existing contact. Returns the updated contact.

    Raises ValueError if contact not found or interaction type is invalid.
    """
    if interaction_type not in VALID_INTERACTION_TYPES:
        raise ValueError(
            f"Invalid interaction type '{interaction_type}'. "
            f"Valid: {', '.join(sorted(VALID_INTERACTION_TYPES))}"
        )

    contacts = load_contacts()
    contact = find_contact(contacts, name)
    if contact is None:
        raise ValueError(f"Contact '{name}' not found. Use --add to create first.")

    interaction = {
        "date": date.today().isoformat(),
        "type": interaction_type,
        "note": note,
    }
    if not isinstance(contact.get("interactions"), list):
        contact["interactions"] = []
    contact["interactions"].append(interaction)

    # Bump relationship strength on meaningful interactions (cap at 10)
    if bump_strength:
        current = contact.get("relationship_strength", 1)
        if isinstance(current, (int, float)):
            # Larger bumps for higher-signal interactions
            bump_map = {
                "meeting": 2,
                "call": 2,
                "referral_ask": 2,
                "intro": 2,
                "coffee": 2,
                "dm": 1,
                "email": 1,
                "connect": 1,
            }
            bump = bump_map.get(interaction_type, 1)
            contact["relationship_strength"] = min(10, current + bump)

    save_contacts(contacts)
    return contact


def link_entry(name: str, entry_id: str) -> dict:
    """Link a pipeline entry to a contact. Returns the updated contact.

    Raises ValueError if contact not found.
    """
    contacts = load_contacts()
    contact = find_contact(contacts, name)
    if contact is None:
        raise ValueError(f"Contact '{name}' not found.")

    if not isinstance(contact.get("pipeline_entries"), list):
        contact["pipeline_entries"] = []
    if entry_id not in contact["pipeline_entries"]:
        contact["pipeline_entries"].append(entry_id)

    save_contacts(contacts)
    return contact


def set_next_action(name: str, action: str, action_date: str = "") -> dict:
    """Set the next action and optional date for a contact.

    Raises ValueError if contact not found.
    """
    contacts = load_contacts()
    contact = find_contact(contacts, name)
    if contact is None:
        raise ValueError(f"Contact '{name}' not found.")

    contact["next_action"] = action
    contact["next_action_date"] = action_date

    save_contacts(contacts)
    return contact


# --- Analytics ---


def get_strength_distribution(contacts: list[dict]) -> dict[int, int]:
    """Return {strength_level: count} distribution."""
    dist: dict[int, int] = {}
    for c in contacts:
        strength = c.get("relationship_strength", 1)
        if not isinstance(strength, (int, float)):
            strength = 1
        strength = int(strength)
        dist[strength] = dist.get(strength, 0) + 1
    return dict(sorted(dist.items()))


def get_interactions_per_week(contacts: list[dict], weeks: int = 4) -> float:
    """Average interactions per week over the last N weeks."""
    cutoff = date.today() - timedelta(weeks=weeks)
    count = 0
    for c in contacts:
        for interaction in c.get("interactions", []) or []:
            d = interaction.get("date", "")
            if d and d >= cutoff.isoformat():
                count += 1
    return round(count / max(weeks, 1), 1) if weeks > 0 else 0.0


def get_orgs_covered(contacts: list[dict]) -> list[str]:
    """Return sorted list of unique organizations."""
    orgs = set()
    for c in contacts:
        org = c.get("organization", "")
        if org:
            orgs.add(org)
    return sorted(orgs)


def get_contacts_by_org(contacts: list[dict], org: str) -> list[dict]:
    """Filter contacts by organization (case-insensitive)."""
    org_lower = org.lower()
    return [c for c in contacts if c.get("organization", "").lower() == org_lower]


def get_overdue_contacts(contacts: list[dict]) -> list[dict]:
    """Return contacts with next_action_date before today."""
    today_str = date.today().isoformat()
    overdue = []
    for c in contacts:
        action_date = c.get("next_action_date", "")
        action = c.get("next_action", "")
        if action_date and action and action_date < today_str:
            overdue.append(c)
    return overdue


def suggest_network_proximity(contacts: list[dict], entry_id: str) -> int:
    """Suggest a network_proximity score based on contact data.

    Returns:
        8 — direct contact linked to entry (referral potential)
        5 — contact exists at same organization
        2 — no contacts at org
    """
    for c in contacts:
        linked = c.get("pipeline_entries", []) or []
        if entry_id in linked:
            return 8  # Direct contact linked

    # Look up entry organization
    entries = load_entries(include_filepath=False)
    entry_org = ""
    for e in entries:
        if e.get("id") == entry_id:
            target = e.get("target", {})
            if isinstance(target, dict):
                entry_org = target.get("organization", "")
            break

    if not entry_org:
        return 2

    # Check if we have any contacts at this org
    for c in contacts:
        if c.get("organization", "").lower() == entry_org.lower():
            return 5  # Shared org contact

    return 2  # No contacts


def get_uncovered_entries(contacts: list[dict]) -> list[dict]:
    """Find active pipeline entries with no contacts at their organization.

    Returns entries sorted by score descending.
    """
    contact_orgs = {c.get("organization", "").lower() for c in contacts if c.get("organization")}

    entries = load_entries(include_filepath=False)
    uncovered = []
    for entry in entries:
        status = entry.get("status", "")
        if status not in ("qualified", "drafting", "staged", "submitted", "acknowledged"):
            continue
        target = entry.get("target", {})
        if not isinstance(target, dict):
            continue
        org = target.get("organization", "")
        if org and org.lower() not in contact_orgs:
            uncovered.append(entry)

    # Sort by score descending
    uncovered.sort(key=lambda e: -(float(e.get("fit", {}).get("score", 0)) if isinstance(e.get("fit"), dict) else 0))
    return uncovered


def compute_stats(contacts: list[dict]) -> dict:
    """Compute summary statistics for the contact database."""
    return {
        "total_contacts": len(contacts),
        "orgs_covered": len(get_orgs_covered(contacts)),
        "strength_distribution": get_strength_distribution(contacts),
        "interactions_per_week": get_interactions_per_week(contacts),
        "overdue_actions": len(get_overdue_contacts(contacts)),
        "total_interactions": sum(
            len(c.get("interactions", []) or []) for c in contacts
        ),
    }


# --- Display ---


def show_dashboard(contacts: list[dict]) -> None:
    """Print the main CRM dashboard."""
    if not contacts:
        print("No contacts in CRM. Use --add to create your first contact.")
        return

    stats = compute_stats(contacts)

    print("Relationship CRM Dashboard")
    print("=" * 60)
    print(f"  Contacts: {stats['total_contacts']}")
    print(f"  Organizations: {stats['orgs_covered']}")
    print(f"  Total interactions: {stats['total_interactions']}")
    print(f"  Interactions/week (4wk avg): {stats['interactions_per_week']}")
    print()

    # Strength distribution
    print("Relationship Strength Distribution:")
    dist = stats["strength_distribution"]
    for level in range(1, 11):
        count = dist.get(level, 0)
        bar = "#" * count
        if count:
            print(f"  {level:2d}: {bar} ({count})")
    print()

    # Contacts by org
    print("Contacts by Organization:")
    org_counts: dict[str, int] = Counter()
    for c in contacts:
        org = c.get("organization", "Unknown")
        org_counts[org] += 1
    for org, count in sorted(org_counts.items(), key=lambda x: -x[1]):
        print(f"  {org:<35s} {count}")
    print()

    # Overdue actions
    overdue = get_overdue_contacts(contacts)
    if overdue:
        print(f"Overdue Actions ({len(overdue)}):")
        for c in overdue:
            print(f"  {c['name']:<25s} {c.get('next_action_date', '?'):<12s} {c.get('next_action', '')}")
        print()

    # Coverage gaps
    uncovered = get_uncovered_entries(contacts)
    if uncovered:
        print(f"Active Entries Without Contacts ({len(uncovered)}):")
        for entry in uncovered[:10]:
            entry_id = entry.get("id", "?")
            target = entry.get("target", {})
            org = target.get("organization", "?") if isinstance(target, dict) else "?"
            score = entry.get("fit", {}).get("score", "?") if isinstance(entry.get("fit"), dict) else "?"
            url = target.get("application_url", "") if isinstance(target, dict) else ""
            line = f"  {entry_id:<40s} {org:<25s} score={score}"
            if url:
                line += f"\n    {url}"
            print(line)
        if len(uncovered) > 10:
            print(f"  ... and {len(uncovered) - 10} more")
        print()

    print("=" * 60)


def show_org(contacts: list[dict], org: str) -> None:
    """Show all contacts at a specific organization."""
    filtered = get_contacts_by_org(contacts, org)
    if not filtered:
        print(f"No contacts found at '{org}'.")
        return

    print(f"Contacts at {org}")
    print("=" * 60)
    for c in filtered:
        strength = c.get("relationship_strength", 1)
        print(f"\n  {c['name']} — {c.get('role', '?')}")
        print(f"    Channel: {c.get('channel', '?')} | Strength: {strength}/10")

        linked = c.get("pipeline_entries", []) or []
        if linked:
            print(f"    Linked entries: {', '.join(linked)}")

        tags = c.get("tags", []) or []
        if tags:
            print(f"    Tags: {', '.join(tags)}")

        interactions = c.get("interactions", []) or []
        if interactions:
            print(f"    Interactions ({len(interactions)}):")
            for i in interactions[-5:]:  # Last 5
                print(f"      {i.get('date', '?')} [{i.get('type', '?')}] {i.get('note', '')}")
            if len(interactions) > 5:
                print(f"      ... and {len(interactions) - 5} earlier")

        action = c.get("next_action", "")
        if action:
            action_date = c.get("next_action_date", "")
            overdue = action_date and action_date < date.today().isoformat()
            marker = " [OVERDUE]" if overdue else ""
            print(f"    Next: {action} ({action_date}){marker}")

    print(f"\n{'=' * 60}")
    print(f"Total: {len(filtered)} contacts at {org}")


def show_due(contacts: list[dict]) -> None:
    """Show contacts with overdue next_action_date."""
    overdue = get_overdue_contacts(contacts)
    if not overdue:
        print("No overdue actions.")
        return

    print("Overdue Contact Actions")
    print("=" * 60)
    # Sort by date ascending (most overdue first)
    overdue.sort(key=lambda c: c.get("next_action_date", ""))
    for c in overdue:
        days_late = (date.today() - date.fromisoformat(c["next_action_date"])).days
        print(f"\n  {c['name']} ({c.get('organization', '?')})")
        print(f"    Due: {c['next_action_date']} ({days_late}d overdue)")
        print(f"    Action: {c.get('next_action', '?')}")
    print(f"\n{'=' * 60}")
    print(f"Total overdue: {len(overdue)}")


def show_stats(contacts: list[dict]) -> None:
    """Show relationship statistics."""
    stats = compute_stats(contacts)

    print("CRM Statistics")
    print("=" * 60)
    print(f"  Total contacts: {stats['total_contacts']}")
    print(f"  Organizations covered: {stats['orgs_covered']}")
    print(f"  Total interactions: {stats['total_interactions']}")
    print(f"  Interactions/week (4wk avg): {stats['interactions_per_week']}")
    print(f"  Overdue actions: {stats['overdue_actions']}")
    print()

    print("Strength Distribution:")
    dist = stats["strength_distribution"]
    for level in range(1, 11):
        count = dist.get(level, 0)
        bar = "#" * count
        if count:
            print(f"  {level:2d}: {bar} ({count})")
    print()

    print("Organizations:")
    for org in get_orgs_covered(contacts):
        count = len(get_contacts_by_org(contacts, org))
        print(f"  {org:<35s} {count} contact(s)")
    print(f"\n{'=' * 60}")


# --- CLI ---


def generate_crm_data(contacts: list[dict]) -> dict:
    """Generate structured CRM data for JSON output."""
    orgs = get_orgs_covered(contacts)
    overdue = get_overdue_contacts(contacts)
    strength_dist: dict[int, int] = {}
    for c in contacts:
        s = c.get("relationship_strength", 0)
        strength_dist[s] = strength_dist.get(s, 0) + 1
    by_org: dict[str, int] = {}
    for org in orgs:
        by_org[org] = len(get_contacts_by_org(contacts, org))
    return {
        "total_contacts": len(contacts),
        "organizations": len(orgs),
        "overdue_count": len(overdue),
        "overdue": [{"name": c.get("name"), "next_action_date": c.get("next_action_date")} for c in overdue],
        "strength_distribution": strength_dist,
        "by_org": by_org,
    }


def suggest_all_proximity(contacts: list[dict], entries: list[dict]) -> list[dict]:
    """Compute network_proximity suggestions for all entries based on contact depth."""
    suggestions = []
    for entry in entries:
        eid = entry.get("id", "")
        score = suggest_network_proximity(contacts, eid)
        current = (entry.get("fit", {}) or {}).get("dimensions", {}) or {}
        current_prox = current.get("network_proximity")
        if current_prox != score:
            suggestions.append({"id": eid, "current": current_prox, "suggested": score})
    return suggestions


def main():
    parser = argparse.ArgumentParser(
        description="Lightweight relationship CRM for the application pipeline"
    )

    # Modes
    parser.add_argument("--add", action="store_true", help="Add a new contact")
    parser.add_argument("--log", action="store_true", help="Log an interaction")
    parser.add_argument("--due", action="store_true", help="Show contacts with overdue actions")
    parser.add_argument("--org", metavar="ORG", help="Show all contacts at an organization")
    parser.add_argument("--link", action="store_true", help="Link a contact to a pipeline entry")
    parser.add_argument("--stats", action="store_true", help="Relationship statistics")
    parser.add_argument("--set-action", action="store_true", help="Set next action for a contact")
    parser.add_argument("--proximity", metavar="ENTRY_ID", help="Suggest network_proximity score for an entry")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of formatted text")
    parser.add_argument("--wire-proximity", action="store_true", help="Update entry YAML with suggested network_proximity")

    # Contact fields
    parser.add_argument("--name", metavar="NAME", help="Contact name")
    parser.add_argument("--role", default="", help="Contact role/title")
    parser.add_argument("--channel", default="linkedin", help="Channel: linkedin, email, twitter, referral, event, slack, phone")
    parser.add_argument("--tags", nargs="*", default=[], help="Contact tags")

    # Interaction fields
    parser.add_argument("--type", default="dm", dest="interaction_type",
                        help="Interaction type: connect, dm, email, call, meeting, referral_ask, intro, coffee")
    parser.add_argument("--note", default="", help="Interaction note")

    # Link fields
    parser.add_argument("--entry", metavar="ENTRY_ID", help="Pipeline entry ID to link")

    # Action fields
    parser.add_argument("--action", metavar="ACTION", help="Next action text")
    parser.add_argument("--action-date", metavar="DATE", default="", help="Next action date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.add:
        if not args.name:
            parser.error("--name is required when adding a contact")
        if not args.org:
            parser.error("--org is required when adding a contact")
        try:
            contact = add_contact(
                name=args.name,
                organization=args.org,
                role=args.role,
                channel=args.channel,
                tags=args.tags,
            )
            print(f"Added contact: {contact['name']} at {contact['organization']}")
            print(f"  Role: {contact['role'] or '(none)'}")
            print(f"  Channel: {contact['channel']}")
            if contact["tags"]:
                print(f"  Tags: {', '.join(contact['tags'])}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.log:
        if not args.name:
            parser.error("--name is required when logging an interaction")
        if not args.note:
            parser.error("--note is required when logging an interaction")
        try:
            contact = log_interaction(
                name=args.name,
                interaction_type=args.interaction_type,
                note=args.note,
            )
            print(f"Logged interaction for {contact['name']}:")
            print(f"  Type: {args.interaction_type}")
            print(f"  Note: {args.note}")
            print(f"  Strength: {contact['relationship_strength']}/10")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.link:
        if not args.name:
            parser.error("--name is required when linking")
        if not args.entry:
            parser.error("--entry is required when linking")
        try:
            contact = link_entry(name=args.name, entry_id=args.entry)
            print(f"Linked {args.entry} to {contact['name']}")
            print(f"  Entries: {', '.join(contact['pipeline_entries'])}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.set_action:
        if not args.name:
            parser.error("--name is required when setting an action")
        if not args.action:
            parser.error("--action is required when setting an action")
        try:
            contact = set_next_action(
                name=args.name,
                action=args.action,
                action_date=args.action_date,
            )
            print(f"Set next action for {contact['name']}:")
            print(f"  Action: {contact['next_action']}")
            if contact["next_action_date"]:
                print(f"  Date: {contact['next_action_date']}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.proximity:
        contacts = load_contacts()
        score = suggest_network_proximity(contacts, args.proximity)
        labels = {8: "direct contact (referral potential)", 5: "shared org contact", 2: "no contacts at org"}
        print(f"Suggested network_proximity for {args.proximity}: {score}")
        print(f"  Basis: {labels.get(score, 'unknown')}")
        return

    contacts = load_contacts()

    if args.json:
        import json
        data = generate_crm_data(contacts)
        print(json.dumps(data, indent=2, default=str))
        return

    if args.wire_proximity:
        from pipeline_lib import load_entries, load_entry_by_id, update_yaml_field
        entries = load_entries()
        suggestions = suggest_all_proximity(contacts, entries)
        if not suggestions:
            print("All entries already have matching network_proximity scores.")
            return
        for s in suggestions:
            path, entry = load_entry_by_id(s["id"])
            if path:
                content = path.read_text()
                content = update_yaml_field(content, "network_proximity", str(s["suggested"]),
                                            nested=True, parent_key="dimensions")
                path.write_text(content)
                print(f"  {s['id']}: {s['current']} → {s['suggested']}")
        print(f"\nUpdated {len(suggestions)} entries.")
        return

    if args.due:
        show_due(contacts)
    elif args.org:
        show_org(contacts, args.org)
    elif args.stats:
        show_stats(contacts)
    else:
        show_dashboard(contacts)


if __name__ == "__main__":
    main()
