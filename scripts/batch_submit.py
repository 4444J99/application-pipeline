#!/usr/bin/env python3
"""Batch-process staged entries with rolling deadlines through the submission pipeline.

Runs preflight check -> checklist -> record submission for each candidate.
Filters to staged entries with rolling deadlines, sorted by readiness and
fit score, so the highest-value submissions go first.

Usage:
    python scripts/batch_submit.py                      # Dry-run preview of batch candidates
    python scripts/batch_submit.py --yes                 # Execute batch submission
    python scripts/batch_submit.py --limit 5             # Process top 5 only
    python scripts/batch_submit.py --min-readiness 4     # Require readiness >= 4
    python scripts/batch_submit.py --report              # Detailed candidate report
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    get_score,
    load_entries,
)
from preflight import check_entry, readiness_score
from submit import record_submission

# --- Candidate selection ---


def get_batch_candidates(min_readiness: int = 3) -> list[dict]:
    """Find staged entries with rolling deadlines that meet the readiness threshold.

    Loads active pipeline entries, filters to status=staged with rolling or
    no-deadline entries, computes readiness scores, and returns candidates
    sorted by readiness (desc) then fit score (desc).

    Args:
        min_readiness: Minimum readiness_score (0-5) to include. Default 3.

    Returns:
        List of entry dicts, each with _filepath from load_entries.
    """
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE], include_filepath=True)

    candidates = []
    for entry in entries:
        # Must be staged
        if entry.get("status") != "staged":
            continue

        # Must be rolling deadline (type == "rolling" or no deadline date)
        deadline = entry.get("deadline", {})
        if not isinstance(deadline, dict):
            deadline = {}
        dl_type = deadline.get("type", "")
        dl_date = deadline.get("date")

        if dl_type != "rolling" and dl_date is not None:
            continue

        # Must meet readiness threshold
        rscore = readiness_score(entry)
        if rscore < min_readiness:
            continue

        entry["_readiness"] = rscore
        candidates.append(entry)

    # Sort by readiness desc, then fit score desc
    candidates.sort(key=lambda e: (-e.get("_readiness", 0), -get_score(e)))

    return candidates


# --- Validation ---


def validate_candidate(entry: dict) -> tuple[list[str], list[str]]:
    """Validate a candidate entry for submission readiness.

    Delegates to preflight.check_entry for the full suite of checks.

    Args:
        entry: Pipeline entry dict.

    Returns:
        (errors, warnings) tuple. Errors block submission; warnings are advisory.
    """
    return check_entry(entry)


# --- Processing ---


def process_entry(entry: dict, dry_run: bool = True) -> dict:
    """Process a single entry through the submission pipeline.

    In dry-run mode, validates and reports readiness without submitting.
    In execute mode, calls record_submission to move the entry to submitted/
    and update the conversion log.

    Args:
        entry: Pipeline entry dict (must have _filepath from load_entries).
        dry_run: If True, validate only. If False, execute submission.

    Returns:
        Result dict with keys: id, status ("ready"/"blocked"/"submitted"),
        and optionally errors, warnings, readiness.
    """
    entry_id = entry.get("id", "?")
    errors, warnings = check_entry(entry)

    if errors:
        return {
            "id": entry_id,
            "status": "blocked",
            "errors": errors,
            "warnings": warnings,
        }

    rscore = readiness_score(entry)

    if dry_run:
        return {
            "id": entry_id,
            "status": "ready",
            "readiness": rscore,
            "warnings": warnings,
        }

    # Execute: record the submission
    filepath = entry.get("_filepath")
    if not filepath:
        return {
            "id": entry_id,
            "status": "blocked",
            "errors": ["no _filepath — entry was not loaded with include_filepath=True"],
            "warnings": warnings,
        }

    record_submission(filepath, entry)

    return {
        "id": entry_id,
        "status": "submitted",
        "warnings": warnings,
    }


# --- Batch orchestration ---


def run_batch(
    dry_run: bool = True,
    min_readiness: int = 3,
    limit: int | None = None,
) -> list[dict]:
    """Run the batch submission pipeline on all eligible candidates.

    Args:
        dry_run: If True, validate only. If False, execute submissions.
        min_readiness: Minimum readiness score threshold.
        limit: Max number of entries to process. None = all.

    Returns:
        List of result dicts from process_entry.
    """
    candidates = get_batch_candidates(min_readiness=min_readiness)

    if limit is not None:
        candidates = candidates[:limit]

    if not candidates:
        print("No batch candidates found.")
        return []

    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"BATCH SUBMIT ({mode}): {len(candidates)} candidate(s)")
    print("=" * 60)

    results = []
    for entry in candidates:
        result = process_entry(entry, dry_run=dry_run)
        results.append(result)

        entry_id = result["id"]
        status = result["status"]
        name = entry.get("name", entry_id)

        if status == "blocked":
            error_count = len(result.get("errors", []))
            print(f"  x {name} — BLOCKED ({error_count} error(s))")
            for err in result.get("errors", []):
                print(f"      [ERROR] {err}")
        elif status == "ready":
            rscore = result.get("readiness", 0)
            print(f"  - {name} — READY [{rscore}/5]")
            for warn in result.get("warnings", []):
                print(f"      [WARN] {warn}")
        elif status == "submitted":
            print(f"  + {name} — SUBMITTED")
            for warn in result.get("warnings", []):
                print(f"      [WARN] {warn}")

    # Summary
    submitted = sum(1 for r in results if r["status"] == "submitted")
    blocked = sum(1 for r in results if r["status"] == "blocked")
    ready = sum(1 for r in results if r["status"] == "ready")

    print("=" * 60)
    if dry_run:
        print(f"Summary: {ready} ready, {blocked} blocked (dry-run — nothing submitted)")
    else:
        print(f"Summary: {submitted} submitted, {blocked} blocked")

    return results


# --- Reporting ---


READINESS_LABELS = {
    5: "full",
    4: "high",
    3: "adequate",
}


def show_batch_report(candidates: list[dict]) -> None:
    """Print a formatted report of batch candidates grouped by readiness level.

    For each candidate: name, organization, fit score, readiness, track,
    deadline info, and application URL.

    Args:
        candidates: List of entry dicts (with _readiness already computed).
    """
    if not candidates:
        print("No candidates found for batch submission.")
        return

    print(f"BATCH CANDIDATES: {len(candidates)} entries")
    print("=" * 60)

    # Group by readiness level
    groups: dict[int, list[dict]] = {}
    for entry in candidates:
        rscore = entry.get("_readiness", readiness_score(entry))
        groups.setdefault(rscore, []).append(entry)

    for level in sorted(groups.keys(), reverse=True):
        label = READINESS_LABELS.get(level, f"level-{level}")
        entries = groups[level]
        print(f"\n  [{level}/5] {label.upper()} ({len(entries)} entries)")
        print(f"  {'-' * 56}")

        for entry in entries:
            entry_id = entry.get("id", "?")
            name = entry.get("name", entry_id)
            target = entry.get("target", {})
            org = target.get("organization", "—") if isinstance(target, dict) else "—"
            app_url = target.get("application_url", "") if isinstance(target, dict) else ""
            track = entry.get("track", "—")
            score = get_score(entry)

            deadline = entry.get("deadline", {})
            if isinstance(deadline, dict):
                dl_type = deadline.get("type", "—")
            else:
                dl_type = "—"

            print(f"    {name}")
            print(f"      Org: {org} | Track: {track} | Score: {score:.1f} | Deadline: {dl_type}")
            if app_url:
                print(f"      URL: {app_url}")

    print()


# --- CLI ---


def main():
    parser = argparse.ArgumentParser(
        description="Batch-process staged entries with rolling deadlines through submission pipeline"
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Execute batch submission (default is dry-run preview)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Maximum number of entries to process"
    )
    parser.add_argument(
        "--min-readiness", type=int, default=3,
        help="Minimum readiness score (0-5, default: 3)"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Show detailed candidate report instead of processing"
    )
    args = parser.parse_args()

    if args.report:
        candidates = get_batch_candidates(min_readiness=args.min_readiness)
        show_batch_report(candidates)
    else:
        dry_run = not args.yes
        run_batch(dry_run=dry_run, min_readiness=args.min_readiness, limit=args.limit)


if __name__ == "__main__":
    main()
