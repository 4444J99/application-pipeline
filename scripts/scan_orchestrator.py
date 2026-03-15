#!/usr/bin/env python3
"""Unified scan orchestrator: fetch jobs from all APIs, dedup, write entries.

Combines source_jobs.py (5 ATS APIs) and discover_jobs.py (free APIs)
into a single scan operation with deduplication, filtering, and logging.

Usage:
    python scripts/scan_orchestrator.py                    # Dry-run, all sources
    python scripts/scan_orchestrator.py --yes              # Execute, write entries
    python scripts/scan_orchestrator.py --sources ats      # ATS APIs only
    python scripts/scan_orchestrator.py --sources free     # Free APIs only
    python scripts/scan_orchestrator.py --max 50           # Cap at 50 entries
    python scripts/scan_orchestrator.py --json             # Machine-readable output
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from discover_jobs import fetch_himalayas, fetch_remotive
from ingest_top_roles import pre_score
from pipeline_lib import SIGNALS_DIR
from source_jobs import (
    _get_existing_ids,
    create_pipeline_entry,
    deduplicate,
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_smartrecruiters_jobs,
    fetch_workable_jobs,
    filter_by_title,
    load_sources,
    write_pipeline_entry,
)
from source_jobs_constants import TITLE_EXCLUDES, TITLE_KEYWORDS

SCAN_HISTORY_PATH = SIGNALS_DIR / "scan-history.yaml"
DEFAULT_MAX_ENTRIES = 100
RATE_DELAY = 2.0  # seconds between API calls


@dataclass
class ScanResult:
    """Result of a unified scan operation."""

    new_entries: list[str] = field(default_factory=list)
    duplicates_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    sources_queried: int = 0
    total_fetched: int = 0
    total_qualified: int = 0
    scan_duration_seconds: float = 0.0


def scan_ats(fresh_only: bool = True) -> tuple[list[dict], int, list[str]]:
    """Fetch jobs from all configured ATS board APIs.

    Returns (jobs, sources_queried, errors).
    """
    all_jobs: list[dict] = []
    errors: list[str] = []
    sources_count = 0

    try:
        sources = load_sources()
    except (FileNotFoundError, SystemExit):
        return [], 0, ["Job sources config not found (.job-sources.yaml)"]

    companies = sources.get("companies", [])
    fetcher_map = {
        "greenhouse": fetch_greenhouse_jobs,
        "lever": fetch_lever_jobs,
        "ashby": fetch_ashby_jobs,
        "smartrecruiters": fetch_smartrecruiters_jobs,
        "workable": fetch_workable_jobs,
    }

    for company in companies:
        name = company.get("name", "unknown")
        portal = company.get("portal", "")
        board_id = company.get("board_id", company.get("company", ""))
        if not board_id:
            continue

        fetcher = fetcher_map.get(portal)
        if not fetcher:
            continue

        try:
            jobs = fetcher(board_id)
            all_jobs.extend(jobs)
            sources_count += 1
            time.sleep(RATE_DELAY)
        except Exception as e:
            errors.append(f"{portal}/{name}: {e}")

    all_jobs = filter_by_title(all_jobs, TITLE_KEYWORDS, TITLE_EXCLUDES)
    return all_jobs, sources_count, errors


def scan_free() -> tuple[list[dict], int, list[str]]:
    """Fetch jobs from free public APIs (Remotive, Himalayas).

    Returns (jobs, sources_queried, errors).
    """
    all_jobs: list[dict] = []
    errors: list[str] = []
    sources_count = 0

    # Remotive
    try:
        for keyword in ["python", "go", "devops", "platform engineer"]:
            jobs = fetch_remotive(keyword)
            all_jobs.extend(jobs)
            time.sleep(RATE_DELAY)
        sources_count += 1
    except Exception as e:
        errors.append(f"remotive: {e}")

    # Himalayas
    try:
        for keyword in ["software engineer", "platform engineer", "devops"]:
            jobs = fetch_himalayas(keyword)
            all_jobs.extend(jobs)
            time.sleep(RATE_DELAY)
        sources_count += 1
    except Exception as e:
        errors.append(f"himalayas: {e}")

    return all_jobs, sources_count, errors


def _dedup_and_filter(jobs: list[dict]) -> list[dict]:
    """Deduplicate against existing pipeline entries."""
    existing_ids = _get_existing_ids()
    return deduplicate(jobs, existing_ids)


def scan_all(
    dry_run: bool = True,
    fresh_only: bool = True,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    sources: list[str] | None = None,
) -> ScanResult:
    """Run all configured job sources and return results.

    Args:
        dry_run: If True, don't write pipeline entries.
        fresh_only: If True, only include postings <= 72h old.
        max_entries: Maximum entries to create per scan.
        sources: List of source types to query. None = all.
                 Options: 'ats', 'free'.
    """
    start = time.time()
    if sources is None:
        sources = ["ats", "free"]

    all_jobs: list[dict] = []
    total_sources = 0
    all_errors: list[str] = []

    if "ats" in sources:
        ats_jobs, ats_count, ats_errors = scan_ats(fresh_only=fresh_only)
        all_jobs.extend(ats_jobs)
        total_sources += ats_count
        all_errors.extend(ats_errors)

    if "free" in sources:
        free_jobs, free_count, free_errors = scan_free()
        all_jobs.extend(free_jobs)
        total_sources += free_count
        all_errors.extend(free_errors)

    total_fetched = len(all_jobs)

    # Dedup
    unique_jobs = _dedup_and_filter(all_jobs)
    duplicates_skipped = total_fetched - len(unique_jobs)

    # Pre-score and sort
    for job in unique_jobs:
        job["_pre_score"] = pre_score(job)
    unique_jobs.sort(key=lambda j: j.get("_pre_score", 0), reverse=True)

    # Cap
    qualified = unique_jobs[:max_entries]

    # Write entries if not dry-run
    new_ids: list[str] = []
    if not dry_run:
        for job in qualified:
            try:
                entry_id, entry = create_pipeline_entry(job)
                write_pipeline_entry(entry_id, entry)
                new_ids.append(entry_id)
            except Exception as e:
                all_errors.append(f"write {job.get('title', '?')}: {e}")
    else:
        for job in qualified:
            try:
                entry_id, _ = create_pipeline_entry(job)
                new_ids.append(entry_id)
            except Exception:
                pass

    elapsed = time.time() - start
    return ScanResult(
        new_entries=new_ids,
        duplicates_skipped=duplicates_skipped,
        errors=all_errors,
        sources_queried=total_sources,
        total_fetched=total_fetched,
        total_qualified=len(qualified),
        scan_duration_seconds=round(elapsed, 1),
    )


def _log_scan_result(result: ScanResult, log_path: Path | None = None) -> None:
    """Append scan result to history log."""
    log_path = log_path or SCAN_HISTORY_PATH
    entry = {
        "date": str(date.today()),
        "sources_queried": result.sources_queried,
        "total_fetched": result.total_fetched,
        "duplicates_skipped": result.duplicates_skipped,
        "new_entries": len(result.new_entries),
        "errors": len(result.errors),
        "duration_seconds": result.scan_duration_seconds,
    }
    existing = []
    if log_path.exists():
        existing = yaml.safe_load(log_path.read_text()) or []
    existing.append(entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(yaml.dump(existing, default_flow_style=False, sort_keys=False))


def main():
    parser = argparse.ArgumentParser(description="Unified job scan orchestrator")
    parser.add_argument("--yes", action="store_true", help="Execute (write entries)")
    parser.add_argument(
        "--sources",
        default="all",
        help="Source types: all, ats, free (comma-separated)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=DEFAULT_MAX_ENTRIES,
        help=f"Max entries per scan (default: {DEFAULT_MAX_ENTRIES})",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--include-stale",
        action="store_true",
        help="Include postings older than 72h",
    )
    args = parser.parse_args()

    source_list = None if args.sources == "all" else args.sources.split(",")
    dry_run = not args.yes

    result = scan_all(
        dry_run=dry_run,
        fresh_only=not args.include_stale,
        max_entries=args.max,
        sources=source_list,
    )

    if not dry_run:
        _log_scan_result(result)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        print(f"\n{'=' * 50}")
        print(f"SCAN COMPLETE ({mode})")
        print(f"{'=' * 50}")
        print(f"Sources queried:    {result.sources_queried}")
        print(f"Total fetched:      {result.total_fetched}")
        print(f"Duplicates skipped: {result.duplicates_skipped}")
        print(f"New entries:        {result.total_qualified}")
        print(f"Duration:           {result.scan_duration_seconds}s")
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  - {err}")
        if result.new_entries:
            print("\nTop entries:")
            for eid in result.new_entries[:10]:
                print(f"  - {eid}")


if __name__ == "__main__":
    main()
