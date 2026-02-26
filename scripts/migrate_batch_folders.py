#!/usr/bin/env python3
"""One-time migration: restructure batch resume directories into per-role folders.

Moves flat files like:
    batch-NN/<id>-resume.{html,pdf}
Into per-role folders:
    batch-NN/<id>/<id>-resume.{html,pdf}

Also copies matching cover letters and greenhouse answers into each role folder.
Updates pipeline YAML materials_attached references.

Usage:
    python scripts/migrate_batch_folders.py           # Dry run
    python scripts/migrate_batch_folders.py --execute  # Actually move files
"""

import argparse
import shutil
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RESUMES_DIR = REPO_ROOT / "materials" / "resumes"
VARIANTS_DIR = REPO_ROOT / "variants"
ANSWERS_DIR = Path(__file__).resolve().parent / ".greenhouse-answers"
PIPELINE_DIRS = [
    REPO_ROOT / "pipeline" / "active",
    REPO_ROOT / "pipeline" / "submitted",
    REPO_ROOT / "pipeline" / "deferred",
    REPO_ROOT / "pipeline" / "closed",
]

BATCHES = ["batch-01", "batch-02", "batch-03"]


def find_resume_files(batch_dir: Path) -> list[tuple[str, list[Path]]]:
    """Find flat resume files (not already in subdirectories) grouped by entry ID."""
    entries: dict[str, list[Path]] = {}
    for f in sorted(batch_dir.iterdir()):
        if f.is_file() and f.name.endswith(("-resume.html", "-resume.pdf")):
            # Extract entry ID: strip the -resume.{ext} suffix
            entry_id = f.stem.replace("-resume", "")
            entries.setdefault(entry_id, []).append(f)
    return list(entries.items())


def find_cover_letter(entry_id: str) -> Path | None:
    """Find matching alchemized cover letter in variants/cover-letters/."""
    cl_path = VARIANTS_DIR / "cover-letters" / f"{entry_id}-alchemized.md"
    return cl_path if cl_path.exists() else None


def find_answers(entry_id: str) -> Path | None:
    """Find matching greenhouse answers."""
    answer_path = ANSWERS_DIR / f"{entry_id}.yaml"
    return answer_path if answer_path.exists() else None


def update_pipeline_yamls(old_ref: str, new_ref: str, execute: bool) -> int:
    """Update materials_attached references in pipeline YAML files."""
    updated = 0
    for pipeline_dir in PIPELINE_DIRS:
        if not pipeline_dir.exists():
            continue
        for yaml_path in sorted(pipeline_dir.glob("*.yaml")):
            if yaml_path.name.startswith("_"):
                continue
            content = yaml_path.read_text()
            if old_ref in content:
                if execute:
                    content = content.replace(old_ref, new_ref)
                    yaml_path.write_text(content)
                print(f"    YAML: {yaml_path.relative_to(REPO_ROOT)}: {old_ref} -> {new_ref}")
                updated += 1
    return updated


def migrate_batch(batch_name: str, execute: bool) -> dict:
    """Migrate a single batch directory."""
    batch_dir = RESUMES_DIR / batch_name
    if not batch_dir.exists():
        return {"moved": 0, "cover_letters": 0, "answers": 0, "yaml_updates": 0}

    entries = find_resume_files(batch_dir)
    if not entries:
        return {"moved": 0, "cover_letters": 0, "answers": 0, "yaml_updates": 0}

    stats = {"moved": 0, "cover_letters": 0, "answers": 0, "yaml_updates": 0}

    for entry_id, files in entries:
        role_dir = batch_dir / entry_id
        print(f"  {entry_id}/")

        if execute:
            role_dir.mkdir(exist_ok=True)

        # Move resume files
        for f in files:
            dest = role_dir / f.name
            print(f"    move: {f.name}")
            if execute:
                shutil.move(str(f), str(dest))
            stats["moved"] += 1

            # Update pipeline YAML references
            old_ref = f"resumes/{batch_name}/{f.name}"
            new_ref = f"resumes/{batch_name}/{entry_id}/{f.name}"
            stats["yaml_updates"] += update_pipeline_yamls(old_ref, new_ref, execute)

        # Copy cover letter
        cl_path = find_cover_letter(entry_id)
        if cl_path:
            dest = role_dir / "cover-letter.md"
            # Strip the metadata header — keep only the body after "---\n\n"
            cl_content = cl_path.read_text()
            separator = "\n---\n\n"
            if separator in cl_content:
                body = cl_content.split(separator, 1)[1]
            else:
                body = cl_content
            print(f"    copy: cover-letter.md (from {cl_path.name})")
            if execute:
                dest.write_text(body)
            stats["cover_letters"] += 1

        # Copy answers
        answer_path = find_answers(entry_id)
        if answer_path:
            dest = role_dir / "answers.yaml"
            print(f"    copy: answers.yaml (from {answer_path.name})")
            if execute:
                shutil.copy2(str(answer_path), str(dest))
            stats["answers"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Migrate batch resume directories to per-role folder structure"
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually move files (default is dry run)"
    )
    args = parser.parse_args()

    mode = "EXECUTING" if args.execute else "DRY RUN"
    print(f"=== Batch folder migration ({mode}) ===\n")

    totals = {"moved": 0, "cover_letters": 0, "answers": 0, "yaml_updates": 0}

    for batch in BATCHES:
        print(f"\n--- {batch} ---")
        stats = migrate_batch(batch, args.execute)
        for k in totals:
            totals[k] += stats[k]

    print(f"\n=== Summary ===")
    print(f"  Files moved:       {totals['moved']}")
    print(f"  Cover letters:     {totals['cover_letters']}")
    print(f"  Answers copied:    {totals['answers']}")
    print(f"  YAML refs updated: {totals['yaml_updates']}")

    if not args.execute:
        print(f"\nThis was a dry run. Re-run with --execute to apply changes.")


if __name__ == "__main__":
    main()
