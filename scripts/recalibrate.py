#!/usr/bin/env python3
"""Quarterly rubric recalibration: propose weight adjustments based on outcomes.

Closes the feedback loop between rejection_learner insights and scoring
rubric weights. Requires human approval before any changes are applied.

Usage:
    python scripts/recalibrate.py                  # Preview proposed changes
    python scripts/recalibrate.py --apply --yes    # Apply after review
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import REPO_ROOT, atomic_write
from score import DIMENSION_ORDER, WEIGHTS, recalibrate_weights

RUBRIC_PATH = REPO_ROOT / "strategy" / "scoring-rubric.yaml"


def _load_rubric_text() -> str:
    return RUBRIC_PATH.read_text()


def run_proposal():
    """Analyze outcomes and propose weight adjustments."""
    suggested = recalibrate_weights()
    if suggested is None:
        print("INSUFFICIENT DATA: Need at least 2 accepted and 2 rejected entries")
        print("with dimension scores to compute recalibration.")
        print("\nCollect more outcome data before recalibrating.")
        return None

    print("RUBRIC RECALIBRATION PROPOSAL")
    print(f"Date: {date.today().isoformat()}")
    print(f"{'=' * 60}")
    print()

    print(f"  {'Dimension':<25s} {'Current':>8s} {'Suggested':>10s} {'Delta':>8s}")
    print(f"  {'-' * 25} {'-' * 8} {'-' * 10} {'-' * 8}")

    max_delta = 0.0
    for dim in DIMENSION_ORDER:
        current = WEIGHTS.get(dim, 0)
        new = suggested.get(dim, 0)
        delta = new - current
        max_delta = max(max_delta, abs(delta))
        marker = " ***" if abs(delta) >= 0.03 else ""
        print(f"  {dim:<25s} {current:>7.1%} {new:>9.1%} {delta:>+7.1%}{marker}")

    print()
    print(f"  Sum check: current={sum(WEIGHTS.values()):.3f}, suggested={sum(suggested.values()):.3f}")

    if max_delta < 0.02:
        print("\n  Current weights are well-calibrated (max delta < 2%). No changes needed.")
    elif max_delta < 0.05:
        print("\n  Minor adjustments suggested. Consider applying at next quarterly review.")
    else:
        print("\n  Significant recalibration suggested. Review dimension deltas marked ***.")

    return suggested


def apply_proposal(suggested: dict[str, float]):
    """Apply suggested weights to scoring-rubric.yaml with backup."""
    content = _load_rubric_text()
    rubric = yaml.safe_load(content)

    # Backup current weights in the rubric
    rubric["weights_previous"] = dict(rubric.get("weights", {}))
    rubric["weights_previous_date"] = date.today().isoformat()

    # Apply new weights
    rubric["weights"] = suggested
    rubric["last_recalibrated"] = date.today().isoformat()

    atomic_write(RUBRIC_PATH, yaml.dump(rubric, default_flow_style=False, sort_keys=False, allow_unicode=True))
    print(f"\nApplied new weights to {RUBRIC_PATH}")
    print("Previous weights saved as weights_previous for rollback.")


def main():
    parser = argparse.ArgumentParser(description="Quarterly rubric recalibration")
    parser.add_argument("--apply", action="store_true", help="Apply proposed weights")
    parser.add_argument("--yes", action="store_true", help="Confirm application")
    args = parser.parse_args()

    suggested = run_proposal()
    if suggested is None:
        return

    if args.apply:
        if not args.yes:
            print("\nAdd --yes to confirm applying these weights.")
            return
        apply_proposal(suggested)
    else:
        print("\nRun with --apply --yes to update scoring-rubric.yaml.")


if __name__ == "__main__":
    main()
