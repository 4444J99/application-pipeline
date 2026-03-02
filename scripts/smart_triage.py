#!/usr/bin/env python3
"""Intelligent triage of research-pool entries using time-decay scoring.

Surfaces the top opportunities and auto-archives low-value entries based on
a composite score that factors in base fit score, posting age, effort level,
and track type.

Usage:
    python scripts/smart_triage.py                    # Full triage report
    python scripts/smart_triage.py --top 20           # Top 20 opportunities
    python scripts/smart_triage.py --archive --dry-run # Preview auto-archive
    python scripts/smart_triage.py --archive --yes    # Execute auto-archive
    python scripts/smart_triage.py --threshold 4.0    # Custom archive threshold
"""

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_RESEARCH_POOL,
    get_effort,
    get_score,
    load_entries,
    parse_date,
)

# Tracks that represent rarer opportunities worth a scoring bonus
ART_TRACKS = {"grant", "residency", "fellowship", "prize"}


def _get_posting_age_days(entry: dict) -> int | None:
    """Extract age in days from posting_date or date_added in timeline/metadata.

    Returns None if no date is available.
    """
    # Check timeline.posting_date first (most common for auto-sourced entries)
    timeline = entry.get("timeline", {})
    if isinstance(timeline, dict):
        posting = parse_date(timeline.get("posting_date"))
        if posting:
            return (date.today() - posting).days
        added = parse_date(timeline.get("date_added"))
        if added:
            return (date.today() - added).days

    # Fallback: metadata.date_added
    metadata = entry.get("metadata", {})
    if isinstance(metadata, dict):
        added = parse_date(metadata.get("date_added"))
        if added:
            return (date.today() - added).days

    return None


def compute_decay_score(entry: dict) -> float:
    """Compute a time-decay-adjusted score for triage ranking.

    Formula:
        final = clamp(base * decay + effort_adj + track_adj, 0, 10)

    Where:
        base     = fit.score (0-10 composite)
        decay    = max(0, 1 - age_days/180) or 0.5 if no date
        effort   = +0.5 (quick), 0 (standard), -0.5 (intensive)
        track    = +0.3 for art tracks (grant/residency/fellowship/prize)
    """
    base = get_score(entry)

    # Time decay: fresh postings score higher
    age_days = _get_posting_age_days(entry)
    if age_days is not None:
        decay = max(0.0, 1.0 - age_days / 180.0)
    else:
        decay = 0.5  # neutral when no date available

    # Effort adjustment: quick wins get a bonus, intensive gets a penalty
    effort = get_effort(entry)
    effort_adj = {"quick": 0.5, "standard": 0.0, "deep": -0.25, "intensive": -0.5}.get(effort, 0.0)

    # Track adjustment: rarer art opportunities get a bonus
    track = entry.get("track", "")
    track_adj = 0.3 if track in ART_TRACKS else 0.0

    final = base * decay + effort_adj + track_adj

    # Clamp to 0-10
    final = max(0.0, min(10.0, final))

    return round(final, 2)


def triage_entries(
    entries: list[dict],
    archive_threshold: float = 3.0,
    top_n: int = 30,
) -> dict:
    """Score and split entries into three tiers.

    Returns:
        {
            "top": [...],       # score >= 6.0 — actively pursue
            "hold": [...],      # archive_threshold <= score < 6.0 — keep but deprioritize
            "archive": [...],   # score < archive_threshold — auto-archive candidates
            "total": int
        }

    Each item is {"entry": dict, "decay_score": float, "base_score": float, "age_days": int|None}.
    """
    scored = []
    for entry in entries:
        decay_score = compute_decay_score(entry)
        base_score = get_score(entry)
        age_days = _get_posting_age_days(entry)
        scored.append({
            "entry": entry,
            "decay_score": decay_score,
            "base_score": base_score,
            "age_days": age_days,
        })

    top = sorted(
        [s for s in scored if s["decay_score"] >= 6.0],
        key=lambda s: -s["decay_score"],
    )[:top_n]

    hold = sorted(
        [s for s in scored if archive_threshold <= s["decay_score"] < 6.0],
        key=lambda s: -s["decay_score"],
    )

    archive = sorted(
        [s for s in scored if s["decay_score"] < archive_threshold],
        key=lambda s: -s["decay_score"],
    )

    return {
        "top": top,
        "hold": hold,
        "archive": archive,
        "total": len(entries),
    }


def show_triage_report(triage_result: dict):
    """Print a formatted triage report with three sections."""
    top = triage_result["top"]
    hold = triage_result["hold"]
    archive = triage_result["archive"]
    total = triage_result["total"]

    print(f"\n{'=' * 70}")
    print(f"  SMART TRIAGE REPORT — {total} entries analyzed")
    print(f"{'=' * 70}")

    # Top tier
    print(f"\n  TOP OPPORTUNITIES ({len(top)} entries, score >= 6.0)")
    print(f"  {'-' * 64}")
    if top:
        for i, item in enumerate(top, 1):
            e = item["entry"]
            name = e.get("name", e.get("id", "?"))[:40]
            org = (e.get("target", {}) or {}).get("organization", "")[:20]
            track = e.get("track", "?")
            age_str = f"{item['age_days']}d" if item["age_days"] is not None else "n/a"
            print(
                f"  {i:3}. {name:<40} {org:<20} "
                f"base={item['base_score']:.1f} decay={item['decay_score']:.1f} "
                f"age={age_str} [{track}]"
            )
    else:
        print("  (none)")

    # Hold tier
    print(f"\n  HOLD ({len(hold)} entries, {triage_result.get('_threshold', 3.0):.1f} <= score < 6.0)")
    print(f"  {'-' * 64}")
    if hold:
        shown = hold[:5]
        for item in shown:
            e = item["entry"]
            name = e.get("name", e.get("id", "?"))[:40]
            org = (e.get("target", {}) or {}).get("organization", "")[:20]
            print(
                f"       {name:<40} {org:<20} "
                f"decay={item['decay_score']:.1f}"
            )
        if len(hold) > 5:
            print(f"       ... and {len(hold) - 5} more")
    else:
        print("  (none)")

    # Archive tier
    print(f"\n  ARCHIVE CANDIDATES ({len(archive)} entries, score < {triage_result.get('_threshold', 3.0):.1f})")
    print(f"  {'-' * 64}")
    if archive:
        print(f"  {len(archive)} entries scored below threshold.")
        print("  Run with --archive --dry-run to preview, --archive --yes to execute.")
    else:
        print("  (none)")

    print(f"\n{'=' * 70}\n")


def auto_archive(
    entries: list[dict],
    threshold: float = 3.0,
    dry_run: bool = True,
) -> list[dict]:
    """Archive entries that score below the threshold.

    Moves YAML files from active/ or research_pool/ source to research_pool/.
    Entries already in research_pool/ that score below threshold are noted
    but not moved.

    Returns list of archived entry summaries.
    """
    PIPELINE_DIR_RESEARCH_POOL.mkdir(parents=True, exist_ok=True)

    archived = []
    for entry in entries:
        decay_score = compute_decay_score(entry)
        if decay_score >= threshold:
            continue

        entry_id = entry.get("id", "unknown")
        name = entry.get("name", entry_id)
        filepath = entry.get("_filepath")

        summary = {
            "id": entry_id,
            "name": name,
            "decay_score": decay_score,
            "base_score": get_score(entry),
        }

        # Only move files that are in active/ (research_pool entries stay put)
        if filepath and filepath.parent == PIPELINE_DIR_ACTIVE:
            dest = PIPELINE_DIR_RESEARCH_POOL / filepath.name
            if dest.exists():
                print(f"  SKIP {entry_id} — already exists in research_pool/")
                continue

            if dry_run:
                print(f"  [dry-run] {entry_id} (score={decay_score:.1f}) -> research_pool/")
            else:
                shutil.move(str(filepath), str(dest))
                print(f"  ARCHIVED {entry_id} (score={decay_score:.1f}) -> research_pool/")
            summary["action"] = "archived" if not dry_run else "would_archive"
        else:
            if dry_run:
                print(f"  [info] {entry_id} (score={decay_score:.1f}) already in research_pool/")
            summary["action"] = "already_in_pool"

        archived.append(summary)

    total_actionable = sum(1 for a in archived if a["action"] in ("archived", "would_archive"))
    print(f"\n{'=' * 60}")
    if dry_run:
        print(f"Would archive {total_actionable} entries (dry run)")
    else:
        print(f"Archived {total_actionable} entries to research_pool/")

    return archived


def show_top_opportunities(entries: list[dict], n: int = 20):
    """Print top N opportunities sorted by decay score."""
    scored = []
    for entry in entries:
        scored.append({
            "entry": entry,
            "decay_score": compute_decay_score(entry),
            "base_score": get_score(entry),
            "age_days": _get_posting_age_days(entry),
        })

    scored.sort(key=lambda s: -s["decay_score"])
    top = scored[:n]

    print(f"\n{'=' * 70}")
    print(f"  TOP {n} OPPORTUNITIES")
    print(f"{'=' * 70}\n")

    for i, item in enumerate(top, 1):
        e = item["entry"]
        entry_id = e.get("id", "?")
        name = e.get("name", entry_id)[:45]
        org = (e.get("target", {}) or {}).get("organization", "")[:22]
        track = e.get("track", "?")
        effort = get_effort(e)
        url = (e.get("target", {}) or {}).get("application_url", "")
        age_str = f"{item['age_days']}d" if item["age_days"] is not None else "n/a"

        # Deadline info
        dl = e.get("deadline", {})
        dl_date = dl.get("date", "") if isinstance(dl, dict) else ""
        dl_str = str(dl_date)[:10] if dl_date else "rolling"

        print(f"  {i:3}. {name}")
        print(
            f"       {org:<22} track={track:<12} effort={effort:<10} "
            f"age={age_str}"
        )
        print(
            f"       base={item['base_score']:.1f}  decay={item['decay_score']:.1f}  "
            f"deadline={dl_str}"
        )
        if url:
            print(f"       {url}")
        print()

    print(f"{'=' * 70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Intelligent triage of pipeline entries using time-decay scoring"
    )
    parser.add_argument("--top", type=int, metavar="N",
                        help="Show top N opportunities (default: 20)")
    parser.add_argument("--archive", action="store_true",
                        help="Auto-archive low-scoring entries")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview archive actions without executing")
    parser.add_argument("--yes", action="store_true",
                        help="Execute archive actions")
    parser.add_argument("--threshold", type=float, default=3.0,
                        help="Archive threshold score (default: 3.0)")
    args = parser.parse_args()

    # Load entries from both active/ and research_pool/ for full picture
    entries = load_entries(
        dirs=[PIPELINE_DIR_ACTIVE, PIPELINE_DIR_RESEARCH_POOL],
        include_filepath=True,
    )

    # Filter to actionable statuses only
    entries = [e for e in entries if e.get("status") in ACTIONABLE_STATUSES]

    if not entries:
        print("No actionable entries found.")
        return

    if args.top:
        show_top_opportunities(entries, n=args.top)
        return

    if args.archive:
        dry_run = not args.yes or args.dry_run
        auto_archive(entries, threshold=args.threshold, dry_run=dry_run)
        return

    # Default: full triage report
    result = triage_entries(entries, archive_threshold=args.threshold)
    result["_threshold"] = args.threshold
    show_triage_report(result)


if __name__ == "__main__":
    main()
