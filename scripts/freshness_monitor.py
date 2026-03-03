#!/usr/bin/env python3
"""Entry freshness monitor — age-based categorization and URL liveness checking.

Monitors entry freshness by computing posting age, categorizing entries into
freshness tiers, and optionally checking whether application URLs are still live.

For job-track entries, uses hour-based thresholds (24/48/72h) from pipeline_lib.
For all other tracks, uses day-based thresholds (14/30/60d).

Usage:
    python scripts/freshness_monitor.py                          # Freshness report (no HTTP)
    python scripts/freshness_monitor.py --check-urls             # Check URLs (HTTP HEAD, limit 20)
    python scripts/freshness_monitor.py --check-urls --limit 50  # Larger batch
    python scripts/freshness_monitor.py --stale-only             # Show only stale/expired
    python scripts/freshness_monitor.py --auto-expire-jobs       # Expire stale job postings (dry-run)
    python scripts/freshness_monitor.py --auto-expire-jobs --yes # Execute expiration
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_CLOSED,
    PIPELINE_DIR_RESEARCH_POOL,
    SIGNALS_DIR,
    get_freshness_tier,  # noqa: F401 — imported per freshness system API contract
    get_posting_age_hours,
    load_entries,
    parse_date,
    update_last_touched,
    update_yaml_field,
)

HTTP_TIMEOUT = 10
USER_AGENT = "application-pipeline/freshness-monitor/1.0"

FRESHNESS_CHECK_FILE = SIGNALS_DIR / "freshness-last-check.txt"

# Age thresholds in days (for non-job tracks)
FRESH_MAX = 14
AGING_MAX = 30
STALE_MAX = 60

# Job-track hour thresholds (imported from pipeline_lib via get_freshness_tier)
JOB_FRESH_HOURS = 24
JOB_AGING_HOURS = 48
JOB_STALE_HOURS = 72

# Only auto-expire entries whose date_added is on or after this date.
# Grandfathers existing entries added before this date.
DEFAULT_FRESHNESS_POLICY_START_DATE = "2026-03-04"


# ---------------------------------------------------------------------------
# URL liveness check
# ---------------------------------------------------------------------------

def check_url_liveness(url: str, timeout: int = HTTP_TIMEOUT) -> dict:
    """Send HTTP HEAD request to a URL and return liveness status.

    Returns:
        {"url": str, "status": "live"|"dead"|"redirect"|"error",
         "code": int|None, "detail": str}
    """
    if not url:
        return {"url": url, "status": "error", "code": None, "detail": "empty URL"}
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            if code and 200 <= code < 300:
                return {"url": url, "status": "live", "code": code, "detail": "OK"}
            return {"url": url, "status": "error", "code": code, "detail": f"HTTP {code}"}
    except HTTPError as e:
        code = e.code
        if code in (301, 302, 303, 307, 308):
            location = e.headers.get("Location", "unknown")
            return {"url": url, "status": "redirect", "code": code, "detail": f"redirect to {location}"}
        if code in (403, 404, 410):
            return {"url": url, "status": "dead", "code": code, "detail": f"HTTP {code}"}
        return {"url": url, "status": "error", "code": code, "detail": f"HTTP {code}"}
    except (URLError, TimeoutError, OSError) as e:
        return {"url": url, "status": "error", "code": None, "detail": str(e)}


# ---------------------------------------------------------------------------
# Entry filtering
# ---------------------------------------------------------------------------

def get_entries_with_urls(entries: list[dict] | None = None) -> list[dict]:
    """Return entries that have a non-empty application URL and actionable status.

    If entries is None, loads from active and research_pool directories.
    """
    if entries is None:
        entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE, PIPELINE_DIR_RESEARCH_POOL])

    result = []
    for entry in entries:
        status = entry.get("status", "")
        if status not in ACTIONABLE_STATUSES:
            continue
        target = entry.get("target", {})
        if not isinstance(target, dict):
            continue
        url = target.get("application_url", "")
        if url:
            result.append(entry)
    return result


# ---------------------------------------------------------------------------
# ATS posting check
# ---------------------------------------------------------------------------

def check_ats_posting(entry: dict) -> dict:
    """Check whether an ATS posting is still active.

    For Greenhouse and Lever entries, checks the appropriate API endpoint.
    For other portals, falls back to URL liveness check.

    Returns:
        {"entry_id": str, "portal": str,
         "status": "active"|"closed"|"unknown"|"error", "detail": str}
    """
    entry_id = entry.get("id", "?")
    target = entry.get("target", {})
    portal = target.get("portal", "unknown") if isinstance(target, dict) else "unknown"
    url = target.get("application_url", "") if isinstance(target, dict) else ""

    if not url:
        return {"entry_id": entry_id, "portal": portal, "status": "error", "detail": "no URL"}

    if portal == "greenhouse" and "greenhouse.io" in url:
        return _check_greenhouse_posting(entry_id, url, portal)
    if portal == "lever" and "lever.co" in url:
        return _check_lever_posting(entry_id, url, portal)

    # Fallback: generic URL liveness
    result = check_url_liveness(url)
    if result["status"] == "live":
        return {"entry_id": entry_id, "portal": portal, "status": "active", "detail": "URL live"}
    if result["status"] == "dead":
        return {"entry_id": entry_id, "portal": portal, "status": "closed", "detail": result["detail"]}
    return {"entry_id": entry_id, "portal": portal, "status": "unknown", "detail": result["detail"]}


def _check_greenhouse_posting(entry_id: str, url: str, portal: str) -> dict:
    """Check Greenhouse job board API for posting status."""
    # Extract board token and job ID from URL patterns like:
    # https://boards.greenhouse.io/company/jobs/12345
    # https://job-boards.greenhouse.io/company/jobs/12345
    try:
        parts = url.rstrip("/").split("/")
        job_id = parts[-1]
        # Find company token (the segment before "jobs")
        jobs_idx = parts.index("jobs")
        board_token = parts[jobs_idx - 1]
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
        req = Request(api_url, method="GET", headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            if resp.getcode() == 200:
                return {"entry_id": entry_id, "portal": portal, "status": "active", "detail": "posting live"}
    except HTTPError as e:
        if e.code == 404:
            return {"entry_id": entry_id, "portal": portal, "status": "closed", "detail": "posting not found (404)"}
        return {"entry_id": entry_id, "portal": portal, "status": "error", "detail": f"HTTP {e.code}"}
    except (URLError, TimeoutError, OSError, ValueError, IndexError) as e:
        return {"entry_id": entry_id, "portal": portal, "status": "error", "detail": str(e)}
    return {"entry_id": entry_id, "portal": portal, "status": "unknown", "detail": "unexpected state"}


def _check_lever_posting(entry_id: str, url: str, portal: str) -> dict:
    """Check Lever posting by URL liveness (Lever has no public board API)."""
    result = check_url_liveness(url)
    if result["status"] == "live":
        return {"entry_id": entry_id, "portal": portal, "status": "active", "detail": "posting live"}
    if result["status"] == "dead":
        return {"entry_id": entry_id, "portal": portal, "status": "closed", "detail": result["detail"]}
    return {"entry_id": entry_id, "portal": portal, "status": "unknown", "detail": result["detail"]}


# ---------------------------------------------------------------------------
# Freshness computation
# ---------------------------------------------------------------------------

def _get_entry_age_days(entry: dict) -> int | None:
    """Compute age in days from posting_date or date_added."""
    timeline = entry.get("timeline", {})
    if not isinstance(timeline, dict):
        return None

    d = parse_date(timeline.get("posting_date")) or parse_date(timeline.get("date_added"))
    if d is None:
        return None
    return (date.today() - d).days


def _categorize_age(age_days: int | None) -> str:
    """Map age in days to a freshness category (for non-job tracks)."""
    if age_days is None:
        return "unknown"
    if age_days < FRESH_MAX:
        return "fresh"
    if age_days <= AGING_MAX:
        return "aging"
    if age_days <= STALE_MAX:
        return "stale"
    return "expired"


def _categorize_job_age_hours(age_hours: float | None) -> str:
    """Map age in hours to a freshness category for job-track entries."""
    if age_hours is None:
        return "unknown"
    if age_hours <= JOB_FRESH_HOURS:
        return "fresh"
    if age_hours <= JOB_AGING_HOURS:
        return "aging"
    if age_hours <= JOB_STALE_HOURS:
        return "stale"
    return "expired"


def _categorize_entry(entry: dict) -> tuple[str, int | None, float | None]:
    """Categorize an entry using track-aware thresholds.

    For job-track entries, uses hour-based thresholds.
    For all other tracks, uses day-based thresholds.

    Returns:
        (category, age_days, age_hours) — age_hours is only populated for job entries.
    """
    track = entry.get("track", "")
    if track == "job":
        age_hours = get_posting_age_hours(entry)
        category = _categorize_job_age_hours(age_hours)
        age_days = int(age_hours / 24.0) if age_hours is not None else None
        return category, age_days, age_hours
    else:
        age_days = _get_entry_age_days(entry)
        category = _categorize_age(age_days)
        return category, age_days, None


def compute_freshness_report(entries: list[dict] | None = None) -> dict:
    """Compute freshness report categorizing entries by posting age.

    Uses track-aware thresholds: hour-based for job entries, day-based for others.

    Returns:
        {"fresh": list, "aging": list, "stale": list, "expired": list,
         "unknown": list, "total": int}
        Each item: {"entry_id": str, "name": str, "age_days": int|None,
                     "age_hours": float|None, "track": str, "url": str, "portal": str}
    """
    url_entries = get_entries_with_urls(entries)

    categories: dict[str, list[dict]] = {
        "fresh": [],
        "aging": [],
        "stale": [],
        "expired": [],
        "unknown": [],
    }

    for entry in url_entries:
        category, age_days, age_hours = _categorize_entry(entry)
        target = entry.get("target", {})
        item = {
            "entry_id": entry.get("id", "?"),
            "name": entry.get("name", entry.get("id", "?")),
            "age_days": age_days,
            "age_hours": age_hours,
            "track": entry.get("track", ""),
            "url": target.get("application_url", "") if isinstance(target, dict) else "",
            "portal": target.get("portal", "unknown") if isinstance(target, dict) else "unknown",
        }
        categories[category].append(item)

    categories["total"] = sum(len(v) for v in categories.values() if isinstance(v, list))
    return categories


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

_CATEGORY_LABELS = {
    "fresh": ("Fresh (< 14 days)", ""),
    "aging": ("Aging (14-30 days)", " -- consider prioritizing"),
    "stale": ("Stale (30-60 days)", " -- re-verify or archive"),
    "expired": ("Expired (> 60 days)", " -- strongly recommend archiving"),
    "unknown": ("Unknown age", " -- missing posting_date / date_added"),
}


def show_freshness_report(report: dict, stale_only: bool = False) -> None:
    """Print formatted freshness report to stdout."""
    total = report.get("total", 0)
    print(f"\n{'='*60}")
    print(f"  ENTRY FRESHNESS REPORT  ({total} entries)")
    print(f"{'='*60}\n")

    categories_to_show = ["fresh", "aging", "stale", "expired", "unknown"]
    if stale_only:
        categories_to_show = ["stale", "expired"]

    for cat in categories_to_show:
        items = report.get(cat, [])
        label, note = _CATEGORY_LABELS.get(cat, (cat, ""))
        print(f"  {label}: {len(items)}{note}")

        if items:
            # Sort by age descending (oldest first), unknowns at end
            sorted_items = sorted(items, key=lambda x: x.get("age_days") or 0, reverse=True)
            for item in sorted_items:
                # Show hour-based age for job entries, day-based for others
                if item.get("track") == "job" and item.get("age_hours") is not None:
                    hours = item["age_hours"]
                    if hours < 1:
                        age_str = "<1h"
                    elif hours < 24:
                        age_str = f"{int(hours)}h"
                    else:
                        age_str = f"{int(hours)}h ({item['age_days']}d)"
                elif item["age_days"] is not None:
                    age_str = f"{item['age_days']}d"
                else:
                    age_str = "??d"
                track_tag = f" [{item['track']}]" if item.get("track") == "job" else ""
                print(f"    [{age_str:>10}] {item['entry_id']}{track_tag}")
                print(f"               {item['url']}")
        print()

    # Summary line
    stale_count = len(report.get("stale", []))
    expired_count = len(report.get("expired", []))
    if stale_count + expired_count > 0:
        print(f"  ACTION NEEDED: {stale_count} stale + {expired_count} expired entries")
        print("  Run: python scripts/hygiene.py --auto-expire --dry-run")
    else:
        print("  All entries within freshness thresholds.")
    print()


# ---------------------------------------------------------------------------
# Batch URL checking
# ---------------------------------------------------------------------------

def check_urls_batch(entries: list[dict] | None = None, limit: int = 20) -> list[dict]:
    """Check URLs for up to `limit` entries, oldest first.

    This is the expensive operation — makes HTTP HEAD requests.

    Returns:
        List of check result dicts from check_url_liveness.
    """
    url_entries = get_entries_with_urls(entries)

    # Sort by age descending (oldest first) to prioritize stale entries
    def _sort_key(entry):
        age = _get_entry_age_days(entry)
        return age if age is not None else -1

    url_entries.sort(key=_sort_key, reverse=True)
    batch = url_entries[:limit]

    results = []
    print(f"Checking {len(batch)} URLs (oldest first)...\n")
    for entry in batch:
        entry_id = entry.get("id", "?")
        target = entry.get("target", {})
        url = target.get("application_url", "") if isinstance(target, dict) else ""

        result = check_url_liveness(url)
        result["entry_id"] = entry_id
        results.append(result)

        status_label = result["status"].upper()
        code_str = f" ({result['code']})" if result["code"] else ""
        print(f"  [{status_label:>8}] {entry_id}{code_str}")

    print(f"\nChecked {len(results)} URLs.")
    live = sum(1 for r in results if r["status"] == "live")
    dead = sum(1 for r in results if r["status"] == "dead")
    errors = len(results) - live - dead
    print(f"  Live: {live}  Dead: {dead}  Other: {errors}")

    return results


# ---------------------------------------------------------------------------
# Auto-expire stale job postings
# ---------------------------------------------------------------------------

def _get_job_entries_for_expiry(
    policy_start_date: str = DEFAULT_FRESHNESS_POLICY_START_DATE,
) -> list[dict]:
    """Find job-track entries in active/ eligible for auto-expiry.

    Criteria:
      - track == "job"
      - status in ACTIONABLE_STATUSES (research, qualified, drafting, staged)
      - posting age > 72 hours
      - date_added >= freshness_policy_start_date (grandfathers older entries)
      - last_touched NOT within 24 hours (human override)

    Returns list of dicts with entry metadata and filepath.
    """
    entries = load_entries(
        dirs=[PIPELINE_DIR_ACTIVE, PIPELINE_DIR_RESEARCH_POOL],
        include_filepath=True,
    )

    policy_date = parse_date(policy_start_date)
    candidates = []

    for entry in entries:
        # Must be job track
        if entry.get("track") != "job":
            continue

        # Must be in an actionable status
        status = entry.get("status", "")
        if status not in ACTIONABLE_STATUSES:
            continue

        # Check posting age
        age_hours = get_posting_age_hours(entry)
        if age_hours is None or age_hours <= JOB_STALE_HOURS:
            continue

        # Grandfather: only expire entries added on or after policy start date
        timeline = entry.get("timeline", {})
        if isinstance(timeline, dict):
            date_added = parse_date(timeline.get("date_added"))
        else:
            date_added = None
        if date_added and policy_date and date_added < policy_date:
            continue

        # Human override: skip if last_touched within 24 hours
        last_touched = parse_date(entry.get("last_touched"))
        if last_touched is not None:
            days_since_touch = (date.today() - last_touched).days
            if days_since_touch < 1:
                continue

        candidates.append({
            "id": entry.get("id", "?"),
            "name": entry.get("name", "?"),
            "status": status,
            "age_hours": age_hours,
            "date_added": date_added.isoformat() if date_added else "?",
            "_filepath": entry.get("_filepath"),
        })

    return candidates


def _expire_job_entry(filepath: Path) -> bool:
    """Move a job entry to closed/ with outcome=expired and outcome_stage=posting_stale.

    Returns True on success, False on failure.
    """
    if not filepath or not filepath.exists():
        print(f"  WARNING: File not found: {filepath}", file=sys.stderr)
        return False

    content = filepath.read_text()
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        print(f"  WARNING: Invalid YAML in {filepath.name}", file=sys.stderr)
        return False

    # Guard: only expire actionable entries
    if data.get("status") not in ACTIONABLE_STATUSES:
        print(f"  WARNING: Skipping {filepath.stem} -- status '{data.get('status')}' not actionable",
              file=sys.stderr)
        return False

    # Update status to outcome
    content = update_yaml_field(content, "status", "outcome")

    # Update outcome to expired
    try:
        content = update_yaml_field(content, "outcome", "expired")
    except ValueError:
        # outcome field might be 'null' -- try regex
        content = re.sub(
            r'^(outcome:)\s+.*$', r'\1 expired',
            content, count=1, flags=re.MULTILINE,
        )

    # Add conversion.outcome_stage if conversion block exists
    try:
        content = update_yaml_field(
            content, "outcome_stage", "posting_stale",
            nested=True, parent_key="conversion",
        )
    except ValueError:
        # outcome_stage field might not exist -- append to conversion block
        conversion_pattern = re.compile(r'^(conversion:\s*)$', re.MULTILINE)
        match = conversion_pattern.search(content)
        if match:
            insert_pos = match.end()
            # Find indentation of next line in the block
            next_line_match = re.search(r'\n([ \t]+)', content[insert_pos:])
            indent = next_line_match.group(1) if next_line_match else "  "
            content = content[:insert_pos] + f"\n{indent}outcome_stage: posting_stale" + content[insert_pos:]

    content = update_last_touched(content)

    # Verify YAML is still valid
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        print(f"  WARNING: YAML invalid after editing {filepath.stem}: {e}", file=sys.stderr)
        return False

    # Move to closed/
    PIPELINE_DIR_CLOSED.mkdir(parents=True, exist_ok=True)
    dest = PIPELINE_DIR_CLOSED / filepath.name
    dest.write_text(content)
    filepath.unlink()
    return True


def run_auto_expire_jobs(
    dry_run: bool = True,
    policy_start_date: str = DEFAULT_FRESHNESS_POLICY_START_DATE,
) -> list[dict]:
    """Find and expire stale job-track entries.

    Args:
        dry_run: If True, print what would be expired without making changes.
        policy_start_date: Only expire entries added on or after this date.

    Returns:
        List of expired entry metadata dicts.
    """
    candidates = _get_job_entries_for_expiry(policy_start_date=policy_start_date)

    if not candidates:
        print("No stale job entries eligible for auto-expiry.")
        print(f"  (policy start date: {policy_start_date})")
        return []

    print(f"Stale job entries eligible for auto-expiry ({len(candidates)}):")
    print(f"  (policy: only entries added >= {policy_start_date}, posting age > {JOB_STALE_HOURS}h)\n")

    expired = []
    for item in candidates:
        age_str = f"{int(item['age_hours'])}h"
        action = "[dry-run]" if dry_run else "[expiring]"
        print(f"  {action} {item['id']}")
        print(f"          status={item['status']}  age={age_str}  added={item['date_added']}")

        if not dry_run:
            if _expire_job_entry(item["_filepath"]):
                expired.append(item)
            else:
                print("          FAILED to expire")
        else:
            expired.append(item)

    print()
    if dry_run:
        print(f"Would expire {len(expired)} entries. Run with --yes to execute.")
    else:
        print(f"Expired {len(expired)} entries to pipeline/closed/")

    return expired


# ---------------------------------------------------------------------------
# Weekly check gating
# ---------------------------------------------------------------------------

def should_run_weekly_check(check_file: Path | None = None) -> bool:
    """Return True if no freshness check has been recorded in the last 7 days.

    Args:
        check_file: Path to the check timestamp file. Defaults to
            signals/freshness-last-check.txt.
    """
    path = check_file or FRESHNESS_CHECK_FILE
    if not path.exists():
        return True
    try:
        content = path.read_text().strip()
        last_check = parse_date(content)
        if last_check is None:
            return True
        return (date.today() - last_check).days >= 7
    except (OSError, ValueError):
        return True


def record_check_run(check_file: Path | None = None) -> None:
    """Write today's date to the freshness check file."""
    path = check_file or FRESHNESS_CHECK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(date.today().isoformat() + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Entry freshness monitor — age categorization and URL liveness checking."
    )
    parser.add_argument(
        "--check-urls", action="store_true",
        help="Check application URLs via HTTP HEAD (expensive).",
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Max URLs to check (default: 20). Only used with --check-urls.",
    )
    parser.add_argument(
        "--stale-only", action="store_true",
        help="Show only stale and expired entries.",
    )
    parser.add_argument(
        "--auto-expire-jobs", action="store_true",
        help="Expire job-track entries with posting age >72h (dry-run by default).",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Execute changes (required for --auto-expire-jobs).",
    )
    parser.add_argument(
        "--policy-start-date", type=str, default=DEFAULT_FRESHNESS_POLICY_START_DATE,
        help=f"Only expire entries added on or after this date (default: {DEFAULT_FRESHNESS_POLICY_START_DATE}).",
    )
    args = parser.parse_args()

    if args.auto_expire_jobs:
        print(f"\n{'='*60}")
        print("  AUTO-EXPIRE STALE JOB POSTINGS")
        print(f"{'='*60}\n")
        dry_run = not args.yes
        run_auto_expire_jobs(dry_run=dry_run, policy_start_date=args.policy_start_date)
        return

    report = compute_freshness_report()
    show_freshness_report(report, stale_only=args.stale_only)

    if args.check_urls:
        print(f"\n{'='*60}")
        print("  URL LIVENESS CHECK")
        print(f"{'='*60}\n")
        check_urls_batch(limit=args.limit)
        record_check_run()
        print(f"\n  Recorded check timestamp to {FRESHNESS_CHECK_FILE.name}")


if __name__ == "__main__":
    main()
