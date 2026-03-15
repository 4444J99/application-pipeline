#!/usr/bin/env python3
"""Outreach template generator for pipeline entries.

Generates personalized LinkedIn connect notes, cold emails, and follow-up
messages using entry data, identity positions, and block content.

Usage:
    python scripts/outreach_templates.py --target <entry-id>              # All templates
    python scripts/outreach_templates.py --target <entry-id> --type connect  # LinkedIn only
    python scripts/outreach_templates.py --target <entry-id> --type email    # Cold email only
    python scripts/outreach_templates.py --target <entry-id> --type followup # Follow-up only
    python scripts/outreach_templates.py --target <entry-id> --json          # JSON output
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import ALL_PIPELINE_DIRS_WITH_POOL, load_entries

VALID_TYPES = {"connect", "email", "followup"}


def _find_entry(entry_id: str) -> dict | None:
    """Load a single pipeline entry by ID."""
    entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL, include_filepath=True)
    for e in entries:
        if e.get("id") == entry_id:
            return e
    return None


def _org_name(entry: dict) -> str:
    """Extract organization name from entry."""
    target = entry.get("target", {})
    return target.get("organization", target.get("company", "the organization"))


def _role_title(entry: dict) -> str:
    """Extract role/opportunity title from entry."""
    target = entry.get("target", {})
    return target.get("title", target.get("name", "the role"))


def _identity_position(entry: dict) -> str:
    """Get identity position for framing."""
    return entry.get("identity_position", "independent-engineer")


def _track(entry: dict) -> str:
    """Get track (job, grant, residency, etc.)."""
    return entry.get("track", "job")


def generate_connect_note(entry: dict) -> dict:
    """Generate a LinkedIn connect note (max 300 chars).

    Returns dict with template text and metadata.
    """
    org = _org_name(entry)
    role = _role_title(entry)
    position = _identity_position(entry)
    track = _track(entry)

    if track in ("grant", "residency", "fellowship"):
        templates = [
            f"Hi — I'm exploring {org}'s programs and am preparing an application for {role}. "
            f"I'd love to connect and learn about your experience with the program.",
            f"Hi — I work at the intersection of software engineering and systems art. "
            f"I'm interested in {org}'s mission and would value connecting.",
        ]
    else:
        position_hooks = {
            "independent-engineer": "I build production infrastructure for AI orchestration systems",
            "systems-artist": "I create governance-as-artwork at systemic scale",
            "educator": "I teach complex systems engineering at scale",
            "creative-technologist": "I build AI orchestration tools for creative production",
            "community-practitioner": "I design community-informed systemic practices",
        }
        hook = position_hooks.get(position, "I'm a software engineer")

        templates = [
            f"Hi — {hook}. I noticed {org} is hiring for {role} and I'd love to "
            f"connect to learn more about the team's work.",
            f"Hi — I'm interested in {org}'s work and saw the {role} opening. "
            f"{hook}. Would love to connect.",
        ]

    # Pick the shortest template that fits LinkedIn's 300-char limit
    best = min(templates, key=len)
    if len(best) > 300:
        best = best[:297] + "..."

    return {
        "type": "connect",
        "platform": "linkedin",
        "max_chars": 300,
        "char_count": len(best),
        "template": best,
        "entry_id": entry.get("id"),
        "org": org,
    }


def generate_cold_email(entry: dict) -> dict:
    """Generate a cold outreach email.

    Returns dict with subject, body template, and metadata.
    """
    org = _org_name(entry)
    role = _role_title(entry)
    position = _identity_position(entry)
    track = _track(entry)

    position_evidence = {
        "independent-engineer": (
            "I maintain a 113-repository infrastructure system with 21,449 verified tests "
            "and have built production pipelines for AI orchestration across multiple frameworks."
        ),
        "systems-artist": (
            "I create governance systems as artistic practice — my ORGANVM project spans "
            "113 repositories treating institutional structure as a creative medium."
        ),
        "educator": (
            "I've developed curriculum for teaching complex systems at scale, including "
            "a self-documenting 113-repository codebase used as a teaching instrument."
        ),
        "creative-technologist": (
            "I build production-grade creative instruments — my current work spans AI orchestration, "
            "generative art systems, and modular synthesis software across 113 repositories."
        ),
        "community-practitioner": (
            "I design community-centered systems informed by lived experience with "
            "precarity, building infrastructure that amplifies both individuals and institutions."
        ),
    }
    evidence = position_evidence.get(position, "I build large-scale software systems.")

    if track in ("grant", "residency", "fellowship"):
        subject = f"Inquiry: {role} — systems engineering meets artistic practice"
        body = (
            f"Dear {org} team,\n\n"
            f"I'm writing regarding {role}. {evidence}\n\n"
            f"My work sits at the intersection of rigorous software engineering and systemic "
            f"creative practice. I'd welcome the chance to discuss how my approach aligns "
            f"with {org}'s mission.\n\n"
            f"Would you be open to a brief conversation?\n\n"
            f"Best regards"
        )
    else:
        subject = f"Re: {role} — {org}"
        body = (
            f"Hi,\n\n"
            f"I saw the {role} posting at {org} and wanted to reach out directly. "
            f"{evidence}\n\n"
            f"I'm particularly drawn to {org} because of [SPECIFIC REASON — research their "
            f"recent work, blog posts, or public statements]. My approach emphasizes "
            f"building systems that compound in value over time.\n\n"
            f"I'd love to learn more about the team. Would you have 15 minutes this week?\n\n"
            f"Best"
        )

    return {
        "type": "email",
        "subject": subject,
        "template": body,
        "entry_id": entry.get("id"),
        "org": org,
        "word_count": len(body.split()),
    }


def generate_followup(entry: dict) -> dict:
    """Generate a follow-up message (Day 7-10 after submission).

    Returns dict with template text and metadata.
    """
    org = _org_name(entry)
    role = _role_title(entry)
    track = _track(entry)

    if track in ("grant", "residency", "fellowship"):
        template = (
            f"Hi — I submitted my application for {role} at {org} recently and wanted "
            f"to follow up briefly. I'm very excited about the opportunity and would be "
            f"happy to provide any additional materials or context. Thank you for your time."
        )
    else:
        template = (
            f"Hi — I applied for the {role} position at {org} last week and wanted to "
            f"follow up. I'm very interested in the team's work and believe my background "
            f"in building large-scale AI infrastructure systems would be a strong fit.\n\n"
            f"Happy to share additional context or answer any questions. Thanks for considering "
            f"my application."
        )

    return {
        "type": "followup",
        "template": template,
        "entry_id": entry.get("id"),
        "org": org,
        "word_count": len(template.split()),
        "timing": "Day 7-10 after submission",
    }


def generate_all_templates(entry: dict) -> dict:
    """Generate all outreach templates for an entry."""
    return {
        "entry_id": entry.get("id"),
        "org": _org_name(entry),
        "role": _role_title(entry),
        "track": _track(entry),
        "identity_position": _identity_position(entry),
        "templates": {
            "connect": generate_connect_note(entry),
            "email": generate_cold_email(entry),
            "followup": generate_followup(entry),
        },
    }


def format_report(data: dict) -> str:
    """Format templates for human reading."""
    lines = [
        f"  Outreach templates for: {data.get('entry_id', '?')}",
        f"  Org: {data.get('org', '?')} | Role: {data.get('role', '?')}",
        f"  Track: {data.get('track', '?')} | Position: {data.get('identity_position', '?')}",
        "",
    ]

    templates = data.get("templates", data)
    if isinstance(templates, dict) and "type" in templates:
        # Single template
        templates = {templates["type"]: templates}

    for ttype, tmpl in templates.items():
        lines.append(f"  {'=' * 60}")
        lines.append(f"  {ttype.upper()}")
        if tmpl.get("subject"):
            lines.append(f"  Subject: {tmpl['subject']}")
        if tmpl.get("platform"):
            lines.append(f"  Platform: {tmpl['platform']} (max {tmpl.get('max_chars', '?')} chars)")
        if tmpl.get("timing"):
            lines.append(f"  Timing: {tmpl['timing']}")
        lines.append(f"  {'─' * 60}")
        lines.append(f"  {tmpl['template']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Outreach template generator")
    parser.add_argument("--target", required=True, help="Entry ID")
    parser.add_argument("--type", choices=sorted(VALID_TYPES), help="Template type")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    entry = _find_entry(args.target)
    if not entry:
        print(f"Entry not found: {args.target}", file=sys.stderr)
        sys.exit(1)

    if args.type == "connect":
        result = generate_connect_note(entry)
    elif args.type == "email":
        result = generate_cold_email(entry)
    elif args.type == "followup":
        result = generate_followup(entry)
    else:
        result = generate_all_templates(entry)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if "templates" not in result:
            result = {"entry_id": entry.get("id"), "org": _org_name(entry), "role": _role_title(entry), "track": _track(entry), "identity_position": _identity_position(entry), "templates": {result["type"]: result}}
        print(format_report(result))


if __name__ == "__main__":
    main()
