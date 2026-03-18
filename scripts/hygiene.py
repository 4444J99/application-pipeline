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
    python scripts/hygiene.py --company-focus    # Rule of Three: flag companies >3 active+submitted
    python scripts/hygiene.py --company-focus --limit 3  # Override Rule of Three limit
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    COMPANY_CAP,
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_CLOSED,
    PIPELINE_DIR_RESEARCH_POOL,
    PIPELINE_DIR_SUBMITTED,
    SIGNALS_DIR,
    atomic_write,
    days_until,
    get_deadline,
    http_request_with_retry,
    load_entries,
    load_entry_by_id,
    parse_date,
)
from source_jobs import (
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
)
from yaml_mutation import YAMLEditor

HTTP_TIMEOUT = 10
STALE_ROLLING_DAYS = 30


# ---------------------------------------------------------------------------
# URL liveness check
# ---------------------------------------------------------------------------

def check_url_liveness(url: str) -> tuple[str, int | None]:
    """HTTP HEAD check on a URL with retry. Returns (status_label, http_code)."""
    if not url:
        return "missing", None
    result = http_request_with_retry(
        url, method="HEAD", timeout=HTTP_TIMEOUT,
        headers={"User-Agent": "application-pipeline/1.0"},
        max_retries=2,
    )
    if result is not None:
        return "ok", 200
    # Retry failed — try to distinguish error type
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
                live_ids.add(str(j.get("id", "")))
        elif portal == "lever":
            jobs = fetch_lever_jobs(board)
            for j in jobs:
                live_urls.add(j.get("url", ""))
                live_ids.add(str(j.get("id", "")))
        elif portal == "ashby":
            jobs = fetch_ashby_jobs(board)
            for j in jobs:
                live_urls.add(j.get("url", ""))
                live_ids.add(str(j.get("id", "")))

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
        print("\nDry run — run with --yes to execute.")
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
            # Guard: only expire actionable entries
            data = yaml.safe_load(content)
            if isinstance(data, dict) and data.get("status") not in ACTIONABLE_STATUSES:
                print(f"  WARNING: Skipping {entry_id} — status '{data.get('status')}' not actionable",
                      file=sys.stderr)
                return
            editor = YAMLEditor(content)
            editor.set("status", "outcome")
            editor.set("outcome", "expired")
            editor.touch()

            PIPELINE_DIR_CLOSED.mkdir(parents=True, exist_ok=True)
            dest = PIPELINE_DIR_CLOSED / filepath.name
            atomic_write(dest, editor.dump())
            filepath.unlink()
            return

    print(f"  WARNING: Could not find file for {entry_id}", file=sys.stderr)


def run_expire_stale_submissions(entries: list[dict], max_days: int = 21, dry_run: bool = True) -> list[dict]:
    """Auto-expire job submissions with no response after max_days.

    Only affects job-track entries with status submitted/acknowledged.
    Grant, writing, and fellowship tracks have longer response cycles
    and are excluded.
    """
    today = date.today()
    expired = []

    for e in entries:
        if e.get("status") not in ("submitted", "acknowledged"):
            continue
        if e.get("track") not in ("job",):
            continue

        timeline = e.get("timeline", {})
        if not isinstance(timeline, dict):
            continue
        sub_date = parse_date(timeline.get("submitted"))
        if not sub_date:
            continue

        days_since = (today - sub_date).days
        if days_since < max_days:
            continue

        entry_id = e.get("id", "?")
        expired.append({"id": entry_id, "days_since": days_since, "submitted": sub_date.isoformat()})

    if not expired:
        return expired

    print(f"Stale job submissions ({len(expired)}, >{max_days}d no response):")
    for item in expired:
        action = "[dry-run]" if dry_run else "[expiring]"
        print(f"  {action} {item['id']} — submitted {item['submitted']} ({item['days_since']}d ago)")

        if not dry_run:
            filepath = PIPELINE_DIR_SUBMITTED / f"{item['id']}.yaml"
            if filepath.exists():
                content = filepath.read_text()
                editor = YAMLEditor(content)
                editor.set("status", "outcome")
                editor.set("outcome", "expired")
                editor.touch()
                PIPELINE_DIR_CLOSED.mkdir(parents=True, exist_ok=True)
                dest = PIPELINE_DIR_CLOSED / filepath.name
                atomic_write(dest, editor.dump())
                filepath.unlink()

    if dry_run:
        print("\nDry run — run with --yes to execute.")
    else:
        print(f"\nExpired {len(expired)} stale job submissions to pipeline/closed/")

    return expired


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
            print("\nRun `python scripts/hygiene.py --auto-expire --dry-run` to handle expired entries")


# ---------------------------------------------------------------------------
# Research pool pruning
# ---------------------------------------------------------------------------

DEFAULT_PRUNE_AGE_DAYS = 90

# 3-day flash memory: jobs have a ~72h competitive shelf life
FLASH_PRUNE_HOURS = 72
RESEARCH_ARCHIVE_DIR = PIPELINE_DIR_RESEARCH_POOL / "_archived"


def run_prune_research(entries: list[dict], older_than: int = DEFAULT_PRUNE_AGE_DAYS, dry_run: bool = True, flash: bool = False) -> list[dict]:
    """Archive research_pool entries that are stale.

    Two modes:
    - Default (flash=False): Archive entries older than `older_than` days with no score.
      Moves to closed/ with outcome=expired.
    - Flash mode (flash=True): Archive entries where EITHER posting_date OR
      date_added exceeds 72h — whichever is older. Moves to
      research_pool/_archived/ to preserve data without polluting the funnel.
      Scored entries (score > 0) are kept regardless.
    """
    from datetime import datetime

    today = date.today()
    now = datetime.now()
    pruned = []

    for e in entries:
        if e.get("status") != "research":
            continue
        filepath = e.get("_filepath")
        if not filepath or not Path(filepath).parent.name == "research_pool":
            continue

        # Check for score — keep scored entries in both modes
        fit = e.get("fit", {})
        score = fit.get("score") if isinstance(fit, dict) else None
        if score is not None and float(score) > 0:
            continue

        if flash:
            # Flash mode: check posting_date and date_added, archive if EITHER > 72h
            timeline = e.get("timeline", {})
            if not isinstance(timeline, dict):
                timeline = {}
            posting_date = parse_date(timeline.get("posting_date"))
            date_added = parse_date(timeline.get("date_added"))
            # Use the older of the two dates (most conservative = most aggressive pruning)
            ref_date = min(filter(None, [posting_date, date_added]), default=None)
            if not ref_date:
                # No dates at all — use last_touched as fallback
                ref_date = parse_date(e.get("last_touched"))
            if not ref_date:
                continue
            age_hours = (now - datetime.combine(ref_date, datetime.min.time())).total_seconds() / 3600.0
            if age_hours < FLASH_PRUNE_HOURS:
                continue
            age_days = (today - ref_date).days
            reason = "flash"
        else:
            # Legacy mode: check last_touched/discovered, archive if > older_than days
            lt = parse_date(e.get("last_touched"))
            timeline = e.get("timeline", {})
            discovered = parse_date(timeline.get("discovered")) if isinstance(timeline, dict) else None
            ref_date = lt or discovered
            if not ref_date:
                continue
            age_days = (today - ref_date).days
            if age_days < older_than:
                continue
            reason = "age"

        entry_id = e.get("id", "?")
        pruned.append({"id": entry_id, "age_days": age_days, "last_touched": ref_date.isoformat(), "reason": reason})

        if not dry_run:
            src = Path(filepath)
            if flash:
                # Flash mode: move to research_pool/_archived/
                RESEARCH_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                dest = RESEARCH_ARCHIVE_DIR / src.name
                src.rename(dest)
            else:
                # Legacy mode: move to closed/ with outcome=expired
                content = src.read_text()
                editor = YAMLEditor(content)
                editor.set("status", "outcome")
                editor.set("outcome", "expired")
                editor.touch()
                PIPELINE_DIR_CLOSED.mkdir(parents=True, exist_ok=True)
                dest = PIPELINE_DIR_CLOSED / src.name
                atomic_write(dest, editor.dump())
                src.unlink()

    if not pruned:
        if flash:
            print(f"No research_pool entries older than {FLASH_PRUNE_HOURS}h.")
        else:
            print(f"No research_pool entries older than {older_than} days with no score.")
    else:
        action = "Would archive" if dry_run else "Archived"
        if flash:
            dest_label = "research_pool/_archived/"
            print(f"{action} {len(pruned)} research_pool entries (>{FLASH_PRUNE_HOURS}h, no score) → {dest_label}:")
        else:
            print(f"{action} {len(pruned)} research_pool entries (>{older_than} days, no score):")
        for item in pruned[:20]:
            print(f"  {item['id']} — {item['age_days']}d old (last: {item['last_touched']})")
        if len(pruned) > 20:
            print(f"  ... and {len(pruned) - 20} more")
        if dry_run:
            print("\nDry run — run with --prune-research --yes to execute.")

    return pruned


# ---------------------------------------------------------------------------
# Company focus (Rule of Three)
# ---------------------------------------------------------------------------

DEFAULT_FOCUS_LIMIT = COMPANY_CAP


def section_company_focus(focus_limit: int = DEFAULT_FOCUS_LIMIT):
    """Flag companies with more than focus_limit active+submitted job entries.

    Loads active/ and submitted/ job-track entries, groups by organization,
    and shows triage suggestions for over-concentrated companies.
    Submitted entries are immutable (shown for context). Triage actions
    apply to active/ entries only.
    """
    active_entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE], include_filepath=True)
    submitted_entries = load_entries(dirs=[PIPELINE_DIR_SUBMITTED], include_filepath=True)

    job_entries: list[tuple[dict, str]] = []  # (entry, source)
    for e in active_entries:
        if e.get("track") == "job":
            job_entries.append((e, "active"))
    for e in submitted_entries:
        if e.get("track") == "job":
            job_entries.append((e, "submitted"))

    # Group by organization
    by_company: dict[str, list[tuple[dict, str]]] = {}
    for entry, source in job_entries:
        org = entry.get("target", {}).get("organization", "Unknown") if isinstance(entry.get("target"), dict) else "Unknown"
        by_company.setdefault(org, []).append((entry, source))

    violators = {
        org: entries
        for org, entries in by_company.items()
        if len(entries) > focus_limit
    }

    print(f"COMPANY FOCUS — Rule of {focus_limit}")
    print("=" * 60)
    print(f"Limit: {focus_limit} total active+submitted per company (job track)")
    print()

    if not violators:
        total_companies = len(by_company)
        print(f"ALL CLEAR — {total_companies} companies, none exceed limit of {focus_limit}")
        return

    print(f"FLAGGED COMPANIES ({len(violators)}):")
    print()

    for org, entries in sorted(violators.items(), key=lambda x: -len(x[1])):
        active_count = sum(1 for _, src in entries if src == "active")
        submitted_count = sum(1 for _, src in entries if src == "submitted")
        total = len(entries)

        print(f"  {org}  [{total} total: {active_count} active, {submitted_count} submitted]")
        print(f"  {'─' * 56}")

        # Sort by score descending; missing score goes last
        def sort_key(item: tuple[dict, str]) -> float:
            e, _ = item
            fit = e.get("fit", {})
            score = fit.get("score", 0) if isinstance(fit, dict) else 0
            return -(score or 0)

        ranked = sorted(entries, key=sort_key)

        # Submitted entries always shown first (immutable context)
        submitted_list = [(e, src) for e, src in ranked if src == "submitted"]
        active_list = [(e, src) for e, src in ranked if src == "active"]

        keep_slots = max(0, focus_limit - len(submitted_list))

        for idx, (e, src) in enumerate(submitted_list + active_list):
            entry_id = e.get("id", "?")
            status = e.get("status", "?")
            fit = e.get("fit", {})
            score = fit.get("score", 0) if isinstance(fit, dict) else 0
            score_str = f"{score:.1f}" if score else " — "
            target = e.get("target", {}) if isinstance(e.get("target"), dict) else {}
            app_url = target.get("application_url", "")

            if src == "submitted":
                action = "[submitted — immutable]"
            elif (idx - len(submitted_list)) < keep_slots:
                action = "[keep]"
            else:
                action = "[suggest defer]"

            print(f"    {score_str:>5}  {status:<12}  {action:<26}  {entry_id}")
            if app_url:
                print(f"           {app_url}")

        print()

    print(f"{'─' * 60}")
    active_violations = sum(
        max(0, sum(1 for _, src in entries if src == "active") - max(0, focus_limit - sum(1 for _, src in entries if src == "submitted")))
        for entries in violators.values()
    )
    print(f"ACTION: {active_violations} active entries exceed focus limit — consider deferring")
    print("To defer an entry: update its status to 'deferred' in the pipeline YAML")


# ---------------------------------------------------------------------------
# Main
DEFAULT_SIGNAL_AGE_DAYS = 90


def run_rotate_signals(older_than: int = DEFAULT_SIGNAL_AGE_DAYS, *, dry_run: bool = True):
    """Archive signal-actions entries older than *older_than* days.

    Moves old entries to signals/archive/YYYY-MM/signal-actions.yaml,
    keeping the production file lean.
    """
    from datetime import datetime, timedelta

    sa_path = SIGNALS_DIR / "signal-actions.yaml"
    if not sa_path.exists():
        print("signal-actions.yaml not found — nothing to rotate.")
        return

    data = yaml.safe_load(sa_path.read_text()) or {}
    actions = data.get("actions", []) or []
    if not actions:
        print("No signal actions to rotate.")
        return

    cutoff = (datetime.now() - timedelta(days=older_than)).date()
    keep, archive = [], []
    for action in actions:
        action_date_str = action.get("action_date", "")
        try:
            action_date = date.fromisoformat(str(action_date_str))
        except (ValueError, TypeError):
            keep.append(action)  # keep unparseable entries
            continue
        if action_date < cutoff:
            archive.append(action)
        else:
            keep.append(action)

    if not archive:
        print(f"No signal actions older than {older_than} days (cutoff {cutoff}).")
        return

    print(f"Signal actions: {len(actions)} total, {len(archive)} older than {older_than}d, {len(keep)} to keep")

    if dry_run:
        print("\nDry run — run with --rotate-signals --yes to execute.")
        return

    # Group archived entries by month
    monthly: dict[str, list] = {}
    for a in archive:
        d_str = str(a.get("action_date", ""))
        month_key = d_str[:7] if len(d_str) >= 7 else "unknown"
        monthly.setdefault(month_key, []).append(a)

    archive_dir = SIGNALS_DIR / "archive"
    for month, entries in sorted(monthly.items()):
        month_dir = archive_dir / month
        month_dir.mkdir(parents=True, exist_ok=True)
        archive_file = month_dir / "signal-actions.yaml"
        existing = []
        if archive_file.exists():
            existing_data = yaml.safe_load(archive_file.read_text()) or {}
            existing = existing_data.get("actions", []) or []
        existing.extend(entries)
        atomic_write(
            archive_file,
            yaml.dump({"actions": existing}, default_flow_style=False, sort_keys=False, allow_unicode=True),
        )
        print(f"  Archived {len(entries)} entries to {archive_file}")

    # Write trimmed production file
    data["actions"] = keep
    atomic_write(
        sa_path,
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
    )
    print(f"  Production file trimmed to {len(keep)} entries")


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
    parser.add_argument("--company-focus", action="store_true",
                        help="Rule of Three: flag companies with >limit active+submitted job entries")
    parser.add_argument("--limit", type=int, default=DEFAULT_FOCUS_LIMIT, metavar="N",
                        help=f"Focus limit for --company-focus (default: {DEFAULT_FOCUS_LIMIT})")
    parser.add_argument("--prune-research", action="store_true",
                        help="Archive research_pool entries older than --older-than days with no score")
    parser.add_argument("--flash", action="store_true",
                        help="Use 72h flash memory mode: archive entries where posting_date or date_added > 72h")
    parser.add_argument("--older-than", type=int, default=DEFAULT_PRUNE_AGE_DAYS, metavar="DAYS",
                        help=f"Age threshold for --prune-research (default: {DEFAULT_PRUNE_AGE_DAYS})")
    parser.add_argument("--rotate-signals", action="store_true",
                        help="Archive signal-actions entries older than --signal-age days")
    parser.add_argument("--signal-age", type=int, default=DEFAULT_SIGNAL_AGE_DAYS, metavar="DAYS",
                        help=f"Age threshold for --rotate-signals (default: {DEFAULT_SIGNAL_AGE_DAYS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without executing")
    parser.add_argument("--yes", action="store_true",
                        help="Execute changes (required for --auto-expire, --prune-research, --rotate-signals)")
    args = parser.parse_args()

    if args.gate:
        issues = run_gate(args.gate)
        sys.exit(1 if issues else 0)

    if args.company_focus:
        section_company_focus(focus_limit=args.limit)
        return

    entries = load_entries(
        dirs=[PIPELINE_DIR_ACTIVE, PIPELINE_DIR_RESEARCH_POOL],
        include_filepath=True,
    )

    if args.rotate_signals:
        dry_run = not args.yes or args.dry_run
        run_rotate_signals(older_than=args.signal_age, dry_run=dry_run)
        return

    if args.prune_research:
        dry_run = not args.yes or args.dry_run
        run_prune_research(entries, older_than=args.older_than, dry_run=dry_run, flash=args.flash)
    elif args.check_urls:
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
