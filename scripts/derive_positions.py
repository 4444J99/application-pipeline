#!/usr/bin/env python3
"""Derive identity position relevance from ecosystem activity data.

Reads system-snapshot.json to analyze which organs are most active,
then suggests which identity positions are best supported by current work.
This makes identity-positions.md a living document rather than a static list.

Surface 3 of the ecosystem integration spec.

Usage:
    python scripts/derive_positions.py                # Show position relevance
    python scripts/derive_positions.py --json         # Machine-readable output
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SNAPSHOT_PATH = (
    Path.home() / "Workspace" / "meta-organvm"
    / "organvm-corpvs-testamentvm" / "system-snapshot.json"
)

# Organ → position affinity map
# Which positions benefit from activity in each organ?
ORGAN_POSITION_AFFINITY: dict[str, list[tuple[str, float]]] = {
    "ORGAN-I": [
        ("independent-engineer", 0.3),
        ("creative-technologist", 0.4),
        ("systems-artist", 0.2),
    ],
    "ORGAN-II": [
        ("systems-artist", 0.8),
        ("creative-technologist", 0.5),
        ("educator", 0.1),
    ],
    "ORGAN-III": [
        ("independent-engineer", 0.5),
        ("platform-orchestrator", 0.3),
        ("founder-operator", 0.4),
    ],
    "ORGAN-IV": [
        ("platform-orchestrator", 0.8),
        ("governance-architect", 0.6),
        ("independent-engineer", 0.3),
        ("founder-operator", 0.3),
    ],
    "ORGAN-V": [
        ("documentation-engineer", 0.7),
        ("educator", 0.4),
        ("creative-technologist", 0.2),
        ("systems-artist", 0.2),
    ],
    "ORGAN-VI": [
        ("community-practitioner", 0.8),
        ("educator", 0.5),
        ("founder-operator", 0.2),
    ],
    "ORGAN-VII": [
        ("founder-operator", 0.3),
        ("creative-technologist", 0.2),
    ],
    "META-ORGANVM": [
        ("platform-orchestrator", 0.7),
        ("governance-architect", 0.5),
        ("documentation-engineer", 0.4),
        ("founder-operator", 0.5),
    ],
}

# Static evidence that always contributes regardless of snapshot
STATIC_EVIDENCE: dict[str, float] = {
    "documentation-engineer": 0.8,   # 739K words, MFA, 100+ courses
    "educator": 0.7,                  # 11 years, 100+ courses, 2000+ students
    "community-practitioner": 0.5,   # LGBTQ+, precarity, recovery
    "systems-artist": 0.4,           # MFA, governance as artwork
}


def compute_position_scores(snapshot: dict) -> dict[str, dict]:
    """Compute relevance scores for each position from ecosystem state.

    Returns a dict mapping position → {score, evidence, recommendation}.
    """
    organs = snapshot.get("organs", [])
    system = snapshot.get("system", {})

    # Build organ repo_count weights (normalized)
    total_repos = system.get("total_repos", 1)
    organ_weights: dict[str, float] = {}
    for organ in organs:
        key = organ.get("key", "")
        count = organ.get("repo_count", 0)
        organ_weights[key] = count / total_repos if total_repos else 0

    # Accumulate position scores from organ activity
    scores: dict[str, float] = {}
    evidence: dict[str, list[str]] = {}

    for organ_key, weight in organ_weights.items():
        affinities = ORGAN_POSITION_AFFINITY.get(organ_key, [])
        for position, affinity in affinities:
            contribution = weight * affinity
            scores[position] = scores.get(position, 0) + contribution
            if contribution > 0.02:  # threshold for mention
                evidence.setdefault(position, []).append(
                    f"{organ_key} ({weight:.0%} of repos, affinity {affinity})"
                )

    # Add static evidence
    for position, base_score in STATIC_EVIDENCE.items():
        scores[position] = scores.get(position, 0) + base_score

    # Normalize to 0-1 range
    max_score = max(scores.values()) if scores else 1
    if max_score > 0:
        for pos in scores:
            scores[pos] = round(scores[pos] / max_score, 3)

    # Build result
    result: dict[str, dict] = {}
    for position in sorted(scores, key=lambda p: -scores[p]):
        score = scores[position]
        rec = "strong" if score >= 0.7 else "moderate" if score >= 0.4 else "emerging"
        result[position] = {
            "score": score,
            "recommendation": rec,
            "evidence": evidence.get(position, []),
        }

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive identity position relevance")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--snapshot", default=str(SNAPSHOT_PATH))
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot)
    if not snapshot_path.is_file():
        print(f"ERROR: Snapshot not found at {snapshot_path}", file=sys.stderr)
        return 1

    with snapshot_path.open() as f:
        snapshot = json.load(f)

    scores = compute_position_scores(snapshot)

    if args.json:
        print(json.dumps(scores, indent=2))
        return 0

    print("Identity Position Relevance (derived from ecosystem activity)\n")
    print(f"{'Position':<30} {'Score':>6}  {'Level':<10}  Evidence")
    print("-" * 90)
    for position, data in scores.items():
        ev = ", ".join(data["evidence"][:3]) if data["evidence"] else "(static)"
        print(f"  {position:<28} {data['score']:>5.3f}  {data['recommendation']:<10}  {ev}")

    print(f"\nSource: {snapshot.get('generated_at', 'unknown')[:19]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
