#!/usr/bin/env python3
"""Autofix submission blockers where safe, and report manual blockers clearly.

This command runs deep submission audit checks, applies non-destructive fixes for
common blockers, then re-audits and prints what remains.

Auto-fixable blockers:
  - review_approved: mark staged entries as reviewed
  - answer_file / answers_complete (Greenhouse/Ashby):
      1) refresh answer templates from live schema
      2) auto-fill defaults + generate AI prompt for unresolved fields
      3) re-run answer completeness check

Non-auto-fixable blockers are reported with concrete next actions.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import PIPELINE_DIR_ACTIVE, load_entries, load_submit_config
from review_entry import mark_reviewed
from submission_audit import check_entry

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

ANSWER_PORTALS = {"greenhouse", "ashby"}


@dataclass
class AuditRow:
    entry: dict
    result: dict


def run_cmd(args: list[str]) -> tuple[int, str]:
    """Run a command and return (exit_code, combined_output)."""
    proc = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def deep_audit(portal_filter: str | None = None) -> list[AuditRow]:
    """Return deep audit rows for active entries."""
    config = load_submit_config(strict=False)
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE], include_filepath=True)
    rows: list[AuditRow] = []
    for entry in entries:
        result = check_entry(entry, deep=True, config=config)
        portal = result.get("portal", "")
        if portal_filter and portal != portal_filter:
            continue
        rows.append(AuditRow(entry=entry, result=result))
    return rows


def print_blockers(rows: list[AuditRow], title: str) -> None:
    """Print blocker summary."""
    total = len(rows)
    ready = sum(1 for row in rows if row.result.get("ready"))
    print(f"{title}: {ready}/{total} ready")
    blockers: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.result.get("ready"):
            continue
        for check_name, passed in row.result.get("results", {}).items():
            if not passed:
                blockers[check_name].append(row.result.get("id", "?"))
    if not blockers:
        print("  No blockers found.")
        return
    for check_name, entry_ids in sorted(blockers.items(), key=lambda item: (-len(item[1]), item[0])):
        print(f"  {check_name:<20s} {len(entry_ids):>3} entries")


def _needs_answer_fix(row: AuditRow) -> bool:
    portal = row.result.get("portal", "")
    if portal not in ANSWER_PORTALS:
        return False
    results = row.result.get("results", {})
    return (not results.get("answer_file", True)) or (not results.get("answers_complete", True))


def fix_review_gate(rows: list[AuditRow], reviewer: str, note: str, apply: bool) -> tuple[int, int]:
    """Mark staged entries reviewed when missing review metadata."""
    targets: list[Path] = []
    for row in rows:
        results = row.result.get("results", {})
        status = row.result.get("status", "")
        if status == "staged" and not results.get("review_approved", True):
            filepath = row.entry.get("_filepath")
            if filepath:
                targets.append(Path(filepath))

    if not targets:
        print("Review gate: no fixable entries.")
        return 0, 0

    fixed = 0
    failed = 0
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"Review gate ({mode}): {len(targets)} entr(y/ies)")
    for filepath in sorted(targets):
        if not apply:
            print(f"  would mark reviewed: {filepath.stem}")
            continue
        result = mark_reviewed(filepath, reviewer=reviewer, note=note or None, dry_run=False)
        if result.get("ok"):
            fixed += 1
            print(f"  marked reviewed: {filepath.stem}")
        else:
            failed += 1
            print(f"  failed review mark: {filepath.stem}")
    if not apply:
        fixed = len(targets)
    return fixed, failed


def _portal_script_name(portal: str) -> str:
    if portal == "greenhouse":
        return "greenhouse_submit.py"
    if portal == "ashby":
        return "ashby_submit.py"
    raise ValueError(f"Unsupported answer portal: {portal}")


def fix_answer_blockers(rows: list[AuditRow], apply: bool) -> tuple[int, int]:
    """Refresh answers and run auto-answer prompt generation for ATS entries."""
    targets = [row for row in rows if _needs_answer_fix(row)]
    if not targets:
        print("Answer blockers: no fixable entries.")
        return 0, 0

    fixed = 0
    failed = 0
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"Answer blockers ({mode}): {len(targets)} entr(y/ies)")

    for row in sorted(targets, key=lambda r: r.result.get("id", "")):
        eid = row.result.get("id", "?")
        portal = row.result.get("portal", "")
        script_name = _portal_script_name(portal)
        init_cmd = [PYTHON, str(SCRIPTS_DIR / script_name), "--target", eid, "--init-answers", "--force"]
        auto_cmd = [PYTHON, str(SCRIPTS_DIR / "answer_questions.py"), "--target", eid]
        check_cmd = [PYTHON, str(SCRIPTS_DIR / script_name), "--target", eid, "--check-answers"]

        if not apply:
            print(f"  [{eid}] would run: {' '.join(init_cmd)}")
            print(f"  [{eid}] would run: {' '.join(auto_cmd)}")
            print(f"  [{eid}] would run: {' '.join(check_cmd)}")
            continue

        init_code, init_out = run_cmd(init_cmd)
        auto_code, auto_out = run_cmd(auto_cmd)
        check_code, check_out = run_cmd(check_cmd)

        if init_code == 0 and auto_code == 0 and check_code == 0:
            fixed += 1
            print(f"  fixed: {eid}")
        else:
            failed += 1
            print(f"  unresolved: {eid}")
            if init_code != 0:
                print(f"    init-answers failed (exit {init_code})")
            if auto_code != 0:
                print(f"    answer_questions failed (exit {auto_code})")
            if check_code != 0:
                print(f"    check-answers failed (exit {check_code})")
            for label, text in (("init", init_out), ("auto", auto_out), ("check", check_out)):
                if text:
                    first = text.splitlines()[0]
                    print(f"    {label}: {first[:220]}")

    if not apply:
        fixed = len(targets)
    return fixed, failed


def print_manual_next_steps(rows: list[AuditRow]) -> None:
    """Print actionable manual remediation for remaining blockers."""
    unresolved = [row for row in rows if not row.result.get("ready")]
    if not unresolved:
        print("No manual blockers remain.")
        return

    by_check: dict[str, list[AuditRow]] = defaultdict(list)
    for row in unresolved:
        for check_name, passed in row.result.get("results", {}).items():
            if not passed:
                by_check[check_name].append(row)

    print("Manual next steps:")
    if "auth_configured" in by_check:
        portals = sorted({row.result.get("portal", "?") for row in by_check["auth_configured"]})
        print("  auth_configured:")
        print("    Add missing API credentials to scripts/.submit-config.yaml:")
        if "greenhouse" in portals:
            print("      greenhouse_api_key: <key>")
        if "ashby" in portals:
            print("      ashby_api_keys: {company: <key>, ...}")
        if "lever" in portals:
            print("      lever_api_keys: {company: <key>, ...}")

    if "answers_complete" in by_check or "answer_file" in by_check:
        print("  answers_complete / answer_file:")
        print("    Fill unresolved fields in scripts/.greenhouse-answers/*.yaml and scripts/.ashby-answers/*.yaml")
        print("    Prompt files are in scripts/.alchemize-work/<entry-id>/answers-prompt.md")

    if "review_approved" in by_check:
        print("  review_approved:")
        print("    Mark staged entries reviewed:")
        print("      .venv/bin/python scripts/review_entry.py --all-staged --reviewer <you>")

    if "has_target_url" in by_check:
        print("  has_target_url:")
        print("    Set target.application_url (or target.email for email portal) in entry YAML.")

    if "resume_pdf" in by_check or "cover_letter" in by_check:
        print("  resume_pdf / cover_letter:")
        print("    Ensure submission.materials_attached has a valid PDF resume and variant_ids.cover_letter is set.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autofix submission blockers where safe, then print manual blockers"
    )
    parser.add_argument("--apply", action="store_true", help="Apply safe fixes (default is dry-run)")
    parser.add_argument("--portal", help="Filter by portal type (greenhouse, ashby, lever, custom)")
    parser.add_argument("--reviewer", default="4jp", help="Reviewer name used for review_approved fixes")
    parser.add_argument("--note", default="autofix-unblocker", help="Review note when marking entries reviewed")
    parser.add_argument(
        "--skip-review",
        action="store_true",
        help="Skip auto-fixing review_approved blockers",
    )
    parser.add_argument(
        "--skip-answers",
        action="store_true",
        help="Skip auto-fixing answer_file/answers_complete blockers",
    )
    args = parser.parse_args()

    before = deep_audit(portal_filter=args.portal)
    print_blockers(before, "Before")
    print()

    review_fixed = review_failed = 0
    answer_fixed = answer_failed = 0

    if not args.skip_review:
        review_fixed, review_failed = fix_review_gate(
            before,
            reviewer=args.reviewer,
            note=args.note,
            apply=args.apply,
        )
        print()

    if not args.skip_answers:
        answer_fixed, answer_failed = fix_answer_blockers(before, apply=args.apply)
        print()

    after = deep_audit(portal_filter=args.portal)
    print_blockers(after, "After")
    print()

    print("Autofix summary:")
    mode = "applied" if args.apply else "planned"
    print(f"  review fixes {mode}: {review_fixed}")
    print(f"  review fixes failed:  {review_failed}")
    print(f"  answer fixes {mode}: {answer_fixed}")
    print(f"  answer fixes failed:  {answer_failed}")
    print()

    print_manual_next_steps(after)


if __name__ == "__main__":
    main()
