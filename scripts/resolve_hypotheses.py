#!/usr/bin/env python3
"""Auto-resolve outcome hypotheses using historical evidence.

Resolves cold-app hypotheses that can be confirmed by historical data:
1,469 cold applications with 0% interview rate validates that cold-app
predictions were correct.

Usage:
    python scripts/resolve_hypotheses.py                   # Dry-run preview
    python scripts/resolve_hypotheses.py --apply           # Write resolved outcomes
    python scripts/resolve_hypotheses.py --json            # JSON output
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR

HYPOTHESES_PATH = SIGNALS_DIR / "hypotheses.yaml"

# Patterns that indicate a cold-app hypothesis
COLD_APP_PATTERNS = [
    "cold app",
    "referral pathway not established",
    "no warm introduction",
    "no referral",
]


def _is_cold_app_hypothesis(hypothesis: dict) -> bool:
    """Check if a hypothesis is about cold application failure."""
    text = (hypothesis.get("hypothesis") or "").lower()
    return any(p in text for p in COLD_APP_PATTERNS)


def resolve_cold_app_hypotheses(
    hyp_path: Path = HYPOTHESES_PATH,
    dry_run: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Resolve cold-app hypotheses using historical evidence.

    Returns (resolved, unresolved) lists of hypothesis dicts.
    If dry_run=False, writes the resolved outcomes back to the file.
    """
    if not hyp_path.exists():
        return [], []

    with open(hyp_path) as f:
        data = yaml.safe_load(f)

    hypotheses = data.get("hypotheses", []) if isinstance(data, dict) else data or []
    resolved = []
    unresolved = []

    for h in hypotheses:
        if h.get("outcome") is not None:
            continue  # already resolved
        if _is_cold_app_hypothesis(h):
            h["outcome"] = "confirmed"
            h["predicted_outcome"] = "rejected"
            h["resolution_date"] = date.today().isoformat()
            h["resolution_evidence"] = (
                "historical data: 1,469 cold applications (Jul 2024 - Apr 2025) "
                "with 0% interview rate confirms cold-app hypothesis"
            )
            resolved.append(h)
        else:
            unresolved.append(h)

    if not dry_run and resolved:
        with open(hyp_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return resolved, unresolved


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-resolve outcome hypotheses")
    parser.add_argument("--apply", action="store_true", help="Write resolved outcomes")
    parser.add_argument("--json", action="store_true", dest="json_output", help="JSON output")
    args = parser.parse_args()

    resolved, unresolved = resolve_cold_app_hypotheses(
        dry_run=not args.apply,
    )

    if args.json_output:
        print(json.dumps({
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "entries": [{"entry_id": h["entry_id"], "outcome": h.get("outcome")}
                        for h in resolved],
        }, indent=2))
        return

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"HYPOTHESIS RESOLUTION — {mode}")
    print(f"{'=' * 50}")
    print(f"Resolved: {len(resolved)} cold-app hypotheses")
    print(f"Remaining: {len(unresolved)} unresolved")
    for h in resolved:
        print(f"  [+] {h['entry_id']}: confirmed (cold app)")
    if not args.apply and resolved:
        print(f"\nRun with --apply to write resolved outcomes to {HYPOTHESES_PATH}")


if __name__ == "__main__":
    main()
