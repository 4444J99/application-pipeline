#!/usr/bin/env python3
"""Auto-derive startup profile fields from pipeline data.

Scans pipeline entries to populate derivable fields in startup-profile.yaml
that are currently set manually. Validates existing values and suggests
updates based on pipeline evidence.

Usage:
    python scripts/derive_profile.py              # Report: show derivable fields
    python scripts/derive_profile.py --apply      # Apply derivations to startup-profile.yaml
    python scripts/derive_profile.py --dry-run    # Preview changes (same as default)
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    PIPELINE_DIR_RESEARCH_POOL,
    load_entries,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILE_FILE = REPO_ROOT / "strategy" / "startup-profile.yaml"

# Tracks that indicate grant/art activity
ART_TRACKS = {"grant", "residency", "fellowship", "prize"}


def load_profile() -> dict:
    """Load startup-profile.yaml, return empty dict if missing."""
    if not PROFILE_FILE.exists():
        return {}
    try:
        with open(PROFILE_FILE) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def derive_from_pipeline(profile: dict) -> list[dict]:
    """Scan pipeline and compute derivable updates.

    Returns list of dicts with: section, field, current_value,
    derived_value, reason, confidence.
    """
    entries = load_entries(
        dirs=ALL_PIPELINE_DIRS + [PIPELINE_DIR_RESEARCH_POOL],
    )

    updates = []

    # --- prior_grant_history ---
    # True if any art-track entry has been submitted or has an outcome
    art_submitted = [
        e for e in entries
        if e.get("track") in ART_TRACKS
        and e.get("status") in ("submitted", "acknowledged", "interview", "outcome")
    ]
    current_grant = _nested_get(profile, "startup", "prior_grant_history")
    derived_grant = len(art_submitted) > 0

    if derived_grant != current_grant:
        updates.append({
            "section": "startup",
            "field": "prior_grant_history",
            "current_value": current_grant,
            "derived_value": derived_grant,
            "reason": f"{len(art_submitted)} art-track entries submitted/with-outcome",
            "confidence": "high",
        })

    # --- exhibition_history ---
    # Validate against pipeline: any art entries with positive outcome
    art_accepted = [
        e for e in entries
        if e.get("track") in ART_TRACKS
        and e.get("outcome") == "accepted"
    ]
    current_exhibit = _nested_get(profile, "startup", "exhibition_history")
    if art_accepted and not current_exhibit:
        updates.append({
            "section": "startup",
            "field": "exhibition_history",
            "current_value": current_exhibit,
            "derived_value": True,
            "reason": f"{len(art_accepted)} art-track entry(ies) accepted",
            "confidence": "high",
        })

    # --- Pipeline-derived stats (informational, not profile fields) ---
    by_track: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for e in entries:
        track = e.get("track", "unknown")
        status = e.get("status", "unknown")
        by_track[track] = by_track.get(track, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1

    # --- published_exhibited (founder section) ---
    # If exhibition_history is True in profile or derived, founder.published_exhibited should match
    exhibit_value = current_exhibit or (art_accepted and len(art_accepted) > 0)
    current_published = _nested_get(profile, "founder", "published_exhibited")
    if exhibit_value and not current_published:
        updates.append({
            "section": "founder",
            "field": "published_exhibited",
            "current_value": current_published,
            "derived_value": True,
            "reason": "exhibition_history is True → published_exhibited should match",
            "confidence": "medium",
        })

    return updates


def _nested_get(d: dict, *keys, default=None):
    """Nested dict access: _nested_get(d, 'a', 'b') -> d['a']['b']."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d


def apply_derivations(profile: dict, updates: list[dict], dry_run: bool = True) -> dict:
    """Merge updates into profile. Returns modified profile dict.

    If dry_run=True, returns modified copy without writing.
    """
    import copy
    modified = copy.deepcopy(profile)

    for update in updates:
        section = update["section"]
        field = update["field"]
        value = update["derived_value"]

        if section not in modified:
            modified[section] = {}
        if not isinstance(modified[section], dict):
            modified[section] = {}
        modified[section][field] = value

    if not dry_run and updates:
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROFILE_FILE, "w") as f:
            yaml.dump(modified, f, default_flow_style=False, sort_keys=False)

    return modified


def show_derivation_report(profile: dict, updates: list[dict]):
    """Print what would change and why."""
    today = date.today()
    print(f"PROFILE DERIVATION REPORT — {today.isoformat()}")
    print("=" * 60)

    if not updates:
        print("\nAll derivable fields are current. No changes needed.")
        print(f"\nProfile: {PROFILE_FILE}")
        return

    print(f"\n{len(updates)} field(s) can be updated:\n")

    for u in updates:
        section = u["section"]
        field = u["field"]
        current = u["current_value"]
        derived = u["derived_value"]
        reason = u["reason"]
        confidence = u["confidence"]

        print(f"  {section}.{field}")
        print(f"    Current: {current}")
        print(f"    Derived: {derived}")
        print(f"    Reason:  {reason}")
        print(f"    Confidence: {confidence}")
        print()

    print("Apply with: python scripts/derive_profile.py --apply")
    print(f"Profile: {PROFILE_FILE}")


def show_pipeline_stats():
    """Print pipeline-derived statistics useful for profile context."""
    entries = load_entries(
        dirs=ALL_PIPELINE_DIRS + [PIPELINE_DIR_RESEARCH_POOL],
    )

    by_track: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for e in entries:
        track = e.get("track", "unknown")
        status = e.get("status", "unknown")
        by_track[track] = by_track.get(track, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1

    print("\nPIPELINE CONTEXT:")
    print(f"  Total entries: {len(entries)}")
    print(f"  By track: {dict(sorted(by_track.items(), key=lambda x: -x[1]))}")

    submitted = sum(1 for e in entries if e.get("status") in ("submitted", "acknowledged", "interview"))
    outcomes = sum(1 for e in entries if e.get("outcome"))
    print(f"  Submitted: {submitted} | With outcome: {outcomes}")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-derive startup profile fields from pipeline data"
    )
    parser.add_argument("--apply", action="store_true",
                        help="Apply derivations to startup-profile.yaml")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes (same as default report)")
    args = parser.parse_args()

    profile = load_profile()
    updates = derive_from_pipeline(profile)

    show_derivation_report(profile, updates)
    show_pipeline_stats()

    if args.apply and updates:
        apply_derivations(profile, updates, dry_run=False)
        print(f"\nApplied {len(updates)} update(s) to {PROFILE_FILE}")
    elif args.apply and not updates:
        print("\nNo updates to apply.")


if __name__ == "__main__":
    main()
