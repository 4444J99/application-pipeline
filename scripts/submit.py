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
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml
from pipeline_lib import (
    BLOCKS_DIR,
    MATERIALS_DIR,
    PIPELINE_DIR_SUBMITTED,
    REPO_ROOT,
    SIGNALS_DIR,
    VARIANTS_DIR,
    count_chars,
    count_words,
    days_until,
    get_deadline,
    get_operator_name,
    load_block,
    load_entry_by_id,
    load_legacy_script,
    load_profile,
    strip_markdown,
    update_yaml_field,
)
from pipeline_lib import (
    update_last_touched as update_last_touched_content,
)

# --- Content resolution ---


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

    # Priority 2.5: Variant files (e.g. cover_letter → variants/cover-letters/...)
    if isinstance(submission, dict):
        variant_ids = submission.get("variant_ids", {})
        if isinstance(variant_ids, dict) and field_name in variant_ids:
            variant_path = VARIANTS_DIR / variant_ids[field_name]
            if not variant_path.suffix:
                variant_path = variant_path.with_suffix(".md")
            if variant_path.exists():
                return variant_path.read_text().strip(), f"variant:{variant_ids[field_name]}"

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

    # If still no fields, use entry's portal_fields.fields
    if not fields:
        portal_fields = entry.get("portal_fields", {})
        if isinstance(portal_fields, dict):
            pf_list = portal_fields.get("fields", [])
            if isinstance(pf_list, list):
                for pf in pf_list:
                    if isinstance(pf, dict) and "name" in pf:
                        fields.append({"name": pf["name"], "word_limit": pf.get("word_limit")})

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
                    status = "UNDER 50% target"
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
                if "resumes/base/" in str(m):
                    status = "BASE RESUME"
                    lines.append(f"    File: {m} [{status}]")
                    issues.append(f"BASE RESUME — must use tailored resume, not {m}")
                elif not exists:
                    status = "NOT FOUND"
                    lines.append(f"    File: {m} [{status}]")
                    issues.append(f"Material not found: {m}")
                else:
                    lines.append(f"    File: {m} [ok]")
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

    # Post-submission reminder
    lines.append("")
    lines.append("POST-SUBMISSION:")
    lines.append(f"  Record outcome: python scripts/check_outcomes.py "
                 f"--record {entry_id} --outcome <result> --category <cat> --hypothesis '...'")

    return "\n".join(lines), issues


# --- Cover letter quality gate ---

COVER_LETTER_MIN_WORDS = 300
COVER_LETTER_MAX_WORDS = 550
COVER_LETTER_BANNED_PHRASES = [
    "South Florida",  # Wrong location — user is in NYC
    "MCP integration layer",  # MCP is Anthropic's, not OpenAI's
    "I don't have",  # Apologetic framing
    "I haven't",  # Apologetic framing
    "gap I'm being transparent about",  # Apologetic framing
]
COVER_LETTER_REQUIRED_LOCATION = "New York"


def check_cover_letter_quality(entry: dict) -> list[str]:
    """Pre-submission quality check on cover letter content.

    Returns list of issues. Empty list = passes.
    """
    issues = []
    variant = entry.get("submission", {}).get("variant_ids", {}).get("cover_letter", "")
    if not variant:
        issues.append("No cover letter variant assigned")
        return issues

    cl_path = REPO_ROOT / "variants" / f"{variant}.md"
    if not cl_path.exists():
        issues.append(f"Cover letter file not found: {cl_path}")
        return issues

    content = cl_path.read_text()
    words = len(content.split())

    if words < COVER_LETTER_MIN_WORDS:
        issues.append(f"Cover letter too short: {words} words (min {COVER_LETTER_MIN_WORDS})")
    if words > COVER_LETTER_MAX_WORDS:
        issues.append(f"Cover letter too long: {words} words (max {COVER_LETTER_MAX_WORDS})")

    for phrase in COVER_LETTER_BANNED_PHRASES:
        if phrase.lower() in content.lower():
            issues.append(f"Banned phrase found: \"{phrase}\"")

    if COVER_LETTER_REQUIRED_LOCATION not in content:
        issues.append(f"Missing location reference: \"{COVER_LETTER_REQUIRED_LOCATION}\"")

    if content.startswith("#") or content.startswith("---"):
        issues.append("Cover letter starts with markdown header — should be plain text")

    if "Sincerely" not in content and "sincerely" not in content:
        issues.append("Missing closing (\"Sincerely\")")

    return issues


# --- Outreach plan generation ---


def generate_daily_outreach_plan() -> str | None:
    """Generate a consolidated outreach plan for all entries submitted today.

    Reads all submitted entries, filters to today's submissions,
    and produces a markdown document with LinkedIn search URLs,
    connection messages, and follow-up DMs for each.

    Returns the output path, or None if no submissions today.
    """
    from urllib.parse import quote

    today_str = date.today().isoformat()
    today_fmt = date.today().strftime("%B %d, %Y")

    submitted_dir = PIPELINE_DIR_SUBMITTED
    todays_entries = []
    for f in sorted(submitted_dir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        timeline = data.get("timeline", {})
        if isinstance(timeline, dict) and str(timeline.get("submitted", ""))[:10] == today_str:
            todays_entries.append(data)

    if not todays_entries:
        return None

    lines = [
        f"# Outreach Plan — {today_fmt}",
        "",
        f"{len(todays_entries)} applications submitted today. Connect with hiring contacts within 1-3 days.",
        "",
        "---",
        "",
    ]

    for i, entry in enumerate(todays_entries, 1):
        org = entry.get("target", {}).get("organization", "Unknown")
        name = entry.get("name", "Unknown Role")
        url = entry.get("target", {}).get("application_url", "")
        eid = entry.get("id", "?")
        title = name.lower()

        # Derive search terms from role context
        if "forward deployed" in title or "fde" in title:
            terms = ["Head of Forward Deployed Engineering", "Engineering Manager"]
        elif "solutions engineer" in title:
            terms = ["Solutions Engineering Manager", "Head of Solutions"]
        elif "technical writer" in title or "documentation" in title:
            terms = ["Technical Writing Manager", "Head of Documentation"]
        elif "developer advocate" in title or "devrel" in title:
            terms = ["Head of Developer Relations", "DevRel Manager"]
        elif "agent" in title:
            terms = ["Engineering Manager AI", "Head of AI"]
        elif "platform" in title or "infrastructure" in title:
            terms = ["Engineering Manager Platform", "VP Engineering"]
        elif "full stack" in title or "staff" in title:
            terms = ["Engineering Manager", "VP Engineering"]
        else:
            terms = ["Engineering Manager", "VP Engineering"]

        search_urls = []
        for term in terms[:2]:
            q = quote(f"{term} {org}")
            search_urls.append((term, f"https://www.linkedin.com/search/results/people/?keywords={q}&origin=GLOBAL_SEARCH_HEADER"))

        # Role-specific connection message (300 char max)
        role_short = name.replace(f"{org} ", "")
        conn_msg = (
            f"Hi [Name] — 113 repos, 82K files, 23,470 tests, 739K words of governance docs. "
            f"Applied for {role_short}. Would love to connect."
        )
        if len(conn_msg) > 300:
            conn_msg = conn_msg[:297] + "..."

        # Follow-up DM template
        dm_template = (
            f"Thanks for connecting. Context beyond the resume — I maintain a 113-repository "
            f"system across 8 GitHub organizations with automated governance, documentation "
            f"architecture (739K words), and 23,470 tests. Happy to walk through how the "
            f"patterns map to {org}'s work.\n\n"
            f"Portfolio: https://4444j99.github.io/portfolio/\n"
            f"GitHub: https://github.com/meta-organvm"
        )

        # Check for existing contacts at this org
        known_contacts = []
        contacts_path = SIGNALS_DIR / "contacts.yaml"
        if contacts_path.exists():
            try:
                contacts_data = yaml.safe_load(contacts_path.read_text()) or {}
                for contact in contacts_data.get("contacts", []):
                    if isinstance(contact, dict) and contact.get("organization", "").lower() == org.lower():
                        cname = contact.get("name", "?")
                        curl = contact.get("linkedin_url", "")
                        known_contacts.append((cname, curl))
            except Exception:
                pass

        lines.extend([
            f"### [ ] {i}. {org} — {role_short}",
            f"- **Status:** Submitted {today_fmt} (Day 0)",
            f"- **Portal:** {url}",
            "- **Contacts** (connect with 2-3):",
        ])
        if known_contacts:
            for ci, (cname, curl) in enumerate(known_contacts[:3]):
                star = "★ " if ci == 0 else ""
                if curl:
                    lines.append(f"  - {star}**{cname}** — [{curl}]({curl})")
                else:
                    lines.append(f"  - {star}**{cname}**")
        else:
            lines.extend([
                f"  - ★ **[Search: {terms[0]}]** — [Find on LinkedIn]({search_urls[0][1]})",
                f"  - **[Search: {terms[1]}]** — [Find on LinkedIn]({search_urls[1][1]})",
                f'  - **[Recruiter]** — search "{org} recruiter" on LinkedIn',
            ])
        lines.extend([
            "- **Connection message (<300 chars):**",
            f"  > {conn_msg}",
            "- **If accepted — DM:**",
            f"  > {dm_template}",
            f'- **Log:** `python scripts/followup.py --log {eid} --channel linkedin --contact "[Name]" --note "Connection request sent"`',
            "",
            "---",
            "",
        ])

    lines.extend([
        "## Rules",
        "",
        "1. Find the most relevant person — hiring manager > team lead > recruiter",
        "2. Never say \"following up on my application\" — lead with what you bring",
        "3. Log every action with the followup.py command",
        "4. 300 character limit on LinkedIn connection messages",
        "5. If they accept → send a longer DM with portfolio link and specific context",
        "",
    ])

    # Write to applications/ directory
    apps_dir = REPO_ROOT / "applications" / today_str
    apps_dir.mkdir(parents=True, exist_ok=True)
    output_path = apps_dir / "outreach-plan.md"
    output_path.write_text("\n".join(lines))
    return str(output_path)


# --- Record mode ---


def record_submission(filepath: Path, entry: dict) -> None:
    """Record that a submission was completed.

    Runs cover letter quality gate first. Blocks on critical issues.
    Updates: status → submitted, timeline.submitted, last_touched.
    Moves file to pipeline/submitted/.
    Appends to conversion-log.yaml.
    """
    # Quality gate — check cover letter before recording
    cl_issues = check_cover_letter_quality(entry)
    if cl_issues:
        print("  QUALITY GATE — Cover letter issues:")
        for issue in cl_issues:
            print(f"    ✗ {issue}")
        print("  Fix issues before recording submission.")
        return

    today_str = date.today().isoformat()
    content = filepath.read_text()

    # Update status
    content = update_yaml_field(content, "status", "submitted")

    # Update last_touched
    content = update_last_touched_content(content)

    # Update timeline.submitted
    try:
        content = update_yaml_field(
            content, "submitted", f"'{today_str}'", nested=True,
        )
    except ValueError:
        pass  # Field may not exist in this entry

    # Submission governance metadata (audit trail).
    operator = get_operator_name()
    data = yaml.safe_load(content) or {}
    if isinstance(data, dict):
        status_meta = data.get("status_meta")
        if not isinstance(status_meta, dict):
            status_meta = {}
        status_meta["submitted_by"] = operator
        status_meta["submitted_at"] = today_str
        data["status_meta"] = status_meta
        content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    filepath.write_text(content)

    # Move to submitted directory
    PIPELINE_DIR_SUBMITTED.mkdir(parents=True, exist_ok=True)
    dest = PIPELINE_DIR_SUBMITTED / filepath.name
    shutil.move(str(filepath), str(dest))

    # Append to conversion log
    _append_conversion_log(entry, today_str, submitted_by=operator)

    print(f"Recorded: {entry.get('name', '?')}")
    print("  Status: submitted")
    print(f"  Date: {today_str}")
    print(f"  Moved: {filepath.name} -> pipeline/submitted/")
    print("  Conversion log updated")

    # Regenerate daily outreach plan
    outreach_path = generate_daily_outreach_plan()
    if outreach_path:
        print(f"  Outreach plan: {outreach_path}")


def _append_conversion_log(entry: dict, submitted_date: str, submitted_by: str | None = None) -> None:
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

    # Determine composition method
    composition_method = "manual"
    if blocks_list:
        composition_method = "blocks"
    elif variant_id and "alchemized" in str(variant_id):
        composition_method = "alchemized"
    elif isinstance(submission, dict) and submission.get("profile_used"):
        composition_method = "profiles"
    elif isinstance(submission, dict) and submission.get("legacy_script_used"):
        composition_method = "legacy"

    log_entry = {
        "id": entry.get("id"),
        "submitted": submitted_date,
        "submitted_by": submitted_by,
        "track": entry.get("track"),
        "identity_position": entry.get("fit", {}).get("identity_position"),
        "composition_method": composition_method,
        "blocks_used": blocks_list or None,
        "variant_id": variant_id,
        "outcome": None,
        "response_date": None,
        "time_to_response_days": None,
        "feedback": None,
    }

    log_data["entries"].append(log_entry)

    log_path.write_text(yaml.dump(log_data, default_flow_style=False, sort_keys=False))


# --- Metrics freshness check ---


def _check_metrics_freshness(entry: dict) -> list[str]:
    """Check blocks_used for stale metrics. Returns list of issue strings."""
    issues = []
    try:
        from check_metrics import check_file
    except ImportError:
        return issues  # check_metrics not available

    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return issues

    blocks_used = submission.get("blocks_used", {})
    if not isinstance(blocks_used, dict):
        return issues

    for field_name, block_path in blocks_used.items():
        if not isinstance(block_path, str):
            continue
        full_path = BLOCKS_DIR / block_path
        if not full_path.suffix:
            full_path = full_path.with_suffix(".md")
        if not full_path.exists():
            continue

        errors = check_file(full_path)
        for error in errors:
            issues.append(
                f"Stale metric in block '{block_path}': "
                f"{error['metric']} is {error['found']}, expected {error['expected']}"
            )

    return issues


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
        print("  This will:")
        print("    - Set status to 'submitted'")
        print(f"    - Set timeline.submitted to {date.today().isoformat()}")
        print(f"    - Move {filepath.name} to pipeline/submitted/")
        print("    - Append to signals/conversion-log.yaml")
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
        # Validation only — run metrics freshness check on blocks_used
        name = entry.get("name", target_id)
        metric_issues = _check_metrics_freshness(entry)
        all_issues = issues + metric_issues

        if not all_issues:
            print(f"PASS: {name} — ready to submit")
        else:
            print(f"FAIL: {name} — {len(all_issues)} issue(s):")
            for issue in all_issues:
                print(f"  - {issue}")
        sys.exit(1 if all_issues else 0)

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
