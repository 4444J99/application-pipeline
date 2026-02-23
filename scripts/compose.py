#!/usr/bin/env python3
"""Assemble blocks into target-specific submission documents."""

import argparse
import sys
from pathlib import Path

from pipeline_lib import (
    BLOCKS_DIR, VARIANTS_DIR, SUBMISSIONS_DIR,
    load_entry_by_id, load_profile,
    strip_markdown, count_words, count_chars,
)

# Common portal limits for flagging
WORD_LIMITS = [100, 150, 250, 500, 1000]
CHAR_LIMITS = [500, 1000, 2000, 5000]


def find_entry(target_id: str) -> dict | None:
    """Find a pipeline entry by ID."""
    _, data = load_entry_by_id(target_id)
    return data


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


def _profile_fallback(profile: dict, slot: str) -> str | None:
    """Try to get content for a slot from the profile JSON."""
    from draft import get_profile_content
    return get_profile_content(profile, slot, "medium")


def compose_sections(entry: dict, profile: dict | None = None) -> list[tuple[str, str]]:
    """Compose sections from an entry's block references. Returns (title, content) pairs.

    If profile is provided, missing blocks fall back to profile content.
    """
    sections = []

    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return sections

    blocks_used = submission.get("blocks_used", {})
    if isinstance(blocks_used, dict):
        for slot, block_path in blocks_used.items():
            title = slot.replace('_', ' ').title()
            content = load_block(block_path)
            if content:
                sections.append((title, content.strip()))
            elif profile:
                fallback = _profile_fallback(profile, slot)
                if fallback:
                    sections.append((title, fallback.strip()))
                else:
                    sections.append((title, f"[Block not found: {block_path}]"))
            else:
                sections.append((title, f"[Block not found: {block_path}]"))

    variant_ids = submission.get("variant_ids", {})
    if isinstance(variant_ids, dict):
        for slot, variant_path in variant_ids.items():
            title = slot.replace('_', ' ').title()
            content = load_variant(variant_path)
            if content:
                sections.append((title, content.strip()))

    return sections


def compose(entry: dict, profile: dict | None = None) -> str:
    """Compose a full submission document from an entry's block references."""
    parts = []
    name = entry.get("name", entry.get("id", "Unknown"))
    org = entry.get("target", {}).get("organization", "")

    parts.append(f"# Submission: {name}")
    parts.append(f"**Target:** {org}")
    parts.append(f"**Track:** {entry.get('track', '?')}")
    parts.append(f"**Status:** {entry.get('status', '?')}")

    deadline = entry.get("deadline", {})
    if isinstance(deadline, dict) and deadline.get("date"):
        parts.append(f"**Deadline:** {deadline['date']} {deadline.get('time', '')}")

    parts.append("")
    parts.append("---")
    parts.append("")

    sections = compose_sections(entry, profile)
    if not sections:
        submission = entry.get("submission", {})
        if not isinstance(submission, dict):
            parts.append("*No submission blocks configured.*")
        else:
            parts.append("*No blocks or variants referenced.*")
    else:
        for title, content in sections:
            parts.append(f"## {title}")
            parts.append("")
            parts.append(content)
            parts.append("")

    # Materials
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        materials = submission.get("materials_attached", [])
        if materials:
            parts.append("## Attached Materials")
            for m in materials:
                parts.append(f"- {m}")
            parts.append("")

        portfolio = submission.get("portfolio_url")
        if portfolio:
            parts.append(f"**Portfolio:** {portfolio}")
            parts.append("")

    return "\n".join(parts)


def print_counts(entry: dict, profile: dict | None = None):
    """Print per-section word and character counts with limit flags."""
    name = entry.get("name", entry.get("id", "?"))
    sections = compose_sections(entry, profile)

    print(f"Section Counts: {name}")
    print(f"{'─' * 60}")
    print(f"  {'Section':<30s} {'Words':>6s} {'Chars':>7s}  Flags")
    print(f"  {'─' * 30} {'─' * 6} {'─' * 7}  {'─' * 15}")

    total_words = 0
    total_chars = 0

    for title, content in sections:
        plain = strip_markdown(content)
        words = count_words(plain)
        chars = count_chars(plain)
        total_words += words
        total_chars += chars

        # Flag sections near common limits
        flags = []
        for limit in WORD_LIMITS:
            if words > limit:
                flags.append(f">{limit}w")
        for limit in CHAR_LIMITS:
            if chars > limit:
                flags.append(f">{limit}c")

        flag_str = " ".join(flags) if flags else "—"
        print(f"  {title:<30s} {words:>6d} {chars:>7d}  {flag_str}")

    print(f"  {'─' * 30} {'─' * 6} {'─' * 7}")
    print(f"  {'TOTAL':<30s} {total_words:>6d} {total_chars:>7d}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Compose submission from blocks")
    parser.add_argument("--target", required=True,
                        help="Target ID (matches pipeline YAML filename)")
    parser.add_argument("--output", "-o",
                        help="Output file (default: stdout)")
    parser.add_argument("--plain", action="store_true",
                        help="Output plain text (markdown stripped)")
    parser.add_argument("--counts", action="store_true",
                        help="Show per-section word/character counts")
    parser.add_argument("--max-words", type=int, default=0,
                        help="Warn if composed document exceeds N words")
    parser.add_argument("--word-count", action="store_true",
                        help="Report word count only (don't print document)")
    parser.add_argument("--snapshot", action="store_true",
                        help="Save composed output to pipeline/submissions/{id}-{date}.md")
    parser.add_argument("--profile", action="store_true",
                        help="Fall back to profile content when blocks are missing")
    args = parser.parse_args()

    entry = find_entry(args.target)
    if not entry:
        print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
        sys.exit(1)

    profile = None
    if args.profile:
        profile = load_profile(args.target)
        if not profile:
            print(f"Warning: No profile found for '{args.target}'", file=sys.stderr)

    # Counts mode
    if args.counts:
        print_counts(entry, profile)
        if not args.word_count and not args.output and not args.plain:
            return

    document = compose(entry, profile)

    if args.plain:
        document = strip_markdown(document)

    wc = count_words(document)

    if args.word_count:
        name = entry.get("name", args.target)
        print(f"{name}: {wc} words")
        if args.max_words and wc > args.max_words:
            print(f"  WARNING: exceeds limit of {args.max_words} words by {wc - args.max_words}")
            sys.exit(1)
        return

    if args.max_words and wc > args.max_words:
        print(f"WARNING: Document is {wc} words, exceeds limit of {args.max_words} "
              f"by {wc - args.max_words} words.", file=sys.stderr)

    if args.snapshot:
        from datetime import date as _date
        SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_name = f"{args.target}-{_date.today().isoformat()}.md"
        snapshot_path = SUBMISSIONS_DIR / snapshot_name
        snapshot_path.write_text(document)
        print(f"Snapshot saved: {snapshot_path.relative_to(SUBMISSIONS_DIR.parent.parent)} ({wc} words)")

    if args.output:
        Path(args.output).write_text(document)
        fmt = "plain text" if args.plain else "markdown"
        print(f"Composed submission written to {args.output} ({wc} words, {fmt})")
    else:
        if not args.counts and not args.snapshot:
            print(document)


if __name__ == "__main__":
    main()
