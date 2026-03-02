#!/usr/bin/env python3
"""Blind spot tracker — maps startup-profile blind spots to concrete pipeline actions.

Loads the startup profile and market intelligence, scores blind spots via
funding_scorer.score_blindspots(), then maps each incomplete item to an
actionable next step (legal task, pipeline operation, or strategic move).

Usage:
    python scripts/blind_spot_tracker.py                # Full tracker report
    python scripts/blind_spot_tracker.py --actions      # Actionable items only
    python scripts/blind_spot_tracker.py --progress     # Progress bar only (one line)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from funding_scorer import PROFILE_FILE, load_startup_profile, score_blindspots  # noqa: F401 (PROFILE_FILE re-exported)
from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    PIPELINE_DIR_CLOSED,  # noqa: F401 (re-exported for callers)
    PIPELINE_DIR_SUBMITTED,  # noqa: F401 (re-exported for callers)
    SIGNALS_DIR,  # noqa: F401 (re-exported for callers)
    get_score,  # noqa: F401 (re-exported for callers)
    load_entries,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKET_INTEL_FILE = REPO_ROOT / "strategy" / "market-intelligence-2026.json"


def _load_market_intel() -> dict:
    """Load market intelligence JSON, return empty dict on failure."""
    if not MARKET_INTEL_FILE.exists():
        return {}
    try:
        with open(MARKET_INTEL_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def get_blind_spots(profile: dict | None = None) -> dict:
    """Get categorized blind spots checklist from the startup profile.

    Returns dict with keys: categories, total, completed, urgent.
    """
    if profile is None:
        profile = load_startup_profile()
    intel = _load_market_intel()
    return score_blindspots(profile, intel)


# --- Action mapping ---

# Spot name fragments → (action template, category hint, pipeline_relevant)
# Templates can use {submitted} and {entries} placeholders.
_ACTION_MAP = [
    ("83(b) election", "File 83(b) election (legal task, not pipeline)", "Legal & Financial", False),
    ("IP assignment", "Sign IP assignment agreements (legal task)", "Legal & Financial", False),
    ("D&O insurance", "Get D&O insurance quote ($125/mo)", "Legal & Financial", False),
    ("Delaware franchise tax", "Switch to Assumed Par Value method (legal task)", "Legal & Financial", False),
    ("Warm intro audit", "Review {submitted} submitted entries for warm intro opportunities", "Strategic", True),
    ("Open source strategy", "Document open source contribution approach", "Strategic", True),
    ("Academic partnership", "Identify STTR-eligible academic partners (required for STTR grants)", "Strategic", True),
    ("Documentation as leverage", "Update blocks with latest metrics ({entries} entries)", "Strategic", True),
    ("Disability grant", "Research disability-specific grant eligibility", "Strategic", True),
    ("Climate/ESG", "Add ESG/climate framing to relevant blocks", "Strategic", True),
    ("EU AI Act", "Document AI Act compliance posture", "Strategic", True),
    ("burnout", "Schedule personal infrastructure (health category)", "Health & Sustainability", False),
    ("Structured breaks", "Schedule personal infrastructure (health category)", "Health & Sustainability", False),
    ("Peer support", "Schedule personal infrastructure (health category)", "Health & Sustainability", False),
    ("Professional support", "Schedule personal infrastructure (health category)", "Health & Sustainability", False),
]


def map_spot_to_actions(spot_name: str, entries: list[dict]) -> list[dict]:
    """Given a blind spot name and pipeline entries, suggest concrete actions.

    Returns list of dicts with keys: spot, action, category, pipeline_relevant.
    """
    submitted = [e for e in entries if e.get("status") == "submitted"]
    result = []

    for fragment, action_tpl, category, pipeline_relevant in _ACTION_MAP:
        if fragment.lower() in spot_name.lower():
            action = action_tpl.format(
                submitted=len(submitted),
                entries=len(entries),
            )
            result.append({
                "spot": spot_name,
                "action": action,
                "category": category,
                "pipeline_relevant": pipeline_relevant,
            })

    # Fallback: if no mapping matched, produce a generic action
    if not result:
        result.append({
            "spot": spot_name,
            "action": f"Address: {spot_name}",
            "category": "Uncategorized",
            "pipeline_relevant": False,
        })

    return result


def compute_progress(blind_spots: dict) -> dict:
    """Compute progress metrics from blind spots result.

    Returns dict with keys: total, completed, pct, bar.
    """
    total = blind_spots.get("total", 0)
    completed = blind_spots.get("completed", 0)
    pct = round(completed / total * 100) if total > 0 else 0

    # Build ascii progress bar: 10 chars wide
    bar_width = 10
    filled = round(bar_width * completed / total) if total > 0 else 0
    bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
    progress_bar = f"[{bar}] {completed}/{total}"

    return {
        "total": total,
        "completed": completed,
        "pct": pct,
        "bar": progress_bar,
    }


def get_actionable_items(blind_spots: dict, entries: list[dict]) -> list[dict]:
    """Return only incomplete blind spots that have pipeline-relevant actions.

    Useful for morning digest integration.
    """
    result = []
    for cat_name, items in blind_spots.get("categories", {}).items():
        for item in items:
            label, done = item[0], item[1]
            if done:
                continue
            actions = map_spot_to_actions(label, entries)
            for action in actions:
                if action["pipeline_relevant"]:
                    action["category"] = cat_name
                    result.append(action)
    return result


def show_tracker(blind_spots: dict, entries: list[dict]) -> None:
    """Print formatted blind spot tracker report to stdout."""
    progress = compute_progress(blind_spots)

    print("BLIND SPOT TRACKER")
    print("=" * 60)
    print()
    print(f"  Progress: {progress['bar']}  ({progress['pct']}%)")
    print()

    # Per-category breakdown
    for cat_name, items in blind_spots.get("categories", {}).items():
        print(f"  {cat_name.upper()}")
        print(f"  {'-' * 40}")
        for item in items:
            label, done = item[0], item[1]
            check = "\u2713" if done else "\u2610"
            line = f"    {check} {label}"
            if not done:
                actions = map_spot_to_actions(label, entries)
                if actions:
                    line += f"\n      -> {actions[0]['action']}"
            print(line)
        print()

    # Urgent items
    urgent = blind_spots.get("urgent", [])
    if urgent:
        print("  !! URGENT ITEMS:")
        for item in urgent:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                cat, label, note = item[0], item[1], item[2]
                print(f"     [{cat}] {label} -- {note}")
            elif isinstance(item, dict):
                print(f"     {item.get('name', item)} -- {item.get('note', '')}")
        print()

    # Pipeline-relevant actions summary
    actionable = get_actionable_items(blind_spots, entries)
    if actionable:
        print(f"  PIPELINE-RELEVANT ACTIONS ({len(actionable)} items):")
        for a in actionable:
            print(f"    - {a['action']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Blind spot tracker — maps startup-profile gaps to pipeline actions"
    )
    parser.add_argument("--actions", action="store_true",
                        help="Show only actionable (pipeline-relevant) items")
    parser.add_argument("--progress", action="store_true",
                        help="Show progress bar only (single line)")
    args = parser.parse_args()

    blind_spots = get_blind_spots()
    entries = load_entries(ALL_PIPELINE_DIRS)

    if args.progress:
        progress = compute_progress(blind_spots)
        print(f"Blind spots: {progress['bar']}  ({progress['pct']}%)")
        return

    if args.actions:
        actionable = get_actionable_items(blind_spots, entries)
        if not actionable:
            print("No pipeline-relevant blind spot actions pending.")
            return
        print(f"ACTIONABLE BLIND SPOTS ({len(actionable)} items)")
        print("=" * 50)
        for a in actionable:
            print(f"  [{a['category']}] {a['action']}")
        return

    show_tracker(blind_spots, entries)


if __name__ == "__main__":
    main()
