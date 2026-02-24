#!/usr/bin/env python3
"""Deadline-aware campaign orchestrator.

Shows what needs to happen this week with urgency tiers, and optionally
executes the full enrichment → advance → preflight → checklist pipeline.

Usage:
    python scripts/campaign.py                            # 14-day window
    python scripts/campaign.py --days 7                   # Next 7 days
    python scripts/campaign.py --days 30                  # Full month
    python scripts/campaign.py --days 90                  # Full quarter
    python scripts/campaign.py --save                     # Save markdown to strategy/
    python scripts/campaign.py --execute --dry-run        # Preview pipeline
    python scripts/campaign.py --execute --yes            # Execute for urgent
    python scripts/campaign.py --execute --id <id> --yes  # Single entry
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from pipeline_lib import (
    load_entries, load_entry_by_id, load_profile,
    get_deadline, days_until, get_effort, get_score, format_amount,
    ACTIONABLE_STATUSES, DRAFTS_DIR, REPO_ROOT, EFFORT_MINUTES,
)

from enrich import (
    enrich_materials, enrich_variant, enrich_portal_fields,
    find_matching_variant, detect_gaps,
    GRANT_TEMPLATE_PATH, GRANT_TEMPLATE_TRACKS,
)
from score import QUALIFICATION_THRESHOLD


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


def is_effort_feasible(entry: dict) -> bool:
    """Check if an entry's effort fits within its remaining deadline time.

    Returns False if the estimated effort (in working hours) exceeds
    the days remaining before the deadline. Assumes ~6 productive hours/day.
    """
    dl_date, _ = get_deadline(entry)
    if not dl_date:
        return True  # rolling/tba — always feasible

    d = days_until(dl_date)
    if d < 0:
        return False  # expired

    effort = get_effort(entry)
    effort_minutes = EFFORT_MINUTES.get(effort, 90)
    # Assume ~6 productive hours (360 min) per day
    available_minutes = d * 360

    return effort_minutes <= available_minutes


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
    lines.append("=" * 70)
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
                score = get_score(e)
                amount = format_amount(e.get("amount"))
                track = e.get("track", "")
                dl_date, dl_type = get_deadline(e)

                if dl_date:
                    d = days_until(dl_date)
                    if d < 0:
                        dl_str = f"EXPIRED {abs(d)}d"
                    else:
                        dl_str = f"{d}d"
                else:
                    dl_str = dl_type or "rolling"

                low_tag = " [LOW]" if score and score < QUALIFICATION_THRESHOLD else ""
                feasible_tag = "" if is_effort_feasible(e) else " [INFEASIBLE]"
                score_str = f"[{score:.1f}]" if score else ""
                lines.append(
                    f"  {score_str:>6} {name:<38} {dl_str:<8} "
                    f"{status:<12} {effort:<10} {amount}{low_tag}{feasible_tag}"
                )

                gaps = detect_gaps(e)
                if gaps:
                    lines.append(f"         gaps: {', '.join(gaps)}")

                # Suggest action
                if status in ("qualified", "drafting"):
                    lines.append(f"         needs: advance to staged")

        lines.append("")

    # Recommended execution order (deadlined entries sorted by urgency × fit)
    deadlined = []
    for tier_key in ("critical", "urgent", "upcoming"):
        for e in tiers[tier_key]:
            deadlined.append(e)
    # Also include "ready" entries that have actual deadlines (hard, window, etc.)
    for e in tiers["ready"]:
        dl_date, dl_type = get_deadline(e)
        if dl_date and dl_type in ("hard", "window", "soft"):
            deadlined.append(e)

    if deadlined:
        # Sort by: urgency tier first, then deadline week, then fit desc
        def exec_sort_key(e):
            urgency = classify_urgency(e)
            tier_rank = {"critical": 0, "urgent": 1, "upcoming": 2, "ready": 3}
            dl_date, _ = get_deadline(e)
            # Group by deadline week (7-day buckets)
            week_bucket = days_until(dl_date) // 7 if dl_date else 99
            return (tier_rank.get(urgency, 4), week_bucket, -get_score(e))

        deadlined.sort(key=exec_sort_key)

        lines.append("RECOMMENDED EXECUTION ORDER (urgency x fit):")
        for i, e in enumerate(deadlined, 1):
            name = e.get("name", e.get("id", "?"))
            score = get_score(e)
            dl_date, _ = get_deadline(e)
            dl_str = f"{days_until(dl_date)}d" if dl_date else "rolling"
            effort = get_effort(e)
            amount = format_amount(e.get("amount"))
            low_tag = " [LOW]" if score and score < QUALIFICATION_THRESHOLD else ""
            feasible_tag = "" if is_effort_feasible(e) else " [INFEASIBLE]"
            lines.append(
                f"  {i:>2}. [{score:.1f}] {name:<36} {dl_str:<6} "
                f"{effort:<10} {amount}{low_tag}{feasible_tag}"
            )
        lines.append("")

    # Summary
    lines.append("=" * 70)

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


def generate_campaign_markdown(entries: list[dict], days_ahead: int) -> str:
    """Generate a full markdown campaign report for saving to strategy/."""
    today = date.today()
    lines = []
    lines.append(f"# Campaign View — Application Pipeline (as of {today.strftime('%b %d, %Y')})")
    lines.append("")

    tiers = {
        "critical": [],
        "urgent": [],
        "upcoming": [],
        "ready": [],
    }
    for e in entries:
        tiers[classify_urgency(e)].append(e)

    # Deadlined entries by date cluster
    deadlined = []
    for tier_key in ("critical", "urgent", "upcoming"):
        deadlined.extend(tiers[tier_key])
    for e in tiers["ready"]:
        dl_date, dl_type = get_deadline(e)
        if dl_date and dl_type in ("hard", "window", "soft"):
            deadlined.append(e)

    # Group deadlined by date
    date_groups = {}
    for e in deadlined:
        dl_date, _ = get_deadline(e)
        if dl_date:
            date_groups.setdefault(dl_date, []).append(e)
    sorted_dates = sorted(date_groups.keys())

    if sorted_dates:
        lines.append("## Deadlined Queue (chronological)")
        lines.append("")

        for dl_date in sorted_dates:
            group = date_groups[dl_date]
            d = days_until(dl_date)
            lines.append(f"### {dl_date.strftime('%B %d')} — {d} days")
            lines.append("")
            lines.append("| Entry | Track | Status | Fit | Effort | Amount |")
            lines.append("|-------|-------|--------|-----|--------|--------|")
            for e in group:
                name = e.get("name", e.get("id", "?"))
                track = e.get("track", "")
                status = e.get("status", "?")
                score = get_score(e)
                effort = get_effort(e)
                amount = format_amount(e.get("amount"))
                score_str = f"{score:.1f}" if score else "—"
                lines.append(
                    f"| {name} | {track} | `{status}` "
                    f"| {score_str} | {effort} | {amount} |"
                )
            lines.append("")

    # Rolling/no-deadline entries
    rolling = [e for e in tiers["ready"]
               if not (get_deadline(e)[0]
                       and get_deadline(e)[1] in ("hard", "window", "soft"))]

    if rolling:
        lines.append("## Rolling/No-Deadline (staged, submit anytime)")
        lines.append("")

        # Group by track
        track_groups = {}
        for e in rolling:
            track = e.get("track", "other")
            track_groups.setdefault(track, []).append(e)

        for track_name in sorted(track_groups.keys()):
            group = track_groups[track_name]
            lines.append(f"### {track_name.title()}")
            lines.append("")
            lines.append("| Entry | Status | Fit | Effort |")
            lines.append("|-------|--------|-----|--------|")
            for e in group:
                name = e.get("name", e.get("id", "?"))
                status = e.get("status", "?")
                score = get_score(e)
                effort = get_effort(e)
                score_str = f"{score:.1f}" if score else "—"
                lines.append(f"| {name} | `{status}` | {score_str} | {effort} |")
            lines.append("")

    # Recommended execution order
    if deadlined:
        def exec_sort_key(e):
            urgency = classify_urgency(e)
            tier_rank = {"critical": 0, "urgent": 1, "upcoming": 2, "ready": 3}
            dl_date, _ = get_deadline(e)
            week_bucket = days_until(dl_date) // 7 if dl_date else 99
            return (tier_rank.get(urgency, 4), week_bucket, -get_score(e))

        deadlined_sorted = sorted(deadlined, key=exec_sort_key)

        lines.append("## Recommended Execution Order (urgency x fit)")
        lines.append("")
        for i, e in enumerate(deadlined_sorted, 1):
            name = e.get("name", e.get("id", "?"))
            score = get_score(e)
            dl_date, _ = get_deadline(e)
            dl_str = f"{days_until(dl_date)}d" if dl_date else "rolling"
            effort = get_effort(e)
            amount = format_amount(e.get("amount"))
            lines.append(
                f"{i}. **{name}** — {dl_str}, fit {score:.1f}, "
                f"{effort}, {amount}"
            )
        lines.append("")

    lines.append("---")
    lines.append(f"*Generated {today.isoformat()} by `campaign.py --save`*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Deadline-aware campaign orchestrator"
    )
    parser.add_argument("--days", type=int, default=14,
                        help="Look-ahead window in days (default: 14)")
    parser.add_argument("--save", action="store_true",
                        help="Save markdown campaign report to strategy/")
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
    elif args.save:
        md = generate_campaign_markdown(campaign, args.days)
        strategy_dir = REPO_ROOT / "strategy"
        strategy_dir.mkdir(parents=True, exist_ok=True)
        today = date.today()
        filename = f"campaign-{today.strftime('%Y-%m')}.md"
        out_path = strategy_dir / filename
        out_path.write_text(md + "\n")
        print(f"Campaign report saved to {out_path.relative_to(REPO_ROOT)}")
        view = format_campaign_view(campaign, args.days)
        print(view)
    else:
        view = format_campaign_view(campaign, args.days)
        print(view)


if __name__ == "__main__":
    main()
