#!/usr/bin/env python3
"""Batch-populate enrichment data across pipeline entries.

Wires materials_attached, variant_ids, and portal_fields into pipeline
YAML entries that have empty values for these fields.

Usage:
    python scripts/enrich.py --report
    python scripts/enrich.py --all --dry-run
    python scripts/enrich.py --all --yes
    python scripts/enrich.py --materials --yes
    python scripts/enrich.py --variants --yes
    python scripts/enrich.py --portal --yes
    python scripts/enrich.py --variants --grant-template --yes
    python scripts/enrich.py --all --effort quick --yes
"""

import argparse
import re
import sys
from datetime import date

from pipeline_lib import (
    load_entries, load_entry_by_id, load_profile,
    get_effort, ACTIONABLE_STATUSES,
    MATERIALS_DIR, VARIANTS_DIR,
    update_last_touched as _update_last_touched_content,
)


# --- Constants ---

DEFAULT_RESUME = "resumes/base/multimedia-specialist.pdf"

# Fallback resumes by identity — only used when no tailored resume exists
# in the current batch directory (materials/resumes/batch-03/<entry-id>/).
# Always prefer tailored resumes over these base templates.
RESUME_BY_IDENTITY = {
    "independent-engineer": "resumes/base/independent-engineer-resume.pdf",
    "systems-artist": "resumes/base/systems-artist-resume.pdf",
    "creative-technologist": "resumes/base/creative-technologist-resume.pdf",
    "community-practitioner": "resumes/base/community-practitioner-resume.pdf",
    "educator": "resumes/base/educator-resume.pdf",
}

CURRENT_BATCH = "batch-03"

RESUME_TRACKS = {"job", "fellowship", "grant", "residency", "prize", "program"}

COVER_LETTER_MAP = {
    "anthropic-fde": "cover-letters/anthropic-fde-custom-agents",
    "huggingface-dev-advocate": "cover-letters/huggingface-dev-advocate-hub-enterprise",
    "openai-se-evals": "cover-letters/openai-se-applied-evals",
    "together-ai": "cover-letters/together-ai-lead-dx-documentation",
}

GRANT_TEMPLATE_TRACKS = {"grant", "residency", "prize"}
GRANT_TEMPLATE_PATH = "cover-letters/grant-art-template"

# Default blocks_used mappings for job entries, keyed by identity_position.
# Analogous to RESUME_BY_IDENTITY for materials.
JOB_BLOCKS_BY_IDENTITY = {
    "independent-engineer": {
        "framing": "framings/independent-engineer",
        "evidence": "evidence/differentiators",
        "work_samples": "evidence/work-samples",
        "credentials": "pitches/credentials-creative-tech",
        "methodology": "methodology/ai-conductor",
    },
    "creative-technologist": {
        "framing": "framings/creative-technologist",
        "evidence": "evidence/differentiators",
        "work_samples": "evidence/work-samples",
        "credentials": "pitches/credentials-creative-tech",
        "methodology": "methodology/process-as-product",
    },
    "systems-artist": {
        "framing": "framings/systems-artist",
        "evidence": "evidence/differentiators",
        "work_samples": "evidence/work-samples",
    },
    "community-practitioner": {
        "framing": "framings/community-practitioner",
        "evidence": "evidence/differentiators",
        "work_samples": "evidence/work-samples",
    },
    "educator": {
        "framing": "framings/educator-researcher",
        "evidence": "evidence/differentiators",
        "work_samples": "evidence/work-samples",
        "project": "projects/classroom-rpg-aetheria",
    },
}


# --- Enrichment operations ---


def _update_last_touched(content: str) -> str:
    """Update last_touched to today in YAML content."""
    return _update_last_touched_content(content)


def select_resume(entry: dict) -> str:
    """Select the best available resume for an entry.

    Priority:
      1. Tailored resume in current batch (materials/resumes/batch-03/<entry-id>/)
      2. Identity-position base resume (RESUME_BY_IDENTITY fallback)
      3. DEFAULT_RESUME
    """
    entry_id = entry.get("id", "")
    # Check for tailored resume in current batch
    if entry_id:
        batch_dir = MATERIALS_DIR / "resumes" / CURRENT_BATCH / entry_id
        if batch_dir.exists():
            for ext in (".pdf", ".html"):
                candidates = sorted(batch_dir.glob(f"*{ext}"))
                if candidates:
                    return str(candidates[0].relative_to(MATERIALS_DIR))
    # Fall back to identity-based base resume
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        position = fit.get("identity_position", "")
        if position in RESUME_BY_IDENTITY:
            return RESUME_BY_IDENTITY[position]
    return DEFAULT_RESUME


def enrich_materials(filepath, entry, dry_run=False) -> bool:
    """Wire identity-matched resume into materials_attached if empty.

    Reads fit.identity_position to select the right resume variant.
    Falls back to DEFAULT_RESUME if position is unrecognized.
    Returns True if the entry was (or would be) modified.
    """
    track = entry.get("track", "")
    if track not in RESUME_TRACKS:
        return False

    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return False

    materials = submission.get("materials_attached", [])
    if isinstance(materials, list) and materials:
        return False  # already populated

    if dry_run:
        return True

    resume = select_resume(entry)
    content = filepath.read_text()

    # Replace empty materials_attached: [] with the selected resume
    new_content = re.sub(
        r'^(\s*materials_attached:\s*)\[\]',
        rf'\1\n    - {resume}',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if new_content == content:
        return False  # pattern didn't match — already populated or different format

    import yaml
    try:
        yaml.safe_load(new_content)
    except yaml.YAMLError:
        return False  # refuse to write invalid YAML

    new_content = _update_last_touched(new_content)
    filepath.write_text(new_content)
    return True


def find_matching_variant(entry_id: str) -> str | None:
    """Find the matching cover letter variant for an entry ID."""
    return COVER_LETTER_MAP.get(entry_id)


def enrich_variant(filepath, entry, variant_path, dry_run=False) -> bool:
    """Wire a cover letter variant into variant_ids if empty.

    Returns True if the entry was (or would be) modified.
    """
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return False

    variant_ids = submission.get("variant_ids", {})
    if isinstance(variant_ids, dict) and variant_ids:
        return False  # already has variants

    if dry_run:
        return True

    content = filepath.read_text()

    # Replace empty variant_ids: {} with the cover letter
    new_content = re.sub(
        r'^(\s*variant_ids:\s*)\{\}',
        rf'\1\n    cover_letter: {variant_path}',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if new_content == content:
        return False  # pattern didn't match — already populated or different format

    import yaml
    try:
        yaml.safe_load(new_content)
    except yaml.YAMLError:
        return False  # refuse to write invalid YAML

    new_content = _update_last_touched(new_content)
    filepath.write_text(new_content)
    return True


def enrich_portal_fields(filepath, entry, dry_run=False) -> bool:
    """Populate portal_fields from profile submission_format.

    Delegates to draft.populate_portal_fields().
    Returns True if the entry was (or would be) modified.
    """
    entry_id = entry.get("id", "?")
    profile = load_profile(entry_id)
    if not profile:
        return False

    # Check if already populated
    existing = entry.get("portal_fields")
    if existing and isinstance(existing, dict) and existing.get("fields"):
        return False

    # Check if profile has parseable format
    from draft import build_portal_fields
    portal_fields = build_portal_fields(profile)
    if not portal_fields.get("fields"):
        return False

    if dry_run:
        return True

    from draft import populate_portal_fields
    modified = populate_portal_fields(filepath, entry, profile)
    if modified:
        content = filepath.read_text()
        content = _update_last_touched(content)
        filepath.write_text(content)
    return modified


def enrich_blocks(filepath, entry, dry_run=False) -> bool:
    """Wire identity-matched blocks into blocks_used for job entries.

    Looks up fit.identity_position to select default blocks from
    JOB_BLOCKS_BY_IDENTITY. Skips if blocks_used already has entries.
    Returns True if the entry was (or would be) modified.
    """
    track = entry.get("track", "")
    if track != "job":
        return False

    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return False

    blocks = submission.get("blocks_used", {})
    if isinstance(blocks, dict) and blocks:
        return False  # already has blocks wired

    fit = entry.get("fit", {})
    if not isinstance(fit, dict):
        return False

    position = fit.get("identity_position", "")
    if position not in JOB_BLOCKS_BY_IDENTITY:
        return False

    if dry_run:
        return True

    default_blocks = JOB_BLOCKS_BY_IDENTITY[position]

    content = filepath.read_text()

    # Build the replacement YAML for blocks_used
    blocks_lines = []
    for key, path in default_blocks.items():
        blocks_lines.append(f"    {key}: {path}")
    blocks_yaml = "\n".join(blocks_lines)

    # Replace empty blocks_used: {} with the block mappings
    new_content = re.sub(
        r'^(\s*blocks_used:\s*)\{\}',
        rf'\1\n{blocks_yaml}',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if new_content == content:
        return False  # pattern didn't match

    import yaml
    try:
        yaml.safe_load(new_content)
    except yaml.YAMLError:
        return False  # refuse to write invalid YAML

    new_content = _update_last_touched(new_content)
    filepath.write_text(new_content)
    return True


# --- Report ---


def run_report(entries: list[dict]):
    """Show per-entry enrichment gaps."""
    print("ENRICHMENT REPORT")
    print("=" * 70)
    print()

    needs_materials = 0
    needs_blocks = 0
    needs_variants = 0
    needs_portal = 0
    already_complete = 0

    for e in entries:
        entry_id = e.get("id", "?")
        name = e.get("name", entry_id)
        track = e.get("track", "")
        status = e.get("status", "")

        gaps = detect_gaps(e)

        if not gaps:
            already_complete += 1
            continue

        gap_str = ", ".join(gaps)
        print(f"  {name}")
        print(f"    {status} | {track} | gaps: {gap_str}")

        if "materials" in gaps:
            needs_materials += 1
        if "blocks" in gaps:
            needs_blocks += 1
        if "variants" in gaps:
            needs_variants += 1
        if "portal_fields" in gaps:
            needs_portal += 1

    print()
    print("=" * 70)
    total = needs_materials + needs_blocks + needs_variants + needs_portal
    print(f"Summary: {needs_materials} need materials | "
          f"{needs_blocks} need blocks | "
          f"{needs_variants} need variants | "
          f"{needs_portal} need portal_fields | "
          f"{already_complete} complete | "
          f"{total} total gaps")


def detect_gaps(entry: dict) -> list[str]:
    """Detect which enrichment fields are missing on an entry."""
    gaps = []
    track = entry.get("track", "")
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        submission = {}

    # Materials gap
    materials = submission.get("materials_attached", [])
    if track in RESUME_TRACKS and (not isinstance(materials, list) or not materials):
        gaps.append("materials")

    # Blocks gap (job entries with identity mapping but no blocks wired)
    blocks = submission.get("blocks_used", {})
    if track == "job" and (not isinstance(blocks, dict) or not blocks):
        fit = entry.get("fit", {})
        position = fit.get("identity_position", "") if isinstance(fit, dict) else ""
        if position in JOB_BLOCKS_BY_IDENTITY:
            gaps.append("blocks")

    # Variants gap
    entry_id = entry.get("id", "?")
    variant_ids = submission.get("variant_ids", {})
    has_variants = isinstance(variant_ids, dict) and bool(variant_ids)
    if not has_variants and (find_matching_variant(entry_id) or track in GRANT_TEMPLATE_TRACKS):
        gaps.append("variants")

    # Portal fields gap
    portal = entry.get("portal_fields")
    if not portal or not isinstance(portal, dict) or not portal.get("fields"):
        profile = load_profile(entry_id)
        if profile and profile.get("submission_format"):
            gaps.append("portal_fields")

    return gaps


# --- Main orchestrator ---


def run_enrich(
    entries: list[dict],
    do_materials: bool,
    do_blocks: bool,
    do_variants: bool,
    do_portal: bool,
    grant_template: bool,
    effort_filter: str | None,
    status_filter: str | None,
    entry_id: str | None,
    dry_run: bool,
    auto_yes: bool,
):
    """Enrich entries matching filters."""
    candidates = []
    for e in entries:
        eid = e.get("id", "?")
        status = e.get("status", "")

        if entry_id and eid != entry_id:
            continue
        if status_filter and status != status_filter:
            continue
        if effort_filter and get_effort(e) != effort_filter:
            continue

        candidates.append(e)

    if not candidates:
        print("No entries match the specified filters.")
        return

    # Preview
    actions = []
    for e in candidates:
        eid = e.get("id", "?")
        name = e.get("name", eid)
        track = e.get("track", "")
        filepath = e.get("_filepath")
        entry_actions = []

        if do_materials and track in RESUME_TRACKS:
            sub = e.get("submission", {})
            mat = sub.get("materials_attached", []) if isinstance(sub, dict) else []
            if not mat:
                entry_actions.append("materials")

        if do_blocks and track == "job":
            sub = e.get("submission", {})
            blk = sub.get("blocks_used", {}) if isinstance(sub, dict) else {}
            if not (isinstance(blk, dict) and blk):
                fit = e.get("fit", {})
                position = fit.get("identity_position", "") if isinstance(fit, dict) else ""
                if position in JOB_BLOCKS_BY_IDENTITY:
                    entry_actions.append("blocks")

        if do_variants:
            sub = e.get("submission", {})
            vids = sub.get("variant_ids", {}) if isinstance(sub, dict) else {}
            if not (isinstance(vids, dict) and vids):
                variant = find_matching_variant(eid)
                if variant:
                    entry_actions.append(f"variant:{variant}")
                elif grant_template and track in GRANT_TEMPLATE_TRACKS:
                    entry_actions.append(f"variant:{GRANT_TEMPLATE_PATH}")

        if do_portal:
            existing = e.get("portal_fields")
            if not (existing and isinstance(existing, dict) and existing.get("fields")):
                profile = load_profile(eid)
                if profile and profile.get("submission_format"):
                    entry_actions.append("portal_fields")

        if entry_actions:
            actions.append((e, filepath, entry_actions))

    if not actions:
        print("No enrichment needed for matching entries.")
        return

    print(f"{'DRY RUN: ' if dry_run else ''}Enriching {len(actions)} entries")
    print(f"{'─' * 60}")

    for e, filepath, entry_actions in actions:
        name = e.get("name", e.get("id", "?"))
        print(f"  {name}")
        for a in entry_actions:
            print(f"    + {a}")

    if dry_run:
        print(f"{'─' * 60}")
        print(f"Dry run complete. {len(actions)} entries would be enriched.")
        return

    # Confirmation
    if not auto_yes:
        print(f"{'─' * 60}")
        try:
            confirm = input("Proceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if confirm != "y":
            print("Aborted.")
            return

    # Execute
    enriched = 0
    for e, filepath, entry_actions in actions:
        eid = e.get("id", "?")
        if not filepath:
            continue

        modified = False
        for action in entry_actions:
            if action == "materials":
                if enrich_materials(filepath, e):
                    modified = True
            elif action == "blocks":
                if enrich_blocks(filepath, e):
                    modified = True
            elif action.startswith("variant:"):
                variant_path = action[len("variant:"):]
                if enrich_variant(filepath, e, variant_path):
                    modified = True
            elif action == "portal_fields":
                if enrich_portal_fields(filepath, e):
                    modified = True

        if modified:
            enriched += 1

    print(f"{'─' * 60}")
    print(f"Enriched {enriched} entries.")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-populate enrichment data across pipeline entries"
    )
    parser.add_argument("--report", action="store_true",
                        help="Show enrichment gaps per entry")
    parser.add_argument("--all", action="store_true",
                        help="Run all enrichment operations")
    parser.add_argument("--materials", action="store_true",
                        help="Wire resume into materials_attached")
    parser.add_argument("--blocks", action="store_true",
                        help="Wire identity-matched blocks into blocks_used for jobs")
    parser.add_argument("--variants", action="store_true",
                        help="Wire cover letters into variant_ids")
    parser.add_argument("--portal", action="store_true",
                        help="Populate portal_fields from profile")
    parser.add_argument("--grant-template", action="store_true",
                        help="Also wire grant template to grant/residency/prize entries")
    parser.add_argument("--effort", choices=["quick", "standard", "deep", "complex"],
                        help="Filter by effort level")
    parser.add_argument("--status",
                        help="Filter by current status")
    parser.add_argument("--id", dest="entry_id",
                        help="Enrich a specific entry by ID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying files")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompt")
    args = parser.parse_args()

    if args.report:
        entries = load_entries()
        run_report(entries)
        return

    do_materials = args.all or args.materials
    do_blocks = args.all or args.blocks
    do_variants = args.all or args.variants
    do_portal = args.all or args.portal

    if not (do_materials or do_blocks or do_variants or do_portal):
        parser.error("Specify --all, --materials, --blocks, --variants, --portal, or --report")

    entries = load_entries(include_filepath=True)
    run_enrich(
        entries=entries,
        do_materials=do_materials,
        do_blocks=do_blocks,
        do_variants=do_variants,
        do_portal=do_portal,
        grant_template=args.grant_template,
        effort_filter=args.effort,
        status_filter=args.status,
        entry_id=args.entry_id,
        dry_run=args.dry_run,
        auto_yes=args.yes,
    )


if __name__ == "__main__":
    main()
