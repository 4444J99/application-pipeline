#!/usr/bin/env python3
"""Auto-classify identity positions from job titles and descriptions.

Maps job characteristics to the 9 canonical identity positions instead of
defaulting everything to independent-engineer. Called from source_jobs.py
and discover_jobs.py when creating new pipeline entries.

Usage:
    from classify_position import classify_position
    position = classify_position(title, description)
"""

from __future__ import annotations

import re

# Keyword → position mapping. Order matters: first match wins.
# More specific patterns come before general ones.
POSITION_RULES: list[tuple[str, list[str]]] = [
    ("documentation-engineer", [
        r"technical\s*writ",
        r"documentation\s*engineer",
        r"docs?\s*engineer",
        r"content\s*architect",
        r"information\s*architect",
        r"docs?\s*lead",
        r"knowledge\s*engineer",
        r"developer\s*documentation",
    ]),
    ("governance-architect", [
        r"ai\s*(?:safety|governance|compliance|ethics)",
        r"responsible\s*ai",
        r"trust\s*(?:and|&)\s*safety",
        r"compliance\s*(?:engineer|architect)",
        r"policy\s*engineer",
        r"ai\s*risk",
        r"eu\s*ai\s*act",
        r"model\s*governance",
    ]),
    ("platform-orchestrator", [
        r"platform\s*engineer",
        r"developer\s*(?:experience|productivity|tools)\s*(?:engineer|lead)",
        r"engineering\s*effectiveness",
        r"devex\b",
        r"internal\s*tools",
        r"infrastructure\s*(?:engineer|architect)",
        r"developer\s*platform",
        r"staff.*platform",
    ]),
    ("founder-operator", [
        r"fractional\s*cto",
        r"technical\s*(?:co-?)?founder",
        r"entrepreneur\s*in\s*residence",
        r"eir\b",
        r"cto\s*(?:in|at)",
        r"founding\s*engineer",  # startup founding role
    ]),
    ("educator", [
        r"instructor",
        r"curriculum",
        r"instructional\s*design",
        r"learning\s*(?:engineer|architect|designer)",
        r"edtech",
        r"education\s*(?:engineer|technolog)",
        r"teaching",
        r"l\s*&\s*d\b",
    ]),
    ("creative-technologist", [
        r"creative\s*technolog",
        r"generative\s*(?:ai|art)",
        r"creative\s*engineer",
        r"art\s*(?:and|&)\s*tech",
        r"creative\s*(?:director|lead).*tech",
    ]),
    # systems-artist and community-practitioner are rarely auto-sourced
    # (art grants and identity-specific funding are manual entries)
]

# Default fallback — documentation-engineer reflects the actual work profile
# (70% documentation/governance, 22 languages, 739K words, MFA)
DEFAULT_POSITION = "documentation-engineer"


def classify_position(
    title: str,
    description: str = "",
) -> str:
    """Classify a job into an identity position based on title and description.

    Args:
        title: Job title string.
        description: Optional job description text.

    Returns:
        One of the 9 canonical identity position slugs.
    """
    combined = f"{title} {description}".lower()

    for position, patterns in POSITION_RULES:
        for pattern in patterns:
            if re.search(pattern, combined):
                return position

    return DEFAULT_POSITION


def classify_batch(entries: list[dict]) -> dict[str, int]:
    """Classify a batch of entries and return position counts.

    Useful for diagnostics — shows the distribution across positions.
    """
    counts: dict[str, int] = {}
    for entry in entries:
        target = entry.get("target", {})
        title = target.get("title", "") if isinstance(target, dict) else ""
        description = target.get("description", "") if isinstance(target, dict) else ""
        pos = classify_position(title, description)
        counts[pos] = counts.get(pos, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from pipeline_lib import ALL_PIPELINE_DIRS, load_entries

    entries = load_entries(dirs=ALL_PIPELINE_DIRS)
    print(f"Classifying {len(entries)} entries...\n")

    counts = classify_batch(entries)
    for pos, count in counts.items():
        pct = count / len(entries) * 100
        print(f"  {pos:<30} {count:>5}  ({pct:5.1f}%)")

    # Show reclassification opportunities
    reclassified = 0
    for entry in entries:
        current = entry.get("fit", {}).get("identity_position", "independent-engineer") if isinstance(entry.get("fit"), dict) else "independent-engineer"
        target = entry.get("target", {})
        title = target.get("title", "") if isinstance(target, dict) else ""
        suggested = classify_position(title)
        if suggested != current and suggested != DEFAULT_POSITION:
            if reclassified < 20:
                print(f"\n  RECLASSIFY: {entry.get('id', '?')}")
                print(f"    Current:   {current}")
                print(f"    Suggested: {suggested}")
                print(f"    Title:     {title}")
            reclassified += 1

    if reclassified > 20:
        print(f"\n  ... and {reclassified - 20} more reclassification opportunities")
    print(f"\n  Total reclassification opportunities: {reclassified}")
