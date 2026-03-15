#!/usr/bin/env python3
"""Generate minimal profile JSONs for auto-sourced job entries without profiles.

Unblocks preflight checks that require a profile by generating a lightweight
profile from entry metadata (identity position, company, role name).

Usage:
    python scripts/generate_job_profile.py --target <id>           # Generate one profile
    python scripts/generate_job_profile.py --target <id> --yes     # Write to disk
    python scripts/generate_job_profile.py --batch --dry-run       # Preview all
    python scripts/generate_job_profile.py --batch --yes           # Generate all missing
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS_WITH_POOL,
    PROFILE_ID_MAP,
    PROFILES_DIR,
    load_entries,
    load_entry_by_id,
)

# Standard work samples shared across all auto-generated job profiles.
STANDARD_WORK_SAMPLES = [
    {
        "name": "Portfolio",
        "url": "https://4444j99.github.io/portfolio/",
        "description": "20 case studies, generative art, interactive resume",
    },
    {
        "name": "Agentic Titan",
        "url": "https://github.com/organvm-iv-taxis/agentic-titan",
        "description": "Multi-agent orchestration framework: 1,095 tests, 18 development phases",
    },
    {
        "name": "Recursive Engine",
        "url": "https://github.com/organvm-i-theoria/recursive-engine--generative-entity",
        "description": "Symbolic operating system: 1,254 tests, 85% coverage, custom DSL",
    },
    {
        "name": "Eight-Organ System Hub",
        "url": "https://github.com/meta-organvm/organvm-corpvs-testamentvm",
        "description": "103 repositories, 8 organizations, 49 essays, ~739K words of documentation",
    },
]

# Evidence highlights by identity position.
EVIDENCE_BY_POSITION = {
    "independent-engineer": [
        "103 repositories with 21,449 verified tests across 20 repos across flagship frameworks",
        "82+ CI/CD workflows with automated governance and promotion state machine",
        "AI-conductor methodology: AI generates volume, human directs architecture",
    ],
    "creative-technologist": [
        "Eight-organ system: 103 repos coordinating theory, art, commerce, and governance",
        "Production-grade orchestration frameworks with comprehensive test coverage",
        "49 published essays documenting creative-technical methodology in real time",
    ],
    "systems-artist": [
        "Eight-organ system as primary creative output: governance as artwork",
        "103 repositories across 8 organizations, 33 development sprints",
        "Solo production at institutional scale using AI as compositional instrument",
    ],
    "educator": [
        "11 years college instruction at 8+ institutions, 2,000+ students",
        "Eight-organ system as pedagogical case study in systems thinking",
        "49 essays documenting complex systems methodology for public audience",
    ],
    "community-practitioner": [
        "Precarity-informed systemic practice across 33 development sprints",
        "Community-centered design: ORGAN-VI (koinonia) community infrastructure",
        "Open-source methodology: 103 public repositories with full documentation",
    ],
    "documentation-engineer": [
        "739K words of production-grade documentation across 113 repositories",
        "Auto-generating context files (CLAUDE.md/GEMINI.md) with variable binding system",
        "MFA in Creative Writing, 100+ college courses in composition and rhetoric",
    ],
    "governance-architect": [
        "Promotion state machine (5 states), dependency graph validation, zero violations",
        "17-criterion omega scorecard with threshold-based advisory policies",
        "Human-oversight architecture: governance-rules.json, mutation operations with lineage",
    ],
    "platform-orchestrator": [
        "8-organization orchestration: registry, seed contracts, superproject management",
        "Pulse daemon computing system density every 15 minutes across 1,833 entities",
        "MCP server with 88 tools exposing full system graph to AI agent sessions",
    ],
    "founder-operator": [
        "Solo operation at institutional scale: 113 repos, 8 orgs, automated governance",
        "AI-conductor methodology: AI generates volume, human directs architecture",
        "Full-stack pipeline: application engine, portfolio, stakeholder portal, dashboard",
    ],
}


def profile_exists(entry_id: str) -> bool:
    """Check if a profile already exists for the given entry ID."""
    # Check via PROFILE_ID_MAP first
    profile_id = PROFILE_ID_MAP.get(entry_id, entry_id)
    profile_path = PROFILES_DIR / f"{profile_id}.json"
    return profile_path.exists()


def generate_profile(entry: dict) -> dict:
    """Generate a minimal profile dict from entry metadata."""
    entry_id = entry.get("id", "")
    name = entry.get("name", entry_id)
    target = entry.get("target", {})
    fit = entry.get("fit", {})

    position = fit.get("identity_position", "independent-engineer") if isinstance(fit, dict) else "independent-engineer"
    category = "Job" if entry.get("track") == "job" else entry.get("track", "job").capitalize()

    evidence = EVIDENCE_BY_POSITION.get(position, EVIDENCE_BY_POSITION["independent-engineer"])

    profile = {
        "target_id": entry_id,
        "target_name": name,
        "category": category,
        "primary_position": position,
        "auto_generated": True,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "work_samples": STANDARD_WORK_SAMPLES,
        "evidence_highlights": evidence,
    }

    # Add optional fields from entry if available
    amount = target.get("compensation") if isinstance(target, dict) else None
    if amount:
        profile["amount"] = amount

    url = target.get("application_url") if isinstance(target, dict) else None
    if url:
        profile["url"] = url

    deadline = entry.get("deadline", {})
    if isinstance(deadline, dict):
        dl_type = deadline.get("type")
        if dl_type:
            profile["deadline"] = dl_type.capitalize()

    return profile


def write_profile(entry_id: str, profile: dict) -> Path:
    """Write profile JSON to disk."""
    profile_path = PROFILES_DIR / f"{entry_id}.json"
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")
    return profile_path


def find_entries_without_profiles(entries: list[dict]) -> list[dict]:
    """Find auto-sourced entries that lack profiles."""
    results = []
    for entry in entries:
        tags = entry.get("tags", [])
        if not isinstance(tags, list):
            continue
        # Only auto-sourced job entries
        if "auto-sourced" not in tags:
            continue
        entry_id = entry.get("id", "")
        if not entry_id:
            continue
        # Skip entries that already have profiles
        if profile_exists(entry_id):
            continue
        # Skip terminal statuses
        status = entry.get("status", "")
        if status in {"outcome", "withdrawn"}:
            continue
        results.append(entry)
    return results


def main():
    parser = argparse.ArgumentParser(description="Generate minimal profiles for auto-sourced job entries")
    parser.add_argument("--target", metavar="ENTRY_ID", help="Generate profile for a single entry")
    parser.add_argument("--batch", action="store_true", help="Generate for all auto-sourced entries without profiles")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview without writing (default)")
    parser.add_argument("--yes", action="store_true", help="Write profiles to disk")
    args = parser.parse_args()

    if args.yes:
        args.dry_run = False

    if not args.target and not args.batch:
        parser.error("Provide --target <id> or --batch")

    if args.target:
        filepath, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Entry not found: {args.target}", file=sys.stderr)
            sys.exit(1)

        if profile_exists(args.target):
            print(f"Profile already exists for {args.target}")
            return

        entry["id"] = entry.get("id", args.target)
        profile = generate_profile(entry)

        if args.dry_run:
            print(f"[DRY RUN] Would generate profile for: {args.target}")
            print(json.dumps(profile, indent=2))
        else:
            path = write_profile(args.target, profile)
            print(f"Generated profile: {path}")
        return

    # Batch mode
    entries = load_entries(ALL_PIPELINE_DIRS_WITH_POOL, include_filepath=True)
    candidates = find_entries_without_profiles(entries)

    if not candidates:
        print("No auto-sourced entries need profiles.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Generating profiles for {len(candidates)} entries...")
    print()

    for entry in candidates:
        entry_id = entry.get("id", "")
        name = entry.get("name", entry_id)
        fit = entry.get("fit", {})
        position = fit.get("identity_position", "?") if isinstance(fit, dict) else "?"

        if args.dry_run:
            print(f"  would generate: {entry_id} ({position}) — {name}")
        else:
            profile = generate_profile(entry)
            path = write_profile(entry_id, profile)
            print(f"  generated: {path.name} ({position}) — {name}")

    if args.dry_run:
        print(f"\n{len(candidates)} profiles would be generated. Run with --yes to write.")


if __name__ == "__main__":
    main()
