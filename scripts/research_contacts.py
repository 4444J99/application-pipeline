#!/usr/bin/env python3
"""Recruiter identification and outreach templating for submitted entries.

Generates structured research prompts for finding hiring contacts and
populates follow-up protocol dates relative to submission.

Usage:
    python scripts/research_contacts.py --target <id>     # Research contacts for one entry
    python scripts/research_contacts.py --batch            # All submitted entries without contacts
    python scripts/research_contacts.py --batch --limit 10 # Top 10 by tier
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_SUBMITTED,
    PIPELINE_DIR_CLOSED,
    load_entries,
    load_entry_by_id,
    parse_date,
    update_last_touched,
)

# Follow-up protocol timing (days after submission)
PROTOCOL_STEPS = [
    {"day": 1, "action": "Connect with hiring manager/recruiter on LinkedIn", "type": "connect"},
    {"day": 7, "action": "First follow-up DM or email referencing application", "type": "dm"},
    {"day": 14, "action": "Final follow-up or status check", "type": "check_in"},
]

# Tier priority for ordering
TIER_PRIORITY = {
    "job-tier-1": 1,
    "job-tier-2": 2,
    "job-tier-3": 3,
    "job-tier-4": 4,
}


def get_tier(entry: dict) -> int:
    """Get tier priority from tags."""
    tags = entry.get("tags", []) or []
    for tag in tags:
        if tag in TIER_PRIORITY:
            return TIER_PRIORITY[tag]
    return 5


def has_contacts(entry: dict) -> bool:
    """Check if an entry already has outreach contacts populated."""
    outreach = entry.get("outreach", [])
    if isinstance(outreach, list) and outreach:
        for o in outreach:
            if isinstance(o, dict) and o.get("contact"):
                return True
    return False


def generate_research_prompt(entry: dict) -> str:
    """Generate a structured research prompt for finding hiring contacts."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    target = entry.get("target", {})
    org = target.get("organization", "Unknown") if isinstance(target, dict) else "Unknown"
    url = target.get("url", "") if isinstance(target, dict) else ""

    lines = [
        f"CONTACT RESEARCH: {name}",
        f"Organization: {org}",
    ]
    if url:
        lines.append(f"Company page: {url}")
    lines.append("")
    lines.append("Search LinkedIn for these roles at this organization:")
    lines.append(f"  1. Hiring manager for \"{name}\"")
    lines.append(f"  2. Technical recruiter handling this role")
    lines.append(f"  3. Engineering/team lead for the relevant team")
    lines.append("")
    lines.append("For each contact found, record:")
    lines.append("  - Full name")
    lines.append("  - Title")
    lines.append("  - LinkedIn URL")
    lines.append("  - Any mutual connections")
    lines.append("")

    return "\n".join(lines)


def generate_outreach_template(entry: dict) -> list[dict]:
    """Generate outreach field entries for an entry."""
    outreach = []

    target = entry.get("target", {})
    org = target.get("organization", "Unknown") if isinstance(target, dict) else "Unknown"

    outreach.append({
        "type": "warm_contact",
        "channel": "linkedin",
        "contact": f"[Hiring Manager at {org}]",
        "status": "planned",
        "note": f"Research hiring manager for {entry.get('name', '?')}",
    })
    outreach.append({
        "type": "warm_contact",
        "channel": "linkedin",
        "contact": f"[Recruiter at {org}]",
        "status": "planned",
        "note": f"Connect with recruiter handling this role",
    })

    return outreach


def generate_followup_dates(entry: dict) -> list[dict]:
    """Generate follow-up protocol dates relative to submission date."""
    timeline = entry.get("timeline", {})
    sub_date = parse_date(timeline.get("submitted")) if isinstance(timeline, dict) else None
    if not sub_date:
        sub_date = date.today()

    follow_ups = []
    for step in PROTOCOL_STEPS:
        target_date = sub_date + timedelta(days=step["day"])
        follow_ups.append({
            "type": step["type"],
            "target_date": target_date.isoformat(),
            "action": step["action"],
            "status": "pending",
        })

    return follow_ups


def research_single(entry_id: str):
    """Generate research prompt and templates for a single entry."""
    filepath, entry = load_entry_by_id(entry_id)
    if not entry:
        print(f"Entry not found: {entry_id}", file=sys.stderr)
        sys.exit(1)

    name = entry.get("name", entry_id)
    print(f"{'=' * 60}")
    print(f"CONTACT RESEARCH: {name}")
    print(f"{'=' * 60}")
    print()

    # Research prompt
    prompt = generate_research_prompt(entry)
    print(prompt)

    # Outreach template
    print("OUTREACH TEMPLATE (add to YAML outreach field):")
    outreach = generate_outreach_template(entry)
    for o in outreach:
        print(f"  - type: {o['type']}")
        print(f"    channel: {o['channel']}")
        print(f"    contact: \"{o['contact']}\"")
        print(f"    status: {o['status']}")
        print(f"    note: \"{o['note']}\"")
        print()

    # Follow-up protocol
    print("FOLLOW-UP PROTOCOL:")
    follow_ups = generate_followup_dates(entry)
    for fu in follow_ups:
        print(f"  {fu['target_date']} — {fu['action']} [{fu['type']}]")
    print()


def research_batch(limit: int = 0):
    """Generate research prompts for all submitted entries without contacts."""
    entries = load_entries(
        dirs=[PIPELINE_DIR_SUBMITTED],
        include_filepath=True,
    )
    # Filter to submitted/acknowledged without contacts
    candidates = [
        e for e in entries
        if e.get("status") in ("submitted", "acknowledged")
        and not has_contacts(e)
    ]

    # Sort by tier
    candidates.sort(key=get_tier)

    if limit:
        candidates = candidates[:limit]

    if not candidates:
        print("No submitted entries need contact research.")
        return

    print(f"CONTACT RESEARCH BATCH — {len(candidates)} entries")
    print(f"{'=' * 60}")
    print()

    for entry in candidates:
        entry_id = entry.get("id", "?")
        name = entry.get("name", entry_id)
        tier = get_tier(entry)
        target = entry.get("target", {})
        org = target.get("organization", "Unknown") if isinstance(target, dict) else "Unknown"

        timeline = entry.get("timeline", {})
        sub_date = parse_date(timeline.get("submitted")) if isinstance(timeline, dict) else None
        days_ago = (date.today() - sub_date).days if sub_date else "?"

        print(f"  [{tier}] {name}")
        print(f"      Org: {org} | Submitted: {days_ago}d ago")

        # Show follow-up protocol dates
        follow_ups = generate_followup_dates(entry)
        for fu in follow_ups:
            target_date = parse_date(fu["target_date"])
            if target_date:
                is_past = target_date < date.today()
                marker = "OVERDUE" if is_past else "upcoming"
                print(f"      {fu['target_date']} — {fu['action']} [{marker}]")
        print()

    print(f"{'=' * 60}")
    print(f"Total: {len(candidates)} entries need contact research")
    print(f"\nUse --target <id> for detailed research prompt per entry")


def main():
    parser = argparse.ArgumentParser(
        description="Recruiter identification and outreach templating"
    )
    parser.add_argument("--target", metavar="ENTRY_ID",
                        help="Research contacts for a single entry")
    parser.add_argument("--batch", action="store_true",
                        help="All submitted entries without contacts")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit batch results")
    args = parser.parse_args()

    if args.target:
        research_single(args.target)
    elif args.batch:
        research_batch(limit=args.limit)
    else:
        # Default to batch
        research_batch()


if __name__ == "__main__":
    main()
