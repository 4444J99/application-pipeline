#!/usr/bin/env python3
"""Backfill date_added from timeline.researched for entries missing freshness data.

Scans all pipeline directories (including research_pool) and sets
date_added = timeline.researched for entries that have neither posting_date
nor date_added. This gives freshness_monitor.py usable age data.

Usage:
    python scripts/backfill_dates.py --report        # Show freshness tier counts
    python scripts/backfill_dates.py --dry-run       # Preview changes (default)
    python scripts/backfill_dates.py --yes           # Execute backfill
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import ALL_PIPELINE_DIRS_WITH_POOL, load_entries, parse_date


def classify_freshness(days_old: int | None) -> str:
    """Classify entry age into freshness tiers."""
    if days_old is None:
        return "unknown"
    if days_old <= 7:
        return "fresh (<=7d)"
    if days_old <= 30:
        return "recent (8-30d)"
    if days_old <= 90:
        return "aging (31-90d)"
    return "stale (>90d)"


def find_backfill_candidates(entries: list[dict]) -> list[dict]:
    """Find entries that need date_added backfill."""
    candidates = []
    for entry in entries:
        timeline = entry.get("timeline", {})
        if not isinstance(timeline, dict):
            continue
        posting_date = timeline.get("posting_date")
        date_added = timeline.get("date_added")
        researched = timeline.get("researched")
        if not posting_date and not date_added and researched:
            candidates.append(entry)
    return candidates


def backfill_entry(filepath: Path, dry_run: bool = True) -> bool:
    """Add date_added to a single entry's timeline section."""
    content = filepath.read_text()
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        return False

    timeline = data.get("timeline", {})
    if not isinstance(timeline, dict):
        return False

    researched = timeline.get("researched")
    if not researched:
        return False

    # Format the date value to match YAML style
    if isinstance(researched, date):
        date_str = researched.isoformat()
    else:
        date_str = str(researched)

    if dry_run:
        return True

    # Insert date_added after researched or posting_date in the timeline block
    lines = content.split("\n")
    insert_after = None
    in_timeline = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("timeline:"):
            in_timeline = True
            continue
        if in_timeline:
            # End of timeline block: non-indented, non-blank line
            if stripped and not line[0].isspace():
                break
            if stripped.startswith("researched:") or stripped.startswith("posting_date:"):
                insert_after = i

    if insert_after is not None:
        # Match the indentation of the line we're inserting after
        ref_line = lines[insert_after]
        indent = ref_line[: len(ref_line) - len(ref_line.lstrip())]
        lines.insert(insert_after + 1, f"{indent}date_added: {date_str}")
        filepath.write_text("\n".join(lines))
        return True

    return False


def show_report(entries: list[dict]):
    """Show freshness distribution across all entries."""
    today = date.today()
    tiers: dict[str, int] = {}
    for entry in entries:
        timeline = entry.get("timeline", {})
        if not isinstance(timeline, dict):
            age = None
        else:
            d = timeline.get("posting_date") or timeline.get("date_added") or timeline.get("researched")
            parsed = parse_date(d) if d else None
            age = (today - parsed).days if parsed else None
        tier = classify_freshness(age)
        tiers[tier] = tiers.get(tier, 0) + 1

    print(f"FRESHNESS DISTRIBUTION — {today.isoformat()}")
    print("=" * 45)
    total = sum(tiers.values())
    for tier in ["fresh (<=7d)", "recent (8-30d)", "aging (31-90d)", "stale (>90d)", "unknown"]:
        count = tiers.get(tier, 0)
        pct = count / total * 100 if total else 0
        bar = "█" * (count // 5) if count > 0 else ""
        print(f"  {tier:<18s} {count:>4} ({pct:4.1f}%)  {bar}")
    print(f"  {'TOTAL':<18s} {total:>4}")


def main():
    parser = argparse.ArgumentParser(description="Backfill date_added from timeline.researched")
    parser.add_argument("--report", action="store_true", help="Show freshness tier counts")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview changes (default)")
    parser.add_argument("--yes", action="store_true", help="Execute backfill")
    args = parser.parse_args()

    if args.yes:
        args.dry_run = False

    entries = load_entries(ALL_PIPELINE_DIRS_WITH_POOL, include_filepath=True)

    if args.report:
        show_report(entries)
        return

    candidates = find_backfill_candidates(entries)

    if not candidates:
        print("No entries need date_added backfill.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Backfilling date_added for {len(candidates)} entries...")
    print()

    updated = 0
    for entry in candidates:
        filepath = entry.get("_filepath")
        if not filepath:
            continue
        filepath = Path(filepath)
        entry_id = entry.get("id", filepath.stem)
        timeline = entry.get("timeline", {})
        researched = timeline.get("researched", "?")

        if backfill_entry(filepath, dry_run=args.dry_run):
            action = "would set" if args.dry_run else "set"
            print(f"  {action} date_added={researched} for {entry_id}")
            updated += 1

    print(f"\n{'Would update' if args.dry_run else 'Updated'}: {updated} entries")
    if args.dry_run and updated > 0:
        print("Run with --yes to execute.")


if __name__ == "__main__":
    main()
