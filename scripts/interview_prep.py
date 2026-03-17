#!/usr/bin/env python3
"""Interview preparation — generate prep materials for interview-status entries.

Combines pipeline YAML, org intelligence, skills gap analysis, STAR question
bank, and submission block talking points into a comprehensive prep document.

Usage:
    python scripts/interview_prep.py --target <id>     # Single entry
    python scripts/interview_prep.py --auto            # All interview-status entries
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    BLOCKS_DIR,
    REPO_ROOT,
    SIGNALS_DIR,
    get_score,
    load_entries,
    load_entry_by_id,
)

SUBMISSIONS_DIR = REPO_ROOT / "pipeline" / "submissions"

# STAR question bank by identity position
STAR_QUESTIONS = {
    "independent-engineer": [
        "Describe a time you designed a system that handled scale beyond initial requirements.",
        "Tell me about a testing strategy you implemented that caught critical bugs before production.",
        "Walk through a time you had to debug a complex distributed system issue.",
        "Describe how you introduced AI/automation into an engineering workflow.",
    ],
    "systems-artist": [
        "Describe a project where you used governance or institutional structures as artistic material.",
        "Tell me about a piece that required building custom software infrastructure.",
        "Walk through your process for translating systemic concepts into audience-accessible work.",
        "Describe how you sustain long-term artistic practice alongside technical work.",
    ],
    "educator": [
        "Describe a time you taught a complex technical concept to a non-technical audience.",
        "Tell me about a curriculum you designed from scratch.",
        "Walk through how you assess student learning in a project-based environment.",
        "Describe your approach to making abstract systems thinking concrete for learners.",
    ],
    "creative-technologist": [
        "Describe a project where you bridged creative vision with technical implementation.",
        "Tell me about a time you used AI orchestration in a production context.",
        "Walk through a system you built that served both creative and business goals.",
        "Describe how you evaluate emerging technologies for creative applications.",
    ],
    "community-practitioner": [
        "Describe how you built a community practice from limited resources.",
        "Tell me about a program that served an underrepresented population.",
        "Walk through a time systemic barriers affected your work and how you navigated them.",
        "Describe your approach to participatory design in community contexts.",
    ],
    "documentation-engineer": [
        "Describe a documentation system you designed from scratch at scale.",
        "Tell me about a time you treated documentation as a product, not an afterthought.",
        "Walk through how you keep 113 repos' documentation consistent and current.",
        "Describe your approach to auto-generating context files from structured data.",
    ],
    "governance-architect": [
        "Describe a governance system you designed that enforced human oversight over automated processes.",
        "Tell me about a compliance requirement you implemented as running code, not just policy.",
        "Walk through the promotion state machine and why state-skipping is prohibited by design.",
        "Describe how you would audit an AI system for EU AI Act compliance.",
    ],
    "platform-orchestrator": [
        "Describe how you designed infrastructure that lets one person manage 113 repositories.",
        "Tell me about the dependency graph design and why unidirectional flow matters.",
        "Walk through the pulse daemon — what it measures, how often, and what it triggers.",
        "Describe a developer productivity problem you solved with platform tooling.",
    ],
    "founder-operator": [
        "Describe building and operating a system that would normally require a team.",
        "Tell me about the AI-conductor methodology and how it changed your output capacity.",
        "Walk through a decision where you chose governance over speed.",
        "Describe what 'institutional scale as a solo practitioner' means in practice.",
    ],
}


def _load_org_intel(org: str) -> dict | None:
    """Load org intelligence if available."""
    try:
        import yaml
        from org_intelligence import aggregate_org
        contacts_path = SIGNALS_DIR / "contacts.yaml"
        contacts = []
        if contacts_path.exists():
            with open(contacts_path) as f:
                data = yaml.safe_load(f)
            contacts = data.get("contacts", []) if isinstance(data, dict) else []
        entries = load_entries()
        return aggregate_org(org, entries, contacts)
    except ImportError:
        return None


def _load_skills_gap(entry: dict) -> dict | None:
    """Load skills gap analysis if available."""
    try:
        from skills_gap import analyze_entry
        return analyze_entry(entry)
    except ImportError:
        return None


def _get_blocks_content(entry: dict) -> list[str]:
    """Get talking points from blocks used in submission."""
    blocks = (entry.get("submission", {}) or {}).get("blocks_used", {})
    if not isinstance(blocks, dict):
        return []

    talking_points = []
    for slot, block_path in blocks.items():
        full_path = BLOCKS_DIR / block_path
        if not full_path.suffix:
            full_path = full_path.with_suffix(".md")
        if full_path.exists():
            content = full_path.read_text()
            # Extract first non-frontmatter paragraph
            lines = content.split("\n")
            in_frontmatter = False
            for line in lines:
                if line.strip() == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if not in_frontmatter and line.strip() and not line.startswith("#"):
                    talking_points.append(f"[{slot}] {line.strip()[:200]}")
                    break
    return talking_points


def generate_prep(entry_id: str) -> str:
    """Generate comprehensive interview prep document."""
    path, entry = load_entry_by_id(entry_id)
    if not entry:
        return f"Entry not found: {entry_id}"

    name = entry.get("name", entry_id)
    score = get_score(entry)
    position = (entry.get("fit", {}) or {}).get("identity_position", "unknown")
    org = (entry.get("target", {}) or {}).get("organization", "unknown")
    track = entry.get("track", "unknown")

    lines = [
        f"# Interview Prep: {name}",
        f"**Date prepared:** {date.today()}",
        f"**Entry ID:** {entry_id}",
        f"**Score:** {score or 'N/A'}",
        f"**Position:** {position}",
        f"**Track:** {track}",
        "",
        "## Role Overview",
        f"- Organization: {org}",
        f"- Status: {entry.get('status', 'unknown')}",
    ]

    # Application URL
    target = entry.get("target", {})
    if isinstance(target, dict) and target.get("application_url"):
        lines.append(f"- URL: {target['application_url']}")

    # Amount
    amount = entry.get("amount", {})
    if isinstance(amount, dict) and amount.get("value"):
        lines.append(f"- Amount: {amount.get('value')} ({amount.get('type', '')})")

    # Org intelligence
    lines.append("\n## Organization Intelligence")
    org_intel = _load_org_intel(org)
    if org_intel:
        lines.append(f"- Total entries at {org}: {org_intel['total_entries']}")
        lines.append(f"- Contacts: {org_intel['total_contacts']} ({org_intel['active_contacts']} active)")
        lines.append(f"- Avg response: {org_intel.get('avg_response_days', 'N/A')} days")
        outcomes = org_intel.get("outcomes", {})
        if any(outcomes.values()):
            lines.append(f"- Historical outcomes: {outcomes}")
    else:
        lines.append("- (Org intelligence module not available)")

    # Skills gap
    lines.append("\n## Skills Gap")
    gap = _load_skills_gap(entry)
    if gap:
        lines.append(f"- Coverage: {gap['coverage_pct']:.1f}%")
        if gap.get("missing"):
            lines.append(f"- Missing skills: {', '.join(gap['missing'][:10])}")
            lines.append("- **Prepare responses for these gap areas**")
    else:
        lines.append("- (Skills gap module not available)")

    # STAR questions
    lines.append("\n## STAR Question Bank")
    questions = STAR_QUESTIONS.get(position, STAR_QUESTIONS.get("independent-engineer", []))
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q}")

    # Talking points from blocks
    lines.append("\n## Talking Points (from submission blocks)")
    talking_points = _get_blocks_content(entry)
    if talking_points:
        for tp in talking_points:
            lines.append(f"- {tp}")
    else:
        lines.append("- (No blocks used in submission)")

    # Key metrics to mention
    lines.append("\n## Key Metrics to Reference")
    lines.append("- 103 repositories across 8 organizational organs")
    lines.append("- ~739K words of documentation")
    lines.append("- 23,470 verified tests")
    lines.append("- 49 published essays")
    lines.append("- 33 development sprints")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate interview preparation materials")
    parser.add_argument("--target", metavar="ID", help="Entry ID to prepare for")
    parser.add_argument("--auto", action="store_true", help="Prepare for all interview-status entries")
    args = parser.parse_args()

    if args.target:
        prep = generate_prep(args.target)
        # Save to submissions dir
        SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = SUBMISSIONS_DIR / f"{args.target}-interview-prep.md"
        out_path.write_text(prep + "\n")
        print(prep)
        print(f"\nSaved to {out_path}")
        return

    if args.auto:
        entries = load_entries()
        interview_entries = [e for e in entries if e.get("status") == "interview"]
        if not interview_entries:
            print("No entries in interview status.")
            return
        for entry in interview_entries:
            eid = entry.get("id", "unknown")
            prep = generate_prep(eid)
            SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
            out_path = SUBMISSIONS_DIR / f"{eid}-interview-prep.md"
            out_path.write_text(prep + "\n")
            print(f"  Generated: {out_path.name}")
        print(f"\n{len(interview_entries)} prep documents generated.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
