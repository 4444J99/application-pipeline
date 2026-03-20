#!/usr/bin/env python3
"""Identify and archive stale or low-signal research_pool entries.

Applies four archival criteria against the 1,000+ entries in research_pool/
to reduce technical debt without touching pipeline/active/ or pipeline/submitted/.

Archival criteria (ANY one triggers archival):
    1. Low score:    fit.score < 5.0 (too low to ever qualify under any threshold)
    2. Org cap:      target.organization already has an entry in active/ or submitted/
                     (org-cap = 1; research_pool entries for that org add no value)
    3. Auto-stale:   source is 'auto' or 'source_jobs.py' (auto-sourced) AND score < 7.0
    4. Age-stale:    entry is older than --older-than days with no activity
                     (proxy for expired posting without making HTTP requests)

Scored entries (score >= 7.0) are always kept regardless of other criteria,
because a human or scoring pass has validated their fit.

Usage:
    python scripts/prune_research.py                    # Dry-run report (safe default)
    python scripts/prune_research.py --dry-run          # Explicit dry-run
    python scripts/prune_research.py --execute --yes    # Move files to archive/
    python scripts/prune_research.py --older-than 60    # Custom stale threshold (default: 30)
    python scripts/prune_research.py --min-score 6.0    # Custom low-score threshold (default: 5.0)
    python scripts/prune_research.py --auto-score 8.0   # Custom auto-stale threshold (default: 7.0)
"""

import argparse
import shutil
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_RESEARCH_POOL,
    PIPELINE_DIR_SUBMITTED,
    load_entries,
    parse_date,
)

# Default thresholds
DEFAULT_LOW_SCORE_THRESHOLD = 5.0    # Below this → always archive
DEFAULT_AUTO_SCORE_THRESHOLD = 7.0   # Auto-sourced entries below this → archive
DEFAULT_STALE_AGE_DAYS = 30          # Entries untouched longer than this → archive

# Archive destination: a subdirectory within research_pool/
PRUNE_ARCHIVE_DIR = PIPELINE_DIR_RESEARCH_POOL / "archive"

# Source values considered "auto-sourced"
AUTO_SOURCES = {"auto", "source_jobs.py", "jobspy"}


# ---------------------------------------------------------------------------
# Criteria helpers
# ---------------------------------------------------------------------------

def _get_score(entry: dict) -> float:
    """Return the fit.score as a float, defaulting to 0.0 if missing."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        raw = fit.get("score")
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass
    return 0.0


def _get_last_activity_date(entry: dict) -> date | None:
    """Return the most recent activity date for an entry.

    Checks last_touched, then timeline.date_added, then timeline.posting_date,
    then timeline.discovered. Returns the most recent of these.
    """
    candidates = []

    lt = parse_date(entry.get("last_touched"))
    if lt:
        candidates.append(lt)

    timeline = entry.get("timeline", {})
    if isinstance(timeline, dict):
        for field in ("date_added", "posting_date", "researched"):
            d = parse_date(timeline.get(field))
            if d:
                candidates.append(d)
        # discovered may be a full ISO datetime string — parse date portion only
        discovered_raw = timeline.get("discovered")
        if discovered_raw and isinstance(discovered_raw, str):
            d = parse_date(discovered_raw[:10])  # trim to YYYY-MM-DD
            if d:
                candidates.append(d)

    return max(candidates) if candidates else None


def _is_auto_sourced(entry: dict) -> bool:
    """Return True if the entry was created by an automated sourcing script."""
    source = entry.get("source", "")
    tags = entry.get("tags") or []
    return (
        source in AUTO_SOURCES
        or "auto-sourced" in tags
    )


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def build_active_submitted_orgs() -> set[str]:
    """Collect all organizations that have at least one active or submitted entry.

    Returns a set of lowercased organization names.
    """
    entries = load_entries(
        dirs=[PIPELINE_DIR_ACTIVE, PIPELINE_DIR_SUBMITTED],
        include_filepath=False,
    )
    orgs: set[str] = set()
    for e in entries:
        target = e.get("target", {})
        if isinstance(target, dict):
            org = target.get("organization", "")
            if org:
                orgs.add(org.strip().lower())
    return orgs


def classify_entries(
    pool_entries: list[dict],
    active_submitted_orgs: set[str],
    low_score_threshold: float = DEFAULT_LOW_SCORE_THRESHOLD,
    auto_score_threshold: float = DEFAULT_AUTO_SCORE_THRESHOLD,
    stale_age_days: int = DEFAULT_STALE_AGE_DAYS,
) -> tuple[list[dict], list[dict]]:
    """Classify research_pool entries into (to_archive, to_keep).

    Each archived entry dict carries a 'reasons' list and 'age_days' value.
    Each kept entry dict carries a 'keep_reason' explaining why it was retained.

    A score >= auto_score_threshold always forces keeping, regardless of other criteria.
    """
    to_archive: list[dict] = []
    to_keep: list[dict] = []
    today = date.today()

    for entry in pool_entries:
        if entry.get("status") != "research":
            # Only process research-status entries (safety guard)
            to_keep.append({**entry, "keep_reason": "non-research status"})
            continue

        entry.get("id", "?")
        score = _get_score(entry)
        org = (entry.get("target") or {}).get("organization", "").strip()
        org_lower = org.lower()
        is_auto = _is_auto_sourced(entry)
        last_activity = _get_last_activity_date(entry)
        age_days = (today - last_activity).days if last_activity else None

        # --- Gate: high-scored entries are always kept ---
        if score >= auto_score_threshold:
            to_keep.append({**entry, "keep_reason": f"score {score:.1f} >= {auto_score_threshold}"})
            continue

        # --- Evaluate each archival criterion ---
        reasons: list[str] = []

        # Criterion 1: Low score
        if score < low_score_threshold:
            reasons.append(f"low_score ({score:.1f} < {low_score_threshold})")

        # Criterion 2: Org cap — org already has active/submitted entry
        if org_lower and org_lower in active_submitted_orgs:
            reasons.append(f"org_cap ({org!r} already in active/submitted)")

        # Criterion 3: Auto-sourced + below auto_score_threshold
        # (the high-score gate above already excluded score >= auto_score_threshold)
        if is_auto and score < auto_score_threshold:
            reasons.append(f"auto_stale (auto-sourced, score {score:.1f} < {auto_score_threshold})")

        # Criterion 4: Age-stale (proxy for expired posting)
        if age_days is not None and age_days > stale_age_days:
            reasons.append(f"age_stale ({age_days}d > {stale_age_days}d threshold)")

        if reasons:
            to_archive.append({
                **entry,
                "reasons": reasons,
                "age_days": age_days,
                "score": score,
            })
        else:
            reason_parts = []
            if score >= low_score_threshold:
                reason_parts.append(f"score {score:.1f} >= {low_score_threshold}")
            if org_lower and org_lower not in active_submitted_orgs:
                reason_parts.append("org not capped")
            if not is_auto:
                reason_parts.append("manually sourced")
            if age_days is not None and age_days <= stale_age_days:
                reason_parts.append(f"{age_days}d old (within {stale_age_days}d)")
            to_keep.append({**entry, "keep_reason": "; ".join(reason_parts) or "no criteria met"})

    return to_archive, to_keep


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

REASON_LABELS = {
    "low_score": "Low score (< threshold)",
    "org_cap": "Org cap (org already active/submitted)",
    "auto_stale": "Auto-sourced + below score threshold",
    "age_stale": "Age-stale (no activity > threshold)",
}


def _reason_key(reason: str) -> str:
    """Extract the prefix key from a reason string like 'low_score (…)'."""
    return reason.split("(")[0].strip()


def print_report(
    to_archive: list[dict],
    to_keep: list[dict],
    dry_run: bool,
    show_keep_detail: bool = False,
) -> None:
    """Print a human-readable classification report."""
    total = len(to_archive) + len(to_keep)

    print("=" * 60)
    print("Research Pool Prune Report")
    print("=" * 60)
    print(f"Total research_pool entries scanned: {total}")
    print(f"  To archive:  {len(to_archive)}")
    print(f"  To keep:     {len(to_keep)}")
    print()

    # Reason breakdown
    reason_counts: dict[str, int] = defaultdict(int)
    for entry in to_archive:
        for reason in entry.get("reasons", []):
            reason_counts[_reason_key(reason)] += 1

    if reason_counts:
        print("Archival reasons (entries may match multiple):")
        for key, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            label = REASON_LABELS.get(key, key)
            print(f"  {count:>5}  {label}")
        print()

    # Entries to archive
    if to_archive:
        mode = "DRY-RUN — would archive" if dry_run else "Archiving"
        print(f"{mode} {len(to_archive)} entries → research_pool/archive/:")
        for entry in sorted(to_archive, key=lambda e: e.get("id", "")):
            entry_id = entry.get("id", "?")
            age = entry.get("age_days")
            score = entry.get("score", 0.0)
            age_str = f"{age}d" if age is not None else "no date"
            reasons_str = ", ".join(entry.get("reasons", []))
            print(f"  {entry_id}")
            print(f"    score={score:.1f}  age={age_str}")
            print(f"    reasons: {reasons_str}")
    else:
        print("No entries flagged for archival.")
    print()

    if show_keep_detail and to_keep:
        print(f"Keeping {len(to_keep)} entries:")
        for entry in sorted(to_keep, key=lambda e: e.get("id", "")):
            entry_id = entry.get("id", "?")
            keep_reason = entry.get("keep_reason", "")
            print(f"  {entry_id} — {keep_reason}")
        print()

    if dry_run and to_archive:
        print("Dry-run mode — no files moved.")
        print("Run with --execute --yes to apply.")


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def archive_entries(to_archive: list[dict]) -> tuple[int, int]:
    """Move flagged entries to PRUNE_ARCHIVE_DIR.

    Returns (moved_count, skipped_count).
    """
    PRUNE_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    moved = 0
    skipped = 0

    for entry in to_archive:
        filepath = entry.get("_filepath")
        if not filepath:
            print(f"  [SKIP] {entry.get('id', '?')} — no _filepath metadata", file=sys.stderr)
            skipped += 1
            continue

        src = Path(filepath)
        if not src.exists():
            print(f"  [SKIP] {entry.get('id', '?')} — file not found: {src}", file=sys.stderr)
            skipped += 1
            continue

        dest = PRUNE_ARCHIVE_DIR / src.name
        if dest.exists():
            print(f"  [SKIP] {entry.get('id', '?')} — already in archive/")
            skipped += 1
            continue

        shutil.move(str(src), str(dest))
        print(f"  [MOVED] {src.name}")
        moved += 1

    return moved, skipped


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def print_summary(moved: int, skipped: int, kept: int) -> None:
    """Print execution summary."""
    print()
    print("=" * 60)
    print(f"Moved to archive:  {moved}")
    print(f"Skipped (errors):  {skipped}")
    print(f"Kept in pool:      {kept}")
    print(f"Archive location:  {PRUNE_ARCHIVE_DIR}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Identify and archive stale/low-signal entries from research_pool/.\n\n"
            "By default runs in dry-run mode (safe). Use --execute --yes to move files."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview archival candidates without moving files (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Enable file moves (must be combined with --yes)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm execution (required with --execute)",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=DEFAULT_STALE_AGE_DAYS,
        metavar="DAYS",
        help=f"Age threshold in days for stale entries (default: {DEFAULT_STALE_AGE_DAYS})",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=DEFAULT_LOW_SCORE_THRESHOLD,
        metavar="SCORE",
        help=f"Entries with score below this are always archived (default: {DEFAULT_LOW_SCORE_THRESHOLD})",
    )
    parser.add_argument(
        "--auto-score",
        type=float,
        default=DEFAULT_AUTO_SCORE_THRESHOLD,
        metavar="SCORE",
        help=(
            f"Auto-sourced entries below this score are archived; "
            f"entries at or above are always kept (default: {DEFAULT_AUTO_SCORE_THRESHOLD})"
        ),
    )
    parser.add_argument(
        "--show-kept",
        action="store_true",
        help="Include kept entries in the report output",
    )
    args = parser.parse_args()

    # Determine execution mode
    execute = args.execute and args.yes
    dry_run = not execute

    if args.execute and not args.yes:
        print("Error: --execute requires --yes to confirm.", file=sys.stderr)
        print("Re-run with: --execute --yes", file=sys.stderr)
        sys.exit(1)

    # Validate thresholds
    if args.min_score > args.auto_score:
        print(
            f"Warning: --min-score ({args.min_score}) > --auto-score ({args.auto_score}). "
            "This means all entries below auto-score would also be below min-score, "
            "making --min-score redundant. Consider adjusting.",
            file=sys.stderr,
        )

    # --- Load data ---
    print("Loading research_pool entries...")
    pool_entries = load_entries(
        dirs=[PIPELINE_DIR_RESEARCH_POOL],
        include_filepath=True,
    )
    # Exclude entries already in the archive subdirectory
    pool_entries = [
        e for e in pool_entries
        if "_archived" not in str(e.get("_filepath", ""))
        and "archive" not in str(Path(e.get("_filepath", "")).parent.name)
    ]
    print(f"  {len(pool_entries)} research_pool entries loaded (excluding already-archived)")

    print("Loading active/submitted organizations for org-cap check...")
    active_submitted_orgs = build_active_submitted_orgs()
    print(f"  {len(active_submitted_orgs)} organizations with active/submitted entries")
    print()

    # --- Classify ---
    to_archive, to_keep = classify_entries(
        pool_entries=pool_entries,
        active_submitted_orgs=active_submitted_orgs,
        low_score_threshold=args.min_score,
        auto_score_threshold=args.auto_score,
        stale_age_days=args.older_than,
    )

    # --- Report ---
    print_report(
        to_archive=to_archive,
        to_keep=to_keep,
        dry_run=dry_run,
        show_keep_detail=args.show_kept,
    )

    # --- Execute ---
    if execute:
        if not to_archive:
            print("Nothing to archive.")
            return
        print(f"\nMoving {len(to_archive)} entries to {PRUNE_ARCHIVE_DIR}...")
        moved, skipped = archive_entries(to_archive)
        print_summary(moved, skipped, len(to_keep))
    else:
        # Dry-run final line
        print(f"[DRY-RUN] {len(to_archive)} entries would be archived, {len(to_keep)} kept.")


if __name__ == "__main__":
    main()
