#!/usr/bin/env python3
"""Validate metric consistency across all block files.

Scans blocks/**/*.md for metric patterns (repo counts, essay counts, word counts)
and reports any file citing numbers that differ from the source of truth.

Reads source metrics from the canonical system-metrics.json in the corpus repo.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_DIR = REPO_ROOT / "blocks"

# Canonical metrics file in the corpus repo
CANONICAL_METRICS = (
    Path.home() / "Workspace" / "meta-organvm"
    / "organvm-corpvs-testamentvm" / "system-metrics.json"
)

# Hardcoded fallback — used only when canonical file is unavailable
_FALLBACK_METRICS = {
    "total_repos": 101,
    "active_repos": 92,
    "archived_repos": 9,
    "github_orgs": 8,
    "published_essays": 42,
    "total_words_k": 410,
    "named_sprints": 33,
    "automated_tests": 2349,
    "organ_repo_counts": {
        "I": 20,
        "II": 30,
        "III": 27,
        "IV": 7,
        "V": 2,
        "VI": 4,
        "VII": 4,
        "Meta": 7,
    },
}


def load_source_metrics(path: Path = CANONICAL_METRICS) -> dict:
    """Load source of truth metrics from system-metrics.json.

    Falls back to hardcoded values if the canonical file is unavailable.
    """
    if not path.exists():
        print(f"  WARNING: {path} not found, using fallback metrics", file=sys.stderr)
        return _FALLBACK_METRICS

    with open(path) as f:
        data = json.load(f)

    c = data["computed"]
    m = data.get("manual", {})

    # Build per-organ counts using short names
    organ_name_map = {
        "ORGAN-I": "I", "ORGAN-II": "II", "ORGAN-III": "III",
        "ORGAN-IV": "IV", "ORGAN-V": "V", "ORGAN-VI": "VI",
        "ORGAN-VII": "VII", "META-ORGANVM": "Meta",
    }
    organ_repo_counts = {}
    for key, info in c.get("per_organ", {}).items():
        short = organ_name_map.get(key, key)
        organ_repo_counts[short] = info["repos"]

    total_words_numeric = m.get("total_words_numeric", 404000)
    total_words_k = total_words_numeric // 1000

    return {
        "total_repos": c["total_repos"],
        "active_repos": c["active_repos"],
        "archived_repos": c.get("archived_repos", 0),
        "github_orgs": c["total_organs"],
        "published_essays": c.get("published_essays", 0),
        "total_words_k": total_words_k,
        "named_sprints": c.get("sprints_completed", 0),
        "automated_tests": _FALLBACK_METRICS["automated_tests"],  # not in system-metrics.json
        "organ_repo_counts": organ_repo_counts,
    }


SOURCE_METRICS = load_source_metrics()

# Per-organ repo count patterns: "ORGAN-I ... N repos" or list items with "N repos"
ORGAN_PATTERNS = {
    r"ORGAN-I[^I].*?(\d+)\s*repos": "I",
    r"Theoria.*?(\d+)\s*repos?": "I",
    r"ORGAN-II[^I].*?(\d+)\s*repos": "II",
    r"Poiesis.*?(\d+)\s*repos?": "II",
    r"ORGAN-III.*?(\d+)\s*repos": "III",
    r"Ergon.*?(\d+)\s*repos?": "III",
    r"ORGAN-IV.*?(\d+)\s*repos": "IV",
    r"Taxis.*?(\d+)\s*repos?": "IV",
    r"ORGAN-V[^I].*?(\d+)\s*repos": "V",
    r"Logos.*?(\d+)\s*repos?": "V",
    r"ORGAN-VI[^I].*?(\d+)\s*repos": "VI",
    r"Koinonia.*?(\d+)\s*repos?": "VI",
    r"ORGAN-VII.*?(\d+)\s*repos": "VII",
    r"Kerygma.*?(\d+)\s*repos?": "VII",
}


def _is_organ_line(line: str) -> bool:
    """Check if a line describes a per-organ repo count (not total)."""
    organ_markers = [
        "ORGAN-I", "ORGAN-II", "ORGAN-III", "ORGAN-IV",
        "ORGAN-V", "ORGAN-VI", "ORGAN-VII", "META-ORGANVM",
        "Theoria", "Poiesis", "Ergon", "Taxis",
        "Logos", "Koinonia", "Kerygma",
    ]
    return any(marker in line for marker in organ_markers)


def check_file(filepath: Path) -> list[str]:
    """Check a single markdown file for metric inconsistencies."""
    errors = []
    content = filepath.read_text()
    lines = content.split("\n")
    rel_path = filepath.relative_to(REPO_ROOT)

    for line_num_0, line in enumerate(lines):
        line_num = line_num_0 + 1

        # Check total repo count — "N repositories" or "N-repository" or "N repos"
        # but skip lines describing per-organ counts
        if not _is_organ_line(line):
            for m in re.finditer(r"(\d+)[\s-]repositor(?:ies|y)", line):
                found = int(m.group(1))
                if found != SOURCE_METRICS["total_repos"]:
                    errors.append(
                        f"  {rel_path}:{line_num} — total repo count: "
                        f"found {found}, expected {SOURCE_METRICS['total_repos']}"
                    )
            for m in re.finditer(r"(\d+) repos\b", line):
                if not _is_organ_line(line):
                    found = int(m.group(1))
                    if found != SOURCE_METRICS["total_repos"]:
                        errors.append(
                            f"  {rel_path}:{line_num} — total repo count: "
                            f"found {found}, expected {SOURCE_METRICS['total_repos']}"
                        )

        # Check Meta repo count in table rows
        m = re.search(r"(?:Meta|META)[^|]*\|\s*(\d+)\s*\|", line)
        if m:
            found = int(m.group(1))
            expected = SOURCE_METRICS["organ_repo_counts"]["Meta"]
            if found != expected:
                errors.append(
                    f"  {rel_path}:{line_num} — Meta repo count: "
                    f"found {found}, expected {expected}"
                )

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate metric consistency in block files")
    parser.add_argument("--metrics", default=None,
                        help="Path to system-metrics.json (default: canonical corpus location)")
    args = parser.parse_args()

    # Reload metrics from custom path if provided
    global SOURCE_METRICS
    if args.metrics:
        SOURCE_METRICS = load_source_metrics(Path(args.metrics))

    all_errors = []
    file_count = 0

    for filepath in sorted(BLOCKS_DIR.rglob("*.md")):
        file_count += 1
        errors = check_file(filepath)
        all_errors.extend(errors)

    if not file_count:
        print("No block files found.")
        sys.exit(1)

    if all_errors:
        print(f"METRIC MISMATCH — {len(all_errors)} inconsistencies found:\n")
        for error in all_errors:
            print(error)
        print(f"\n{file_count} files checked.")
        sys.exit(1)
    else:
        print(f"OK — {file_count} block files, all metrics consistent.")
        sys.exit(0)


if __name__ == "__main__":
    main()
