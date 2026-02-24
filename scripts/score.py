#!/usr/bin/env python3
"""Score pipeline entries against the multi-dimensional rubric.

Auto-derives scores for deadline_feasibility, financial_alignment,
portal_friction, and effort_to_value from existing data. Estimates
human-judgment dimensions from existing fit.score and context.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    load_entries as _load_entries_raw,
    load_entry_by_id,
)

# Dimension weights (must sum to 1.0)
WEIGHTS = {
    "mission_alignment": 0.25,
    "evidence_match": 0.20,
    "track_record_fit": 0.15,
    "financial_alignment": 0.10,
    "effort_to_value": 0.10,
    "strategic_value": 0.10,
    "deadline_feasibility": 0.05,
    "portal_friction": 0.05,
}

# Benefits cliff thresholds (annual USD)
SNAP_LIMIT = 20352
MEDICAID_LIMIT = 21597
ESSENTIAL_PLAN_LIMIT = 39125

# Portal friction scores by portal type
PORTAL_SCORES = {
    "email": 9,
    "custom": 6,
    "web": 6,
    "submittable": 5,
    "greenhouse": 5,
    "workable": 5,
    "slideroom": 4,
}

# Strategic value by track (base estimates, individual overrides possible)
STRATEGIC_BASE = {
    "grant": 7,
    "prize": 8,
    "fellowship": 7,
    "residency": 6,
    "program": 5,
    "writing": 5,
    "emergency": 3,
    "job": 4,
    "consulting": 3,
}

# High-prestige organizations that get strategic_value boost
HIGH_PRESTIGE = {
    "Creative Capital": 10,
    "Doris Duke Charitable Foundation": 9,
    "LACMA": 9,
    "Whiting Foundation": 9,
    "Prix Ars Electronica": 9,
    "S+T+ARTS Prize": 8,
    "Google": 8,
    "Anthropic": 8,
    "Eyebeam": 8,
    "Pioneer Works": 7,
    "Rauschenberg Foundation": 8,
    "ZKM": 8,
    "Headlands Center for the Arts": 7,
    "NEW INC": 7,
    "Lambda Literary": 6,
    "Tulsa Artist Fellowship": 8,
    "Processing Foundation": 6,
    "Watermill Center": 7,
}


def load_entries(entry_id: str | None = None) -> list[tuple[Path, dict]]:
    """Load pipeline entries as (filepath, data) tuples.

    If entry_id given, load only that one.
    """
    if entry_id:
        filepath, data = load_entry_by_id(entry_id)
        if filepath and data:
            return [(filepath, data)]
        return []

    entries = _load_entries_raw(include_filepath=True)
    return [(e.pop("_filepath"), e) for e in entries if "_filepath" in e]


def score_deadline_feasibility(entry: dict) -> int:
    """Score deadline feasibility from deadline data."""
    deadline = entry.get("deadline", {})
    if not isinstance(deadline, dict):
        return 7

    dtype = deadline.get("type", "")
    date_str = deadline.get("date")

    if dtype in ("rolling", "tba") or not date_str:
        return 9

    try:
        deadline_date = datetime.strptime(str(date_str), "%Y-%m-%d")
    except ValueError:
        return 7

    days_left = (deadline_date - datetime.now()).days

    if days_left < 0:
        return 1
    if days_left <= 1:
        return 2
    if days_left <= 3:
        return 3
    if days_left <= 7:
        return 5
    if days_left <= 14:
        return 6
    if days_left <= 30:
        return 8
    return 9


def score_financial_alignment(entry: dict) -> int:
    """Score financial alignment from amount and cliff notes."""
    amount = entry.get("amount", {})
    if not isinstance(amount, dict):
        return 9

    value = amount.get("value", 0)
    cliff_note = amount.get("benefits_cliff_note") or ""

    if value == 0:
        return 10

    # Check for explicit cliff warnings
    if "exceeds" in cliff_note.lower() or "nylag" in cliff_note.lower():
        return 4
    if "essential plan" in cliff_note.lower():
        return 5

    if value <= SNAP_LIMIT:
        return 9
    if value <= MEDICAID_LIMIT:
        return 8
    if value <= ESSENTIAL_PLAN_LIMIT:
        return 6
    if value <= 100000:
        return 4
    return 3


def score_portal_friction(entry: dict) -> int:
    """Score portal friction from portal type."""
    target = entry.get("target", {})
    if not isinstance(target, dict):
        return 6
    portal = target.get("portal", "custom")
    return PORTAL_SCORES.get(portal, 6)


def score_effort_to_value(entry: dict) -> int:
    """Estimate effort-to-value from amount, track, and blocks coverage."""
    amount = entry.get("amount", {})
    value = amount.get("value", 0) if isinstance(amount, dict) else 0
    track = entry.get("track", "")

    submission = entry.get("submission", {})
    blocks_count = len(submission.get("blocks_used", {}) or {}) if isinstance(submission, dict) else 0

    # Higher blocks coverage = lower effort
    coverage_bonus = min(blocks_count / 6, 1.0) * 2  # 0-2 bonus for block readiness

    # Base by track
    base = {
        "emergency": 8,  # low effort, high urgency
        "writing": 7,    # moderate effort, direct value
        "prize": 6,      # moderate effort, prestige value
        "grant": 5,      # higher effort, high value
        "fellowship": 5,
        "residency": 5,
        "program": 5,
        "consulting": 6,
        "job": 4,        # highest effort (interviews, etc.)
    }.get(track, 5)

    # Value adjustment
    if value >= 50000:
        base += 1
    elif value == 0 and track not in ("residency", "program"):
        base -= 1

    score = base + coverage_bonus
    return max(1, min(10, round(score)))


def score_strategic_value(entry: dict) -> int:
    """Score strategic value from organization prestige and track."""
    org = ""
    target = entry.get("target", {})
    if isinstance(target, dict):
        org = target.get("organization") or ""

    # Check high-prestige overrides
    for name, score in HIGH_PRESTIGE.items():
        if org and name.lower() in org.lower():
            return score

    # Fall back to track-based estimate
    track = entry.get("track", "")
    return STRATEGIC_BASE.get(track, 5)


def estimate_human_dimensions(entry: dict) -> dict[str, int]:
    """Estimate mission_alignment, evidence_match, track_record_fit from existing data.

    Uses the existing fit.score as a baseline, then adjusts based on
    identity_position match quality and blocks coverage.
    """
    fit = entry.get("fit", {})
    if not isinstance(fit, dict):
        fit = {}

    existing_score = fit.get("score", 5)
    position = fit.get("identity_position")
    framing = fit.get("framing", "")

    submission = entry.get("submission", {})
    blocks_count = len(submission.get("blocks_used", {}) or {}) if isinstance(submission, dict) else 0

    # Mission alignment: existing score is heavily influenced by this
    # If framing exists and is specific, slight boost
    mission = existing_score
    if framing and len(framing) > 30:
        mission = min(10, mission + 1)
    if not framing:
        mission = max(1, mission - 1)

    # Evidence match: blocks coverage matters
    evidence = existing_score
    if blocks_count >= 5:
        evidence = min(10, evidence + 1)
    elif blocks_count == 0:
        evidence = max(1, evidence - 2)
    elif blocks_count <= 2:
        evidence = max(1, evidence - 1)

    # Track record fit: generally slightly below mission alignment
    # Jobs require specific credentials, grants/prizes more flexible
    track = entry.get("track", "")
    track_record = existing_score
    if track in ("job",):
        track_record = max(1, track_record - 2)
    elif track in ("consulting",):
        track_record = max(1, track_record - 1)

    return {
        "mission_alignment": max(1, min(10, mission)),
        "evidence_match": max(1, min(10, evidence)),
        "track_record_fit": max(1, min(10, track_record)),
    }


def compute_dimensions(entry: dict) -> dict[str, int]:
    """Compute all 8 dimension scores for an entry.

    If existing dimensions are present, auto-derivable dimensions are
    always recomputed (they reflect current state), but human-judgment
    dimensions are preserved if they were previously set.
    """
    # Check for existing dimensions (human overrides)
    fit = entry.get("fit", {})
    existing = {}
    if isinstance(fit, dict):
        existing = fit.get("dimensions", {}) or {}

    dims = {}

    # Auto-derivable (always recompute)
    dims["deadline_feasibility"] = score_deadline_feasibility(entry)
    dims["financial_alignment"] = score_financial_alignment(entry)
    dims["portal_friction"] = score_portal_friction(entry)
    dims["effort_to_value"] = score_effort_to_value(entry)
    dims["strategic_value"] = score_strategic_value(entry)

    # Human-judgment: use existing values if present, otherwise estimate
    human_keys = ["mission_alignment", "evidence_match", "track_record_fit"]
    estimated = estimate_human_dimensions(entry)
    for key in human_keys:
        if key in existing and existing[key] is not None:
            dims[key] = int(existing[key])
        else:
            dims[key] = estimated[key]

    return dims


def compute_composite(dimensions: dict[str, int]) -> float:
    """Compute weighted composite score from dimensions."""
    total = 0.0
    for dim, weight in WEIGHTS.items():
        val = dimensions.get(dim, 5)
        total += val * weight
    return round(total, 1)


DIMENSION_ORDER = [
    "mission_alignment", "evidence_match", "track_record_fit",
    "financial_alignment", "effort_to_value", "strategic_value",
    "deadline_feasibility", "portal_friction",
]

# Below this composite score, recommend skipping the application
QUALIFICATION_THRESHOLD = 5.0


def qualify(entry: dict) -> tuple[bool, str]:
    """Return (should_apply, reason) based on composite score.

    Entries at or above QUALIFICATION_THRESHOLD get APPLY.
    Entries below get SKIP with an explanation of which dimensions drag it down.
    """
    dimensions = compute_dimensions(entry)
    composite = compute_composite(dimensions)

    if composite >= QUALIFICATION_THRESHOLD:
        return True, f"composite {composite:.1f} >= {QUALIFICATION_THRESHOLD}"

    # Find the weakest dimensions to explain why
    weak = sorted(
        ((dim, dimensions[dim]) for dim in DIMENSION_ORDER),
        key=lambda x: x[1],
    )
    weak_names = [f"{dim}={val}" for dim, val in weak[:3]]
    return False, f"composite {composite:.1f} < {QUALIFICATION_THRESHOLD} (weak: {', '.join(weak_names)})"


def update_entry_file(filepath: Path, dimensions: dict[str, int], composite: float, dry_run: bool = False):
    """Update a pipeline YAML file with new dimensions and composite score.

    Uses parse-modify-dump via PyYAML. Reads the file, updates the data
    structure, then writes it back preserving key ordering by constructing
    an OrderedDict-based output.
    """
    import re

    with open(filepath) as f:
        content = f.read()

    data = yaml.safe_load(content)
    old_score = data.get("fit", {}).get("score") if isinstance(data.get("fit"), dict) else None

    if dry_run:
        return old_score, composite

    # Update score in-place via regex (preserves surrounding formatting)
    # Match "  score: <number>" within the fit section
    content = re.sub(
        r"^(\s+score:\s+)[\d.]+",
        rf"\g<1>{composite}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Build new dimensions block
    # Detect the indentation used in the file for fit sub-keys
    fit_indent_match = re.search(r"^(\s+)score:", content, re.MULTILINE)
    indent = fit_indent_match.group(1) if fit_indent_match else "  "
    dim_indent = indent + "  "

    new_dims_lines = [f"{indent}dimensions:"]
    for key in DIMENSION_ORDER:
        new_dims_lines.append(f"{dim_indent}{key}: {dimensions[key]}")
    new_dims_block = "\n".join(new_dims_lines)

    # Replace existing dimensions block or insert before next top-level key after fit
    dims_pattern = re.compile(
        r"^(\s+dimensions:\s*\n)"  # dimensions: header
        r"(?:\s+\w+:\s*\d+\s*\n)*",  # dimension key-value lines
        re.MULTILINE,
    )

    if dims_pattern.search(content):
        content = dims_pattern.sub(new_dims_block + "\n", content, count=1)
    else:
        # No dimensions block exists — insert after the last fit sub-key
        # Find the fit section and its last indented line
        fit_section = re.search(
            r"^fit:\s*\n((?:\s+\S.*\n)*)",
            content,
            re.MULTILINE,
        )
        if fit_section:
            insert_pos = fit_section.end()
            content = content[:insert_pos] + new_dims_block + "\n" + content[insert_pos:]

    with open(filepath, "w") as f:
        f.write(content)

    return old_score, composite


def run_qualify(entries: list[tuple[Path, dict]]):
    """Print APPLY/SKIP recommendations for all entries."""
    apply_entries = []
    skip_entries = []

    for filepath, data in entries:
        entry_id = data.get("id", filepath.stem)
        should_apply, reason = qualify(data)
        if should_apply:
            apply_entries.append((entry_id, reason))
        else:
            skip_entries.append((entry_id, reason))

    if skip_entries:
        print("SKIP (below threshold):")
        for eid, reason in sorted(skip_entries, key=lambda x: x[1]):
            print(f"  {eid:<40s} {reason}")
        print()

    if apply_entries:
        print("APPLY (above threshold):")
        for eid, reason in sorted(apply_entries, key=lambda x: x[1], reverse=True):
            print(f"  {eid:<40s} {reason}")
        print()

    print(f"{'=' * 50}")
    print(
        f"Threshold: {QUALIFICATION_THRESHOLD} | "
        f"{len(apply_entries)} APPLY | {len(skip_entries)} SKIP"
    )


def main():
    parser = argparse.ArgumentParser(description="Score pipeline entries against rubric")
    parser.add_argument("--target", help="Score a single entry by ID")
    parser.add_argument("--all", action="store_true", help="Score all entries")
    parser.add_argument("--qualify", action="store_true",
                        help="Show APPLY/SKIP recommendations based on score threshold")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show scores without writing changes")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-dimension breakdowns")
    args = parser.parse_args()

    if not args.target and not args.all and not args.qualify:
        parser.error("Specify --target <id>, --all, or --qualify")

    # --qualify implies --all unless --target is given
    if args.qualify and not args.target:
        args.all = True

    entries = load_entries(args.target if args.target else None)
    if not entries:
        print(f"No entries found.", file=sys.stderr)
        sys.exit(1)

    if args.qualify:
        run_qualify(entries)
        return

    changes = []
    for filepath, data in entries:
        entry_id = data.get("id", filepath.stem)
        dimensions = compute_dimensions(data)
        composite = compute_composite(dimensions)

        old_score, new_score = update_entry_file(filepath, dimensions, composite, dry_run=args.dry_run)

        delta = ""
        if old_score is not None:
            diff = new_score - old_score
            if abs(diff) >= 0.5:
                delta = f" (was {old_score}, delta {diff:+.1f})"
            else:
                delta = f" (was {old_score}, ~same)"

        changes.append((entry_id, old_score, new_score, dimensions))

        if args.verbose:
            print(f"\n{'=' * 50}")
            print(f"{entry_id}: {new_score}{delta}")
            print(f"  {'Dimension':<25s} {'Score':>5s}  {'Weight':>6s}  {'Contrib':>7s}")
            print(f"  {'-' * 25} {'-' * 5}  {'-' * 6}  {'-' * 7}")
            for dim in [
                "mission_alignment", "evidence_match", "track_record_fit",
                "financial_alignment", "effort_to_value", "strategic_value",
                "deadline_feasibility", "portal_friction",
            ]:
                val = dimensions[dim]
                weight = WEIGHTS[dim]
                contrib = val * weight
                print(f"  {dim:<25s} {int(val):>5d}  {weight:>5.0%}  {contrib:>7.2f}")
            print(f"  {'COMPOSITE':<25s}        {'':>6s}  {new_score:>7.1f}")
        else:
            print(f"  {entry_id:<40s} {new_score:>5.1f}{delta}")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Scored {len(changes)} entries" + (" (dry run)" if args.dry_run else ""))

    if not args.dry_run:
        significant = [(eid, old, new, d) for eid, old, new, d in changes
                        if old is not None and abs(new - old) >= 1.0]
        if significant:
            print(f"\nSignificant changes (>= 1.0 delta):")
            for eid, old, new, _ in sorted(significant, key=lambda x: abs(x[2] - x[1]), reverse=True):
                print(f"  {eid:<40s} {old} -> {new} ({new - old:+.1f})")


if __name__ == "__main__":
    main()
