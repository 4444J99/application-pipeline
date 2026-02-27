#!/usr/bin/env python3
"""Follow-up tracker and daily outreach list generator.

Tracks follow-up dates per submitted entry, generates daily action lists,
and logs outreach activity to signals/outreach-log.yaml.

Usage:
    python scripts/followup.py                     # Show today's follow-up actions
    python scripts/followup.py --all               # Show all submitted entries with follow-up status
    python scripts/followup.py --log <id> --channel linkedin --contact "Name" --note "DM sent"
    python scripts/followup.py --schedule           # Show upcoming follow-up schedule
    python scripts/followup.py --overdue            # Show overdue follow-ups only
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
    SIGNALS_DIR,
    load_entries,
    parse_date,
    days_until,
    update_last_touched,
)

# Follow-up protocol timing (days after submission)
PROTOCOL = [
    {"day_range": (1, 2), "action": "Connect with hiring manager/recruiter on LinkedIn", "type": "connect"},
    {"day_range": (7, 10), "action": "First follow-up: short DM or email referencing application", "type": "dm"},
    {"day_range": (14, 21), "action": "Second and final follow-up", "type": "check_in"},
]

# Tier priority for follow-up ordering
TIER_PRIORITY = {
    "job-tier-1": 1,
    "job-tier-2": 2,
    "job-tier-3": 3,
    "job-tier-4": 4,
}

OUTREACH_LOG = SIGNALS_DIR / "outreach-log.yaml"


def get_submitted_entries() -> list[dict]:
    """Load all submitted/acknowledged entries with follow-up context.

    Searches both submitted/ and closed/ directories to find all entries
    that have been submitted, including those that may have been moved.
    """
    entries = load_entries(
        dirs=[PIPELINE_DIR_SUBMITTED, PIPELINE_DIR_CLOSED],
        include_filepath=True,
    )
    return [e for e in entries if e.get("status") in ("submitted", "acknowledged")]


def get_submission_date(entry: dict) -> date | None:
    """Extract submission date from timeline."""
    timeline = entry.get("timeline", {})
    if isinstance(timeline, dict):
        return parse_date(timeline.get("submitted"))
    return None


def get_follow_ups(entry: dict) -> list[dict]:
    """Get existing follow-up actions for an entry."""
    return entry.get("follow_up", []) or []


def get_tier(entry: dict) -> int:
    """Get tier priority from tags (lower = higher priority)."""
    tags = entry.get("tags", []) or []
    for tag in tags:
        if tag in TIER_PRIORITY:
            return TIER_PRIORITY[tag]
    return 5  # default: untiered


def days_since_submission(entry: dict) -> int | None:
    """Calculate days since submission."""
    sub_date = get_submission_date(entry)
    if not sub_date:
        return None
    return (date.today() - sub_date).days


def get_due_actions(entry: dict) -> list[dict]:
    """Determine which follow-up actions are due for an entry."""
    days = days_since_submission(entry)
    if days is None:
        return []

    existing = get_follow_ups(entry)
    existing_types = {fu.get("type") for fu in existing}

    due = []
    for step in PROTOCOL:
        low, high = step["day_range"]
        if low <= days <= high and step["type"] not in existing_types:
            due.append({
                "action": step["action"],
                "type": step["type"],
                "day": days,
                "window": f"Day {low}-{high}",
            })
        elif days > high and step["type"] not in existing_types:
            due.append({
                "action": f"OVERDUE: {step['action']}",
                "type": step["type"],
                "day": days,
                "window": f"Day {low}-{high} (now Day {days})",
            })

    return due


def get_upcoming_actions(entry: dict) -> list[dict]:
    """Determine future follow-up actions not yet due."""
    days = days_since_submission(entry)
    if days is None:
        return []

    existing = get_follow_ups(entry)
    existing_types = {fu.get("type") for fu in existing}

    upcoming = []
    for step in PROTOCOL:
        low, high = step["day_range"]
        if days < low and step["type"] not in existing_types:
            upcoming.append({
                "action": step["action"],
                "type": step["type"],
                "due_in": low - days,
                "window": f"Day {low}-{high}",
            })

    return upcoming


def log_followup(entry_id: str, channel: str, contact: str, note: str, followup_type: str = "dm"):
    """Log a follow-up action to both the entry YAML and outreach log."""
    # Find the entry file
    filepath = PIPELINE_DIR_SUBMITTED / f"{entry_id}.yaml"
    if not filepath.exists():
        print(f"Entry not found: {entry_id}", file=sys.stderr)
        sys.exit(1)

    with open(filepath) as f:
        content = f.read()
    data = yaml.safe_load(content)

    # Add follow-up to entry
    if "follow_up" not in data or data["follow_up"] is None:
        data["follow_up"] = []

    today = date.today().isoformat()
    followup_entry = {
        "date": today,
        "channel": channel,
        "contact": contact,
        "type": followup_type,
        "note": note,
        "response": "none",
    }
    data["follow_up"].append(followup_entry)

    # Update conversion follow_up_count
    conversion = data.get("conversion", {})
    if isinstance(conversion, dict):
        count = conversion.get("follow_up_count", 0) or 0
        conversion["follow_up_count"] = count + 1
        data["conversion"] = conversion

    # Write back
    with open(filepath, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Update last_touched
    with open(filepath) as f:
        raw = f.read()
    raw = update_last_touched(raw)
    with open(filepath, "w") as f:
        f.write(raw)

    # Also log to outreach-log.yaml
    _append_outreach_log(entry_id, channel, contact, note, followup_type)

    print(f"Logged follow-up for {entry_id}:")
    print(f"  Channel: {channel}")
    print(f"  Contact: {contact}")
    print(f"  Type: {followup_type}")
    print(f"  Note: {note}")


def _append_outreach_log(entry_id: str, channel: str, contact: str, note: str, followup_type: str):
    """Append an entry to the outreach log."""
    with open(OUTREACH_LOG) as f:
        log_data = yaml.safe_load(f) or {}

    entries = log_data.get("entries", []) or []
    entries.append({
        "date": date.today().isoformat(),
        "type": "post_submission",
        "contact": contact,
        "channel": channel,
        "note": note,
        "related_targets": [entry_id],
    })
    log_data["entries"] = entries

    with open(OUTREACH_LOG, "w") as f:
        yaml.dump(log_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def init_follow_ups(dry_run: bool = True) -> int:
    """Add follow_up: [] and conversion.follow_up_count: 0 to submitted entries missing them.

    Returns number of entries updated.
    """
    entries = load_entries(
        dirs=[PIPELINE_DIR_SUBMITTED, PIPELINE_DIR_CLOSED],
        include_filepath=True,
    )
    submitted = [e for e in entries if e.get("status") in ("submitted", "acknowledged")]

    updated = 0
    for entry in submitted:
        filepath = entry.get("_filepath")
        if not filepath or not filepath.exists():
            continue

        needs_update = False
        content = filepath.read_text()
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            continue

        # Check if follow_up field is missing or null
        has_follow_up = "follow_up" in data and data["follow_up"] is not None
        # Check if conversion.follow_up_count is missing
        conversion = data.get("conversion", {})
        has_count = (isinstance(conversion, dict)
                     and "follow_up_count" in conversion
                     and conversion["follow_up_count"] is not None)

        if has_follow_up and has_count:
            continue

        entry_id = entry.get("id", "?")

        if dry_run:
            missing = []
            if not has_follow_up:
                missing.append("follow_up")
            if not has_count:
                missing.append("conversion.follow_up_count")
            print(f"  [dry-run] {entry_id} — would add: {', '.join(missing)}")
            updated += 1
            continue

        # Add follow_up field if missing
        if not has_follow_up:
            if "follow_up:" not in content:
                # Insert before tags or at end
                content = content.rstrip() + "\nfollow_up: []\n"
            else:
                # Field exists but is null — update to empty list
                import re
                content = re.sub(
                    r'^(follow_up:)\s*(?:null|~)?\s*$',
                    r'\1 []',
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )

        # Add conversion.follow_up_count if missing
        if not has_count:
            import re
            if "follow_up_count:" not in content:
                # Insert after other conversion fields
                conversion_match = re.search(r'^conversion:\s*$', content, re.MULTILINE)
                if conversion_match:
                    # Find the end of the conversion block
                    pos = conversion_match.end()
                    # Find next top-level key
                    next_key = re.search(r'^\S', content[pos:], re.MULTILINE)
                    if next_key:
                        insert_pos = pos + next_key.start()
                        content = (content[:insert_pos]
                                   + "  follow_up_count: 0\n"
                                   + content[insert_pos:])

        filepath.write_text(content)
        print(f"  {entry_id} — initialized follow-up fields")
        updated += 1

    return updated


def show_today(entries: list[dict]):
    """Show today's follow-up actions."""
    today = date.today()
    actions = []

    for entry in entries:
        entry_id = entry.get("id", "unknown")
        org = entry.get("target", {}).get("organization", "Unknown") if isinstance(entry.get("target"), dict) else "Unknown"
        tier = get_tier(entry)
        due = get_due_actions(entry)
        days = days_since_submission(entry)

        if due:
            for action in due:
                actions.append({
                    "entry_id": entry_id,
                    "org": org,
                    "tier": tier,
                    "days": days,
                    **action,
                })

    if not actions:
        print(f"No follow-up actions due today ({today.isoformat()}).")
        # Show upcoming
        upcoming_all = []
        for entry in entries:
            entry_id = entry.get("id", "unknown")
            upcoming = get_upcoming_actions(entry)
            for u in upcoming:
                upcoming_all.append({"entry_id": entry_id, **u})

        if upcoming_all:
            upcoming_all.sort(key=lambda x: x["due_in"])
            print(f"\nNext upcoming actions:")
            for u in upcoming_all[:5]:
                print(f"  {u['entry_id']:<50s} in {u['due_in']}d  {u['action']}")
        return

    # Sort by tier (priority), then by overdue status
    actions.sort(key=lambda x: (x["tier"], -x["day"]))

    print(f"Follow-up Actions Due — {today.isoformat()}")
    print(f"{'=' * 70}")
    for a in actions:
        overdue = "OVERDUE " if "OVERDUE" in a["action"] else ""
        print(f"\n  [{overdue}Day {a['days']}] {a['org']} — {a['entry_id']}")
        print(f"    Action: {a['action']}")
        print(f"    Window: {a['window']}")
    print(f"\n{'=' * 70}")
    print(f"Total: {len(actions)} actions due")


def show_all(entries: list[dict]):
    """Show all submitted entries with follow-up status."""
    print(f"Follow-Up Status — All Submitted Entries")
    print(f"{'=' * 80}")

    entries_sorted = sorted(entries, key=lambda e: (get_tier(e), -(days_since_submission(e) or 0)))

    for entry in entries_sorted:
        entry_id = entry.get("id", "unknown")
        org = entry.get("target", {}).get("organization", "Unknown") if isinstance(entry.get("target"), dict) else "Unknown"
        days = days_since_submission(entry)
        tier = get_tier(entry)
        existing = get_follow_ups(entry)
        due = get_due_actions(entry)
        upcoming = get_upcoming_actions(entry)

        status_marker = ""
        if due:
            overdue = any("OVERDUE" in d["action"] for d in due)
            status_marker = " [OVERDUE]" if overdue else " [DUE]"
        elif not upcoming:
            status_marker = " [DONE]"

        print(f"\n  {entry_id}{status_marker}")
        print(f"    Org: {org} | Day {days} | Tier {tier}")

        if existing:
            print(f"    Completed ({len(existing)}):")
            for fu in existing:
                print(f"      {fu.get('date', '?')} — {fu.get('type', '?')} via {fu.get('channel', '?')}: {fu.get('note', '')}")

        if due:
            print(f"    Due now ({len(due)}):")
            for d in due:
                print(f"      {d['action']} ({d['window']})")

        if upcoming:
            print(f"    Upcoming ({len(upcoming)}):")
            for u in upcoming:
                print(f"      in {u['due_in']}d — {u['action']}")

    print(f"\n{'=' * 80}")
    print(f"Total entries: {len(entries)}")
    total_done = sum(len(get_follow_ups(e)) for e in entries)
    total_due = sum(len(get_due_actions(e)) for e in entries)
    print(f"Follow-ups completed: {total_done} | Due now: {total_due}")


def show_schedule(entries: list[dict]):
    """Show upcoming follow-up schedule for next 21 days."""
    print(f"Follow-Up Schedule — Next 21 Days")
    print(f"{'=' * 70}")

    today = date.today()
    for day_offset in range(22):
        target_date = today + timedelta(days=day_offset)
        day_actions = []

        for entry in entries:
            sub_date = get_submission_date(entry)
            if not sub_date:
                continue
            days_since = (target_date - sub_date).days
            existing_types = {fu.get("type") for fu in get_follow_ups(entry)}

            for step in PROTOCOL:
                low, high = step["day_range"]
                if low == days_since and step["type"] not in existing_types:
                    day_actions.append({
                        "entry_id": entry.get("id", "unknown"),
                        "action": step["action"],
                        "type": step["type"],
                    })

        if day_actions:
            day_label = "TODAY" if day_offset == 0 else f"+{day_offset}d"
            print(f"\n  {target_date.isoformat()} ({day_label}):")
            for a in day_actions:
                print(f"    {a['entry_id']:<45s} {a['action']}")

    print(f"\n{'=' * 70}")


def show_overdue(entries: list[dict]):
    """Show only overdue follow-ups."""
    overdue = []
    for entry in entries:
        entry_id = entry.get("id", "unknown")
        for action in get_due_actions(entry):
            if "OVERDUE" in action["action"]:
                overdue.append({"entry_id": entry_id, **action})

    if not overdue:
        print("No overdue follow-ups.")
        return

    print(f"Overdue Follow-Ups")
    print(f"{'=' * 70}")
    overdue.sort(key=lambda x: -x["day"])
    for o in overdue:
        print(f"  {o['entry_id']:<45s} Day {o['day']}  {o['action']}")
    print(f"\n{'=' * 70}")
    print(f"Total overdue: {len(overdue)}")


def main():
    parser = argparse.ArgumentParser(description="Follow-up tracker and daily outreach list")
    parser.add_argument("--all", action="store_true", help="Show all submitted entries with follow-up status")
    parser.add_argument("--schedule", action="store_true", help="Show upcoming follow-up schedule")
    parser.add_argument("--overdue", action="store_true", help="Show overdue follow-ups only")
    parser.add_argument("--init", action="store_true",
                        help="Initialize follow_up fields on submitted entries missing them")
    parser.add_argument("--log", metavar="ENTRY_ID", help="Log a follow-up action for an entry")
    parser.add_argument("--channel", default="linkedin", help="Follow-up channel (default: linkedin)")
    parser.add_argument("--contact", default="", help="Contact name")
    parser.add_argument("--note", default="", help="Follow-up note")
    parser.add_argument("--type", default="dm", dest="followup_type",
                        help="Follow-up type: connect, dm, email, check_in, thank_you")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--yes", action="store_true", help="Execute changes")
    args = parser.parse_args()

    if args.init:
        dry_run = not args.yes or args.dry_run
        print(f"Initializing follow-up fields on submitted entries...")
        count = init_follow_ups(dry_run=dry_run)
        print(f"\n{'Would update' if dry_run else 'Updated'} {count} entries")
        if dry_run and count:
            print("Run with --init --yes to execute.")
        return

    if args.log:
        if not args.note:
            parser.error("--note is required when logging a follow-up")
        log_followup(args.log, args.channel, args.contact, args.note, args.followup_type)
        return

    entries = get_submitted_entries()
    if not entries:
        print("No submitted entries found.")
        return

    if args.all:
        show_all(entries)
    elif args.schedule:
        show_schedule(entries)
    elif args.overdue:
        show_overdue(entries)
    else:
        show_today(entries)


if __name__ == "__main__":
    main()
