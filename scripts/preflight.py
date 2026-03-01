#!/usr/bin/env python3
"""Batch submission readiness checker for staged pipeline entries.

Validates that staged entries are actually ready to submit by checking
profiles, required fields, materials, deadlines, and portal URLs.

Usage:
    python scripts/preflight.py                       # Check all staged entries
    python scripts/preflight.py --target artadia-nyc  # Check one entry
    python scripts/preflight.py --status qualified     # Check qualified entries too
"""

import argparse
import sys

from pipeline_lib import (
    MATERIALS_DIR,
    count_words,
    days_until,
    get_deadline,
    load_entries,
    load_entry_by_id,
    load_legacy_script,
    load_profile,
    strip_markdown,
)

# Reasonable word limits per field for flagging overruns
TYPICAL_LIMITS = {
    "artist_statement": 500,
    "bio": 300,
    "project_description": 750,
    "cover_letter": 500,
    "pitch_email": 400,
}


def check_entry(entry: dict) -> tuple[list[str], list[str]]:
    """Run all preflight checks on a single entry.

    Returns (errors, warnings). Errors block submission; warnings are advisory.
    """
    errors = []
    warnings = []
    entry_id = entry.get("id", "?")

    # 1. Profile exists
    profile = load_profile(entry_id)
    if not profile:
        errors.append("no profile found")

    # 2. Submission format parseable
    has_fields = False
    if profile:
        from draft import parse_submission_format
        format_str = profile.get("submission_format", "")
        parsed = parse_submission_format(format_str)
        fields = parsed.get("fields", [])
        if fields:
            has_fields = True

    # 3. Check content availability for required fields
    legacy = load_legacy_script(entry_id)
    submission = entry.get("submission", {})
    blocks_used = {}
    if isinstance(submission, dict):
        blocks_used = submission.get("blocks_used", {})
        if not isinstance(blocks_used, dict):
            blocks_used = {}

    if has_fields:
        from submit import resolve_field_content
        for field in fields:
            field_name = field["name"]
            content, _ = resolve_field_content(field_name, entry, profile, legacy)
            if not content:
                errors.append(f"missing content: {field_name}")
            elif field.get("word_limit"):
                wc = count_words(strip_markdown(content))
                if wc > field["word_limit"] * 1.1:
                    warnings.append(f"{field_name}: {wc}w exceeds ~{field['word_limit']}w limit")
    elif not blocks_used and not legacy:
        warnings.append("no submission fields identified (no format, blocks, or legacy script)")

    # 4. Materials check
    if isinstance(submission, dict):
        materials = submission.get("materials_attached", [])
        if isinstance(materials, list):
            for m in materials:
                mat_path = MATERIALS_DIR / m
                if not mat_path.exists():
                    errors.append(f"material not found: {m}")

    # 4b. Base resume check — tailored resumes should be used, not base templates
    if isinstance(submission, dict):
        materials = submission.get("materials_attached", [])
        if isinstance(materials, list):
            for m in materials:
                if "resumes/base/" in m:
                    warnings.append(f"using base resume: {m} — tailor with tailor_resume.py")

    # 5. Portfolio URL (advisory — not all applications require it)
    if isinstance(submission, dict):
        portfolio = submission.get("portfolio_url")
        if not portfolio:
            warnings.append("no portfolio_url set")

    # 6. Portal URL (error — required to actually submit)
    target = entry.get("target", {})
    if isinstance(target, dict):
        app_url = target.get("application_url")
        if not app_url:
            errors.append("no application_url set")

    # 7. Deadline check
    dl_date, dl_type = get_deadline(entry)
    if dl_date:
        d = days_until(dl_date)
        if d < 0:
            errors.append(f"deadline expired {abs(d)} days ago")

    return errors, warnings


def readiness_score(entry: dict) -> int:
    """Compute a 0-5 readiness score for a pipeline entry.

    Points:
      +1  Resume: materials_attached has a tailored (non-base) resume
      +1  Blocks: blocks_used is populated (not null/empty)
      +1  Cover letter: variant_ids.cover_letter exists
      +1  Portal fields: portal_fields present, OR profile found
      +1  Deadline safe: deadline >3 days away, or rolling/tba/none
    """
    score = 0
    entry_id = entry.get("id", "?")
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        submission = {}

    # Resume: has a tailored (non-base) resume
    materials = submission.get("materials_attached", [])
    if isinstance(materials, list):
        has_tailored = any(
            ("resume" in m.lower() or "cv" in m.lower()) and "resumes/base/" not in m
            for m in materials
        )
        if has_tailored:
            score += 1

    # Blocks: blocks_used populated
    blocks = submission.get("blocks_used", {})
    if isinstance(blocks, dict) and blocks:
        score += 1

    # Cover letter variant
    variant_ids = submission.get("variant_ids", {})
    if isinstance(variant_ids, dict) and variant_ids.get("cover_letter"):
        score += 1

    # Portal fields or profile
    portal_fields = entry.get("portal_fields")
    has_portal = portal_fields and isinstance(portal_fields, dict) and portal_fields.get("fields")
    if has_portal:
        score += 1
    else:
        profile = load_profile(entry_id)
        if profile:
            score += 1

    # Deadline safe (>7 days matches CLAUDE.md urgency protocol, or rolling/tba/none)
    dl_date, dl_type = get_deadline(entry)
    if dl_date:
        d = days_until(dl_date)
        if d > 7:
            score += 1
    elif dl_type in ("rolling", "tba") or dl_type is None:
        score += 1

    return score


def run_preflight(entries: list[dict], single_target: str | None = None):
    """Run preflight checks and display results."""
    if single_target:
        matched = [e for e in entries if e.get("id") == single_target]
        if not matched:
            # Try loading directly
            _, entry = load_entry_by_id(single_target)
            if entry:
                matched = [entry]
        if not matched:
            print(f"Error: No entry found for '{single_target}'", file=sys.stderr)
            sys.exit(1)
        entries_to_check = matched
    else:
        entries_to_check = entries

    if not entries_to_check:
        print("No entries to check.")
        return

    print(f"PREFLIGHT: {len(entries_to_check)} entries")
    print("=" * 60)

    ready_count = 0
    warn_count = 0
    fail_count = 0

    for entry in entries_to_check:
        entry_id = entry.get("id", "?")
        name = entry.get("name", entry_id)
        errors, warnings = check_entry(entry)

        dl_date, dl_type = get_deadline(entry)
        dl_str = ""
        if dl_date:
            d = days_until(dl_date)
            if d < 0:
                dl_str = f"expired {abs(d)}d ago"
            elif d == 0:
                dl_str = "TODAY"
            else:
                dl_str = f"{d}d to deadline"
        elif dl_type in ("rolling", "tba"):
            dl_str = dl_type

        rscore = readiness_score(entry)

        if errors:
            fail_count += 1
            print(f"  ✗ {name} — {len(errors)} error(s) ({dl_str}) [{rscore}/5]")
            for e in errors:
                print(f"      [ERROR] {e}")
            for w in warnings:
                print(f"      [WARN]  {w}")
        elif warnings:
            warn_count += 1
            print(f"  ~ {name} — {len(warnings)} warning(s) ({dl_str}) [{rscore}/5]")
            for w in warnings:
                print(f"      [WARN] {w}")
        else:
            ready_count += 1
            print(f"  ✓ {name} — READY ({dl_str}) [{rscore}/5]")

    print("=" * 60)
    print(f"Ready: {ready_count} | Warnings: {warn_count} | Errors: {fail_count} | "
          f"Total: {ready_count + warn_count + fail_count}")

    if fail_count > 0:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Batch submission readiness checker"
    )
    parser.add_argument("--target", help="Check a specific entry by ID")
    parser.add_argument("--status", default="staged",
                        help="Filter by status (default: staged)")
    args = parser.parse_args()

    if args.target:
        entries = load_entries()
        run_preflight(entries, single_target=args.target)
    else:
        entries = load_entries()
        filtered = [e for e in entries if e.get("status") == args.status]
        run_preflight(filtered)


if __name__ == "__main__":
    main()
