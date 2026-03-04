#!/usr/bin/env python3
"""Mark entries as reviewed for multi-operator submission governance.

Adds/updates status_meta.reviewed_by and status_meta.reviewed_at.
This enables review gating before staged entries are submitted.

Usage:
    python scripts/review_entry.py --target anthropic-... --reviewer 4jp
    python scripts/review_entry.py --all-staged --reviewer 4jp
    python scripts/review_entry.py --all-staged --dry-run
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import PIPELINE_DIR_ACTIVE, atomic_write, load_entries, load_entry_by_id


def _default_reviewer() -> str:
    # Preferred explicit operator env var for automation, then shell user.
    return os.environ.get("PIPELINE_OPERATOR") or os.environ.get("USER") or getpass.getuser() or "unknown"


def mark_reviewed(filepath: Path, reviewer: str, note: str | None = None, dry_run: bool = False) -> dict:
    data = yaml.safe_load(filepath.read_text()) or {}
    if not isinstance(data, dict):
        return {"ok": False, "error": "entry is not a YAML mapping"}

    today = date.today().isoformat()
    status_meta = data.get("status_meta")
    if not isinstance(status_meta, dict):
        status_meta = {}

    status_meta["reviewed_by"] = reviewer
    status_meta["reviewed_at"] = today
    if note:
        status_meta["review_note"] = note

    data["status_meta"] = status_meta
    data["last_touched"] = today

    if dry_run:
        return {"ok": True, "dry_run": True, "status_meta": status_meta}

    content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    atomic_write(filepath, content)

    try:
        from log_signal_action import log_action

        log_action(
            signal_id=f"review-{data.get('id', filepath.stem)}-{today}",
            signal_type="agent_rule",
            description="Submission governance review completed",
            triggered_action="marked entry as reviewed",
            entry_id=data.get("id", filepath.stem),
            responsible=reviewer,
        )
    except Exception:
        pass

    return {"ok": True, "dry_run": False, "status_meta": status_meta}


def _collect_targets(target: str | None, all_staged: bool) -> list[Path]:
    if target:
        filepath, _ = load_entry_by_id(target)
        if not filepath:
            raise FileNotFoundError(f"No pipeline entry found for '{target}'")
        return [filepath]

    if not all_staged:
        raise ValueError("Specify --target <id> or --all-staged")

    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE], include_filepath=True)
    return [e["_filepath"] for e in entries if e.get("status") == "staged" and e.get("_filepath")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Mark entries reviewed for governance gate")
    parser.add_argument("--target", help="Entry ID to mark reviewed")
    parser.add_argument("--all-staged", action="store_true", help="Mark all staged active entries reviewed")
    parser.add_argument("--reviewer", default=_default_reviewer(), help="Reviewer name/handle")
    parser.add_argument("--note", default="", help="Optional review note")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    try:
        targets = _collect_targets(args.target, args.all_staged)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

    if not targets:
        print("No matching entries to review.")
        raise SystemExit(0)

    mode = "DRY RUN" if args.dry_run else "EXECUTE"
    print(f"REVIEW MARKER ({mode}) — {len(targets)} entr(y/ies)")
    print("=" * 70)

    updated = 0
    for filepath in sorted(targets):
        result = mark_reviewed(filepath, reviewer=args.reviewer, note=args.note or None, dry_run=args.dry_run)
        if result.get("ok"):
            updated += 1
            print(f"  {'[dry-run] ' if args.dry_run else ''}{filepath.stem} -> reviewed_by={args.reviewer}")
        else:
            print(f"  [error] {filepath.stem}: {result.get('error', 'unknown error')}")

    print("-" * 70)
    print(f"Updated: {updated}/{len(targets)}")


if __name__ == "__main__":
    main()
