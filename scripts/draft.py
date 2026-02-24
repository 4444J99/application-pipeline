#!/usr/bin/env python3
"""Bridge profile content to portal-ready submission drafts.

The missing link: 44 target profiles already contain artist statements,
bios, work samples, and identity narratives at multiple lengths. This
script assembles them into portal-ready documents matching each target's
submission_format.

Usage:
    python scripts/draft.py --target artadia-nyc
    python scripts/draft.py --target artadia-nyc --length short
    python scripts/draft.py --target artadia-nyc --populate
    python scripts/draft.py --batch --effort quick
    python scripts/draft.py --batch --status qualified
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

from pipeline_lib import (
    BLOCKS_DIR, DRAFTS_DIR,
    load_entries, load_entry_by_id, load_profile,
    strip_markdown, count_words, count_chars,
    get_effort, ACTIONABLE_STATUSES, PIPELINE_DIR_ACTIVE,
)


# --- Submission format parsing ---

# Regex patterns for extracting word limits from format strings
WORD_LIMIT_RE = re.compile(r'~?(\d+)\s*(?:words?|w)\b', re.IGNORECASE)

# Known platform indicators in format strings
PLATFORM_KEYWORDS = {
    "submittable": "submittable",
    "slideroom": "slideroom",
    "greenhouse": "greenhouse",
    "workable": "workable",
}

# Map of recognized section keywords to canonical field names
SECTION_KEYWORDS = {
    "artist statement": "artist_statement",
    "artistic statement": "artist_statement",
    "bio": "bio",
    "biography": "bio",
    "work samples": "work_samples",
    "work sample": "work_samples",
    "support materials": "work_samples",
    "documentation": "work_samples",
    "resume": "resume",
    "cv": "resume",
    "cover letter": "cover_letter",
    "project description": "project_description",
    "project proposal": "project_description",
    "project narrative": "project_description",
    "statement of need": "project_description",
    "documentation of need": "documentation_of_need",
    "budget": "budget",
    "portfolio": "portfolio",
    "portfolio link": "portfolio",
    "writing sample": "writing_sample",
    "writing samples": "writing_sample",
    "references": "references",
    "reference": "references",
    "pitch email": "pitch_email",
    "application form": "application_form",
    "short-answer questions": "short_answers",
    "short questions": "short_answers",
    "technical plan": "technical_plan",
    "literature review": "literature_review",
    "methodology": "methodology",
    "financial documentation": "financial_documentation",
    "proof of public presentation": "proof_of_presentation",
    "tier configuration": "tier_configuration",
    "profile setup": "profile_setup",
    "pair programming interview": "interview",
    "conversational interview": "interview",
    "written application": "written_application",
}

# Sections we can auto-fill from profile data
PROFILE_FILLABLE = {
    "artist_statement", "bio", "work_samples", "project_description",
    "portfolio", "writing_sample",
}

# Word limit defaults per section type
DEFAULT_WORD_LIMITS = {
    "artist_statement": 500,
    "bio": 250,
    "project_description": 500,
    "cover_letter": 400,
    "pitch_email": 300,
}


def parse_submission_format(format_str: str) -> dict:
    """Parse a submission_format string into structured data.

    Returns:
        {
            "platform": str | None,
            "fields": [{"name": str, "word_limit": int | None}, ...],
            "raw": str,
        }
    """
    if not format_str:
        return {"platform": None, "fields": [], "raw": ""}

    result = {"platform": None, "fields": [], "raw": format_str}

    # Detect platform
    lower = format_str.lower()
    for keyword, platform in PLATFORM_KEYWORDS.items():
        if keyword in lower:
            result["platform"] = platform
            break

    # Check for "Direct outreach" patterns — not portal submissions
    if lower.startswith("direct outreach"):
        return result

    # Extract word limit if present at the format level
    global_limit_match = WORD_LIMIT_RE.search(format_str)
    global_limit = int(global_limit_match.group(1)) if global_limit_match else None

    # Split on common delimiters: " + ", ", ", ":"
    # First handle "Short application: project description (~300 words)" pattern
    colon_parts = format_str.split(":", 1)
    if len(colon_parts) == 2 and len(colon_parts[1].strip()) > 0:
        # The part after colon has the actual fields
        field_text = colon_parts[1].strip()
    else:
        field_text = format_str

    # Remove platform parenthetical
    field_text = re.sub(r'\([^)]*(?:Submittable|SlideRoom|Greenhouse)[^)]*\)', '', field_text, flags=re.IGNORECASE)

    # Split on " + " or " + " patterns
    parts = re.split(r'\s*\+\s*', field_text)

    for part in parts:
        part = part.strip().rstrip('.')
        if not part:
            continue

        # Extract per-field word limit
        field_limit_match = WORD_LIMIT_RE.search(part)
        field_limit = int(field_limit_match.group(1)) if field_limit_match else None

        # Clean the part for matching
        clean = re.sub(r'\(.*?\)', '', part).strip().lower()
        # Remove leading numbers like "6 short questions"
        clean = re.sub(r'^\d+\s+', '', clean)

        # Match against known section keywords (deduplicate by canonical name)
        existing_names = {f["name"] for f in result["fields"]}
        matched = False
        for keyword, canonical in SECTION_KEYWORDS.items():
            if keyword in clean:
                if canonical not in existing_names:
                    result["fields"].append({
                        "name": canonical,
                        "word_limit": field_limit or global_limit,
                    })
                matched = True
                break

        if not matched and clean and len(clean) > 2:
            # Use as-is with underscored name
            safe_name = re.sub(r'[^a-z0-9]+', '_', clean).strip('_')
            if safe_name and safe_name not in existing_names:
                result["fields"].append({
                    "name": safe_name,
                    "word_limit": field_limit or global_limit,
                })

    return result


# --- Profile content extraction ---

# Length preference mapping
LENGTH_PREFERENCE = {
    "short": ["short", "medium", "long"],
    "medium": ["medium", "short", "long"],
    "long": ["long", "medium", "short"],
}


def get_profile_content(profile: dict, section_name: str, length: str = "medium") -> str | None:
    """Extract content from a profile for a given section name.

    Args:
        profile: Loaded profile JSON dict.
        section_name: Canonical section name (e.g., "artist_statement").
        length: Preferred length tier ("short", "medium", "long").

    Returns:
        Content string or None if not available.
    """
    prefs = LENGTH_PREFERENCE.get(length, LENGTH_PREFERENCE["medium"])

    if section_name == "artist_statement":
        stmt = profile.get("artist_statement", {})
        if isinstance(stmt, dict):
            for pref in prefs:
                if stmt.get(pref):
                    return stmt[pref]
        elif isinstance(stmt, str):
            return stmt

    elif section_name == "bio":
        bio = profile.get("bio", {})
        if isinstance(bio, dict):
            for pref in prefs:
                if bio.get(pref):
                    return bio[pref]
        elif isinstance(bio, str):
            return bio

    elif section_name in ("project_description", "project_narrative"):
        # Try identity_narrative as project description
        narrative = profile.get("identity_narrative")
        if narrative:
            return narrative

    elif section_name == "work_samples":
        samples = profile.get("work_samples", [])
        if samples:
            lines = []
            for s in samples:
                name = s.get("name", "")
                url = s.get("url", "")
                desc = s.get("description", "")
                lines.append(f"- **{name}**: {desc}")
                if url:
                    lines.append(f"  {url}")
            return "\n".join(lines)

    elif section_name == "portfolio":
        # Check profile work_samples for portfolio URL
        samples = profile.get("work_samples", [])
        for s in samples:
            if "portfolio" in s.get("name", "").lower():
                return s.get("url", "")
        return None

    elif section_name == "writing_sample":
        # Can't auto-fill writing samples — flag as needing manual work
        return None

    elif section_name in ("evidence", "evidence_highlights"):
        highlights = profile.get("evidence_highlights", [])
        if highlights:
            return "\n".join(f"- {h}" for h in highlights)

    elif section_name in ("differentiators", "what_sets_you_apart"):
        diffs = profile.get("differentiators", [])
        if diffs:
            return "\n".join(f"- {d}" for d in diffs)

    return None


def load_block(block_path: str) -> str | None:
    """Load a block file by its reference path."""
    full_path = BLOCKS_DIR / block_path
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if full_path.exists():
        return full_path.read_text()
    return None


# --- Draft assembly ---


def assemble_draft(
    entry: dict,
    profile: dict | None,
    length: str = "medium",
) -> tuple[str, list[str]]:
    """Assemble a portal-ready draft from entry + profile data.

    Returns:
        (document, warnings) tuple.
    """
    warnings = []
    parts = []

    name = entry.get("name", entry.get("id", "Unknown"))
    org = entry.get("target", {}).get("organization", "")
    entry_id = entry.get("id", "?")

    parts.append(f"# Draft: {name}")
    parts.append(f"**Target:** {org}")
    parts.append(f"**Track:** {entry.get('track', '?')}")
    parts.append(f"**Status:** {entry.get('status', '?')}")

    deadline = entry.get("deadline", {})
    if isinstance(deadline, dict) and deadline.get("date"):
        parts.append(f"**Deadline:** {deadline['date']} ({deadline.get('type', '?')})")

    # Parse submission format from profile
    format_str = ""
    if profile:
        format_str = profile.get("submission_format", "")
    parsed = parse_submission_format(format_str)

    if parsed["platform"]:
        parts.append(f"**Platform:** {parsed['platform']}")

    parts.append(f"**Generated:** {date.today().isoformat()}")
    parts.append("")
    parts.append("---")
    parts.append("")

    if not parsed["fields"]:
        if format_str:
            parts.append(f"*Format: {format_str}*")
            parts.append("*No auto-parseable fields — manual assembly required.*")
            warnings.append(f"Unparseable submission_format: {format_str}")
        else:
            parts.append("*No profile found or no submission_format defined.*")
            warnings.append("No profile or submission_format")
        return "\n".join(parts), warnings

    # Get blocks_used from entry
    submission = entry.get("submission", {})
    blocks_used = {}
    if isinstance(submission, dict):
        blocks_used = submission.get("blocks_used", {})
        if not isinstance(blocks_used, dict):
            blocks_used = {}

    # Assemble each required section
    for field in parsed["fields"]:
        field_name = field["name"]
        word_limit = field["word_limit"]
        title = field_name.replace("_", " ").title()

        parts.append(f"## {title}")
        if word_limit:
            parts.append(f"*Target: ~{word_limit} words*")
        parts.append("")

        content = None
        source = None

        # Priority 1: Entry blocks
        if field_name in blocks_used:
            block_content = load_block(blocks_used[field_name])
            if block_content:
                content = block_content.strip()
                source = f"block:{blocks_used[field_name]}"

        # Priority 2: Profile content
        if content is None and profile and field_name in PROFILE_FILLABLE:
            profile_content = get_profile_content(profile, field_name, length)
            if profile_content:
                content = profile_content.strip()
                source = "profile"

        if content:
            parts.append(content)
            parts.append("")

            # Word/char counts
            plain = strip_markdown(content)
            wc = count_words(plain)
            cc = count_chars(plain)
            count_line = f"*[{wc} words, {cc} chars — source: {source}]*"

            if word_limit:
                if wc > word_limit:
                    count_line = f"*[{wc} words, {cc} chars — **OVER LIMIT by {wc - word_limit}w** — source: {source}]*"
                    warnings.append(f"{title}: {wc}w exceeds ~{word_limit}w limit")
                elif wc < word_limit * 0.5:
                    count_line = f"*[{wc} words, {cc} chars — **UNDER 50% of target** — source: {source}]*"
                    warnings.append(f"{title}: {wc}w is under 50% of ~{word_limit}w target")

            parts.append(count_line)
        else:
            parts.append(f"*[MISSING — needs manual content for: {field_name}]*")
            warnings.append(f"Missing content: {field_name}")

        parts.append("")

    return "\n".join(parts), warnings


# --- Portal fields population ---


def build_portal_fields(profile: dict) -> dict:
    """Build a portal_fields dict from a profile's submission_format."""
    format_str = profile.get("submission_format", "")
    parsed = parse_submission_format(format_str)

    fields = []
    for field in parsed["fields"]:
        field_entry = {"name": field["name"]}
        if field["word_limit"]:
            field_entry["word_limit"] = field["word_limit"]
        fields.append(field_entry)

    result = {}
    if parsed["platform"]:
        result["platform"] = parsed["platform"]
    if fields:
        result["fields"] = fields

    return result


def populate_portal_fields(filepath: Path, entry: dict, profile: dict) -> bool:
    """Write portal_fields to a pipeline YAML entry file.

    Returns True if file was modified.
    """
    # Only populate if portal_fields not already set
    existing = entry.get("portal_fields")
    if existing and isinstance(existing, dict) and existing.get("fields"):
        return False

    portal_fields = build_portal_fields(profile)
    if not portal_fields.get("fields"):
        return False

    content = filepath.read_text()

    # Build YAML snippet for portal_fields
    pf_yaml = yaml.dump({"portal_fields": portal_fields}, default_flow_style=False, sort_keys=False)

    if "portal_fields:" in content:
        # Replace existing empty portal_fields
        content = re.sub(
            r'^portal_fields:.*(?:\n(?:  .*)?)*',
            pf_yaml.rstrip(),
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        # Insert before conversion: or at end
        if "\nconversion:" in content:
            content = content.replace("\nconversion:", f"\n{pf_yaml.rstrip()}\nconversion:")
        else:
            content = content.rstrip() + f"\n{pf_yaml}"

    filepath.write_text(content)
    return True


# --- Main ---


def draft_single(target_id: str, length: str, populate: bool, output: str | None):
    """Generate a draft for a single target."""
    filepath, entry = load_entry_by_id(target_id)
    if not entry:
        print(f"Error: No pipeline entry found for '{target_id}'", file=sys.stderr)
        sys.exit(1)

    profile = load_profile(target_id)

    # Also try matching on profile's target_id field
    if not profile:
        # Search profiles for matching target_id
        from pipeline_lib import PROFILES_DIR
        if PROFILES_DIR.exists():
            for pf in PROFILES_DIR.glob("*.json"):
                import json
                pdata = json.loads(pf.read_text())
                if pdata.get("target_id") == target_id:
                    profile = pdata
                    break

    doc, warnings = assemble_draft(entry, profile, length)

    if warnings:
        print("WARNINGS:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
        print(file=sys.stderr)

    if populate and profile and filepath:
        modified = populate_portal_fields(filepath, entry, profile)
        if modified:
            print(f"Updated portal_fields on {filepath.name}", file=sys.stderr)

    if output:
        Path(output).write_text(doc)
        print(f"Draft written to {output}")
    else:
        print(doc)


def draft_batch(status: str | None, effort: str | None, length: str, populate: bool):
    """Generate drafts for multiple entries matching filters."""
    entries = load_entries(include_filepath=True)

    candidates = []
    for e in entries:
        e_status = e.get("status", "")
        e_effort = get_effort(e)

        if status and e_status != status:
            continue
        if not status and e_status not in ACTIONABLE_STATUSES:
            continue
        if effort and e_effort != effort:
            continue

        candidates.append(e)

    if not candidates:
        print("No entries match the specified filters.")
        return

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    drafted = 0
    skipped = 0
    warnings_total = 0

    print(f"Batch drafting {len(candidates)} entries (length={length})")
    print(f"{'─' * 60}")

    for entry in candidates:
        entry_id = entry.get("id", "?")
        name = entry.get("name", entry_id)
        filepath = entry.get("_filepath")

        profile = load_profile(entry_id)
        if not profile:
            print(f"  SKIP  {name} — no profile")
            skipped += 1
            continue

        doc, warnings = assemble_draft(entry, profile, length)
        draft_path = DRAFTS_DIR / f"{entry_id}.md"
        draft_path.write_text(doc)

        warn_str = f" ({len(warnings)} warnings)" if warnings else ""
        print(f"  DRAFT {name} → drafts/{entry_id}.md{warn_str}")
        drafted += 1
        warnings_total += len(warnings)

        if populate and filepath:
            modified = populate_portal_fields(filepath, entry, profile)
            if modified:
                print(f"        + portal_fields updated")

    print(f"{'─' * 60}")
    print(f"Drafted: {drafted} | Skipped: {skipped} | Warnings: {warnings_total}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate portal-ready drafts from profile content"
    )
    parser.add_argument("--target", help="Target ID for single draft")
    parser.add_argument("--length", choices=["short", "medium", "long"],
                        default="medium", help="Preferred content length (default: medium)")
    parser.add_argument("--populate", action="store_true",
                        help="Write portal_fields to pipeline YAML entry")
    parser.add_argument("--output", "-o", help="Output file (single target mode)")
    parser.add_argument("--batch", action="store_true",
                        help="Draft all matching entries")
    parser.add_argument("--status", help="Filter batch by status (default: all actionable)")
    parser.add_argument("--effort", choices=["quick", "standard", "deep", "complex"],
                        help="Filter batch by effort level")

    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    if args.target:
        draft_single(args.target, args.length, args.populate, args.output)
    elif args.batch:
        draft_batch(args.status, args.effort, args.length, args.populate)


if __name__ == "__main__":
    main()
