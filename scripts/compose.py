#!/usr/bin/env python3
"""Assemble blocks into target-specific submission documents."""

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIRS = [
    REPO_ROOT / "pipeline" / "active",
    REPO_ROOT / "pipeline" / "submitted",
    REPO_ROOT / "pipeline" / "closed",
]
BLOCKS_DIR = REPO_ROOT / "blocks"
VARIANTS_DIR = REPO_ROOT / "variants"


def find_entry(target_id: str) -> dict | None:
    """Find a pipeline entry by ID."""
    for pipeline_dir in PIPELINE_DIRS:
        if not pipeline_dir.exists():
            continue
        filepath = pipeline_dir / f"{target_id}.yaml"
        if filepath.exists():
            with open(filepath) as f:
                return yaml.safe_load(f)
    return None


def load_block(block_path: str) -> str | None:
    """Load a block file by its reference path."""
    full_path = BLOCKS_DIR / block_path
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if full_path.exists():
        return full_path.read_text()
    return None


def load_variant(variant_path: str) -> str | None:
    """Load a variant file by its reference path."""
    full_path = VARIANTS_DIR / variant_path
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if full_path.exists():
        return full_path.read_text()
    return None


def compose(entry: dict) -> str:
    """Compose a submission document from an entry's block references."""
    parts = []
    name = entry.get("name", entry.get("id", "Unknown"))
    org = entry.get("target", {}).get("organization", "")

    parts.append(f"# Submission: {name}")
    parts.append(f"**Target:** {org}")
    parts.append(f"**Track:** {entry.get('track', '?')}")
    parts.append(f"**Status:** {entry.get('status', '?')}")

    # Deadline
    deadline = entry.get("deadline", {})
    if isinstance(deadline, dict) and deadline.get("date"):
        parts.append(f"**Deadline:** {deadline['date']} {deadline.get('time', '')}")

    parts.append("")
    parts.append("---")
    parts.append("")

    # Blocks
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        parts.append("*No submission blocks configured.*")
        return "\n".join(parts)

    blocks_used = submission.get("blocks_used", {})
    if isinstance(blocks_used, dict):
        for slot, block_path in blocks_used.items():
            content = load_block(block_path)
            if content:
                parts.append(f"## {slot.replace('_', ' ').title()}")
                parts.append("")
                parts.append(content.strip())
                parts.append("")
            else:
                parts.append(f"## {slot.replace('_', ' ').title()}")
                parts.append(f"*Block not found: {block_path}*")
                parts.append("")

    # Variants
    variant_ids = submission.get("variant_ids", {})
    if isinstance(variant_ids, dict):
        for slot, variant_path in variant_ids.items():
            content = load_variant(variant_path)
            if content:
                parts.append(f"## {slot.replace('_', ' ').title()}")
                parts.append("")
                parts.append(content.strip())
                parts.append("")

    # Materials
    materials = submission.get("materials_attached", [])
    if materials:
        parts.append("## Attached Materials")
        for m in materials:
            parts.append(f"- {m}")
        parts.append("")

    # Portfolio URL
    portfolio = submission.get("portfolio_url")
    if portfolio:
        parts.append(f"**Portfolio:** {portfolio}")
        parts.append("")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Compose submission from blocks")
    parser.add_argument("--target", required=True,
                        help="Target ID (matches pipeline YAML filename)")
    parser.add_argument("--output", "-o",
                        help="Output file (default: stdout)")
    args = parser.parse_args()

    entry = find_entry(args.target)
    if not entry:
        print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
        print(f"Searched: {[str(d) for _, d in PIPELINE_DIRS]}", file=sys.stderr)
        sys.exit(1)

    document = compose(entry)

    if args.output:
        Path(args.output).write_text(document)
        print(f"Composed submission written to {args.output}")
    else:
        print(document)


if __name__ == "__main__":
    main()
