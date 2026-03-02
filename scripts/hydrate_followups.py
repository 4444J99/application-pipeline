#!/usr/bin/env python3
"""Batch-hydrate follow_up fields on submitted pipeline entries.

Smarter than `followup.py --init` — extracts contact/org data from entry
metadata and generates protocol-based follow-up schedules with overdue
detection.

Usage:
    python scripts/hydrate_followups.py              # Dry-run preview
    python scripts/hydrate_followups.py --yes        # Execute hydration
    python scripts/hydrate_followups.py --report     # Show unhydrated entry stats
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from followup import (
    PROTOCOL,
    get_follow_ups,
    get_submission_date,
)
from pipeline_lib import (
    PIPELINE_DIR_SUBMITTED,
    atomic_write,
    load_entries,
    update_last_touched,
)


def get_unhydrated_entries() -> list[dict]:
    """Load submitted/acknowledged entries that lack follow-up hydration.

    Filters to entries where follow_up is empty/null/missing AND
    conversion.follow_up_count is 0 or missing.
    """
    entries = load_entries(
        dirs=[PIPELINE_DIR_SUBMITTED],
        include_filepath=True,
    )
    unhydrated = []
    for entry in entries:
        if entry.get("status") not in ("submitted", "acknowledged"):
            continue
        # Check follow_up field: empty, null, or missing
        follow_ups = get_follow_ups(entry)
        if follow_ups:
            continue
        # Check conversion.follow_up_count: 0 or missing
        conversion = entry.get("conversion", {})
        if isinstance(conversion, dict):
            count = conversion.get("follow_up_count", 0) or 0
            if count > 0:
                continue
        unhydrated.append(entry)
    return unhydrated


def extract_contact_info(entry: dict) -> dict:
    """Pull organization, contact name, and portal from entry metadata.

    Returns dict with keys: organization, contact, portal.
    Contact checks hiring_contact first, then falls back to recruiter.
    """
    target = entry.get("target", {})
    if not isinstance(target, dict):
        target = {}
    org = target.get("organization", "")
    contact = target.get("hiring_contact", "") or target.get("recruiter", "")
    portal = target.get("portal", "")
    return {
        "organization": org or "",
        "contact": contact or "",
        "portal": portal or "",
    }


def generate_schedule(entry: dict) -> list[dict]:
    """Build a follow-up schedule based on submission date and PROTOCOL steps.

    For each PROTOCOL step, computes the due date range from submission_date
    + day_range and assigns status: overdue, pending, or upcoming.

    Returns empty list if no submission date is available.
    """
    sub_date = get_submission_date(entry)
    if not sub_date:
        return []

    today = date.today()
    schedule = []
    for step in PROTOCOL:
        low, high = step["day_range"]
        due_start = sub_date + timedelta(days=low)
        due_end = sub_date + timedelta(days=high)

        if today > due_end:
            status = "overdue"
        elif today >= due_start:
            status = "pending"
        else:
            status = "upcoming"

        schedule.append({
            "action": step["action"],
            "type": step["type"],
            "due_start": due_start.isoformat(),
            "due_end": due_end.isoformat(),
            "status": status,
        })
    return schedule


def hydrate_entry(entry: dict, dry_run: bool = True) -> dict | None:
    """Hydrate a single entry with follow-up schedule data.

    Extracts contact info, generates schedule, and optionally writes to
    the pipeline YAML file.

    Returns a summary dict, or None if the entry has no filepath or
    no submission date.
    """
    filepath = entry.get("_filepath")
    if not filepath or not Path(filepath).exists():
        return None

    contact_info = extract_contact_info(entry)
    schedule = generate_schedule(entry)
    if not schedule:
        return None

    overdue_count = sum(1 for item in schedule if item["status"] == "overdue")
    entry_id = entry.get("id", "unknown")

    summary = {
        "id": entry_id,
        "organization": contact_info["organization"],
        "contact": contact_info["contact"],
        "schedule_items": len(schedule),
        "overdue": overdue_count,
    }

    if dry_run:
        return summary

    # Build the follow_up YAML content from the schedule
    follow_up_items = []
    for item in schedule:
        follow_up_items.append({
            "action": item["action"],
            "type": item["type"],
            "due_start": item["due_start"],
            "due_end": item["due_end"],
            "status": item["status"],
        })

    # Read the file, update follow_up field, and write back
    filepath = Path(filepath)
    content = filepath.read_text()
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        return None

    data["follow_up"] = follow_up_items

    # Ensure conversion.follow_up_count exists
    if "conversion" not in data or not isinstance(data.get("conversion"), dict):
        data["conversion"] = {}
    if "follow_up_count" not in data["conversion"] or not data["conversion"]["follow_up_count"]:
        data["conversion"]["follow_up_count"] = 0

    # Dump updated data and preserve last_touched
    new_content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    new_content = update_last_touched(new_content)

    atomic_write(filepath, new_content)

    return summary


def run_hydrate(dry_run: bool = True) -> list[dict]:
    """Batch-hydrate all unhydrated entries.

    Returns list of summary dicts for each processed entry.
    """
    entries = get_unhydrated_entries()
    if not entries:
        print("All submitted entries are already hydrated.")
        return []

    summaries = []
    for entry in entries:
        result = hydrate_entry(entry, dry_run=dry_run)
        if result:
            summaries.append(result)

    total_items = sum(s["schedule_items"] for s in summaries)
    total_overdue = sum(s["overdue"] for s in summaries)
    mode = "Would hydrate" if dry_run else "Hydrated"

    print(f"\n{mode} {len(summaries)} entries — {total_items} schedule items, {total_overdue} overdue")

    if dry_run and summaries:
        print("Run with --yes to execute.")

    return summaries


def show_hydration_report(entries: list[dict]):
    """Print a formatted report of what would be or was hydrated."""
    if not entries:
        print("All submitted entries are hydrated — nothing to do.")
        return

    print(f"Hydration Report — {len(entries)} entries")
    print(f"{'=' * 70}")
    for entry in entries:
        entry_id = entry.get("id", "unknown")
        contact_info = extract_contact_info(entry)
        schedule = generate_schedule(entry)
        overdue_count = sum(1 for item in schedule if item["status"] == "overdue")

        org = contact_info["organization"] or "Unknown"
        contact = contact_info["contact"] or "—"
        portal = contact_info["portal"] or "—"

        status_tag = f" [OVERDUE x{overdue_count}]" if overdue_count else ""
        print(f"\n  {entry_id}{status_tag}")
        print(f"    Org: {org} | Contact: {contact} | Portal: {portal}")
        print(f"    Schedule: {len(schedule)} steps")

        sub_date = get_submission_date(entry)
        if sub_date:
            days = (date.today() - sub_date).days
            print(f"    Submitted: {sub_date.isoformat()} ({days}d ago)")

        for item in schedule:
            marker = ""
            if item["status"] == "overdue":
                marker = " ** OVERDUE"
            elif item["status"] == "pending":
                marker = " * DUE NOW"
            print(f"      [{item['type']}] {item['due_start']} to {item['due_end']}{marker}")

    print(f"\n{'=' * 70}")
    total_overdue = sum(
        sum(1 for item in generate_schedule(e) if item["status"] == "overdue")
        for e in entries
    )
    print(f"Total: {len(entries)} unhydrated | {total_overdue} overdue items")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-hydrate follow_up fields on submitted pipeline entries"
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Execute hydration (default is dry-run preview)"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Show unhydrated entry statistics"
    )
    args = parser.parse_args()

    if args.report:
        entries = get_unhydrated_entries()
        show_hydration_report(entries)
        return

    dry_run = not args.yes
    summaries = run_hydrate(dry_run=dry_run)

    if summaries:
        print()
        for s in summaries:
            overdue_tag = f" ({s['overdue']} overdue)" if s["overdue"] else ""
            print(f"  {s['id']:<50s} {s['organization']:<20s} {s['schedule_items']} steps{overdue_tag}")


if __name__ == "__main__":
    main()
