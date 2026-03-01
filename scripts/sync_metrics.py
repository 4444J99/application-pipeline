#!/usr/bin/env python3
"""Metric sync checker: compare canonical metrics in covenant-ark.md against
blocks and identity-positions docs to prevent stale number credibility risks.

Usage:
    python scripts/sync_metrics.py              # Full consistency check
    python scripts/sync_metrics.py --verbose    # Show all matches, not just discrepancies
    python scripts/sync_metrics.py --files      # List all scanned files
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COVENANT_ARK_PATH = (
    Path.home() / "Workspace" / "meta-organvm" / "organvm-corpvs-testamentvm"
    / "docs" / "applications" / "00-covenant-ark.md"
)
BLOCKS_DIR = REPO_ROOT / "blocks"
STRATEGY_DIR = REPO_ROOT / "strategy"

# Scan identity/framing/pitch/methodology blocks and strategy docs.
# Exclude evidence/ and projects/ which contain per-project technical specs
# with legitimate sub-system counts that differ from system totals.
SCAN_PATHS = [
    STRATEGY_DIR / "identity-positions.md",
    BLOCKS_DIR / "identity",
    BLOCKS_DIR / "framings",
    BLOCKS_DIR / "pitches",
    BLOCKS_DIR / "methodology",
]

# Canonical metrics: label → config dict.
#
# Patterns are designed to match SYSTEM-WIDE totals only — not per-project counts.
# Key design decisions:
#   - repositories: only match 100-199 range (system total), not sub-counts like "70 repos with tests"
#   - automated_tests: only match "2,XXX" scale numbers (system total), not per-project counts (1,095, 1,254, 291)
#   - ci_cd_workflows: match "N+ CI/CD pipelines/workflows" explicitly
#   - essays: match "N published essays" or "N essays"
CANONICAL_METRICS = {
    "repositories": {
        "canonical": "103",
        "pattern": r"\b(1\d{2})\s*(?:repositories|repos)\b",
        "description": "Total repositories",
        # Matches 100-199 range: system total references. Excludes "70 repos with test coverage."
    },
    "essays": {
        "canonical": "42",
        "pattern": r"\b(\d{2})\s*(?:published\s+)?essays\b",
        "description": "Published essays",
    },
    "ci_cd_workflows": {
        "canonical": "94",
        "pattern": r"\b(\d{2,3})\+?\s*CI(?:/CD)?\s*(?:workflows?|pipelines?)\b",
        "description": "CI/CD workflows",
    },
    "dependency_edges": {
        "canonical": "43",
        "pattern": r"\b(\d{2})\s*(?:validated\s+)?dependency\s*edges?\b",
        "description": "Dependency edges",
    },
    "automated_tests": {
        "canonical": "2,349",
        "pattern": r"\b(2,\d{3})\+?\s*(?:automated\s+)?tests?\b",
        "description": "Automated tests (system total)",
        "allow_higher": True,
        # Only matches "2,XXX tests" — system-level totals. Per-project counts (1,095, 1,254, 291) won't match.
    },
    "development_sprints": {
        "canonical": "33",
        "pattern": r"\b(\d{2})\s*(?:named\s+)?(?:development\s+)?sprints?\b",
        "description": "Named development sprints",
    },
    "code_files": {
        "canonical": "21,160",
        "pattern": r"\b([\d,]+)\s*code\s+files?\b",
        "description": "Code files",
    },
    "test_files": {
        "canonical": "3,610",
        "pattern": r"\b([\d,]+)\s*test\s+files?\b",
        "description": "Test files",
    },
}


def _normalize_number(s: str) -> int:
    """Strip commas and convert to int for comparison."""
    try:
        return int(s.replace(",", "").replace("+", ""))
    except ValueError:
        return -1


def parse_canonical_metrics(path: Path) -> dict[str, str]:
    """Extract metrics from the Ground Truth Metrics table in covenant-ark.md."""
    if not path.exists():
        return {}

    text = path.read_text()
    metrics: dict[str, str] = {}

    # Find the metrics table section
    in_table = False
    table_re = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|")

    for line in text.splitlines():
        if "Ground Truth Metrics" in line:
            in_table = True
            continue
        if in_table:
            if line.startswith("##") and "Ground Truth" not in line:
                break
            if "|---" in line or not line.startswith("|"):
                continue
            m = table_re.match(line)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip()
                if key.lower() != "metric":
                    metrics[key] = val

    return metrics


def collect_scan_files() -> list[Path]:
    """Return all markdown files to scan."""
    files = []
    for p in SCAN_PATHS:
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.md"))
    return sorted(files)


def check_file(
    filepath: Path,
    metrics: dict,
    verbose: bool = False,
) -> list[dict]:
    """Scan a file for metric references and return discrepancy records."""
    try:
        text = filepath.read_text()
    except Exception:
        return []

    discrepancies = []

    for metric_key, config in metrics.items():
        canonical_raw = config["canonical"]
        pattern = config["pattern"]
        canonical_int = _normalize_number(canonical_raw)
        allow_higher = config.get("allow_higher", False)
        description = config["description"]

        for m in re.finditer(pattern, text, re.IGNORECASE):
            found_raw = m.group(1)
            found_int = _normalize_number(found_raw)

            if found_int < 0:
                continue

            is_match = (found_int == canonical_int)
            is_higher = allow_higher and found_int > canonical_int

            if is_match or is_higher:
                if verbose:
                    rel = filepath.relative_to(REPO_ROOT)
                    discrepancies.append({
                        "file": str(rel),
                        "metric": description,
                        "found": found_raw,
                        "canonical": canonical_raw,
                        "status": "ok",
                        "context": text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ").strip(),
                    })
                continue

            # It's a discrepancy
            rel = filepath.relative_to(REPO_ROOT)
            line_num = text[:m.start()].count("\n") + 1
            discrepancies.append({
                "file": str(rel),
                "line": line_num,
                "metric": description,
                "found": found_raw,
                "canonical": canonical_raw,
                "status": "stale",
                "context": text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ").strip(),
            })

    return discrepancies


def main():
    parser = argparse.ArgumentParser(
        description="Check metric consistency between covenant-ark.md and blocks/strategy docs"
    )
    parser.add_argument("--verbose", action="store_true",
                        help="Show all matches, not just discrepancies")
    parser.add_argument("--files", action="store_true",
                        help="List all files that will be scanned")
    args = parser.parse_args()

    # Load canonical values
    if not COVENANT_ARK_PATH.exists():
        print(f"WARNING: covenant-ark.md not found at {COVENANT_ARK_PATH}", file=sys.stderr)
        print("Using hardcoded canonical values from CANONICAL_METRICS.", file=sys.stderr)
        print()
    else:
        # Parse covenant-ark to verify our hardcoded values are current
        ark_metrics = parse_canonical_metrics(COVENANT_ARK_PATH)
        if args.verbose:
            print("CANONICAL METRICS (from covenant-ark.md):")
            for k, v in sorted(ark_metrics.items()):
                print(f"  {k}: {v}")
            print()

    scan_files = collect_scan_files()

    if args.files:
        print(f"FILES TO SCAN ({len(scan_files)}):")
        for f in scan_files:
            print(f"  {f.relative_to(REPO_ROOT)}")
        return

    all_results = []
    for filepath in scan_files:
        results = check_file(filepath, CANONICAL_METRICS, verbose=args.verbose)
        all_results.extend(results)

    stale = [r for r in all_results if r["status"] == "stale"]
    ok = [r for r in all_results if r["status"] == "ok"]

    print(f"METRIC SYNC CHECK — {REPO_ROOT.name}")
    print(f"{'=' * 60}")
    print(f"Files scanned: {len(scan_files)}")
    print(f"Matches found: {len(ok) + len(stale)}")
    print(f"Stale numbers: {len(stale)}")

    if stale:
        print("\nSTALE NUMBERS (need update to match covenant-ark):")
        print(f"{'─' * 60}")
        for r in sorted(stale, key=lambda x: x["file"]):
            print(f"\n  {r['file']}:{r.get('line', '?')}")
            print(f"  Metric: {r['metric']}")
            print(f"  Found:  {r['found']} → should be {r['canonical']}")
            print(f"  Context: ...{r['context']}...")
    else:
        print("\n✓ All metric references match canonical values in covenant-ark.md")

    if args.verbose and ok:
        print(f"\nVALID REFERENCES ({len(ok)}):")
        print(f"{'─' * 60}")
        for r in sorted(ok, key=lambda x: x["file"]):
            print(f"  {r['file']} — {r['metric']}: {r['found']} ✓")

    if stale:
        print(f"\nUpdate covenant-ark.md first, then fix the {len(stale)} stale reference(s) above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
