#!/usr/bin/env python3
"""Validate metric consistency across block files, profiles, and strategy docs.

Scans blocks/**/*.md, targets/profiles/*.json, and strategy/*.md for metric
patterns (repo counts, word counts, essay counts, test counts, sprint counts)
and reports any file citing numbers that differ from the source of truth.

Reads source metrics from the canonical system-metrics.json in the corpus repo.

Usage:
    python scripts/check_metrics.py                 # Full consistency check
    python scripts/check_metrics.py --fix --dry-run  # Preview fixes
    python scripts/check_metrics.py --fix --yes      # Apply fixes
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_DIR = REPO_ROOT / "blocks"
PROFILES_DIR = REPO_ROOT / "targets" / "profiles"
STRATEGY_DIR = REPO_ROOT / "strategy"

# Canonical metrics file in the corpus repo
CANONICAL_METRICS = (
    Path.home() / "Workspace" / "meta-organvm"
    / "organvm-corpvs-testamentvm" / "system-metrics.json"
)

# Hardcoded fallback — used only when canonical file is unavailable
_FALLBACK_METRICS = {
    "total_repos": 103,
    "active_repos": 94,
    "archived_repos": 9,
    "github_orgs": 8,
    "published_essays": 42,
    "total_words_k": 810,
    "named_sprints": 33,
    "automated_tests": 2349,
    "organ_repo_counts": {
        "I": 20,
        "II": 30,
        "III": 27,
        "IV": 7,
        "V": 2,
        "VI": 6,
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

    total_words_numeric = m.get("total_words_numeric", 810000)
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

# Extended metric patterns for word counts, essay counts, test counts, sprints
METRIC_PATTERNS = [
    # Total word counts: "~810K+ words of" (total system aggregate only)
    # Requires "words of" or "words across" or "words written" to distinguish from
    # per-component counts like "142K words" (essay word count)
    {
        "name": "word_count_k",
        "patterns": [
            r"~?(\d+)K\+?\s*words\s+(?:of|across|written|total)",
            r"(\d{3}),000\+?\s*words\s+(?:of|across|written|total)",
        ],
        "metric_key": "total_words_k",
        "transform": lambda m, pat_idx: int(m.group(1)),
    },
    # Essay counts: "42 essays", "42 published essays"
    {
        "name": "essay_count",
        "patterns": [
            r"(\d+)\s*(?:published\s+)?essays",
        ],
        "metric_key": "published_essays",
        "transform": lambda m, pat_idx: int(m.group(1)),
    },
    # Test counts: "2,349+ automated tests", "2,349 tests across N" (total aggregate only)
    # Avoids matching per-project breakdowns like "1,095 unit/integration tests"
    {
        "name": "test_count",
        "patterns": [
            r"([\d,]+)\+?\s*automated\s+tests",
            r"([\d,]+)\+?\s*tests\s+across\s+\d+",
        ],
        "metric_key": "automated_tests",
        "transform": lambda m, pat_idx: int(m.group(1).replace(",", "")),
    },
    # Sprint counts: "33 sprints", "33 named sprints"
    {
        "name": "sprint_count",
        "patterns": [
            r"(\d+)\s*(?:named\s+)?sprints",
        ],
        "metric_key": "named_sprints",
        "transform": lambda m, pat_idx: int(m.group(1)),
    },
]


def _is_organ_line(line: str) -> bool:
    """Check if a line describes a per-organ repo count (not total)."""
    organ_markers = [
        "ORGAN-I", "ORGAN-II", "ORGAN-III", "ORGAN-IV",
        "ORGAN-V", "ORGAN-VI", "ORGAN-VII", "META-ORGANVM",
        "Theoria", "Poiesis", "Ergon", "Taxis",
        "Logos", "Koinonia", "Kerygma",
    ]
    return any(marker in line for marker in organ_markers)


def check_file(filepath: Path, source_root: Path | None = None) -> list[dict]:
    """Check a single file for metric inconsistencies.

    Returns list of dicts with keys: file, line, metric, found, expected, line_text.
    """
    errors = []
    content = filepath.read_text()
    lines = content.split("\n")
    root = source_root or REPO_ROOT
    rel_path = filepath.relative_to(root) if filepath.is_relative_to(root) else filepath

    for line_num_0, line in enumerate(lines):
        line_num = line_num_0 + 1

        # Check total repo count — "N repositories" or "N-repository" or "N repos"
        # but skip lines describing per-organ counts
        if not _is_organ_line(line):
            for m in re.finditer(r"(\d+)[\s-]repositor(?:ies|y)", line):
                found = int(m.group(1))
                if found != SOURCE_METRICS["total_repos"]:
                    errors.append({
                        "file": str(rel_path), "line": line_num,
                        "metric": "total_repos", "found": found,
                        "expected": SOURCE_METRICS["total_repos"],
                        "line_text": line.strip(),
                    })
            for m in re.finditer(r"(\d+) repos\b", line):
                if not _is_organ_line(line):
                    found = int(m.group(1))
                    if found != SOURCE_METRICS["total_repos"]:
                        errors.append({
                            "file": str(rel_path), "line": line_num,
                            "metric": "total_repos", "found": found,
                            "expected": SOURCE_METRICS["total_repos"],
                            "line_text": line.strip(),
                        })

        # Check Meta repo count in table rows
        m = re.search(r"(?:Meta|META)[^|]*\|\s*(\d+)\s*\|", line)
        if m:
            found = int(m.group(1))
            expected = SOURCE_METRICS["organ_repo_counts"].get("Meta", 7)
            if found != expected:
                errors.append({
                    "file": str(rel_path), "line": line_num,
                    "metric": "meta_repos", "found": found,
                    "expected": expected,
                    "line_text": line.strip(),
                })

        # Check extended metrics (word counts, essay counts, test counts, sprints)
        for metric_def in METRIC_PATTERNS:
            for pat_idx, pattern in enumerate(metric_def["patterns"]):
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    found = metric_def["transform"](match, pat_idx)
                    expected = SOURCE_METRICS.get(metric_def["metric_key"])
                    if expected is not None and found != expected:
                        errors.append({
                            "file": str(rel_path), "line": line_num,
                            "metric": metric_def["name"], "found": found,
                            "expected": expected,
                            "line_text": line.strip(),
                        })

    return errors


def check_profile_json(filepath: Path) -> list[dict]:
    """Check a profile JSON file for stale metric values."""
    errors = []
    try:
        data = json.loads(filepath.read_text())
    except (json.JSONDecodeError, OSError):
        return errors

    rel_path = filepath.relative_to(REPO_ROOT) if filepath.is_relative_to(REPO_ROOT) else filepath

    # Check text fields within the profile for metric patterns
    def _check_text(text: str, field_name: str):
        if not isinstance(text, str):
            return
        for line in text.split("\n"):
            for metric_def in METRIC_PATTERNS:
                for pat_idx, pattern in enumerate(metric_def["patterns"]):
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        found = metric_def["transform"](match, pat_idx)
                        expected = SOURCE_METRICS.get(metric_def["metric_key"])
                        if expected is not None and found != expected:
                            errors.append({
                                "file": str(rel_path), "line": 0,
                                "metric": metric_def["name"], "found": found,
                                "expected": expected,
                                "line_text": f"[{field_name}] {line.strip()[:80]}",
                            })

            # Repo counts
            if not _is_organ_line(line):
                for m in re.finditer(r"(\d+)[\s-]repositor(?:ies|y)", line):
                    found = int(m.group(1))
                    if found != SOURCE_METRICS["total_repos"]:
                        errors.append({
                            "file": str(rel_path), "line": 0,
                            "metric": "total_repos", "found": found,
                            "expected": SOURCE_METRICS["total_repos"],
                            "line_text": f"[{field_name}] {line.strip()[:80]}",
                        })

    # Walk through all string values in the JSON
    def _walk(obj, path=""):
        if isinstance(obj, str):
            _check_text(obj, path)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _walk(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _walk(v, f"{path}[{i}]")

    _walk(data)
    return errors


def apply_fix(filepath: Path, error: dict) -> bool:
    """Apply a metric fix to a file. Returns True if fixed."""
    content = filepath.read_text()
    lines = content.split("\n")

    if error["line"] == 0:
        # JSON file — skip auto-fix for now
        return False

    line_idx = error["line"] - 1
    if line_idx >= len(lines):
        return False

    old_line = lines[line_idx]
    found = error["found"]
    expected = error["expected"]

    # Replace the found number with the expected one in the line
    # Handle comma-formatted numbers
    found_str = str(found)
    expected_str = str(expected)

    # Try comma-formatted replacement (e.g., "2,349" -> "2,349")
    found_comma = f"{found:,}"
    expected_comma = f"{expected:,}"

    new_line = old_line
    if found_comma in old_line:
        new_line = old_line.replace(found_comma, expected_comma, 1)
    elif found_str in old_line:
        # Be careful not to replace partial numbers
        new_line = re.sub(rf'\b{found_str}\b', expected_str, old_line, count=1)

    if new_line == old_line:
        return False

    lines[line_idx] = new_line
    filepath.write_text("\n".join(lines))
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Validate metric consistency in blocks, profiles, and strategy docs"
    )
    parser.add_argument("--metrics", default=None,
                        help="Path to system-metrics.json (default: canonical corpus location)")
    parser.add_argument("--fix", action="store_true",
                        help="Fix mismatched metrics in files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview fixes without writing")
    parser.add_argument("--yes", action="store_true",
                        help="Execute fixes (required with --fix)")
    args = parser.parse_args()

    # Reload metrics from custom path if provided
    global SOURCE_METRICS
    if args.metrics:
        SOURCE_METRICS = load_source_metrics(Path(args.metrics))

    all_errors = []
    file_count = 0

    # Scan blocks
    for filepath in sorted(BLOCKS_DIR.rglob("*.md")):
        file_count += 1
        errors = check_file(filepath)
        all_errors.extend(errors)

    # Scan profiles
    if PROFILES_DIR.exists():
        for filepath in sorted(PROFILES_DIR.glob("*.json")):
            file_count += 1
            errors = check_profile_json(filepath)
            all_errors.extend(errors)

    # Scan strategy docs
    if STRATEGY_DIR.exists():
        for filepath in sorted(STRATEGY_DIR.rglob("*.md")):
            file_count += 1
            errors = check_file(filepath)
            all_errors.extend(errors)

    if not file_count:
        print("No files found to check.")
        sys.exit(1)

    if not all_errors:
        print(f"OK — {file_count} files checked, all metrics consistent.")
        print(f"  Canonical values: {SOURCE_METRICS['total_repos']} repos, "
              f"~{SOURCE_METRICS['total_words_k']}K words, "
              f"{SOURCE_METRICS['published_essays']} essays, "
              f"{SOURCE_METRICS['automated_tests']} tests, "
              f"{SOURCE_METRICS['named_sprints']} sprints")
        sys.exit(0)

    print(f"METRIC MISMATCH — {len(all_errors)} inconsistencies found:\n")

    # Group by metric type for clearer output
    by_metric: dict[str, list[dict]] = {}
    for error in all_errors:
        by_metric.setdefault(error["metric"], []).append(error)

    for metric, errors in sorted(by_metric.items()):
        print(f"  [{metric}] ({len(errors)} mismatches)")
        for error in errors:
            line_ref = f":{error['line']}" if error["line"] else ""
            print(f"    {error['file']}{line_ref} — "
                  f"found {error['found']}, expected {error['expected']}")

    print(f"\n{file_count} files checked.")

    # Fix mode
    if args.fix:
        fixable = [e for e in all_errors if e["line"] > 0]
        if not fixable:
            print("\nNo auto-fixable errors (JSON profile fixes require manual editing).")
            sys.exit(1)

        if args.dry_run or not args.yes:
            print(f"\n[DRY RUN] Would fix {len(fixable)} errors in markdown files.")
            print("Run with --fix --yes to apply.")
        else:
            fixed = 0
            for error in fixable:
                filepath = REPO_ROOT / error["file"]
                if filepath.exists() and apply_fix(filepath, error):
                    fixed += 1
                    print(f"  Fixed: {error['file']}:{error['line']} "
                          f"({error['found']} -> {error['expected']})")
            print(f"\nFixed {fixed}/{len(fixable)} errors.")

    sys.exit(1)


if __name__ == "__main__":
    main()
