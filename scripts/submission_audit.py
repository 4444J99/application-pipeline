#!/usr/bin/env python3
"""Batch submission readiness diagnostic.

Checks every active pipeline entry for submission readiness and reports
pass/fail across multiple dimensions: portal, resume, cover letter,
status, answer files, auth configuration, and answer completeness.

Usage:
    python scripts/submission_audit.py                    # Full audit
    python scripts/submission_audit.py --portal greenhouse # Filter by portal
    python scripts/submission_audit.py --ready-only        # Show only ready entries
    python scripts/submission_audit.py --json              # JSON output
    python scripts/submission_audit.py --deep              # Include auth + answer validation
"""

import argparse
import json
import sys
from pathlib import Path

import yaml
from pipeline_lib import (
    PIPELINE_DIR_ACTIVE,
    detect_entry_portal,
    load_entries,
    load_submit_config,
    resolve_cover_letter,
    resolve_resume,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
GREENHOUSE_ANSWERS_DIR = SCRIPTS_DIR / ".greenhouse-answers"
ASHBY_ANSWERS_DIR = SCRIPTS_DIR / ".ashby-answers"

# Portals that can be submitted programmatically (API or email)
SUBMITTABLE_PORTALS = {"greenhouse", "ashby", "lever", "custom", "email", "slideroom"}

# Statuses that indicate submission hasn't happened yet
PRE_SUBMIT_STATUSES = {"research", "qualified", "drafting", "staged", "deferred"}

# Portals requiring API keys
API_KEY_PORTALS = {"greenhouse", "ashby", "lever"}


def _check_auth_configured(portal: str, config: dict | None) -> bool:
    """Check if credentials are configured for the portal type."""
    if portal not in API_KEY_PORTALS:
        return True  # Non-API portals don't need auth
    if config is None:
        return False
    if portal == "greenhouse":
        import os
        key = config.get("greenhouse_api_key", "") or os.environ.get("GREENHOUSE_API_KEY", "")
        return bool(key)
    if portal == "ashby":
        keys = config.get("ashby_api_keys", {})
        return isinstance(keys, dict) and len(keys) > 0
    if portal == "lever":
        keys = config.get("lever_api_keys", {})
        return isinstance(keys, dict) and len(keys) > 0
    return True


def _check_answers_complete(portal: str, eid: str) -> bool:
    """Check if answer file exists AND has no FILL IN placeholders."""
    if portal == "greenhouse":
        answer_file = GREENHOUSE_ANSWERS_DIR / f"{eid}.yaml"
    elif portal == "ashby":
        answer_file = ASHBY_ANSWERS_DIR / f"{eid}.yaml"
    else:
        return True  # Non-ATS portals don't need answer files

    if not answer_file.exists():
        return False

    try:
        content = answer_file.read_text()
        # Scan for unfilled placeholder patterns
        if "FILL IN" in content or "FILL_IN" in content:
            return False
        # Also check YAML values for empty required fields
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, str) and val.strip().upper() in ("FILL IN", "FILL_IN", "TODO", ""):
                    return False
        return True
    except (OSError, yaml.YAMLError):
        return False


def check_entry(entry: dict, *, deep: bool = False, config: dict | None = None) -> dict:
    """Run all readiness checks on an entry. Returns check results dict."""
    eid = entry.get("id", "unknown")
    portal = detect_entry_portal(entry)
    status = entry.get("status", "")
    target = entry.get("target", {}) or {}
    status_meta = entry.get("status_meta", {}) or {}
    if not isinstance(status_meta, dict):
        status_meta = {}

    checks = {
        "id": eid,
        "name": entry.get("name", eid),
        "portal": portal,
        "status": status,
        "results": {},
    }

    # Check 1: Portal parsed
    checks["results"]["portal_parsed"] = portal in SUBMITTABLE_PORTALS

    # Check 2: Resume PDF exists
    resume = resolve_resume(entry)
    checks["results"]["resume_pdf"] = resume is not None and resume.exists()
    if resume:
        checks["resume_path"] = str(resume.name)

    # Check 3: Cover letter exists
    cl = resolve_cover_letter(entry)
    checks["results"]["cover_letter"] = cl is not None and len(cl.strip()) > 0

    # Check 4: Status is submittable (not already submitted)
    checks["results"]["status_submittable"] = status in PRE_SUBMIT_STATUSES

    # Check 4b: Governance review required before staged submissions.
    # (Qualified/drafting entries can still be prepared, but staged is submit-gated.)
    if status == "staged":
        checks["results"]["review_approved"] = bool(status_meta.get("reviewed_by"))
    else:
        checks["results"]["review_approved"] = True

    # Check 5: Answer file exists (portal-specific)
    if portal in ("greenhouse", "ashby"):
        answer_dir = GREENHOUSE_ANSWERS_DIR if portal == "greenhouse" else ASHBY_ANSWERS_DIR
        checks["results"]["answer_file"] = (answer_dir / f"{eid}.yaml").exists()
    else:
        checks["results"]["answer_file"] = True

    # Check 6: Has application URL or email
    app_url = target.get("application_url", "")
    has_target = bool(app_url)
    if portal in ("custom", "email"):
        email = target.get("email", "")
        has_target = bool(email and "@" in email) or app_url.startswith("mailto:")
        if not has_target:
            has_target = bool(app_url)
    checks["results"]["has_target_url"] = has_target

    # Deep checks (--deep flag): auth and answer completeness
    if deep:
        checks["results"]["auth_configured"] = _check_auth_configured(portal, config)
        checks["results"]["answers_complete"] = _check_answers_complete(portal, eid)

    # Overall readiness
    checks["ready"] = all(checks["results"].values())
    checks["pass_count"] = sum(1 for v in checks["results"].values() if v)
    checks["total_checks"] = len(checks["results"])

    return checks


def print_entry_result(result: dict, verbose: bool = True):
    """Print a single entry's audit results."""
    eid = result["id"]
    portal = result["portal"]
    status_icon = "READY" if result["ready"] else "NOT READY"
    score = f"{result['pass_count']}/{result['total_checks']}"

    print(f"  {eid}")
    print(f"    Status: {result['status']}  |  Portal: {portal}  |  {score} checks  |  {status_icon}")

    if verbose:
        for check_name, passed in result["results"].items():
            icon = "+" if passed else "-"
            label = check_name.replace("_", " ")
            print(f"    [{icon}] {label}")
        if "resume_path" in result:
            print(f"        resume: {result['resume_path']}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch submission readiness diagnostic"
    )
    parser.add_argument("--portal", help="Filter by portal type (greenhouse, ashby, lever, custom)")
    parser.add_argument("--ready-only", action="store_true",
                        help="Show only submission-ready entries")
    parser.add_argument("--deep", action="store_true",
                        help="Include auth config and answer completeness checks")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output (summary only)")
    args = parser.parse_args()

    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])

    # Load config for deep checks
    config = None
    if args.deep:
        config = load_submit_config(strict=False)

    # Filter by portal if specified
    if args.portal:
        entries = [e for e in entries if detect_entry_portal(e) == args.portal]

    if not entries:
        print("No matching entries found.")
        sys.exit(0)

    # Run checks
    results = [check_entry(e, deep=args.deep, config=config) for e in entries]

    # Filter to ready-only if requested
    if args.ready_only:
        results = [r for r in results if r["ready"]]

    # JSON output
    if args.json:
        print(json.dumps(results, indent=2, default=str))
        return

    # Group by portal
    by_portal: dict[str, list[dict]] = {}
    for r in results:
        by_portal.setdefault(r["portal"], []).append(r)

    # Print results
    total_ready = sum(1 for r in results if r["ready"])
    total = len(results)

    mode = "DEEP AUDIT" if args.deep else "SUBMISSION AUDIT"
    print(f"{mode} — {total} entries, {total_ready} ready")
    print("=" * 60)

    for portal in sorted(by_portal.keys()):
        portal_results = by_portal[portal]
        portal_ready = sum(1 for r in portal_results if r["ready"])
        print(f"\n{portal.upper()} ({portal_ready}/{len(portal_results)} ready)")
        print("-" * 40)

        portal_results.sort(key=lambda r: (not r["ready"], r["id"]))

        for r in portal_results:
            print_entry_result(r, verbose=not args.quiet)

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY BY PORTAL:")
    for portal in sorted(by_portal.keys()):
        portal_results = by_portal[portal]
        ready = sum(1 for r in portal_results if r["ready"])
        print(f"  {portal:<12s} {ready}/{len(portal_results)} ready")

    print(f"\n  TOTAL        {total_ready}/{total} ready for submission")

    # Common blockers
    blockers: dict[str, int] = {}
    for r in results:
        if r["ready"]:
            continue
        for check_name, passed in r["results"].items():
            if not passed:
                blockers[check_name] = blockers.get(check_name, 0) + 1

    if blockers:
        print("\nTOP BLOCKERS:")
        for check_name, count in sorted(blockers.items(), key=lambda x: -x[1]):
            label = check_name.replace("_", " ")
            print(f"  {label:<20s} {count} entries")

    if not args.deep:
        print("\nTip: Run with --deep for auth + answer completeness checks")


if __name__ == "__main__":
    main()
