#!/usr/bin/env python3
"""Apply engine: readiness check + ATS submission for staged entries.

Validates that all materials (cover letter, resume, answers) are ready,
then submits via the appropriate ATS submitter (Greenhouse, Lever, Ashby).

Usage:
    python scripts/apply_engine.py                         # Readiness check, dry-run
    python scripts/apply_engine.py --yes                   # Submit all ready entries
    python scripts/apply_engine.py --target <id>           # Check/submit single entry
    python scripts/apply_engine.py --json                  # Machine-readable output
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    SIGNALS_DIR,
    load_entries,
    load_entry_by_id,
    resolve_cover_letter,
    resolve_resume,
)

APPLY_HISTORY_PATH = SIGNALS_DIR / "apply-history.yaml"


@dataclass
class ReadinessCheck:
    """Readiness status for a single entry."""

    entry_id: str
    is_ready: bool
    portal: str
    missing: list[str] = field(default_factory=list)
    has_cover_letter: bool = False
    has_resume: bool = False
    has_answers: bool = False
    has_blocks: bool = False


@dataclass
class ApplyResult:
    """Result of an apply operation."""

    checked: list[ReadinessCheck] = field(default_factory=list)
    submitted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def check_readiness(entry: dict) -> ReadinessCheck:
    """Check if an entry has all materials needed for submission."""
    entry_id = entry.get("id", "")
    portal = entry.get("target", {}).get("portal", "")
    missing = []

    has_cover = bool(resolve_cover_letter(entry))
    has_resume = bool(resolve_resume(entry))

    submission = entry.get("submission") or {}
    has_blocks = bool(submission.get("blocks_used"))
    has_answers = True  # Assume OK unless we can verify

    # Check portal-specific answer files
    if portal == "greenhouse":
        answer_path = Path(__file__).resolve().parent / ".greenhouse-answers" / f"{entry_id}.yaml"
        if answer_path.exists():
            text = answer_path.read_text()
            has_answers = "FILL IN" not in text
        else:
            has_answers = True  # No custom questions needed
    elif portal == "ashby":
        answer_path = Path(__file__).resolve().parent / ".ashby-answers" / f"{entry_id}.yaml"
        if answer_path.exists():
            text = answer_path.read_text()
            has_answers = "FILL IN" not in text

    if not has_cover:
        missing.append("cover_letter")
    if not has_resume:
        missing.append("resume")
    if not has_answers:
        missing.append("answers (FILL IN fields remain)")
    if not has_blocks:
        missing.append("blocks_used")
    if not portal:
        missing.append("portal type")

    # Check outreach requirement
    follow_up = entry.get("follow_up") or {}
    outreach_log = follow_up.get("actions_log") or []
    if not outreach_log:
        missing.append("outreach (min 1 action before submission)")

    return ReadinessCheck(
        entry_id=entry_id,
        is_ready=len(missing) == 0,
        portal=portal,
        missing=missing,
        has_cover_letter=has_cover,
        has_resume=has_resume,
        has_answers=has_answers,
        has_blocks=has_blocks,
    )


def _submit_entry(entry: dict) -> tuple[bool, str]:
    """Submit an entry via its portal-specific ATS submitter.

    Returns (success, message).
    """
    portal = entry.get("target", {}).get("portal", "")

    try:
        if portal == "greenhouse":
            from greenhouse_submit import load_config, process_entry
            config = load_config()
            ok = process_entry(entry, config, do_submit=True)
            return ok, "submitted via Greenhouse API" if ok else "Greenhouse submission failed"

        elif portal == "lever":
            from lever_submit import load_config, process_entry
            config = load_config()
            ok = process_entry(entry, config, do_submit=True)
            return ok, "submitted via Lever API" if ok else "Lever submission failed"

        elif portal == "ashby":
            from ashby_submit import load_config, process_entry
            config = load_config()
            ok = process_entry(entry, config, do_submit=True)
            return ok, "submitted via Ashby API" if ok else "Ashby submission failed"

        else:
            return False, f"unsupported portal: {portal}"

    except Exception as e:
        return False, f"submission error: {e}"


def _advance_after_submit(entry_id: str) -> bool:
    """Advance an entry to 'submitted' status after successful ATS submission."""
    filepath, entry = load_entry_by_id(entry_id)
    if not filepath or not entry:
        return False
    if entry.get("status") == "submitted":
        return True  # Already submitted

    try:
        from advance import advance_entry
        return advance_entry(
            Path(filepath), entry_id, "submitted",
            reason="auto-submitted by daily cycle",
        )
    except Exception:
        return False


def apply_ready_entries(
    entry_ids: list[str] | None = None,
    dry_run: bool = True,
) -> ApplyResult:
    """Check readiness and submit staged entries.

    Args:
        entry_ids: Specific entries. None = all staged.
        dry_run: If True, only check readiness without submitting.
    """
    entries = load_entries(dirs=ALL_PIPELINE_DIRS)
    result = ApplyResult()

    for entry in entries:
        eid = entry.get("id", "")
        if entry_ids and eid not in entry_ids:
            continue
        if entry.get("status") != "staged":
            continue

        check = check_readiness(entry)
        result.checked.append(check)

        if not check.is_ready:
            result.skipped.append(eid)
            continue

        if dry_run:
            result.skipped.append(eid)
            continue

        ok, msg = _submit_entry(entry)
        if ok:
            result.submitted.append(eid)
            # Auto-advance to submitted status
            _advance_after_submit(eid)
        else:
            result.errors.append(f"{eid}: {msg}")

    return result


def _log_apply_result(result: ApplyResult, log_path: Path | None = None) -> None:
    """Append apply result to history log."""
    log_path = log_path or APPLY_HISTORY_PATH
    entry = {
        "date": str(date.today()),
        "checked": len(result.checked),
        "submitted": len(result.submitted),
        "skipped": len(result.skipped),
        "errors": len(result.errors),
    }
    existing = []
    if log_path.exists():
        existing = yaml.safe_load(log_path.read_text()) or []
    existing.append(entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        yaml.dump(existing, default_flow_style=False, sort_keys=False)
    )


def main():
    parser = argparse.ArgumentParser(description="Apply engine: readiness + submission")
    parser.add_argument("--yes", action="store_true", help="Execute submissions")
    parser.add_argument("--target", help="Check/submit single entry")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    dry_run = not args.yes
    entry_ids = [args.target] if args.target else None

    result = apply_ready_entries(entry_ids=entry_ids, dry_run=dry_run)

    if not dry_run:
        _log_apply_result(result)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        print(f"\n{'=' * 50}")
        print(f"APPLY RESULTS ({mode})")
        print(f"{'=' * 50}")
        print(f"Checked:   {len(result.checked)}")
        print(f"Submitted: {len(result.submitted)}")
        print(f"Skipped:   {len(result.skipped)}")

        for check in result.checked:
            status = "READY" if check.is_ready else "NOT READY"
            print(f"\n  {check.entry_id} [{check.portal}]: {status}")
            if check.missing:
                for m in check.missing:
                    print(f"    - missing: {m}")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for e in result.errors:
                print(f"  - {e}")


if __name__ == "__main__":
    main()
