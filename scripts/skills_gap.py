#!/usr/bin/env python3
"""Skills gap analysis — compare required skills against portfolio content.

Reuses the text_match TF-IDF tokenizer to extract required skills from
job postings and compare against block/profile content coverage.

Usage:
    python scripts/skills_gap.py --target <id>   # Single entry
    python scripts/skills_gap.py --all           # All entries
    python scripts/skills_gap.py --json          # JSON output
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    BLOCKS_DIR,
    REPO_ROOT,
    get_score,
    load_entries,
    load_entry_by_id,
)


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer, lowercased."""
    return re.findall(r"[a-z][a-z0-9+#.-]{1,30}", text.lower())


def _load_research_md(entry_id: str) -> str:
    """Load research.md for an entry if it exists."""
    for subdir in ("active", "submitted", "research_pool"):
        path = REPO_ROOT / "pipeline" / subdir / f"{entry_id}.md"
        if path.exists():
            return path.read_text()
    return ""


def extract_required_skills(entry: dict) -> list[str]:
    """Extract required skills from entry research notes and target fields.

    Looks for skill-like tokens in research.md, target.requirements, and
    submission.keywords.
    """
    texts = []

    # Research markdown
    research = _load_research_md(entry.get("id", ""))
    if research:
        texts.append(research)

    # Target requirements field
    target = entry.get("target", {})
    if isinstance(target, dict):
        reqs = target.get("requirements", "")
        if isinstance(reqs, str):
            texts.append(reqs)
        elif isinstance(reqs, list):
            texts.extend(str(r) for r in reqs)

    # Submission keywords
    submission = entry.get("submission", {})
    if isinstance(submission, dict):
        kw = submission.get("keywords", [])
        if isinstance(kw, list):
            texts.extend(str(k) for k in kw)

    combined = " ".join(texts)
    tokens = _tokenize(combined)

    # Filter to likely skill tokens (exclude common English words)
    stop_words = {
        "the", "and", "for", "with", "that", "this", "from", "have", "will",
        "are", "was", "were", "been", "being", "has", "had", "but", "not",
        "you", "your", "our", "can", "may", "all", "any", "each", "every",
        "about", "into", "over", "such", "than", "then", "them", "they",
        "their", "these", "those", "what", "when", "where", "which", "while",
        "who", "whom", "how", "should", "would", "could", "must", "shall",
        "experience", "work", "team", "role", "ability", "strong", "skills",
        "years", "including", "working", "understanding", "knowledge",
    }
    skills = [t for t in set(tokens) if t not in stop_words and len(t) > 2]
    return sorted(skills)


def _load_all_block_content() -> str:
    """Load all block markdown content for matching."""
    texts = []
    if BLOCKS_DIR.exists():
        for md in BLOCKS_DIR.rglob("*.md"):
            texts.append(md.read_text())
    return " ".join(texts)


def compute_coverage(required: list[str], content: str) -> dict:
    """Compute skill coverage against portfolio content.

    Returns dict with coverage_pct, matched, missing, and suggested_blocks.
    """
    content_tokens = set(_tokenize(content))
    matched = [s for s in required if s in content_tokens]
    missing = [s for s in required if s not in content_tokens]
    coverage_pct = len(matched) / len(required) * 100 if required else 100.0

    return {
        "total_required": len(required),
        "matched": matched,
        "missing": missing,
        "coverage_pct": round(coverage_pct, 1),
    }


def analyze_entry(entry: dict, block_content: str | None = None) -> dict:
    """Full skills gap analysis for a single entry."""
    if block_content is None:
        block_content = _load_all_block_content()

    required = extract_required_skills(entry)
    coverage = compute_coverage(required, block_content)

    return {
        "id": entry.get("id", "unknown"),
        "name": entry.get("name", ""),
        "score": get_score(entry),
        "required_skills": required,
        **coverage,
    }


def format_analysis(analysis: dict) -> str:
    """Format a single entry's skills gap analysis."""
    lines = [f"Skills Gap: {analysis['id']}", "=" * 50]
    lines.append(f"  Name:         {analysis['name']}")
    lines.append(f"  Score:        {analysis.get('score', 'N/A')}")
    lines.append(f"  Coverage:     {analysis['coverage_pct']:.1f}%")
    lines.append(f"  Required:     {analysis['total_required']} skills")
    lines.append(f"  Matched:      {len(analysis['matched'])}")
    lines.append(f"  Missing:      {len(analysis['missing'])}")
    if analysis["missing"]:
        lines.append("\n  Missing skills:")
        for skill in analysis["missing"][:20]:
            lines.append(f"    - {skill}")
        if len(analysis["missing"]) > 20:
            lines.append(f"    ... and {len(analysis['missing']) - 20} more")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Skills gap analysis")
    parser.add_argument("--target", metavar="ID", help="Analyze single entry")
    parser.add_argument("--all", action="store_true", help="Analyze all actionable entries")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    block_content = _load_all_block_content()

    if args.target:
        path, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Entry not found: {args.target}", file=sys.stderr)
            sys.exit(1)
        analysis = analyze_entry(entry, block_content)
        if args.json:
            print(json.dumps(analysis, indent=2, default=str))
        else:
            print(format_analysis(analysis))
        return

    entries = load_entries()
    actionable = [e for e in entries if e.get("status") in {"qualified", "drafting", "staged"}]

    results = [analyze_entry(e, block_content) for e in actionable]
    results.sort(key=lambda x: x["coverage_pct"])

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print("Skills Gap Analysis — All Actionable Entries")
        print("=" * 60)
        for r in results:
            emoji = "LOW" if r["coverage_pct"] < 50 else "MED" if r["coverage_pct"] < 80 else "HIGH"
            print(f"  [{emoji:>4s}] {r['id']:<40s} {r['coverage_pct']:>5.1f}% ({len(r['missing'])} missing)")
        print(f"\n  Total: {len(results)} entries analyzed")


if __name__ == "__main__":
    main()
