#!/usr/bin/env python3
"""Batch-advance pipeline entries through status stages.

Addresses the qualified → drafting logjam by enabling batch progression
with validation, dry-run preview, and an advancement report.

Usage:
    python scripts/advance.py --report
    python scripts/advance.py --dry-run --to drafting --effort quick
    python scripts/advance.py --to drafting --effort quick --yes
    python scripts/advance.py --to staged --id pen-america
"""

import argparse
import re
import sys
from datetime import date

from pipeline_lib import (
    load_entries, load_entry_by_id, load_profile,
    get_effort, get_score, get_deadline, days_until,
    ACTIONABLE_STATUSES, PROFILES_DIR,
)

# Valid transitions: from validate.py
VALID_TRANSITIONS = {
    "research": {"qualified", "withdrawn"},
    "qualified": {"drafting", "staged", "withdrawn"},
    "drafting": {"staged", "qualified", "withdrawn"},
    "staged": {"submitted", "drafting", "withdrawn"},
    "submitted": {"acknowledged", "interview", "outcome", "withdrawn"},
    "acknowledged": {"interview", "outcome", "withdrawn"},
    "interview": {"outcome", "withdrawn"},
    "outcome": set(),
}

# Map target status to timeline field to set
STATUS_TIMELINE_FIELD = {
    "qualified": "qualified",
    "drafting": None,  # no timeline field for drafting
    "staged": "materials_ready",
    "submitted": "submitted",
    "acknowledged": "acknowledged",
    "interview": "interview",
    "outcome": "outcome_date",
}


def can_advance(current_status: str, target_status: str) -> bool:
    """Check if a transition is valid."""
    return target_status in VALID_TRANSITIONS.get(current_status, set())


def advance_entry(filepath, entry_id: str, target_status: str) -> bool:
    """Advance a single entry to target_status by updating the YAML file.

    Returns True if successful.
    """
    content = filepath.read_text()
    today_str = date.today().isoformat()

    # Update status
    content = re.sub(
        r'^(status:\s+).*$',
        rf'\1{target_status}',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Update last_touched
    if re.search(r'^last_touched:', content, re.MULTILINE):
        content = re.sub(
            r'^(last_touched:\s+).*$',
            rf'\1"{today_str}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        content = content.rstrip() + f'\nlast_touched: "{today_str}"\n'

    # Update timeline field if applicable
    tl_field = STATUS_TIMELINE_FIELD.get(target_status)
    if tl_field:
        pattern = rf'^(\s+{tl_field}:\s+).*$'
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(
                pattern,
                rf"\1'{today_str}'",
                content,
                count=1,
                flags=re.MULTILINE,
            )

    filepath.write_text(content)
    return True


def run_report(entries: list[dict]):
    """Show advancement opportunities and blockers."""
    print("ADVANCEMENT REPORT")
    print("=" * 70)
    print()

    ready = []
    blocked = []

    for e in entries:
        status = e.get("status", "")
        if status not in ACTIONABLE_STATUSES:
            continue

        entry_id = e.get("id", "?")
        name = e.get("name", entry_id)
        score = get_score(e)
        effort = get_effort(e)
        dl_date, dl_type = get_deadline(e)

        # Determine next natural status
        next_status = None
        if status == "research":
            next_status = "qualified"
        elif status == "qualified":
            next_status = "drafting"
        elif status == "drafting":
            next_status = "staged"
        elif status == "staged":
            next_status = "submitted"

        if not next_status:
            continue

        dl_str = ""
        if dl_date:
            d = days_until(dl_date)
            if d < 0:
                dl_str = f"EXPIRED {abs(d)}d ago"
            else:
                dl_str = f"{d}d left"
        elif dl_type in ("rolling", "tba"):
            dl_str = dl_type

        has_profile = load_profile(entry_id) is not None

        # Determine readiness
        blockers = []
        if status == "qualified" and not has_profile:
            blockers.append("no profile")
        if dl_date and days_until(dl_date) < 0:
            blockers.append("expired deadline")

        item = {
            "id": entry_id,
            "name": name,
            "status": status,
            "next": next_status,
            "effort": effort,
            "score": score,
            "dl_str": dl_str,
            "has_profile": has_profile,
            "blockers": blockers,
        }

        if blockers:
            blocked.append(item)
        else:
            ready.append(item)

    # Sort ready by score descending
    ready.sort(key=lambda x: -x["score"])

    if ready:
        print(f"READY TO ADVANCE ({len(ready)}):")
        for item in ready:
            profile_str = "yes" if item["has_profile"] else "no"
            print(f"  {item['name']}")
            print(f"    {item['status']} -> {item['next']} | "
                  f"{item['effort']} | score {item['score']:.1f} | "
                  f"{item['dl_str']} | profile: {profile_str}")
        print()

    if blocked:
        print(f"BLOCKED ({len(blocked)}):")
        for item in blocked:
            print(f"  {item['name']}")
            print(f"    {item['status']} | {', '.join(item['blockers'])}")
        print()

    if not ready and not blocked:
        print("No actionable entries to advance.")
        print()

    # Summary
    total_actionable = len(ready) + len(blocked)
    print(f"Summary: {len(ready)} ready, {len(blocked)} blocked, "
          f"{total_actionable} total actionable")


def run_advance(
    target_status: str,
    effort_filter: str | None,
    status_filter: str | None,
    entry_id: str | None,
    dry_run: bool,
    auto_yes: bool,
):
    """Advance entries matching filters to target_status."""
    entries = load_entries(include_filepath=True)

    candidates = []
    for e in entries:
        current = e.get("status", "")
        eid = e.get("id", "?")

        # Filter by specific ID
        if entry_id and eid != entry_id:
            continue

        # Filter by current status
        if status_filter and current != status_filter:
            continue

        # Must be a valid transition
        if not can_advance(current, target_status):
            continue

        # Filter by effort
        if effort_filter and get_effort(e) != effort_filter:
            continue

        # Must be actionable
        if current not in ACTIONABLE_STATUSES:
            continue

        candidates.append(e)

    if not candidates:
        print("No entries match the specified filters for advancement.")
        return

    print(f"{'DRY RUN: ' if dry_run else ''}Advancing {len(candidates)} entries → {target_status}")
    print(f"{'─' * 60}")

    for e in candidates:
        eid = e.get("id", "?")
        name = e.get("name", eid)
        current = e.get("status", "?")
        filepath = e.get("_filepath")

        print(f"  {name}: {current} → {target_status}")

    if dry_run:
        print(f"{'─' * 60}")
        print(f"Dry run complete. {len(candidates)} entries would be advanced.")
        return

    # Confirmation
    if not auto_yes:
        print(f"{'─' * 60}")
        try:
            confirm = input(f"Proceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if confirm != "y":
            print("Aborted.")
            return

    # Execute
    advanced = 0
    for e in candidates:
        eid = e.get("id", "?")
        filepath = e.get("_filepath")
        if filepath:
            advance_entry(filepath, eid, target_status)
            advanced += 1

    print(f"{'─' * 60}")
    print(f"Advanced {advanced} entries to '{target_status}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-advance pipeline entries through status stages"
    )
    parser.add_argument("--to", dest="target_status",
                        help="Target status to advance entries to")
    parser.add_argument("--effort", choices=["quick", "standard", "deep", "complex"],
                        help="Filter by effort level")
    parser.add_argument("--status",
                        help="Filter by current status (default: infer from --to)")
    parser.add_argument("--id", dest="entry_id",
                        help="Advance a specific entry by ID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying files")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompt")
    parser.add_argument("--report", action="store_true",
                        help="Show advancement opportunities and blockers")
    args = parser.parse_args()

    if args.report:
        entries = load_entries()
        run_report(entries)
        return

    if not args.target_status:
        parser.error("Specify --to <status> or --report")

    run_advance(
        target_status=args.target_status,
        effort_filter=args.effort,
        status_filter=args.status,
        entry_id=args.entry_id,
        dry_run=args.dry_run,
        auto_yes=args.yes,
    )


if __name__ == "__main__":
    main()
