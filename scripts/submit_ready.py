#!/usr/bin/env python3
"""Unified submission orchestrator — submit all audit-ready entries.

Runs submission_audit internally, then dispatches ready entries to the
appropriate portal-specific submitter (greenhouse, ashby, lever, email).

Usage:
    python scripts/submit_ready.py                    # dry-run: show what would submit
    python scripts/submit_ready.py --submit           # actually submit all ready entries
    python scripts/submit_ready.py --portal greenhouse # only greenhouse
    python scripts/submit_ready.py --submit --record   # submit + update YAML status
    python scripts/submit_ready.py --submit --throttle 30  # 30s between API calls
    python scripts/submit_ready.py --submit --max-per-company 2  # max 2 per org
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import PIPELINE_DIR_ACTIVE, detect_entry_portal, load_entries
from submission_audit import SUBMITTABLE_PORTALS, check_entry

SCRIPTS_DIR = Path(__file__).resolve().parent

# Portal -> (script filename, supports --record flag)
PORTAL_SCRIPTS = {
    "greenhouse": ("greenhouse_submit.py", False),
    "ashby": ("ashby_submit.py", False),
    "lever": ("lever_submit.py", False),
    "email": ("email_submit.py", True),
}


def gather_ready_entries(portal_filter: str | None = None) -> list[dict]:
    """Load active entries, run audit checks, return ready ones."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    results = []
    for entry in entries:
        portal = detect_entry_portal(entry)
        if portal_filter and portal != portal_filter:
            continue
        result = check_entry(entry)
        if result["ready"]:
            # Attach the full entry for company cap filtering
            result["_org"] = entry.get("target", {}).get("organization", "")
            results.append(result)
    return results


def group_by_portal(results: list[dict]) -> dict[str, list[dict]]:
    """Group audit results by portal type."""
    groups: dict[str, list[dict]] = {}
    for r in results:
        groups.setdefault(r["portal"], []).append(r)
    return groups


def apply_company_cap(results: list[dict], max_per_company: int) -> list[dict]:
    """Limit entries per organization. Returns filtered list."""
    if max_per_company <= 0:
        return results
    org_counts: dict[str, int] = {}
    filtered = []
    for r in results:
        org = r.get("_org", "unknown")
        count = org_counts.get(org, 0)
        if count < max_per_company:
            filtered.append(r)
            org_counts[org] = count + 1
        else:
            print(f"  CAP: Skipping {r['id']} ({org} already at {max_per_company} submissions)")
    return filtered


def print_dry_run(groups: dict[str, list[dict]], max_per_company: int = 0) -> None:
    """Print summary table of what would be submitted."""
    total = sum(len(entries) for entries in groups.values())
    print(f"SUBMIT READY — {total} entries ready for submission")
    print("=" * 65)

    for portal in sorted(groups.keys()):
        entries = groups[portal]
        submittable = portal in PORTAL_SCRIPTS
        manual = portal in ("custom", "slideroom")
        tag = ""
        if not submittable and manual:
            tag = "  (manual — open URL in browser)"
        elif not submittable:
            tag = "  (no submitter)"

        print(f"\n{portal.upper()} ({len(entries)}){tag}")
        print("-" * 50)

        for r in sorted(entries, key=lambda x: x["id"]):
            checks = f"{r['pass_count']}/{r['total_checks']}"
            status = r.get("status", "?")
            print(f"  {r['id']:<55s} {status:<10s} {checks}")

    # Summary footer
    print()
    print("=" * 65)
    print("DISPATCH PLAN:")
    for portal in sorted(groups.keys()):
        count = len(groups[portal])
        if portal in PORTAL_SCRIPTS:
            script, _ = PORTAL_SCRIPTS[portal]
            print(f"  {portal:<12s} {count} entries -> {script}")
        elif portal in ("custom", "slideroom"):
            print(f"  {portal:<12s} {count} entries -> manual (URLs printed below)")
        else:
            print(f"  {portal:<12s} {count} entries -> SKIP (no submitter available)")

    if max_per_company > 0:
        print(f"\n  Company cap: {max_per_company} per organization")

    # Print manual submission URLs
    manual_entries = []
    for portal in ("custom", "slideroom"):
        manual_entries.extend(groups.get(portal, []))
    if manual_entries:
        all_active = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
        entry_map = {e.get("id", ""): e for e in all_active}
        print()
        print("MANUAL SUBMISSION URLs:")
        for r in sorted(manual_entries, key=lambda x: x["id"]):
            eid = r["id"]
            entry = entry_map.get(eid, {})
            app_url = entry.get("target", {}).get("application_url", "")
            if app_url:
                print(f"  {eid}")
                print(f"    {app_url}")
            else:
                print(f"  {eid}  (no URL on file)")

    print()
    flags = "--submit"
    if max_per_company > 0:
        flags += f" --max-per-company {max_per_company}"
    print(f"Run with {flags} to execute. Add --record to also update YAML status.")
    print("Add --throttle N to wait N seconds between API submissions.")


def dispatch_entry(entry_id: str, portal: str, do_record: bool) -> bool:
    """Shell out to the portal-specific submitter for one entry."""
    if portal not in PORTAL_SCRIPTS:
        print(f"  SKIP {entry_id}: no submitter for portal '{portal}'")
        return False

    script_name, supports_record = PORTAL_SCRIPTS[portal]
    script_path = SCRIPTS_DIR / script_name

    cmd = [sys.executable, str(script_path), "--target", entry_id, "--submit"]

    if do_record and supports_record:
        cmd.append("--record")

    print(f"  Dispatching {entry_id} -> {script_name}")
    result = subprocess.run(cmd, timeout=120)

    if result.returncode == 0:
        print(f"  OK: {entry_id}")
        return True
    else:
        print(f"  FAILED: {entry_id} (exit code {result.returncode})")
        return False


def record_entry(entry_id: str) -> bool:
    """Run submit.py --target <id> --record to update YAML status."""
    script_path = SCRIPTS_DIR / "submit.py"
    cmd = [sys.executable, str(script_path), "--target", entry_id, "--record"]

    print(f"  Recording {entry_id} -> submit.py --record")
    result = subprocess.run(cmd, timeout=30)

    if result.returncode == 0:
        print(f"  RECORDED: {entry_id}")
        return True
    else:
        print(f"  RECORD FAILED: {entry_id} (exit code {result.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Unified submission orchestrator — submit all audit-ready entries"
    )
    parser.add_argument("--submit", action="store_true",
                        help="Actually submit (default is dry-run preview)")
    parser.add_argument("--portal",
                        choices=sorted(SUBMITTABLE_PORTALS | {"unknown"}),
                        help="Filter to a single portal type")
    parser.add_argument("--record", action="store_true",
                        help="After successful submission, update YAML status")
    parser.add_argument("--throttle", type=int, default=0, metavar="SECONDS",
                        help="Delay between API submissions (anti-bot, default: 0)")
    parser.add_argument("--max-per-company", type=int, default=0, metavar="N",
                        help="Max submissions per organization in this batch (default: unlimited)")
    args = parser.parse_args()

    # Gather all ready entries
    ready = gather_ready_entries(portal_filter=args.portal)

    if not ready:
        portal_note = f" for portal '{args.portal}'" if args.portal else ""
        print(f"No audit-ready entries found{portal_note}.")
        print("Run 'python scripts/submission_audit.py' to see blockers.")
        sys.exit(0)

    # Apply company cap
    if args.max_per_company > 0:
        ready = apply_company_cap(ready, args.max_per_company)

    groups = group_by_portal(ready)

    # Dry-run mode
    if not args.submit:
        print_dry_run(groups, max_per_company=args.max_per_company)
        sys.exit(0)

    # Submit mode
    all_active = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
    total = 0
    succeeded = 0
    failed = 0
    skipped = 0
    recorded = 0
    record_failed = 0
    api_call_count = 0

    results_by_portal: dict[str, dict[str, int]] = {}

    for portal in sorted(groups.keys()):
        entries = groups[portal]
        portal_stats = {"ok": 0, "fail": 0, "skip": 0}

        print()
        print(f"{'=' * 65}")
        print(f"SUBMITTING {portal.upper()} ({len(entries)} entries)")
        print(f"{'=' * 65}")

        if portal in ("custom", "slideroom"):
            entry_map = {e.get("id", ""): e for e in all_active}
            print()
            print("MANUAL SUBMISSION REQUIRED:")
            print("-" * 50)
            for r in sorted(entries, key=lambda x: x["id"]):
                eid = r["id"]
                entry = entry_map.get(eid, {})
                app_url = entry.get("target", {}).get("application_url", "")
                org = entry.get("target", {}).get("organization", "")
                print(f"  {eid}")
                print(f"    {org} — {app_url or 'no URL'}")
            portal_stats["skip"] = len(entries)
            skipped += len(entries)
            total += len(entries)
            results_by_portal[portal] = portal_stats
            continue

        if portal not in PORTAL_SCRIPTS:
            print(f"  No submitter for portal '{portal}' — skipping {len(entries)} entries")
            portal_stats["skip"] = len(entries)
            skipped += len(entries)
            total += len(entries)
            results_by_portal[portal] = portal_stats
            continue

        for r in sorted(entries, key=lambda x: x["id"]):
            eid = r["id"]
            total += 1

            # Throttle between API calls
            if args.throttle > 0 and api_call_count > 0:
                print(f"  (throttle: waiting {args.throttle}s)")
                time.sleep(args.throttle)

            ok = dispatch_entry(eid, portal, do_record=False)
            api_call_count += 1

            if ok:
                portal_stats["ok"] += 1
                succeeded += 1
                if args.record:
                    rec_ok = record_entry(eid)
                    if rec_ok:
                        recorded += 1
                    else:
                        record_failed += 1
            else:
                portal_stats["fail"] += 1
                failed += 1

            print()

        results_by_portal[portal] = portal_stats

    # Batch summary
    print()
    print("=" * 65)
    print("BATCH SUMMARY")
    print("=" * 65)

    for portal in sorted(results_by_portal.keys()):
        stats = results_by_portal[portal]
        parts = []
        if stats["ok"]:
            parts.append(f"{stats['ok']} ok")
        if stats["fail"]:
            parts.append(f"{stats['fail']} failed")
        if stats["skip"]:
            parts.append(f"{stats['skip']} skipped")
        detail = ", ".join(parts) if parts else "none"
        print(f"  {portal:<12s} {detail}")

    print()
    print(f"  Total:       {total} entries")
    print(f"  Submitted:   {succeeded}")
    print(f"  Failed:      {failed}")
    print(f"  Skipped:     {skipped} (manual portals)")

    if args.record:
        print(f"  Recorded:    {recorded}")
        if record_failed:
            print(f"  Record fail: {record_failed}")

    if args.throttle:
        print(f"  Throttle:    {args.throttle}s between calls")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
