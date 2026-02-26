#!/usr/bin/env python3
"""Generate role-tailored resume HTML files from the base template.

Uses the alchemize pattern: generate a prompt with (base resume HTML + role info
+ cover letter), let the user run it through AI, then integrate the customized
sections back into the HTML template.

Usage:
    python scripts/tailor_resume.py --target <id>                  # Generate prompt for one entry
    python scripts/tailor_resume.py --batch --status staged         # Generate prompts for all staged jobs
    python scripts/tailor_resume.py --target <id> --integrate       # Integrate AI output → HTML
    python scripts/tailor_resume.py --batch --integrate             # Batch integrate
    python scripts/tailor_resume.py --target <id> --wire            # Wire HTML to pipeline YAML
    python scripts/tailor_resume.py --batch --wire                  # Batch wire
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    MATERIALS_DIR,
    REPO_ROOT,
    VARIANTS_DIR,
    load_entries,
    load_entry_by_id,
    PIPELINE_DIR_ACTIVE,
    update_last_touched,
)

WORK_DIR = Path(__file__).resolve().parent / ".alchemize-work"
RESUMES_DIR = MATERIALS_DIR / "resumes"
CURRENT_BATCH = "batch-03"

BASE_RESUME_BY_IDENTITY = {
    "independent-engineer": RESUMES_DIR / "base" / "independent-engineer-resume.html",
    "educator": RESUMES_DIR / "base" / "educator-resume.html",
    "creative-technologist": RESUMES_DIR / "base" / "creative-technologist-resume.html",
    "systems-artist": RESUMES_DIR / "base" / "systems-artist-resume.html",
    "community-practitioner": RESUMES_DIR / "base" / "community-practitioner-resume.html",
}
DEFAULT_BASE_RESUME = RESUMES_DIR / "base" / "independent-engineer-resume.html"

# All known base resume filename stems (for wire replacement matching)
BASE_RESUME_STEMS = [
    "independent-engineer-resume",
    "educator-resume",
    "creative-technologist-resume",
    "systems-artist-resume",
    "community-practitioner-resume",
]

# Section markers in the HTML template
SECTION_MARKERS = {
    "TITLE_LINE": {
        "start": re.compile(r'<div class="title-line">'),
        "end": re.compile(r'</div>'),
        "description": "The subtitle/title line (e.g. 'Software Engineer & Developer Tools Builder')",
    },
    "PROFILE": {
        "start": re.compile(r'<div class="section-content profile">'),
        "end": re.compile(r'</div>\s*</div>'),
        "description": "The profile/summary paragraph",
    },
    "SKILLS": {
        "start": re.compile(r'<div class="skills-list">'),
        "end": re.compile(r'</div>'),
        "description": "The technical skills list",
    },
    "PROJECTS": {
        "start": re.compile(r'<div class="section-label">Selected<br>Projects</div>'),
        "end": re.compile(r'</div>\s*</div>'),
        "description": "The selected projects section",
    },
    "EXPERIENCE": {
        "start": re.compile(r'<div class="section-label">Experience</div>'),
        "end": re.compile(r'</div>\s*</div>\s*</div>'),
        "description": "The experience section with bullet points",
    },
}


def resolve_base_resume(identity: str | None = None) -> Path:
    """Return the base resume path for the given identity position."""
    if identity and identity in BASE_RESUME_BY_IDENTITY:
        return BASE_RESUME_BY_IDENTITY[identity]
    return DEFAULT_BASE_RESUME


def load_base_template(identity: str | None = None) -> str:
    """Read the base resume HTML for the given identity position."""
    base = resolve_base_resume(identity)
    if not base.exists():
        print(f"Error: Base resume not found: {base}", file=sys.stderr)
        sys.exit(1)
    return base.read_text()


def extract_sections(html: str) -> dict[str, str]:
    """Parse HTML into labeled sections for editing.

    Returns dict of section_name -> raw HTML content.
    Extracts the actual content between section boundaries.
    """
    sections = {}

    # Title line (line 204 area)
    m = re.search(r'(<div class="title-line">)(.*?)(</div>)', html, re.DOTALL)
    if m:
        sections["TITLE_LINE"] = m.group(2).strip()

    # Profile paragraph
    m = re.search(
        r'(<div class="section-content profile">\s*<p>)(.*?)(</p>\s*</div>)',
        html, re.DOTALL,
    )
    if m:
        sections["PROFILE"] = m.group(2).strip()

    # Skills
    m = re.search(
        r'(<div class="skills-list">)\s*(.*?)\s*(</div>)',
        html, re.DOTALL,
    )
    if m:
        sections["SKILLS"] = m.group(2).strip()

    # Projects — everything between the section-content div and its close
    m = re.search(
        r'(Selected<br>Projects</div>\s*<div class="section-content">)\s*(.*?)\s*(</div>\s*</div>\s*<div class="section">\s*<div class="section-label">Experience)',
        html, re.DOTALL,
    )
    if m:
        sections["PROJECTS"] = m.group(2).strip()

    # Experience — the independent engineer entry bullets
    m = re.search(
        r'(Experience</div>\s*<div class="section-content">)\s*(.*?)\s*(</div>\s*</div>\s*<div class="section">\s*<div class="section-label">Education)',
        html, re.DOTALL,
    )
    if m:
        sections["EXPERIENCE"] = m.group(2).strip()

    return sections


def resolve_cover_letter(entry: dict) -> str | None:
    """Load cover letter content for an entry."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return None
    variant_ids = submission.get("variant_ids", {})
    if not isinstance(variant_ids, dict):
        return None
    cl_ref = variant_ids.get("cover_letter")
    if not cl_ref:
        return None
    variant_path = VARIANTS_DIR / cl_ref
    if not variant_path.suffix:
        variant_path = variant_path.with_suffix(".md")
    if variant_path.exists():
        return variant_path.read_text().strip()
    return None


def build_tailoring_prompt(entry: dict, sections: dict[str, str], cover_letter: str) -> str:
    """Generate a prompt for AI to produce customized resume sections."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    org = entry.get("target", {}).get("organization", "")
    framing = entry.get("fit", {}).get("framing", "")

    lines = [
        f"# Resume Tailoring: {name}",
        "",
        f"**Company:** {org}",
        f"**Role:** {name}",
        f"**Identity framing:** {framing}",
        "",
        "## Instructions",
        "",
        "Rewrite the 5 resume sections below to best match this role. Guidelines:",
        "- **Preserve all factual claims** — do not fabricate experience, metrics, or projects",
        "- **Reorder and re-emphasize** to front-load what's most relevant for this role",
        "- **Keep the same HTML structure** — same tags, same classes, same general format",
        "- **TITLE_LINE**: Change the subtitle to match the role focus (max ~6 words, uppercase in display)",
        "- **PROFILE**: Lead with the most relevant signal for this role. Keep to one paragraph.",
        "- **SKILLS**: Reorder to put role-relevant skills first. You may remove less relevant ones.",
        "- **PROJECTS**: Reorder projects by relevance. Rewrite descriptions to emphasize role-relevant aspects.",
        "- **EXPERIENCE**: Reorder bullet points to emphasize most relevant experience.",
        "",
        "Output each section with a `### SECTION_NAME` marker, followed by the HTML content.",
        "",
        "---",
        "",
        "## Cover Letter (shows what we're emphasizing for this role)",
        "",
        cover_letter or "(No cover letter available)",
        "",
        "---",
        "",
        "## Current Resume Sections",
        "",
    ]

    for section_name in ("TITLE_LINE", "PROFILE", "SKILLS", "PROJECTS", "EXPERIENCE"):
        content = sections.get(section_name, "(not found)")
        lines.extend([
            f"### {section_name}",
            "",
            "```html",
            content,
            "```",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## Output",
        "",
        "Produce the 5 rewritten sections below, each preceded by `### SECTION_NAME`:",
        "",
    ])

    return "\n".join(lines)


def generate_prompt_file(entry: dict) -> Path:
    """Write prompt to .alchemize-work/{id}/resume-prompt.md."""
    entry_id = entry.get("id", "?")
    identity = entry.get("fit", {}).get("identity_position")

    template = load_base_template(identity)
    sections = extract_sections(template)
    cover_letter = resolve_cover_letter(entry)

    prompt = build_tailoring_prompt(entry, sections, cover_letter)

    work_path = WORK_DIR / entry_id
    work_path.mkdir(parents=True, exist_ok=True)
    prompt_file = work_path / "resume-prompt.md"
    prompt_file.write_text(prompt)

    return prompt_file


def integrate_tailored_sections(entry_id: str, output_text: str, identity: str | None = None) -> Path | None:
    """Parse AI output, splice into HTML template, write {entry-id}-resume.html.

    Expects output_text to contain sections delimited by ### TITLE_LINE, ### PROFILE, etc.
    Each section contains the HTML to splice in.
    """
    # Parse output into sections
    section_pattern = re.compile(r'^###\s+(\w+)\s*$', re.MULTILINE)
    parts = section_pattern.split(output_text)
    # parts is: [preamble, name1, content1, name2, content2, ...]
    parsed_sections = {}
    for i in range(1, len(parts) - 1, 2):
        section_name = parts[i].strip()
        content = parts[i + 1].strip()
        # Remove ```html ... ``` wrappers if present
        content = re.sub(r'^```html\s*\n?', '', content)
        content = re.sub(r'\n?```\s*$', '', content)
        content = content.strip()
        parsed_sections[section_name] = content

    if not parsed_sections:
        print(f"  Error: No sections found in output for {entry_id}")
        return None

    found = list(parsed_sections.keys())
    print(f"  Found sections: {', '.join(found)}")

    # Load base template and splice in sections
    html = load_base_template(identity)

    if "TITLE_LINE" in parsed_sections:
        html = re.sub(
            r'(<div class="title-line">).*?(</div>)',
            rf'\g<1>{parsed_sections["TITLE_LINE"]}\g<2>',
            html,
            count=1,
            flags=re.DOTALL,
        )
        # Also update the <title> tag
        title_text = re.sub(r'<[^>]+>', '', parsed_sections["TITLE_LINE"])
        title_text = title_text.replace("&amp;", "&").strip()
        html = re.sub(
            r'(<title>Anthony James Padavano — ).*?(</title>)',
            rf'\g<1>{title_text}\g<2>',
            html,
            count=1,
        )

    if "PROFILE" in parsed_sections:
        html = re.sub(
            r'(<div class="section-content profile">\s*<p>).*?(</p>\s*</div>)',
            rf'\g<1>{parsed_sections["PROFILE"]}\g<2>',
            html,
            count=1,
            flags=re.DOTALL,
        )

    if "SKILLS" in parsed_sections:
        html = re.sub(
            r'(<div class="skills-list">)\s*.*?\s*(</div>)',
            rf'\g<1>\n      {parsed_sections["SKILLS"]}\n    \g<2>',
            html,
            count=1,
            flags=re.DOTALL,
        )

    if "PROJECTS" in parsed_sections:
        html = re.sub(
            r'(Selected<br>Projects</div>\s*<div class="section-content">)\s*.*?\s*(</div>\s*</div>\s*<div class="section">\s*<div class="section-label">Experience)',
            rf'\g<1>\n\n{parsed_sections["PROJECTS"]}\n\n  \g<2>',
            html,
            count=1,
            flags=re.DOTALL,
        )

    if "EXPERIENCE" in parsed_sections:
        html = re.sub(
            r'(Experience</div>\s*<div class="section-content">)\s*.*?\s*(</div>\s*</div>\s*<div class="section">\s*<div class="section-label">Education)',
            rf'\g<1>\n\n{parsed_sections["EXPERIENCE"]}\n\n  \g<2>',
            html,
            count=1,
            flags=re.DOTALL,
        )

    # Write per-entry resume HTML to current batch dir (per-role subfolder)
    role_dir = RESUMES_DIR / CURRENT_BATCH / entry_id
    role_dir.mkdir(parents=True, exist_ok=True)
    output_path = role_dir / f"{entry_id}-resume.html"
    output_path.write_text(html)
    print(f"  Wrote: {output_path.relative_to(REPO_ROOT)}")
    return output_path


def wire_resume_to_entry(entry_id: str) -> bool:
    """Update pipeline YAML materials_attached to point to per-entry resume."""
    filepath, entry = load_entry_by_id(entry_id)
    if not filepath or not entry:
        print(f"  Error: Entry not found: {entry_id}")
        return False

    html_path = RESUMES_DIR / CURRENT_BATCH / entry_id / f"{entry_id}-resume.html"
    if not html_path.exists():
        print(f"  Error: Tailored resume not found: {html_path.name}")
        return False

    # Check what's currently in materials_attached
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        print(f"  Error: Invalid submission block in {entry_id}")
        return False

    new_ref = f"resumes/{CURRENT_BATCH}/{entry_id}/{entry_id}-resume.html"
    materials = submission.get("materials_attached", [])
    if isinstance(materials, list) and new_ref in materials:
        print(f"  {entry_id}: Already wired to {new_ref}")
        return True

    # Update the YAML file — replace any base resume reference (any identity)
    content = filepath.read_text()
    replaced = False
    for stem in BASE_RESUME_STEMS:
        for ext in (".html", ".pdf"):
            old_ref = f"resumes/base/{stem}{ext}"
            if old_ref in content:
                content = content.replace(
                    f"- {old_ref}",
                    f"- {new_ref}",
                    1,
                )
                replaced = True
                break
        if replaced:
            break

    if not replaced:
        # Also check for prior batch references (both flat and folder formats)
        for batch in ("batch-01", "batch-02"):
            for fmt in (
                f"resumes/{batch}/{entry_id}/{entry_id}-resume.html",
                f"resumes/{batch}/{entry_id}-resume.html",
            ):
                if fmt in content and fmt != new_ref:
                    content = content.replace(
                        f"- {fmt}",
                        f"- {new_ref}",
                        1,
                    )
                    replaced = True
                    break
            if replaced:
                break

    if not replaced and "materials_attached:" in content:
        # Add the new reference
        content = content.replace(
            "materials_attached:",
            f"materials_attached:\n  - {new_ref}",
            1,
        )

    content = update_last_touched(content)
    filepath.write_text(content)
    print(f"  {entry_id}: Wired to {new_ref}")
    return True


def find_staged_job_entries(status: str = "staged") -> list[dict]:
    """Find active pipeline entries with job track and given status."""
    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE], include_filepath=True)
    return [
        e for e in entries
        if e.get("track") == "job"
        and e.get("status") == status
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Generate role-tailored resume HTML files"
    )
    parser.add_argument("--target", help="Target entry ID")
    parser.add_argument("--batch", action="store_true",
                        help="Process all matching entries")
    parser.add_argument("--status", default="staged",
                        help="Filter by status for --batch (default: staged)")
    parser.add_argument("--integrate", action="store_true",
                        help="Integrate AI output back into HTML template")
    parser.add_argument("--wire", action="store_true",
                        help="Wire tailored resume HTML to pipeline YAML")
    parser.add_argument("--prompt-only", action="store_true",
                        help="Only generate prompts (default behavior)")
    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("Specify --target <id> or --batch")

    # Resolve entries
    if args.batch:
        entries = find_staged_job_entries(args.status)
        if not entries:
            print(f"No job entries with status '{args.status}' found.")
            sys.exit(1)
        print(f"Found {len(entries)} job entries with status '{args.status}':\n")
        for e in entries:
            print(f"  - {e.get('id')}: {e.get('name')}")
        print()
    else:
        filepath, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
            sys.exit(1)
        entries = [entry]

    # --wire mode
    if args.wire:
        results = []
        for entry in entries:
            eid = entry.get("id", "?")
            ok = wire_resume_to_entry(eid)
            results.append((eid, ok))
        if len(results) > 1:
            wired = sum(1 for _, ok in results if ok)
            print(f"\nWired: {wired}/{len(results)}")
        return

    # --integrate mode
    if args.integrate:
        results = []
        for entry in entries:
            eid = entry.get("id", "?")
            identity = entry.get("fit", {}).get("identity_position")
            output_file = WORK_DIR / eid / "resume-output.md"
            if not output_file.exists():
                print(f"  {eid}: No output file at {output_file.name}")
                results.append((eid, False))
                continue
            output_text = output_file.read_text()
            path = integrate_tailored_sections(eid, output_text, identity)
            results.append((eid, path is not None))
        if len(results) > 1:
            ok_count = sum(1 for _, ok in results if ok)
            print(f"\nIntegrated: {ok_count}/{len(results)}")
        return

    # Default: generate prompts
    results = []
    for entry in entries:
        eid = entry.get("id", "?")
        prompt_file = generate_prompt_file(entry)
        print(f"  {eid}: {prompt_file.relative_to(REPO_ROOT.parent)}")
        results.append((eid, True))

    print(f"\nGenerated {len(results)} resume prompt(s).")
    print(f"\nNext steps:")
    print(f"  1. Run each prompt through Claude to get customized sections")
    print(f"  2. Save output to .alchemize-work/<entry-id>/resume-output.md")
    print(f"  3. Run: python scripts/tailor_resume.py --batch --integrate")
    print(f"  4. Run: python scripts/build_resumes.py  (HTML → PDF)")
    print(f"  5. Run: python scripts/tailor_resume.py --batch --wire")


if __name__ == "__main__":
    main()
