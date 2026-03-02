#!/usr/bin/env python3
"""Bridge portfolio case study metadata with pipeline entries.

Auto-suggests work samples from the portfolio site's project data for
submission materials, matching by identity position and track keywords.

Usage:
    python scripts/portfolio_bridge.py                                # Full bridge report
    python scripts/portfolio_bridge.py --target <id>                  # Suggestions for one entry
    python scripts/portfolio_bridge.py --position independent-engineer  # Filter by position
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    PIPELINE_DIR_ACTIVE,
    REPO_ROOT,
    get_score,
    load_entries,
)

# Portfolio site lives adjacent to the application-pipeline repo
PORTFOLIO_DIR = REPO_ROOT.parent / "portfolio"
PORTFOLIO_PROJECTS_PATH = PORTFOLIO_DIR / "src" / "data" / "projects.json"

# Maps each identity position to relevant organ affiliations and description keywords.
# Used by score_project_relevance() to rank portfolio projects for a given entry.
POSITION_PROJECT_MAP = {
    "independent-engineer": {
        "organs": ["ORGAN-I", "ORGAN-III", "ORGAN-IV"],
        "keywords": ["engine", "infra", "api", "testing", "ci"],
    },
    "systems-artist": {
        "organs": ["ORGAN-I", "ORGAN-II"],
        "keywords": ["generative", "art", "performance", "creative", "ritual"],
    },
    "educator": {
        "organs": ["ORGAN-V", "ORGAN-VI"],
        "keywords": ["curriculum", "reading", "learning", "teaching", "workshop"],
    },
    "creative-technologist": {
        "organs": ["ORGAN-II", "ORGAN-III", "ORGAN-IV"],
        "keywords": ["creative", "synthesis", "generative", "tool", "instrument"],
    },
    "community-practitioner": {
        "organs": ["ORGAN-VI", "ORGAN-VII"],
        "keywords": ["community", "salon", "reading", "distribution", "social"],
    },
}


def load_portfolio_projects() -> list[dict]:
    """Load curated projects from the portfolio site's data file.

    Returns:
        List of project dicts, or empty list if the file doesn't exist.
    """
    if not PORTFOLIO_PROJECTS_PATH.exists():
        return []
    try:
        with open(PORTFOLIO_PROJECTS_PATH) as f:
            data = json.load(f)
        return data.get("projects", [])
    except (json.JSONDecodeError, KeyError):
        return []


def score_project_relevance(
    project: dict,
    identity_position: str,
    track: str,
) -> float:
    """Score a portfolio project's relevance to a pipeline entry.

    Scoring rubric (0-10 scale):
        +3  project organ matches position's expected organs
        +2  per keyword match in project name/description (max +4)
        +2  project tier is flagship
        +1  project implementation_status is active

    Args:
        project: Portfolio project dict with name, organ, description, tier, etc.
        identity_position: One of the five canonical identity positions.
        track: Pipeline entry track (job, grant, residency, etc.).

    Returns:
        Relevance score clamped to [0, 10].
    """
    position_info = POSITION_PROJECT_MAP.get(identity_position, {})
    score = 0.0

    # Organ affiliation match
    matching_organs = position_info.get("organs", [])
    if project.get("organ", "") in matching_organs:
        score += 3.0

    # Keyword matches in name + description (max +4, +2 per match)
    keywords = position_info.get("keywords", [])
    searchable = (project.get("description", "") + " " + project.get("name", "")).lower()
    keyword_hits = 0
    for kw in keywords:
        if kw.lower() in searchable:
            keyword_hits += 1
    score += min(keyword_hits * 2.0, 4.0)

    # Flagship tier bonus
    if project.get("tier", "").lower() == "flagship":
        score += 2.0

    # Active implementation bonus
    if project.get("implementation_status", "").lower() == "active":
        score += 1.0

    return min(max(score, 0.0), 10.0)


def suggest_work_samples(
    entry: dict,
    projects: list[dict] | None = None,
    top_n: int = 5,
) -> list[dict]:
    """Suggest portfolio projects as work samples for a pipeline entry.

    Args:
        entry: Pipeline entry dict with fit.identity_position and track fields.
        projects: Portfolio projects list; loaded from disk if None.
        top_n: Maximum number of suggestions to return.

    Returns:
        List of suggestion dicts sorted by relevance_score descending, each with:
        project_name, url, relevance_score, organ, description.
    """
    if projects is None:
        projects = load_portfolio_projects()

    fit = entry.get("fit", {})
    identity_position = fit.get("identity_position", "")
    track = entry.get("track", "")

    scored = []
    for proj in projects:
        rel_score = score_project_relevance(proj, identity_position, track)
        scored.append({
            "project_name": proj.get("name", ""),
            "url": proj.get("url", ""),
            "relevance_score": rel_score,
            "organ": proj.get("organ", ""),
            "description": proj.get("description", ""),
        })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_n]


def suggest_for_batch(
    entries: list[dict] | None = None,
    top_n: int = 3,
) -> dict:
    """Suggest work samples for all staged/drafting pipeline entries.

    Args:
        entries: Pipeline entries list; loads active entries if None.
        top_n: Number of suggestions per entry.

    Returns:
        Dict with 'entries' (list of {entry_id, suggestions}) and 'total' count.
    """
    if entries is None:
        entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])

    # Filter to entries that need work samples (actively being prepared)
    actionable = [e for e in entries if e.get("status") in ("staged", "drafting")]

    projects = load_portfolio_projects()
    results = []
    for entry in actionable:
        suggestions = suggest_work_samples(entry, projects=projects, top_n=top_n)
        results.append({
            "entry_id": entry.get("id", "unknown"),
            "suggestions": suggestions,
        })

    return {"entries": results, "total": len(results)}


def show_bridge_report(entries: list[dict] | None = None) -> None:
    """Print a formatted portfolio-pipeline bridge report to stdout."""
    projects = load_portfolio_projects()

    if entries is None:
        entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])

    actionable = [e for e in entries if e.get("status") in ("staged", "drafting")]

    print("=" * 72)
    print("PORTFOLIO-PIPELINE BRIDGE")
    print("=" * 72)
    print(f"\nPortfolio projects loaded: {len(projects)}")
    print(f"Entries needing work samples (staged/drafting): {len(actionable)}")
    print()

    if not actionable:
        print("No staged or drafting entries found.")
        return

    unique_projects: set[str] = set()

    for entry in actionable:
        entry_id = entry.get("id", "unknown")
        name = entry.get("name", entry_id)
        fit = entry.get("fit", {})
        position = fit.get("identity_position", "unset")
        score = get_score(entry)

        print(f"--- {name} ({entry_id}) ---")
        print(f"    Position: {position}  |  Score: {score:.1f}  |  Status: {entry.get('status', '?')}")

        suggestions = suggest_work_samples(entry, projects=projects, top_n=3)
        if suggestions:
            print("    Top work sample suggestions:")
            for i, s in enumerate(suggestions, 1):
                print(f"      {i}. {s['project_name']} (relevance: {s['relevance_score']:.1f}, {s['organ']})")
                unique_projects.add(s["project_name"])
        else:
            print("    No portfolio projects available.")
        print()

    print("-" * 72)
    print(f"Summary: {len(actionable)} entries need work samples, "
          f"{len(unique_projects)} unique projects suggested")


def _filter_entries_by_position(entries: list[dict], position: str) -> list[dict]:
    """Filter entries to those matching a given identity position."""
    return [
        e for e in entries
        if e.get("fit", {}).get("identity_position", "") == position
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bridge portfolio case studies with pipeline entries for work sample suggestions."
    )
    parser.add_argument("--target", help="Show suggestions for a single entry ID")
    parser.add_argument("--position", help="Filter entries by identity position")
    args = parser.parse_args()

    if args.target:
        # Single-entry mode
        entries = load_entries(dirs=ALL_PIPELINE_DIRS)
        entry = next((e for e in entries if e.get("id") == args.target), None)
        if not entry:
            print(f"Error: entry '{args.target}' not found.")
            sys.exit(1)

        projects = load_portfolio_projects()
        suggestions = suggest_work_samples(entry, projects=projects)

        name = entry.get("name", args.target)
        fit = entry.get("fit", {})
        position = fit.get("identity_position", "unset")

        print(f"Work sample suggestions for: {name} ({args.target})")
        print(f"Position: {position}  |  Track: {entry.get('track', '?')}")
        print()

        if not suggestions:
            print("No portfolio projects available.")
            return

        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s['project_name']}")
            print(f"     Organ: {s['organ']}  |  Relevance: {s['relevance_score']:.1f}")
            print(f"     URL: {s['url']}")
            desc = s.get("description", "")
            if desc:
                # Truncate long descriptions
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                print(f"     {desc}")
            print()
        return

    entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])

    if args.position:
        if args.position not in POSITION_PROJECT_MAP:
            print(f"Error: unknown position '{args.position}'. "
                  f"Valid: {', '.join(sorted(POSITION_PROJECT_MAP))}")
            sys.exit(1)
        entries = _filter_entries_by_position(entries, args.position)

    show_bridge_report(entries=entries)


if __name__ == "__main__":
    main()
