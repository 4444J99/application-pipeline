#!/usr/bin/env python3
"""Daily job pipeline orchestrator.

DEPRECATED: Use `python scripts/standup.py --jobs` for job pipeline status,
and `python scripts/campaign.py --execute` for pipeline execution.

Chains: source → score → qualify → alchemize → queue.
Automates the daily cadence of finding, evaluating, and processing job applications.

Usage:
    python scripts/daily_pipeline.py                    # Full daily pipeline
    python scripts/daily_pipeline.py --source-only      # Just find new jobs
    python scripts/daily_pipeline.py --score-only       # Just re-score all entries
    python scripts/daily_pipeline.py --queue            # Show ready-to-submit entries
    python scripts/daily_pipeline.py --submit --yes     # Submit all staged job entries
"""

import argparse
import subprocess
import sys
import warnings
from datetime import date
from pathlib import Path

import yaml

warnings.warn(
    "daily_pipeline.py is deprecated. Use 'standup.py --jobs' or 'campaign.py --execute' instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    ALL_PIPELINE_DIRS,
    PIPELINE_DIR_ACTIVE,
    load_entries,
    get_score,
    get_effort,
)

SCRIPTS_DIR = Path(__file__).resolve().parent


def run_script(script: str, args: list[str], label: str) -> bool:
    """Run a pipeline script as a subprocess.

    Returns True if script exited successfully.
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"  $ python scripts/{script} {' '.join(args)}")
    print(f"{'─' * 60}")

    result = subprocess.run(cmd, cwd=SCRIPTS_DIR.parent)
    if result.returncode != 0:
        print(f"  [WARN] {script} exited with code {result.returncode}")
        return False
    return True


def phase_source(dry_run: bool = False, limit: int = 0) -> bool:
    """Phase 1: Source new job postings from ATS APIs."""
    print("\n" + "=" * 60)
    print("PHASE 1: SOURCE NEW JOBS")
    print("=" * 60)

    args = ["--fetch"]
    if dry_run:
        args.append("--dry-run")
    else:
        args.append("--yes")
    if limit:
        args.extend(["--limit", str(limit)])

    return run_script("source_jobs.py", args, "Fetching job postings from ATS APIs")


def phase_score() -> bool:
    """Phase 2: Score all entries (including newly sourced ones)."""
    print("\n" + "=" * 60)
    print("PHASE 2: SCORE ALL ENTRIES")
    print("=" * 60)

    return run_script("score.py", ["--all"], "Re-scoring all pipeline entries")


def phase_qualify() -> bool:
    """Phase 3: Show qualification recommendations."""
    print("\n" + "=" * 60)
    print("PHASE 3: QUALIFICATION GATE")
    print("=" * 60)

    return run_script("score.py", ["--qualify"], "Showing APPLY/SKIP recommendations")


def phase_alchemize_queue():
    """Phase 4: Show alchemize commands for qualified job entries."""
    print("\n" + "=" * 60)
    print("PHASE 4: ALCHEMIZE QUEUE")
    print("=" * 60)

    entries = load_entries()
    job_entries = [
        e for e in entries
        if e.get("track") == "job"
        and e.get("status") in ("qualified", "drafting")
    ]

    if not job_entries:
        print("\n  No qualified/drafting job entries to alchemize.")
        return

    job_entries.sort(key=lambda e: get_score(e), reverse=True)

    print(f"\n  {len(job_entries)} job entries ready for alchemize:")
    for e in job_entries:
        entry_id = e.get("id", "?")
        name = e.get("name", entry_id)
        score = get_score(e)
        status = e.get("status", "?")
        print(f"\n  [{score:.1f}] {name} ({status})")
        print(f"    python scripts/alchemize.py --target {entry_id}")
        print(f"    # After generating output.md:")
        print(f"    python scripts/alchemize.py --target {entry_id} --integrate")


def phase_submit_queue():
    """Show staged job entries ready for submission."""
    print("\n" + "=" * 60)
    print("SUBMISSION QUEUE")
    print("=" * 60)

    entries = load_entries()
    staged_jobs = [
        e for e in entries
        if e.get("track") == "job"
        and e.get("status") == "staged"
    ]

    if not staged_jobs:
        print("\n  No staged job entries to submit.")
        return

    staged_jobs.sort(key=lambda e: get_score(e), reverse=True)

    print(f"\n  {len(staged_jobs)} staged job entries ready to submit:")
    for e in staged_jobs:
        entry_id = e.get("id", "?")
        name = e.get("name", entry_id)
        score = get_score(e)
        portal = e.get("target", {}).get("portal", "?")

        submit_script = {
            "greenhouse": "greenhouse_submit.py",
            "lever": "lever_submit.py",
            "ashby": "ashby_submit.py",
        }.get(portal, "submit.py")

        print(f"\n  [{score:.1f}] {name} [{portal}]")
        print(f"    python scripts/{submit_script} --target {entry_id} --submit")


def phase_submit(dry_run: bool = False):
    """Submit all staged job entries."""
    entries = load_entries()
    staged_jobs = [
        e for e in entries
        if e.get("track") == "job"
        and e.get("status") == "staged"
    ]

    if not staged_jobs:
        print("\nNo staged job entries to submit.")
        return

    staged_jobs.sort(key=lambda e: get_score(e), reverse=True)

    for e in staged_jobs:
        entry_id = e.get("id", "?")
        portal = e.get("target", {}).get("portal", "?")

        submit_script = {
            "greenhouse": "greenhouse_submit.py",
            "lever": "lever_submit.py",
            "ashby": "ashby_submit.py",
        }.get(portal)

        if not submit_script:
            print(f"  [SKIP] {entry_id} — no submit script for portal '{portal}'")
            continue

        args = ["--target", entry_id]
        if not dry_run:
            args.append("--submit")

        run_script(submit_script, args, f"Submitting {entry_id} via {portal}")


def main():
    parser = argparse.ArgumentParser(
        description="Daily job pipeline orchestrator"
    )
    parser.add_argument("--source-only", action="store_true",
                        help="Only run the job sourcing phase")
    parser.add_argument("--score-only", action="store_true",
                        help="Only run the scoring phase")
    parser.add_argument("--queue", action="store_true",
                        help="Show ready-to-submit entries")
    parser.add_argument("--submit", action="store_true",
                        help="Submit all staged job entries")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without making changes")
    parser.add_argument("--yes", action="store_true",
                        help="Confirm execution (required for writes)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of new entries sourced")
    args = parser.parse_args()

    today = date.today()
    print("=" * 60)
    print(f"DAILY JOB PIPELINE — {today.strftime('%A, %B %d, %Y')}")
    print("=" * 60)

    if args.source_only:
        phase_source(dry_run=args.dry_run or not args.yes, limit=args.limit)
        return

    if args.score_only:
        phase_score()
        return

    if args.queue:
        phase_submit_queue()
        return

    if args.submit:
        if not args.yes and not args.dry_run:
            print("Use --yes to confirm submission or --dry-run to preview.")
            sys.exit(1)
        phase_submit(dry_run=args.dry_run)
        return

    # Full pipeline
    phase_source(dry_run=args.dry_run or not args.yes, limit=args.limit)
    phase_score()
    phase_qualify()
    phase_alchemize_queue()
    phase_submit_queue()

    print("\n" + "=" * 60)
    print("DAILY PIPELINE COMPLETE")
    print("=" * 60)
    print("\nNext manual steps:")
    print("  1. Review alchemize queue above")
    print("  2. Run alchemize for each qualified entry")
    print("  3. Generate output.md via Claude, then --integrate")
    print("  4. python scripts/daily_pipeline.py --submit --yes")


if __name__ == "__main__":
    main()
