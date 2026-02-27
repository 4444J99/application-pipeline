#!/usr/bin/env python3
"""Entry hygiene: URL liveness, ATS posting verification, auto-expire, and track-specific gates.

Validates entry freshness and data quality beyond schema validation.

Usage:
    python scripts/hygiene.py                    # Full hygiene report
    python scripts/hygiene.py --check-urls       # HTTP HEAD check on application_urls
    python scripts/hygiene.py --check-postings   # Verify jobs still live on ATS APIs
    python scripts/hygiene.py --auto-expire      # Move past-deadline active entries to closed/
    python scripts/hygiene.py --auto-expire --dry-run
    python scripts/hygiene.py --gate <id>        # Track-specific readiness gate for one entry
"""

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    ALL_PIPELINE_DIRS,
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_CLOSED,
    PIPELINE_DIR_RESEARCH_POOL,
    load_entries,
    load_entry_by_id,
    get_deadline,
    days_until,
    parse_date,
    update_yaml_field,
    update_last_touched,
)
from source_jobs import (
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_ashby_jobs,
)

HTTP_TIMEOUT = 10
STALE_ROLLING_DAYS = 30


# ---------------------------------------------------------------------------
# URL liveness check
# ---------------------------------------------------------------------------

def check_url_liveness(url: str) -> tuple[str, int | None]:
    """HTTP HEAD check on a URL. Returns (status_label, http_code)."""
    if not url:
        return "missing", None
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": "application-pipeline/1.0"})
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            code = resp.getcode()
            if code and 200 <= code < 400:
                return "ok", code
            return "error", code
    except HTTPError as e:
        return "error", e.code
    except (URLError, TimeoutError, OSError):
        return "timeout", None


def run_check_urls(entries: list[dict]) -> list[dict]:
    """Check application_url liveness for all entries. Returns issues list."""
    issues = []
    active = [e for e in entries if e.get("status") in ACTIONABLE_STATUSES]
    if not active:
        print("No actionable entries to check.")
        return issues

    print(f"Checking URLs for {len(active)} actionable entries...")
    print()

    for entry in active:
        entry_id = entry.get("id", "?")
        target = entry.get("target", {})
        url = target.get("application_url", "") if isinstance(target, dict) else ""

        if not url:
            issues.append({"id": entry_id, "status": "missing", "url": "", "code": None})
            print(f"  [MISSING] {entry_id} — no application_url")
            continue

        status, code = check_url_liveness(url)
        if status != "ok":
            issues.append({"id": entry_id, "status": status, "url": url, "code": code})
            code_str = f" (HTTP {code})" if code else ""
            print(f"  [{status.upper()}] {entry_id}{code_str}")
            print(f"           {url}")
        else:
            print(f"  [ok] {entry_id}")

    print()
    ok_count = len(active) - len(issues)
    print(f"Results: {ok_count} ok, {len(issues)} issues")
    return issues


# ---------------------------------------------------------------------------
# ATS posting verification
# ---------------------------------------------------------------------------

def _extract_greenhouse_job_id(url: str) -> str | None:
    """Extract job ID from a Greenhouse URL."""
    import re
    m = re.search(r"/jobs/(\d+)", url)
    return m.group(1) if m else None


def _extract_greenhouse_board(url: str) -> str | None:
    """Extract board token from a Greenhouse URL."""
    import re
    m = re.search(r"greenhouse\.io/(\w+)", url)
    return m.group(1) if m else None


def run_check_postings(entries: list[dict]) -> list[dict]:
    """Verify that ATS job postings are still live."""
    issues = []
    ats_entries = []
    for e in entries:
        if e.get("status") not in ACTIONABLE_STATUSES:
            continue
        target = e.get("target", {})
        portal = target.get("portal", "") if isinstance(target, dict) else ""
        if portal in ("greenhouse", "lever", "ashby"):
            ats_entries.append(e)

    if not ats_entries:
        print("No ATS entries to check.")
        return issues

    print(f"Checking {len(ats_entries)} ATS postings...")
    print()

    # Group by portal+company to batch API calls
    board_jobs: dict[tuple[str, str], list[dict]] = {}
    for e in ats_entries:
        target = e.get("target", {})
        portal = target.get("portal", "")
        url = target.get("application_url", "")
        org = target.get("organization", "").lower().replace(" ", "")

        if portal == "greenhouse":
            board = _extract_greenhouse_board(url)
            if board:
                board_jobs.setdefault(("greenhouse", board), []).append(e)
        elif portal == "lever":
            board_jobs.setdefault(("lever", org), []).append(e)
        elif portal == "ashby":
            board_jobs.setdefault(("ashby", org), []).append(e)

    # Fetch live postings per board and check
    for (portal, board), board_entries in board_jobs.items():
        live_urls = set()
        live_ids = set()

        if portal == "greenhouse":
            jobs = fetch_greenhouse_jobs(board)
            for j in jobs:
                live_urls.add(j.get("url", ""))
                live_ids.add(j.get("id", ""))
        elif portal == "lever":
            jobs = fetch_lever_jobs(board)
            for j in jobs:
                live_urls.add(j.get("url", ""))
                live_ids.add(j.get("id", ""))
        elif portal == "ashby":
            jobs = fetch_ashby_jobs(board)
            for j in jobs:
                live_urls.add(j.get("url", ""))
                live_ids.add(j.get("id", ""))

        for e in board_entries:
            entry_id = e.get("id", "?")
            target = e.get("target", {})
            app_url = target.get("application_url", "")

            # Check by URL match or job ID match
            job_id = _extract_greenhouse_job_id(app_url) if portal == "greenhouse" else None
            found = app_url in live_urls or (job_id and job_id in live_ids)

            if not found and live_urls:  # only flag if we got API results
                issues.append({"id": entry_id, "portal": portal, "board": board, "url": app_url})
                print(f"  [CLOSED] {entry_id} — posting no longer on {portal}/{board}")
            elif not live_urls:
                print(f"  [SKIP] {entry_id} — could not fetch {portal}/{board}")
            else:
                print(f"  [LIVE] {entry_id}")

    print()
    print(f"Results: {len(ats_entries) - len(issues)} live, {len(issues)} closed/missing")
    return issues


# ---------------------------------------------------------------------------
# Auto-expire
# ---------------------------------------------------------------------------

def run_auto_expire(entries: list[dict], dry_run: bool = True) -> list[dict]:
    """Move past-deadline active entries to closed/ with outcome=expired."""
    today = date.today()
    expired = []

    for e in entries:
        if e.get("status") not in ACTIONABLE_STATUSES:
            continue
        dl_date, dl_type = get_deadline(e)
        if not dl_date:
            continue
        if dl_type not in ("hard", "fixed"):
            continue
        if days_until(dl_date) >= 0:
            continue

        entry_id = e.get("id", "?")
        days_past = abs(days_until(dl_date))
        expired.append({"id": entry_id, "deadline": dl_date.isoformat(), "days_past": days_past})

    if not expired:
        print("No expired entries to process.")
        return expired

    print(f"Expired entries ({len(expired)}):")
    for item in expired:
        action = "[dry-run]" if dry_run else "[moving]"
        print(f"  {action} {item['id']} — deadline was {item['deadline']} ({item['days_past']}d ago)")

        if not dry_run:
            _expire_entry(item["id"])

    if dry_run:
        print(f"\nDry run — run with --yes to execute.")
    else:
        print(f"\nMoved {len(expired)} entries to pipeline/closed/")

    return expired


def _expire_entry(entry_id: str):
    """Move an entry to closed/ with outcome=expired."""
    # Search active and research_pool
    for search_dir in [PIPELINE_DIR_ACTIVE, PIPELINE_DIR_RESEARCH_POOL]:
        filepath = search_dir / f"{entry_id}.yaml"
        if filepath.exists():
            content = filepath.read_text()
            content = update_yaml_field(content, "status", "outcome")
            try:
                content = update_yaml_field(content, "outcome", "expired")
            except ValueError:
                # outcome field might be 'null' — try regex
                import re
                content = re.sub(
                    r'^(outcome:)\s+.*$', r'\1 expired',
                    content, count=1, flags=re.MULTILINE,
                )
            content = update_last_touched(content)

            PIPELINE_DIR_CLOSED.mkdir(parents=True, exist_ok=True)
            dest = PIPELINE_DIR_CLOSED / filepath.name
            dest.write_text(content)
            filepath.unlink()
            return

    print(f"  WARNING: Could not find file for {entry_id}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Track-specific gates
# ---------------------------------------------------------------------------

GATE_CHECKS = {
    "job": [
        ("target.application_url", "Jobs must have an application URL"),
        ("target.portal", "Jobs must have a portal type"),
        ("target.location_class", "Jobs must have a location classification"),
    ],
    "grant": [
        ("deadline", "Grants must have a deadline date or type=rolling"),
    ],
    "residency": [
        ("deadline", "Residencies must have a deadline date or type=rolling"),
    ],
    "fellowship": [
        ("deadline", "Fellowships must have a deadline date or type=rolling"),
    ],
}

UNIVERSAL_GATES = [
    ("fit.score", "Entry must have a fit score > 0"),
    ("fit.identity_position", "Entry must have an identity position"),
]


def check_gate(entry: dict) -> list[str]:
    """Run track-specific and universal readiness gates on an entry."""
    issues = []
    track = entry.get("track", "unknown")

    # Universal checks
    fit = entry.get("fit", {})
    if not isinstance(fit, dict) or not fit.get("score"):
        issues.append("fit.score is 0 or missing")
    if not isinstance(fit, dict) or not fit.get("identity_position"):
        issues.append("fit.identity_position is not set")

    # Track-specific checks
    checks = GATE_CHECKS.get(track, [])
    for field_path, message in checks:
        if field_path == "target.application_url":
            target = entry.get("target", {})
            if not isinstance(target, dict) or not target.get("application_url"):
                issues.append(message)
        elif field_path == "target.portal":
            target = entry.get("target", {})
            if not isinstance(target, dict) or not target.get("portal"):
                issues.append(message)
        elif field_path == "target.location_class":
            target = entry.get("target", {})
            if not isinstance(target, dict) or not target.get("location_class"):
                issues.append(message)
        elif field_path == "deadline":
            dl = entry.get("deadline", {})
            if isinstance(dl, dict):
                has_date = dl.get("date") is not None
                is_rolling = dl.get("type") in ("rolling", "tba")
                if not has_date and not is_rolling:
                    issues.append(message)
            else:
                issues.append(message)

    return issues


def run_gate(entry_id: str):
    """Run gate checks for a single entry."""
    filepath, entry = load_entry_by_id(entry_id)
    if not entry:
        print(f"Entry not found: {entry_id}", file=sys.stderr)
        sys.exit(1)

    issues = check_gate(entry)
    name = entry.get("name", entry_id)
    track = entry.get("track", "unknown")

    if not issues:
        print(f"PASS: {name} [{track}] — all gates satisfied")
    else:
        print(f"FAIL: {name} [{track}] — {len(issues)} gate(s) failed:")
        for issue in issues:
            print(f"  - {issue}")
    return issues


# ---------------------------------------------------------------------------
# Stale rolling detection
# ---------------------------------------------------------------------------

def check_stale_rolling(entries: list[dict]) -> list[dict]:
    """Flag rolling-deadline entries that haven't been touched in >30 days."""
    today = date.today()
    stale = []

    for e in entries:
        if e.get("status") not in ACTIONABLE_STATUSES:
            continue
        dl = e.get("deadline", {})
        if not isinstance(dl, dict) or dl.get("type") != "rolling":
            continue

        lt = parse_date(e.get("last_touched"))
        if not lt:
            continue

        stale_days = (today - lt).days
        if stale_days > STALE_ROLLING_DAYS:
            stale.append({
                "id": e.get("id", "?"),
                "name": e.get("name", "?"),
                "days_stale": stale_days,
                "last_touched": lt.isoformat(),
            })

    return stale


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------

def run_full_report(entries: list[dict]):
    """Generate a comprehensive hygiene report."""
    today = date.today()
    print(f"PIPELINE HYGIENE REPORT — {today.isoformat()}")
    print("=" * 60)

    active = [e for e in entries if e.get("status") in ACTIONABLE_STATUSES]
    print(f"\nActionable entries: {len(active)}")

    # Missing URLs
    missing_url = [e for e in active
                   if not (isinstance(e.get("target"), dict) and e["target"].get("application_url"))]
    if missing_url:
        print(f"\nMISSING URLs ({len(missing_url)}):")
        for e in missing_url:
            print(f"  {e.get('id', '?')} [{e.get('track', '?')}]")

    # Expired deadlines
    expired = []
    for e in active:
        dl_date, dl_type = get_deadline(e)
        if dl_date and days_until(dl_date) < 0 and dl_type in ("hard", "fixed"):
            expired.append(e)
    if expired:
        print(f"\nEXPIRED DEADLINES ({len(expired)}):")
        for e in expired:
            dl_date, _ = get_deadline(e)
            print(f"  {e.get('id', '?')} — {dl_date} ({abs(days_until(dl_date))}d ago)")

    # Gate failures
    gate_failures = []
    for e in active:
        issues = check_gate(e)
        if issues:
            gate_failures.append((e.get("id", "?"), e.get("track", "?"), issues))
    if gate_failures:
        print(f"\nGATE FAILURES ({len(gate_failures)}):")
        for eid, track, issues in gate_failures[:10]:
            print(f"  {eid} [{track}]:")
            for issue in issues:
                print(f"    - {issue}")
        if len(gate_failures) > 10:
            print(f"  ... and {len(gate_failures) - 10} more")

    # Stale rolling
    stale = check_stale_rolling(entries)
    if stale:
        stale.sort(key=lambda x: -x["days_stale"])
        print(f"\nSTALE ROLLING ({len(stale)}) — rolling deadline, untouched >{STALE_ROLLING_DAYS}d:")
        for s in stale[:10]:
            print(f"  {s['id']} — {s['days_stale']}d since {s['last_touched']}")
        if len(stale) > 10:
            print(f"  ... and {len(stale) - 10} more")

    # Summary
    total_issues = len(missing_url) + len(expired) + len(gate_failures) + len(stale)
    print(f"\n{'=' * 60}")
    if total_issues == 0:
        print(f"ALL CLEAR — {len(active)} entries, no hygiene issues")
    else:
        print(f"ISSUES FOUND: {total_issues} total")
        print(f"  Missing URLs: {len(missing_url)}")
        print(f"  Expired deadlines: {len(expired)}")
        print(f"  Gate failures: {len(gate_failures)}")
        print(f"  Stale rolling: {len(stale)}")
        if expired:
            print(f"\nRun `python scripts/hygiene.py --auto-expire --dry-run` to handle expired entries")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Entry hygiene: URL liveness, ATS checks, auto-expire, track gates"
    )
    parser.add_argument("--check-urls", action="store_true",
                        help="HTTP HEAD check on all active application_urls")
    parser.add_argument("--check-postings", action="store_true",
                        help="Verify ATS job postings are still live")
    parser.add_argument("--auto-expire", action="store_true",
                        help="Move past-deadline active entries to closed/")
    parser.add_argument("--gate", metavar="ENTRY_ID",
                        help="Run track-specific readiness gate for one entry")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without executing")
    parser.add_argument("--yes", action="store_true",
                        help="Execute changes (required for --auto-expire)")
    args = parser.parse_args()

    if args.gate:
        issues = run_gate(args.gate)
        sys.exit(1 if issues else 0)

    entries = load_entries(
        dirs=[PIPELINE_DIR_ACTIVE, PIPELINE_DIR_RESEARCH_POOL],
        include_filepath=True,
    )

    if args.check_urls:
        run_check_urls(entries)
    elif args.check_postings:
        run_check_postings(entries)
    elif args.auto_expire:
        dry_run = not args.yes or args.dry_run
        run_auto_expire(entries, dry_run=dry_run)
    else:
        run_full_report(entries)


if __name__ == "__main__":
    main()
