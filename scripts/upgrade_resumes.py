#!/usr/bin/env python3
"""Batch resume version migration.

Updates all pipeline entries to use the current resume batch directory.
Identifies entries using old batch versions and offers to migrate them.

Usage:
    python scripts/upgrade_resumes.py                    # Report stale batches
    python scripts/upgrade_resumes.py --dry-run          # Preview updates
    python scripts/upgrade_resumes.py --yes              # Execute migration
    python scripts/upgrade_resumes.py --to batch-04      # Migrate to specific batch
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    CURRENT_BATCH,
    MATERIALS_DIR,
    atomic_write,
    load_entries,
)


def find_stale_resumes(entries: list[dict], target_batch: str) -> list[dict]:
    """Find entries with resume paths referencing old batch directories."""
    stale = []
    for entry in entries:
        submission = entry.get("submission", {})
        if not isinstance(submission, dict):
            continue
        materials = submission.get("materials_attached", [])
        if not isinstance(materials, list):
            continue
        resume_path = submission.get("resume_path", "")
        all_paths = list(materials) + ([resume_path] if resume_path else [])

        for path_str in all_paths:
            if not isinstance(path_str, str):
                continue
            match = re.search(r'batch-(\d+)', path_str)
            if match and f"batch-{match.group(1)}" != target_batch:
                stale.append({
                    "entry_id": entry.get("id", "?"),
                    "old_path": path_str,
                    "old_batch": f"batch-{match.group(1)}",
                    "new_path": path_str.replace(f"batch-{match.group(1)}", target_batch),
                    "_file": entry.get("_file", "?"),
                    "_dir": entry.get("_dir", "?"),
                })
    return stale


def upgrade_entry_file(filepath: Path, old_batch: str, new_batch: str) -> bool:
    """Replace old batch references in a YAML file."""
    content = filepath.read_text()
    if old_batch not in content:
        return False
    new_content = content.replace(old_batch, new_batch)
    atomic_write(filepath, new_content)
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch resume version migration")
    parser.add_argument("--to", default=CURRENT_BATCH, help=f"Target batch (default: {CURRENT_BATCH})")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--yes", action="store_true", help="Execute migration")
    args = parser.parse_args()

    target_batch = args.to
    print(f"Target batch: {target_batch}")
    print(f"Auto-detected current batch: {CURRENT_BATCH}")
    print()

    # Check target batch directory exists
    target_dir = MATERIALS_DIR / "resumes" / target_batch
    if not target_dir.exists():
        print(f"Warning: Target batch directory does not exist: {target_dir}", file=sys.stderr)

    entries = load_entries(include_filepath=True)
    stale = find_stale_resumes(entries, target_batch)

    if not stale:
        print(f"All entries already reference {target_batch}. Nothing to migrate.")
        return

    print(f"Found {len(stale)} stale resume reference(s):")
    print()
    for item in stale:
        print(f"  {item['entry_id']}:")
        print(f"    OLD: {item['old_path']}")
        print(f"    NEW: {item['new_path']}")
        # Check if new path actually exists
        new_full = MATERIALS_DIR / item["new_path"]
        if not new_full.exists():
            print("    WARNING: New path does not exist yet")
        print()

    if args.dry_run:
        print("[DRY-RUN] No files modified.")
        return

    if not args.yes:
        print("Run with --yes to execute, or --dry-run to preview.")
        return

    updated = 0
    for item in stale:
        filepath = None
        for d in ALL_PIPELINE_DIRS:
            candidate = d / item["_file"]
            if candidate.exists():
                filepath = candidate
                break
        if filepath and upgrade_entry_file(filepath, item["old_batch"], target_batch):
            print(f"  Updated: {item['entry_id']}")
            updated += 1

    print(f"\nMigrated {updated} entries to {target_batch}.")


if __name__ == "__main__":
    main()
