#!/usr/bin/env python3
"""Verify that CANONICAL metrics in recruiter_filter.py match actual system state.

Checks repo counts (via GitHub API) and CI/CD workflow counts (via filesystem find)
against the CANONICAL dict, then reports drift.

Usage:
    python scripts/verify_canonical.py            # Human-readable report
    python scripts/verify_canonical.py --json     # Machine-readable JSON output
    python scripts/verify_canonical.py --update   # Update CANONICAL in recruiter_filter.py (prompts first)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
RECRUITER_FILTER = SCRIPTS_DIR / "recruiter_filter.py"
WORKSPACE = Path.home() / "Workspace"

# GitHub orgs that make up the ORGANVM system + personal account.
# Order matters only for display; counts are summed.
ORGS = [
    "meta-organvm",
    "ivviiviivvi",
    "omni-dromenon-machina",
    "labores-profani-crux",
    "4444j99",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str], *, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
    )


def gh_repo_count(org: str) -> int | None:
    """Return public + private repo count for *org* using gh api, or None on error."""
    result = run(["gh", "api", f"orgs/{org}", "--jq", ".public_repos,.total_private_repos"])
    if result.returncode != 0:
        # Fall back: try user endpoint (for personal accounts like 4444j99)
        result = run(["gh", "api", f"users/{org}", "--jq", ".public_repos"])
        if result.returncode != 0:
            return None
        try:
            return int(result.stdout.strip())
        except ValueError:
            return None
    try:
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        return sum(int(x) for x in lines)
    except (ValueError, IndexError):
        return None


def count_cicd_workflows() -> int:
    """Count .github/workflows/*.yml files across ~/Workspace/ using find."""
    result = run([
        "find",
        str(WORKSPACE),
        "-path", "*/.github/workflows/*.yml",
        "-not", "-path", "*/node_modules/*",
        "-not", "-path", "*/.venv/*",
    ])
    if result.returncode != 0:
        return -1
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    return len(lines)


def load_canonical() -> dict:
    """Parse the CANONICAL dict from recruiter_filter.py using regex."""
    src = RECRUITER_FILTER.read_text()
    # Find the block between CANONICAL = { ... }
    m = re.search(r"^CANONICAL\s*=\s*\{(.+?)^\}", src, re.MULTILINE | re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    # Parse key: value pairs — handles int and string values
    result: dict = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        km = re.match(r'"(\w+)"\s*:\s*(.+?)(?:,\s*(?:#.*)?)?\s*$', line)
        if not km:
            continue
        key = km.group(1)
        raw = km.group(2).strip().rstrip(",").strip()
        # String value
        if raw.startswith('"') or raw.startswith("'"):
            result[key] = raw.strip('"').strip("'")
        else:
            try:
                result[key] = int(raw)
            except ValueError:
                result[key] = raw
    return result


def update_canonical_in_file(key: str, new_value: int | str) -> bool:
    """Update a single key in the CANONICAL dict in recruiter_filter.py."""
    src = RECRUITER_FILTER.read_text()
    # Match the exact line for this key
    if isinstance(new_value, int):
        replacement = f'    "{key}": {new_value},'
        pattern = rf'^(\s*"{re.escape(key)}"\s*:\s*)\d+(,.*)?$'
    else:
        replacement = f'    "{key}": "{new_value}",'
        pattern = rf'^(\s*"{re.escape(key)}"\s*:\s*)["\'].*?["\'](,.*)?$'

    new_src, count = re.subn(pattern, replacement, src, flags=re.MULTILINE)
    if count == 0:
        return False
    RECRUITER_FILTER.write_text(new_src)
    return True


# ---------------------------------------------------------------------------
# Core verification
# ---------------------------------------------------------------------------

def verify() -> dict:
    """Run all checks. Returns structured results dict."""
    canonical = load_canonical()

    results = {
        "canonical_loaded": bool(canonical),
        "checks": [],
        "errors": [],
    }

    # --- Repo count ---
    org_counts: dict[str, int | None] = {}
    for org in ORGS:
        count = gh_repo_count(org)
        org_counts[org] = count

    org_errors = [org for org, c in org_counts.items() if c is None]
    successful = {org: c for org, c in org_counts.items() if c is not None}
    actual_repos = sum(successful.values()) if successful else None

    canonical_repos = canonical.get("repos")
    repo_check: dict = {
        "key": "repos",
        "canonical": canonical_repos,
        "actual": actual_repos,
        "org_breakdown": org_counts,
        "partial": bool(org_errors),
        "ok": None,
    }
    if actual_repos is not None and canonical_repos is not None:
        repo_check["ok"] = (actual_repos == canonical_repos)
    if org_errors:
        results["errors"].append(f"Could not fetch repo counts for: {', '.join(org_errors)}")
    results["checks"].append(repo_check)

    # --- CI/CD workflow count ---
    actual_cicd = count_cicd_workflows()
    canonical_cicd = canonical.get("cicd")
    cicd_check: dict = {
        "key": "cicd",
        "canonical": canonical_cicd,
        "actual": actual_cicd if actual_cicd >= 0 else None,
        "ok": None,
    }
    if actual_cicd >= 0 and canonical_cicd is not None:
        cicd_check["ok"] = (actual_cicd == canonical_cicd)
    elif actual_cicd < 0:
        results["errors"].append("find command failed for CI/CD workflow count")
    results["checks"].append(cicd_check)

    # Aggregate pass/fail
    checked = [c for c in results["checks"] if c["ok"] is not None]
    results["all_ok"] = all(c["ok"] for c in checked) if checked else False
    results["drift_count"] = sum(1 for c in checked if not c["ok"])

    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_report(results: dict) -> None:
    ok_sym = "OK"
    fail_sym = "DRIFT"

    print("Canonical Metrics Verification")
    print("=" * 50)

    if not results["canonical_loaded"]:
        print("ERROR: Could not load CANONICAL dict from recruiter_filter.py")
        return

    for check in results["checks"]:
        key = check["key"]
        canonical = check["canonical"]
        actual = check["actual"]
        ok = check["ok"]
        partial = check.get("partial", False)

        if ok is None:
            status = "SKIP"
        elif ok:
            status = ok_sym
        else:
            status = fail_sym

        line = f"  [{status}]  {key}: canonical={canonical}, actual={actual}"
        if partial:
            line += "  (partial — some orgs unreachable)"
        print(line)

        # Show org breakdown for repos
        if key == "repos" and "org_breakdown" in check:
            for org, count in check["org_breakdown"].items():
                marker = "?" if count is None else str(count)
                print(f"           {org}: {marker}")

    print()
    if results["errors"]:
        print("Errors encountered:")
        for e in results["errors"]:
            print(f"  - {e}")
        print()

    if results["all_ok"]:
        print("All checks passed. CANONICAL is up to date.")
    else:
        drift = results["drift_count"]
        print(f"Drift detected: {drift} metric(s) differ from canonical values.")
        print("Run with --update to apply corrections.")


# ---------------------------------------------------------------------------
# Update mode
# ---------------------------------------------------------------------------

def do_update(results: dict) -> int:
    drifted = [c for c in results["checks"] if c["ok"] is False and c["actual"] is not None]
    if not drifted:
        print("No actionable drift found. Nothing to update.")
        return 0

    print("The following CANONICAL values would be updated:")
    for c in drifted:
        print(f"  {c['key']}: {c['canonical']} → {c['actual']}")
    print()

    try:
        answer = input("Apply updates to recruiter_filter.py? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return 1

    if answer != "y":
        print("Aborted.")
        return 1

    updated = []
    failed = []
    for c in drifted:
        ok = update_canonical_in_file(c["key"], c["actual"])
        if ok:
            updated.append(c["key"])
        else:
            failed.append(c["key"])

    if updated:
        print(f"Updated: {', '.join(updated)}")
    if failed:
        print(f"Failed to update (regex did not match): {', '.join(failed)}")
        return 1

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify CANONICAL metrics in recruiter_filter.py against actual system state."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_out",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update CANONICAL in recruiter_filter.py where drift is detected (prompts for confirmation)",
    )
    args = parser.parse_args()

    results = verify()

    if args.json_out:
        print(json.dumps(results, indent=2))
    elif args.update:
        print_report(results)
        print()
        return do_update(results)
    else:
        print_report(results)

    return 0 if results["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
