#!/usr/bin/env python3
"""One-time migration helper from 3 source locations to application-pipeline."""

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = Path.home() / "Workspace"

# Source locations
PORTFOLIO_INTAKE = WORKSPACE / "4444J99" / "portfolio" / "intake"
CORPUS_APPS = WORKSPACE / "meta-organvm" / "organvm-corpvs-testamentvm" / "applications"
CORPUS_DOCS_APPS = WORKSPACE / "meta-organvm" / "organvm-corpvs-testamentvm" / "docs" / "applications"

# Migration map: (source, destination_relative_to_repo_root)
MATERIAL_MIGRATIONS = [
    # From portfolio/intake/
    (PORTFOLIO_INTAKE / "multimedia-specialist.pdf", "materials/resumes/multimedia-specialist.pdf"),
    (PORTFOLIO_INTAKE / "auto_resume_research_report.md", "materials/resumes/auto-resume-research-report.md"),
    (PORTFOLIO_INTAKE / "The_Ulti-Meta_Manifesto.docx", "materials/The_Ulti-Meta_Manifesto.docx"),

    # From corpus applications/shared/
    (CORPUS_APPS / "shared" / "metrics-snapshot.md", None),  # Already extracted to blocks
    (CORPUS_APPS / "shared" / "system-overview.md", None),  # Already extracted to blocks

    # From corpus docs/applications/submission-materials/
    (CORPUS_DOCS_APPS / "submission-materials" / "watermill-artist-statement.md", "materials/work-samples/watermill-artist-statement.md"),
    (CORPUS_DOCS_APPS / "submission-materials" / "watermill-proposal.md", "materials/work-samples/watermill-proposal.md"),
]

COVER_LETTER_MIGRATIONS = [
    (CORPUS_DOCS_APPS / "cover-letters", "variants/cover-letters"),
]

STRATEGY_MIGRATIONS = [
    (CORPUS_DOCS_APPS / "09-qualification-assessment.md", None),  # Already extracted
    (CORPUS_DOCS_APPS / "10-funding-strategy.md", None),  # Already extracted
    (CORPUS_DOCS_APPS / "eruptio-execution-guide.md", "docs/eruptio-execution-guide.md"),
]

TARGET_MIGRATIONS = [
    (CORPUS_DOCS_APPS / "01-track-ai-engineering.md", "targets/jobs/ai-engineering-research.md"),
    (CORPUS_DOCS_APPS / "02-track-grants.md", "targets/grants/track-grants-overview.md"),
    (CORPUS_DOCS_APPS / "03-track-residencies.md", "targets/residencies/track-residencies-overview.md"),
    (CORPUS_DOCS_APPS / "06-ai-engineering-role-research.md", "targets/jobs/ai-engineering-role-research.md"),
    (CORPUS_DOCS_APPS / "11-funding-research-exhaustive.md", "targets/grants/funding-research-exhaustive.md"),
]


def copy_file(src: Path, dest_rel: str, dry_run: bool = False) -> bool:
    """Copy a file to destination, creating directories as needed."""
    dest = REPO_ROOT / dest_rel
    if not src.exists():
        print(f"  SKIP (not found): {src}")
        return False

    if dry_run:
        print(f"  WOULD COPY: {src.name} -> {dest_rel}")
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"  COPIED: {src.name} -> {dest_rel}")
    return True


def copy_directory(src: Path, dest_rel: str, dry_run: bool = False) -> int:
    """Copy all files from a directory."""
    if not src.exists():
        print(f"  SKIP (not found): {src}")
        return 0

    count = 0
    for f in sorted(src.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            dest = f"{dest_rel}/{f.name}"
            if copy_file(f, dest, dry_run):
                count += 1
    return count


def copy_profiles(dry_run: bool = False) -> int:
    """Copy profile JSON files to targets."""
    profiles_dir = CORPUS_DOCS_APPS / "profiles"
    if not profiles_dir.exists():
        return 0

    count = 0
    for f in sorted(profiles_dir.glob("*.json")):
        if f.name == "_index.json":
            dest = "targets/profiles-index.json"
        else:
            dest = f"targets/{f.stem}.json"
        if copy_file(f, dest, dry_run):
            count += 1
    return count


def copy_submission_scripts(dry_run: bool = False) -> int:
    """Copy submission scripts to scripts/legacy-submission/."""
    scripts_dir = CORPUS_DOCS_APPS / "submission-scripts"
    if not scripts_dir.exists():
        return 0
    return copy_directory(scripts_dir, "scripts/legacy-submission", dry_run)


def write_pointer(location: Path, pointer_text: str, dry_run: bool = False):
    """Write a README.md pointer in the old location."""
    readme = location / "README.md"
    if dry_run:
        print(f"  WOULD WRITE pointer: {readme}")
        return

    readme.write_text(pointer_text)
    print(f"  WROTE pointer: {readme}")


def main():
    parser = argparse.ArgumentParser(description="Migrate materials to application-pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--pointers", action="store_true",
                        help="Write README.md pointers in old locations")
    args = parser.parse_args()

    print("=" * 60)
    print("APPLICATION PIPELINE MIGRATION")
    print("=" * 60)

    if args.dry_run:
        print("\n*** DRY RUN — no changes will be made ***\n")

    # Materials
    print("\n--- Materials ---")
    for src, dest in MATERIAL_MIGRATIONS:
        if dest:
            copy_file(src, dest, args.dry_run)

    # Cover letters
    print("\n--- Cover Letters ---")
    for src, dest in COVER_LETTER_MIGRATIONS:
        copy_directory(src, dest, args.dry_run)

    # Strategy docs
    print("\n--- Strategy Documents ---")
    for src, dest in STRATEGY_MIGRATIONS:
        if dest:
            copy_file(src, dest, args.dry_run)

    # Target research
    print("\n--- Target Research ---")
    for src, dest in TARGET_MIGRATIONS:
        if dest:
            copy_file(src, dest, args.dry_run)

    # Profiles
    print("\n--- Profiles ---")
    copy_profiles(args.dry_run)

    # Submission scripts
    print("\n--- Legacy Submission Scripts ---")
    copy_submission_scripts(args.dry_run)

    # Pointers
    if args.pointers:
        print("\n--- Writing Pointers ---")

        pointer_portfolio = """\
# Materials Moved

Application materials have been migrated to the application-pipeline repo.

**New location:** `~/Workspace/4444J99/application-pipeline/materials/`

See: https://github.com/4444J99/application-pipeline
"""
        write_pointer(PORTFOLIO_INTAKE, pointer_portfolio, args.dry_run)

        pointer_apps = """\
# Applications Moved

Per-target application materials have been migrated to the application-pipeline repo.

**New location:** `~/Workspace/4444J99/application-pipeline/`
- Target research: `targets/`
- Pipeline tracking: `pipeline/`
- Narrative blocks: `blocks/`

See: https://github.com/4444J99/application-pipeline
"""
        write_pointer(CORPUS_APPS, pointer_apps, args.dry_run)

        pointer_docs = """\
# Application Documents Moved

Application tracker, covenant-ark derivatives, cover letters, submission scripts,
and strategy documents have been migrated to the application-pipeline repo.

**New location:** `~/Workspace/4444J99/application-pipeline/`

Original files remain here as the canonical source. The pipeline repo
consumes and composes from these materials.

See: https://github.com/4444J99/application-pipeline
"""
        write_pointer(CORPUS_DOCS_APPS, pointer_docs, args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
