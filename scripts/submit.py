#!/usr/bin/env python3
"""Generate portal-ready submission checklists and record submissions.

The last mile: produces exactly what to paste into each portal field,
validates counts against limits, and records submissions to the pipeline
and conversion log.

Usage:
    python scripts/submit.py --target artadia-nyc          # Generate checklist
    python scripts/submit.py --target artadia-nyc --open    # Also open portal URL
    python scripts/submit.py --target artadia-nyc --record  # Record after submitting
    python scripts/submit.py --check artadia-nyc            # Pre-submit validation only
"""

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

from pipeline_lib import (
    BLOCKS_DIR, MATERIALS_DIR, PIPELINE_DIR_ACTIVE, PIPELINE_DIR_SUBMITTED,
    SIGNALS_DIR, REPO_ROOT,
    load_entry_by_id, load_profile, load_legacy_script,
    strip_markdown, count_words, count_chars,
    get_deadline, days_until, get_effort,
)


# --- Content resolution ---


def load_block(block_path: str) -> str | None:
    """Load a block file by its reference path."""
    full_path = BLOCKS_DIR / block_path
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if full_path.exists():
        return full_path.read_text().strip()
    return None


def resolve_field_content(
    field_name: str,
    entry: dict,
    profile: dict | None,
    legacy: dict | None,
) -> tuple[str | None, str]:
    """Resolve content for a portal field from available sources.

    Priority: legacy script > entry blocks > profile content.

    Returns:
        (content, source) tuple. source is one of "legacy", "block:<path>", "profile".
    """
    # Priority 1: Legacy submission script (field-specific paste-ready content)
    if legacy and field_name in legacy:
        return legacy[field_name], "legacy"

    # Priority 2: Entry blocks_used
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        blocks_used = submission.get("blocks_used", {})
        if isinstance(blocks_used, dict) and field_name in blocks_used:
            content = load_block(blocks_used[field_name])
            if content:
                return content, f"block:{blocks_used[field_name]}"

    # Priority 3: Profile content
    if profile:
        from draft import get_profile_content
        content = get_profile_content(profile, field_name, "medium")
        if content:
            return content, "profile"

    return None, ""


# --- Checklist generation ---


def generate_checklist(
    entry: dict,
    profile: dict | None,
    legacy: dict | None,
) -> tuple[str, list[str]]:
    """Generate a portal-ready submission checklist.

    Returns:
        (checklist_text, issues) tuple.
    """
    issues = []
    lines = []

    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    org = entry.get("target", {}).get("organization", "")
    portal_url = entry.get("target", {}).get("application_url", "")
    portal_type = entry.get("target", {}).get("portal", "")

    dl_date, dl_type = get_deadline(entry)
    dl_str = ""
    if dl_date:
        d = days_until(dl_date)
        if d < 0:
            dl_str = f"EXPIRED {abs(d)} days ago"
            issues.append(f"Deadline expired {abs(d)} days ago")
        elif d == 0:
            dl_str = "TODAY"
        else:
            dl_str = f"{d} days"
    elif dl_type in ("rolling", "tba"):
        dl_str = dl_type

    lines.append(f"SUBMISSION CHECKLIST: {name}")
    lines.append(f"Organization: {org}")
    if portal_url:
        lines.append(f"Portal: {portal_url}")
    if portal_type:
        lines.append(f"Platform: {portal_type}")
    if dl_str:
        deadline_date_str = dl_date.isoformat() if dl_date else dl_type
        lines.append(f"Deadline: {deadline_date_str} ({dl_str})")
    lines.append(f"Generated: {date.today().isoformat()}")
    lines.append("")

    # Determine required fields from profile submission_format
    fields = []
    if profile:
        from draft import parse_submission_format
        format_str = profile.get("submission_format", "")
        parsed = parse_submission_format(format_str)
        fields = parsed.get("fields", [])

    # If no parsed fields, try to infer from legacy script sections
    if not fields and legacy:
        for section_name in legacy:
            fields.append({"name": section_name, "word_limit": None})

    # If still no fields, use entry's blocks_used keys
    if not fields:
        submission = entry.get("submission", {})
        if isinstance(submission, dict):
            blocks_used = submission.get("blocks_used", {})
            if isinstance(blocks_used, dict):
                for key in blocks_used:
                    fields.append({"name": key, "word_limit": None})

    if not fields:
        lines.append("WARNING: No fields identified for this submission.")
        lines.append("Check profile submission_format or add blocks_used to entry.")
        issues.append("No submission fields identified")
        return "\n".join(lines), issues

    lines.append("=" * 60)
    lines.append("")

    # Generate each field
    for field in fields:
        field_name = field["name"]
        word_limit = field.get("word_limit")
        title = field_name.replace("_", " ").upper()

        content, source = resolve_field_content(
            field_name, entry, profile, legacy,
        )

        limit_str = f" (target: ~{word_limit} words)" if word_limit else ""
        lines.append(f"[ ] {title}{limit_str}")

        if content:
            plain = strip_markdown(content)
            wc = count_words(plain)
            cc = count_chars(plain)

            # Indent content for readability
            for content_line in content.split("\n"):
                lines.append(f"    {content_line}")
            lines.append("")

            # Count validation
            status = "ok"
            if word_limit:
                if wc > word_limit * 1.1:
                    status = f"OVER by {wc - word_limit}w"
                    issues.append(f"{title}: {wc}w exceeds ~{word_limit}w limit")
                elif wc < word_limit * 0.5:
                    status = f"UNDER 50% target"
                    issues.append(f"{title}: {wc}w is under 50% of ~{word_limit}w target")

            check = "!" if status != "ok" else "ok"
            lines.append(f"    -- {wc} words, {cc} chars [{check}] (source: {source})")
        else:
            lines.append(f"    [MISSING — no content found for: {field_name}]")
            issues.append(f"Missing content: {field_name}")

        lines.append("")

    # Materials section
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        materials = submission.get("materials_attached", [])
        portfolio_url = submission.get("portfolio_url", "")

        if materials or portfolio_url:
            lines.append("[ ] MATERIALS")
            if portfolio_url:
                lines.append(f"    Portfolio: {portfolio_url}")
            for m in (materials or []):
                mat_path = MATERIALS_DIR / m
                exists = mat_path.exists()
                status = "ok" if exists else "NOT FOUND"
                lines.append(f"    File: {m} [{status}]")
                if not exists:
                    issues.append(f"Material not found: {m}")
            lines.append("")

    # Validation summary
    lines.append("=" * 60)
    lines.append("PRE-SUBMIT VALIDATION:")

    # Check required fields
    missing_content = [i for i in issues if i.startswith("Missing content")]
    if not missing_content:
        lines.append("  + All identified fields have content")
    else:
        lines.append(f"  - {len(missing_content)} field(s) missing content")

    # Check materials
    missing_materials = [i for i in issues if "Material not found" in i]
    if not missing_materials:
        lines.append("  + Materials check passed")
    else:
        lines.append(f"  - {len(missing_materials)} material(s) not found")

    # Check portal URL
    if portal_url:
        lines.append("  + Portal URL set")
    else:
        lines.append("  - No portal URL — set target.application_url")
        issues.append("No portal URL set")

    # Check deadline
    expired = [i for i in issues if "expired" in i.lower()]
    if expired:
        lines.append("  - DEADLINE EXPIRED")
    elif dl_date and days_until(dl_date) <= 2:
        lines.append(f"  ! Deadline in {days_until(dl_date)} day(s) — submit ASAP")

    # Overall
    if not issues:
        lines.append("")
        lines.append("READY TO SUBMIT")
    else:
        lines.append("")
        lines.append(f"{len(issues)} issue(s) found — review before submitting")

    return "\n".join(lines), issues


# --- Record mode ---


def record_submission(filepath: Path, entry: dict) -> None:
    """Record that a submission was completed.

    Updates: status → submitted, timeline.submitted, last_touched.
    Moves file to pipeline/submitted/.
    Appends to conversion-log.yaml.
    """
    today_str = date.today().isoformat()
    content = filepath.read_text()

    # Update status
    content = re.sub(
        r'^(status:\s+).*$',
        r'\1submitted',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Update last_touched
    if re.search(r'^last_touched:', content, re.MULTILINE):
        content = re.sub(
            r'^(last_touched:\s+).*$',
            rf"\1'{today_str}'",
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        content = content.rstrip() + f"\nlast_touched: '{today_str}'\n"

    # Update timeline.submitted
    pattern = r'^(\s+submitted:\s+).*$'
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(
            pattern,
            rf"\1'{today_str}'",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    filepath.write_text(content)

    # Move to submitted directory
    PIPELINE_DIR_SUBMITTED.mkdir(parents=True, exist_ok=True)
    dest = PIPELINE_DIR_SUBMITTED / filepath.name
    filepath.rename(dest)

    # Append to conversion log
    _append_conversion_log(entry, today_str)

    print(f"Recorded: {entry.get('name', '?')}")
    print(f"  Status: submitted")
    print(f"  Date: {today_str}")
    print(f"  Moved: {filepath.name} -> pipeline/submitted/")
    print(f"  Conversion log updated")


def _append_conversion_log(entry: dict, submitted_date: str) -> None:
    """Append an entry to signals/conversion-log.yaml."""
    log_path = SIGNALS_DIR / "conversion-log.yaml"

    if log_path.exists():
        log_data = yaml.safe_load(log_path.read_text())
    else:
        log_data = {}

    if not isinstance(log_data, dict):
        log_data = {}
    if not isinstance(log_data.get("entries"), list):
        log_data["entries"] = []

    # Build blocks_used list
    submission = entry.get("submission", {})
    blocks_list = []
    if isinstance(submission, dict):
        blocks_used = submission.get("blocks_used", {})
        if isinstance(blocks_used, dict):
            blocks_list = list(blocks_used.values())

    variant_id = None
    if isinstance(submission, dict):
        variant_ids = submission.get("variant_ids", {})
        if isinstance(variant_ids, dict) and variant_ids:
            variant_id = list(variant_ids.values())[0]

    log_entry = {
        "id": entry.get("id"),
        "submitted": submitted_date,
        "track": entry.get("track"),
        "identity_position": entry.get("fit", {}).get("identity_position"),
        "blocks_used": blocks_list or None,
        "variant_id": variant_id,
        "outcome": None,
        "response_date": None,
        "time_to_response_days": None,
        "feedback": None,
    }

    log_data["entries"].append(log_entry)

    log_path.write_text(yaml.dump(log_data, default_flow_style=False, sort_keys=False))


# --- Main ---


def main():
    parser = argparse.ArgumentParser(
        description="Generate portal-ready submission checklists and record submissions"
    )
    parser.add_argument("--target", help="Target ID for checklist generation")
    parser.add_argument("--check", metavar="TARGET_ID",
                        help="Pre-submit validation only (no full checklist)")
    parser.add_argument("--open", action="store_true",
                        help="Open portal URL in browser after generating checklist")
    parser.add_argument("--record", action="store_true",
                        help="Record that submission was completed (updates YAML + log)")
    args = parser.parse_args()

    target_id = args.target or args.check
    if not target_id:
        parser.error("Specify --target <id> or --check <id>")

    filepath, entry = load_entry_by_id(target_id)
    if not entry:
        print(f"Error: No pipeline entry found for '{target_id}'", file=sys.stderr)
        sys.exit(1)

    profile = load_profile(target_id)
    legacy = load_legacy_script(target_id)

    if args.record:
        if not filepath:
            print("Error: Cannot record — no file path found", file=sys.stderr)
            sys.exit(1)

        # Confirm before recording
        name = entry.get("name", target_id)
        print(f"Record submission for: {name}")
        print(f"  This will:")
        print(f"    - Set status to 'submitted'")
        print(f"    - Set timeline.submitted to {date.today().isoformat()}")
        print(f"    - Move {filepath.name} to pipeline/submitted/")
        print(f"    - Append to signals/conversion-log.yaml")
        print()
        try:
            confirm = input("Proceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)

        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

        record_submission(filepath, entry)
        return

    checklist, issues = generate_checklist(entry, profile, legacy)

    if args.check:
        # Validation only — just report issues
        name = entry.get("name", target_id)
        if not issues:
            print(f"PASS: {name} — ready to submit")
        else:
            print(f"FAIL: {name} — {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")
        sys.exit(1 if issues else 0)

    print(checklist)

    if args.open:
        portal_url = entry.get("target", {}).get("application_url", "")
        if portal_url:
            try:
                subprocess.run(["open", portal_url], check=False)
            except FileNotFoundError:
                print(f"\nOpen manually: {portal_url}")
        else:
            print("\nNo portal URL set — cannot open browser.")


if __name__ == "__main__":
    main()
