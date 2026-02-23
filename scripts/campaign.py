#!/usr/bin/env python3
"""Deadline-aware campaign orchestrator.

Shows what needs to happen this week with urgency tiers, and optionally
executes the full enrichment → advance → preflight → checklist pipeline.

Usage:
    python scripts/campaign.py                            # 14-day window
    python scripts/campaign.py --days 7                   # Next 7 days
    python scripts/campaign.py --days 30                  # Full month
    python scripts/campaign.py --execute --dry-run        # Preview pipeline
    python scripts/campaign.py --execute --yes            # Execute for urgent
    python scripts/campaign.py --execute --id artadia-nyc --yes  # Single entry
"""

import argparse
import sys
from datetime import date

from pipeline_lib import (
    load_entries, load_entry_by_id, load_profile,
    get_deadline, days_until, get_effort,
    ACTIONABLE_STATUSES, DRAFTS_DIR,
)

from enrich import (
    enrich_materials, enrich_variant, enrich_portal_fields,
    find_matching_variant, detect_gaps,
    GRANT_TEMPLATE_PATH, GRANT_TEMPLATE_TRACKS,
)


# --- Urgency classification ---


def classify_urgency(entry: dict) -> str:
    """Classify an entry's urgency tier.

    Returns: "critical", "urgent", "upcoming", or "ready".
    """
    dl_date, dl_type = get_deadline(entry)

    if not dl_date:
        # Rolling or TBA deadlines go to "ready"
        return "ready"

    d = days_until(dl_date)

    if d < 0:
        return "critical"  # expired but still in pipeline
    elif d <= 3:
        return "critical"
    elif d <= 7:
        return "urgent"
    elif d <= 14:
        return "upcoming"
    else:
        return "ready"


def get_campaign_entries(entries: list[dict], days_ahead: int = 14) -> list[dict]:
    """Filter and sort entries relevant to the campaign window.

    Includes:
    - Staged entries with deadlines within days_ahead
    - Qualified/drafting entries with deadlines within days_ahead
    - All staged entries with rolling deadlines
    Excludes:
    - Submitted, outcome, or withdrawn entries
    - Entries with expired deadlines (more than 7 days past)
    """
    campaign = []

    for e in entries:
        status = e.get("status", "")

        # Skip non-actionable
        if status not in ACTIONABLE_STATUSES:
            continue

        # Skip research — too early for campaign
        if status == "research":
            continue

        dl_date, dl_type = get_deadline(e)

        # Include rolling/tba staged entries
        if not dl_date:
            if status in ("staged", "qualified", "drafting") and dl_type in ("rolling", "tba"):
                campaign.append(e)
            continue

        d = days_until(dl_date)

        # Exclude long-expired (>7 days past)
        if d < -7:
            continue

        # Include if within window
        if d <= days_ahead:
            campaign.append(e)

    # Sort by deadline (soonest first), rolling at end
    def sort_key(e):
        dl_date, _ = get_deadline(e)
        if dl_date:
            return (0, days_until(dl_date))
        return (1, 0)

    campaign.sort(key=sort_key)
    return campaign


def format_campaign_view(entries: list[dict], days_ahead: int) -> str:
    """Format the campaign view with urgency tiers."""
    lines = []
    today = date.today()

    lines.append(f"CAMPAIGN: Week of {today.isoformat()}")
    lines.append("=" * 60)
    lines.append("")

    tiers = {
        "critical": [],
        "urgent": [],
        "upcoming": [],
        "ready": [],
    }

    for e in entries:
        urgency = classify_urgency(e)
        tiers[urgency].append(e)

    tier_labels = {
        "critical": "CRITICAL (0-3 days)",
        "urgent": "URGENT (4-7 days)",
        "upcoming": f"UPCOMING (8-{days_ahead} days)",
        "ready": "READY (staged, rolling/30d+)",
    }

    for tier_key, label in tier_labels.items():
        tier_entries = tiers[tier_key]
        lines.append(f"{label}:")

        if not tier_entries:
            lines.append("  (none)")
        else:
            for e in tier_entries:
                name = e.get("name", e.get("id", "?"))
                status = e.get("status", "?")
                effort = get_effort(e)
                dl_date, dl_type = get_deadline(e)

                if dl_date:
                    d = days_until(dl_date)
                    if d < 0:
                        dl_str = f"EXPIRED {abs(d)}d"
                    else:
                        dl_str = f"{d}d"
                else:
                    dl_str = dl_type or "rolling"

                lines.append(f"  {name:<40} {dl_str:<8} {status:<12} {effort}")

                gaps = detect_gaps(e)
                if gaps:
                    lines.append(f"    gaps: {', '.join(gaps)}")

                # Suggest action
                if status in ("qualified", "drafting"):
                    lines.append(f"    needs: advance to staged")

        lines.append("")

    # Summary
    lines.append("=" * 60)

    total_gaps = {"materials": 0, "variants": 0, "portal_fields": 0}
    for e in entries:
        for gap in detect_gaps(e):
            if gap in total_gaps:
                total_gaps[gap] += 1

    lines.append(
        f"Summary: {len(tiers['critical'])} critical | "
        f"{len(tiers['urgent'])} urgent | "
        f"{len(tiers['upcoming'])} upcoming | "
        f"{len(tiers['ready'])} ready"
    )
    lines.append(
        f"         {total_gaps['materials']} need materials | "
        f"{total_gaps['portal_fields']} need portal_fields | "
        f"{total_gaps['variants']} need variants"
    )

    return "\n".join(lines)


# --- Execute mode ---


def run_execute(
    entries: list[dict],
    entry_id: str | None,
    dry_run: bool,
    auto_yes: bool,
):
    """Execute the full pipeline sequence for campaign entries."""
    if entry_id:
        candidates = [e for e in entries if e.get("id") == entry_id]
        if not candidates:
            print(f"Error: Entry '{entry_id}' not found in campaign entries.", file=sys.stderr)
            sys.exit(1)
    else:
        candidates = entries

    if not candidates:
        print("No entries to process.")
        return

    print(f"{'DRY RUN: ' if dry_run else ''}Processing {len(candidates)} entries")
    print(f"{'─' * 60}")

    for e in candidates:
        name = e.get("name", e.get("id", "?"))
        eid = e.get("id", "?")
        status = e.get("status", "?")
        dl_date, dl_type = get_deadline(e)
        dl_str = f"{days_until(dl_date)}d" if dl_date else (dl_type or "rolling")

        print(f"\n  {name} ({dl_str}, {status})")
        gaps = detect_gaps(e)
        if gaps:
            print(f"    gaps: {', '.join(gaps)}")

    if dry_run:
        print(f"\n{'─' * 60}")
        print(f"Dry run complete. {len(candidates)} entries would be processed.")
        print("Steps per entry: enrich → advance (if needed) → preflight → checklist")
        return

    if not auto_yes:
        print(f"\n{'─' * 60}")
        try:
            confirm = input("Proceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if confirm != "y":
            print("Aborted.")
            return

    # Import execution dependencies
    from advance import can_advance, advance_entry
    from preflight import check_entry
    from submit import generate_checklist

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0
    for e in candidates:
        eid = e.get("id", "?")
        name = e.get("name", eid)
        filepath = e.get("_filepath")
        status = e.get("status", "")

        if not filepath:
            print(f"  SKIP {name} — no file path")
            continue

        print(f"\n  Processing: {name}")

        # Step 1: Enrich
        enriched = False
        if enrich_materials(filepath, e):
            print(f"    + materials wired")
            enriched = True

        variant = find_matching_variant(eid)
        if not variant and e.get("track") in GRANT_TEMPLATE_TRACKS:
            variant = GRANT_TEMPLATE_PATH
        if variant:
            sub = e.get("submission", {})
            vids = sub.get("variant_ids", {}) if isinstance(sub, dict) else {}
            if not (isinstance(vids, dict) and vids):
                if enrich_variant(filepath, e, variant):
                    print(f"    + variant wired: {variant}")
                    enriched = True

        if enrich_portal_fields(filepath, e):
            print(f"    + portal_fields populated")
            enriched = True

        # Step 2: Advance to staged if needed
        if status in ("qualified", "drafting") and can_advance(status, "staged"):
            advance_entry(filepath, eid, "staged")
            print(f"    + advanced: {status} → staged")

        # Step 3: Preflight — reload entry after modifications
        from pipeline_lib import load_entry_by_id as reload_entry
        _, fresh_entry = reload_entry(eid)
        if fresh_entry:
            issues = check_entry(fresh_entry)
            if issues:
                print(f"    ! preflight: {len(issues)} issue(s)")
                for issue in issues:
                    print(f"      - {issue}")
            else:
                print(f"    + preflight: READY")

            # Step 4: Generate checklist
            profile = load_profile(eid)
            from pipeline_lib import load_legacy_script
            legacy = load_legacy_script(eid)
            checklist, _ = generate_checklist(fresh_entry, profile, legacy)

            checklist_path = DRAFTS_DIR / f"{eid}-checklist.md"
            checklist_path.write_text(checklist)
            print(f"    + checklist: drafts/{eid}-checklist.md")

        processed += 1

    print(f"\n{'─' * 60}")
    print(f"Processed {processed} entries. Checklists in pipeline/drafts/")
    print("Next: review checklists → open portals → paste → submit.py --record")


def main():
    parser = argparse.ArgumentParser(
        description="Deadline-aware campaign orchestrator"
    )
    parser.add_argument("--days", type=int, default=14,
                        help="Look-ahead window in days (default: 14)")
    parser.add_argument("--execute", action="store_true",
                        help="Execute full pipeline sequence for campaign entries")
    parser.add_argument("--id", dest="entry_id",
                        help="Process a specific entry by ID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview execution without modifying files")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompt")
    args = parser.parse_args()

    entries = load_entries(include_filepath=True)
    campaign = get_campaign_entries(entries, days_ahead=args.days)

    if args.execute:
        run_execute(campaign, args.entry_id, args.dry_run, args.yes)
    else:
        view = format_campaign_view(campaign, args.days)
        print(view)


if __name__ == "__main__":
    main()
