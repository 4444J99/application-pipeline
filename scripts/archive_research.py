#!/usr/bin/env python3
"""Move research-status entries from active/ to research_pool/.

Reduces noise in active/ so daily workflow scripts only read actionable entries.

Usage:
    python scripts/archive_research.py --report        # Show what would move
    python scripts/archive_research.py --dry-run        # Preview file moves
    python scripts/archive_research.py --yes             # Execute moves
    python scripts/archive_research.py --restore <id>    # Move entry back to active/
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_RESEARCH_POOL,
    load_entries,
    get_score,
)


def get_research_entries() -> list[dict]:
    """Load research-status entries from active/."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE], include_filepath=True)
    return [e for e in entries if e.get("status") == "research"]


def report(entries: list[dict]):
    """Show summary of research entries that would be archived."""
    print(f"Research entries in active/: {len(entries)}")
    if not entries:
        print("Nothing to archive.")
        return

    # Score distribution
    scored = [get_score(e) for e in entries]
    high = sum(1 for s in scored if s >= 7.0)
    mid = sum(1 for s in scored if 5.5 <= s < 7.0)
    low = sum(1 for s in scored if 0 < s < 5.5)
    unscored = sum(1 for s in scored if s == 0)

    print(f"  Score >= 7.0 (high match):   {high}")
    print(f"  Score 5.5-6.9 (above qual):  {mid}")
    print(f"  Score < 5.5 (below qual):    {low}")
    print(f"  Unscored:                    {unscored}")

    # Auto-sourced vs manual
    auto = sum(1 for e in entries if "auto-sourced" in (e.get("tags") or []))
    manual = len(entries) - auto
    print(f"  Auto-sourced: {auto} | Manual: {manual}")

    # Count existing pool entries
    pool_entries = load_entries(dirs=[PIPELINE_DIR_RESEARCH_POOL])
    print(f"\nExisting research_pool/ entries: {len(pool_entries)}")

    # Count non-research entries staying in active/
    all_active = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    staying = len(all_active) - len(entries)
    print(f"Entries staying in active/: {staying}")


def archive(entries: list[dict], dry_run: bool = False) -> int:
    """Move research entries from active/ to research_pool/.

    Returns count of files moved.
    """
    PIPELINE_DIR_RESEARCH_POOL.mkdir(parents=True, exist_ok=True)
    moved = 0

    for entry in entries:
        filepath = entry.get("_filepath")
        if not filepath:
            continue

        dest = PIPELINE_DIR_RESEARCH_POOL / filepath.name
        if dest.exists():
            print(f"  SKIP {filepath.name} — already exists in research_pool/")
            continue

        if dry_run:
            print(f"  [dry-run] {filepath.name} -> research_pool/")
        else:
            shutil.move(str(filepath), str(dest))
            print(f"  {filepath.name} -> research_pool/")
        moved += 1

    return moved


def restore(entry_id: str) -> bool:
    """Move a single entry from research_pool/ back to active/.

    Returns True if restored successfully.
    """
    source = PIPELINE_DIR_RESEARCH_POOL / f"{entry_id}.yaml"
    if not source.exists():
        print(f"Not found in research_pool/: {entry_id}.yaml")
        return False

    dest = PIPELINE_DIR_ACTIVE / f"{entry_id}.yaml"
    if dest.exists():
        print(f"Already exists in active/: {entry_id}.yaml")
        return False

    shutil.move(str(source), str(dest))
    print(f"Restored: {entry_id}.yaml -> active/")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Archive research-status entries from active/ to research_pool/"
    )
    parser.add_argument("--report", action="store_true",
                        help="Show summary of what would be archived")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview file moves without executing")
    parser.add_argument("--yes", action="store_true",
                        help="Execute the archive (move files)")
    parser.add_argument("--restore", metavar="ENTRY_ID",
                        help="Move an entry back from research_pool/ to active/")
    args = parser.parse_args()

    if args.restore:
        success = restore(args.restore)
        sys.exit(0 if success else 1)

    entries = get_research_entries()

    if args.report or (not args.dry_run and not args.yes):
        report(entries)
        return

    if not entries:
        print("No research entries to archive.")
        return

    moved = archive(entries, dry_run=args.dry_run)

    print(f"\n{'=' * 60}")
    if args.dry_run:
        print(f"Would archive {moved} entries (dry run)")
    else:
        print(f"Archived {moved} entries to research_pool/")
        remaining = len(load_entries(dirs=[PIPELINE_DIR_ACTIVE]))
        print(f"Active entries remaining: {remaining}")


if __name__ == "__main__":
    main()
