#!/usr/bin/env python3
"""DM Composer — composes acceptance DMs using Outreach Protocol constraints.

Generates post-acceptance LinkedIn DMs that satisfy all 7 Protocol articles
by building on the original connect note's hooks, targeting the recipient's
daily inhabitation, and terminating with a response-compelling question.

Usage:
    python scripts/dm_composer.py --target <entry-id>
    python scripts/dm_composer.py --contact "Mario Tayah"
    python scripts/dm_composer.py --contact "Mario Tayah" --connect "original connect text"
    python scripts/dm_composer.py --all-pending
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import SIGNALS_DIR
from protocol_types import Agent, Message
from protocol_validator import (
    extract_claims,
    identify_tensions,
    validate_full_sequence,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTACTS_PATH = SIGNALS_DIR / "contacts.yaml"
OUTREACH_LOG_PATH = SIGNALS_DIR / "outreach-log.yaml"
OUTREACH_PLANS_GLOB = [
    REPO_ROOT / "applications",
    REPO_ROOT / "strategy",
    REPO_ROOT / "signals",
]

PORTFOLIO_URL = "https://4444j99.github.io/portfolio/"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_contacts() -> list[dict]:
    """Load contacts from contacts.yaml."""
    if not CONTACTS_PATH.exists():
        return []
    data = yaml.safe_load(CONTACTS_PATH.read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "contacts" in data:
        return data["contacts"] if isinstance(data["contacts"], list) else []
    return []


def load_outreach_log() -> list[dict]:
    """Load outreach log entries."""
    if not OUTREACH_LOG_PATH.exists():
        return []
    data = yaml.safe_load(OUTREACH_LOG_PATH.read_text())
    return data if isinstance(data, list) else []


def find_contact(name: str) -> dict | None:
    """Find a contact by name (case-insensitive substring match)."""
    contacts = load_contacts()
    name_lower = name.lower()
    for c in contacts:
        if name_lower in c.get("name", "").lower():
            return c
    return None


def find_connect_note_from_plans(contact_name: str, org: str) -> str | None:
    """Search outreach plan markdown files for the connect note sent to this contact."""
    patterns_to_search = []
    for base in OUTREACH_PLANS_GLOB:
        if base.is_dir():
            patterns_to_search.extend(base.rglob("outreach-plan*.md"))
            patterns_to_search.extend(base.rglob("outreach*.md"))

    for plan_path in patterns_to_search:
        try:
            content = plan_path.read_text()
        except Exception:
            continue

        # Look for the contact's name or org in the plan
        if contact_name not in content and org not in content:
            continue

        # Extract connection message block quotes
        # Pattern: **Connection message:** followed by a blockquote
        matches = re.findall(
            r"\*\*Connection message:\*\*\s*\n\s*>\s*(.+?)(?:\n\n|\n-|\n\*\*|\Z)",
            content,
            re.DOTALL,
        )
        for match in matches:
            # Check if this block is near the contact's name or org section
            name_pos = content.find(contact_name)
            org_pos = content.find(org) if org else -1
            match_pos = content.find(match)

            # Heuristic: the message should be within ~500 chars of the name/org
            if name_pos >= 0 and abs(match_pos - name_pos) < 1000:
                return match.strip().replace("\n  > ", " ").replace("\n> ", " ")
            if org_pos >= 0 and abs(match_pos - org_pos) < 1000:
                return match.strip().replace("\n  > ", " ").replace("\n> ", " ")

    return None


def find_connect_note_from_log(contact_name: str) -> str | None:
    """Check outreach log for connect note text (usually just metadata)."""
    log = load_outreach_log()
    for entry in log:
        if entry.get("contact", "").lower() == contact_name.lower():
            if entry.get("type") in ("post_submission", "doubling_back", "seed"):
                note = entry.get("note", "")
                if "Connection request" in note:
                    return note
    return None


def find_acceptance_dm_template(contact_name: str, org: str) -> str | None:
    """Search outreach plans for pre-written 'If accepted — DM:' templates."""
    for base in OUTREACH_PLANS_GLOB:
        if not base.is_dir():
            continue
        for plan_path in base.rglob("outreach-plan*.md"):
            try:
                content = plan_path.read_text()
            except Exception:
                continue

            if contact_name not in content and org not in content:
                continue

            # Pattern: **If accepted — DM:** followed by blockquote
            matches = re.findall(
                r"\*\*If accepted\s*[—–-]\s*DM:\*\*\s*\n\s*>\s*(.+?)(?:\n\n|\n-|\n\*\*|\Z)",
                content,
                re.DOTALL,
            )
            for match in matches:
                name_pos = content.find(contact_name)
                org_pos = content.find(org) if org else -1
                match_pos = content.find(match)

                if name_pos >= 0 and abs(match_pos - name_pos) < 1500:
                    cleaned = match.strip()
                    cleaned = re.sub(r"\n\s*>\s*", "\n", cleaned)
                    return cleaned.strip()
                if org_pos >= 0 and abs(match_pos - org_pos) < 1500:
                    cleaned = match.strip()
                    cleaned = re.sub(r"\n\s*>\s*", "\n", cleaned)
                    return cleaned.strip()

    return None


# ---------------------------------------------------------------------------
# DM Composition
# ---------------------------------------------------------------------------

@dataclass
class ComposedDM:
    """Result of DM composition."""

    contact_name: str
    organization: str
    connect_note: str
    dm_text: str
    template_source: str  # "outreach-plan", "protocol-generated", "manual"
    hooks_continued: list[str] = field(default_factory=list)
    question: str = ""
    protocol_valid: bool = False
    protocol_report: str = ""


def _generate_protocol_dm(
    contact: dict,
    connect_text: str,
    agent: Agent,
) -> str:
    """Generate a DM from first principles using Protocol constraints.

    Structure:
    1. Brief thanks (1 sentence)
    2. Hook development (1-2 sentences, expanding the connect note's claim)
    3. Terminal question (1 sentence targeting recipient's tension/decision)
    4. Bare portfolio URL
    """
    first_name = contact.get("name", "").split()[0] if contact.get("name") else ""

    # Extract hooks from connect note
    connect_msg = Message(text=connect_text, phase="pre_boundary", channel="linkedin")
    claims = extract_claims(connect_msg)
    valid_hooks = [c for c in claims if c.is_valid]

    # Identify tensions for the question
    tensions = identify_tensions(agent)

    # Build hook development
    hook_dev = ""
    if valid_hooks:
        primary_hook = valid_hooks[0]
        # Reference the hook and develop it one level deeper
        hook_dev = f"The {_compress_hook(primary_hook.text)} — that's not abstract. "
        hook_dev += _develop_hook(primary_hook, agent)

    # Build terminal question
    question = _generate_question(agent, tensions)

    # Compose
    parts = []
    parts.append(f"Thanks for connecting, {first_name}.")
    if hook_dev:
        parts.append(hook_dev.strip())
    parts.append(question)
    parts.append(PORTFOLIO_URL)

    return "\n\n".join(parts)


def _compress_hook(hook_text: str) -> str:
    """Compress a hook claim to a short reference (P-I.2 recoverability)."""
    # Extract the most distinctive phrase
    # Try to find a novel frame or a number-bearing phrase
    for frame in [
        "governance-as-artwork",
        "governance-as-medium",
        "state transition invariants",
        "correctness guarantees",
        "promotion state machine",
        "conversion funnels",
        "variant tracking",
        "product analytics",
        "institutional system",
    ]:
        if frame.lower() in hook_text.lower():
            return frame

    # Fall back to first significant phrase
    words = hook_text.split()
    if len(words) > 6:
        return " ".join(words[:6]) + "..."
    return hook_text


def _develop_hook(hook, recipient: Agent) -> str:
    """Develop a hook one level deeper (P-II development obligation)."""
    text = hook.text.lower()

    if "governance" in text and ("artwork" in text or "medium" in text):
        return (
            "113 repositories, 8 organizations, a promotion state machine that governs lifecycle "
            "from LOCAL through GRADUATED. The system itself is the work."
        )
    if "state transition" in text or "correctness" in text or "promotion state machine" in text:
        return (
            "Forward-only transitions, CI-enforced validation, audit trail on every state change. "
            f"Same invariants {recipient.organization} infrastructure requires, different domain."
        )
    if "analytics" in text or "funnel" in text or "variant" in text:
        return (
            "Not a product — an actual operating system with A/B tracked materials "
            "and outcome attribution feeding back into composition strategy."
        )
    if "documentation" in text or "739K" in text or "words" in text:
        return (
            "739K words across 113 repositories — not sprawl, but governed. "
            "Schema validation, quality ratchets, automated indexing."
        )
    if "analytics" in text or "product analytics" in text or "open-source" in text:
        return (
            "Not a product — an actual operating system with A/B tracked materials "
            "and outcome attribution feeding back into composition strategy."
        )
    # Generic development
    return (
        f"The system I referenced operates at institutional scale — "
        f"same patterns {recipient.organization} works with, different domain."
    )


def _generate_question(recipient: Agent, tensions: list) -> str:
    """Generate a terminal question targeting the recipient's inhabitation."""
    role_lower = recipient.role.lower()
    org = recipient.organization

    # Specific question templates based on role + org context
    if "head of engineering" in role_lower or "vp of engineering" in role_lower:
        if tensions:
            t = tensions[0]
            return (
                f"How does {org} handle the tension between {t.description}? "
                f"That seems like the defining eng constraint right now."
            )
        return (
            f"What's the hardest engineering tradeoff at {org} right now — "
            f"the one that doesn't have a clean answer?"
        )

    if "artistic director" in role_lower or "curator" in role_lower:
        return (
            f"Most submissions treat technology as material rather than institution. "
            f"Is governance-as-medium something {org} is actively tracking, "
            f"or is it still too structural for most applicants?"
        )

    if "ceo" in role_lower or "founder" in role_lower or "co-ceo" in role_lower:
        return (
            f"{org} bet on a specific thesis early. At this point, has that bet "
            f"paid off in ways you didn't expect, or mostly in the ways you predicted?"
        )

    if "recruiter" in role_lower:
        return (
            "What's the most underrated signal you look for in candidates — "
            "something most people don't think to demonstrate?"
        )

    if "developer advocate" in role_lower or "devrel" in role_lower:
        return (
            f"What's the gap between what {org}'s docs explain and what "
            f"developers actually need to know to ship? That gap is usually where "
            f"the best advocacy work lives."
        )

    # Fallback: generic but still recipient-focused
    return (
        f"What's the most interesting problem at {org} right now — "
        f"the one that doesn't fit neatly into anyone's roadmap?"
    )


def compose_acceptance_dm(
    contact_name: str,
    connect_text: str | None = None,
    entry_id: str | None = None,
) -> ComposedDM | None:
    """Compose an acceptance DM for a contact.

    Priority chain:
    1. Pre-written DM template from outreach plans
    2. Protocol-generated DM from connect note hooks
    3. Protocol-generated DM from outreach log metadata

    All outputs are validated against the full Protocol.
    """
    contact = find_contact(contact_name)
    if not contact:
        print(f"Contact not found: {contact_name}", file=sys.stderr)
        return None

    agent = Agent.from_contact(contact)
    org = agent.organization

    # Step 1: Find the connect note
    if not connect_text:
        connect_text = find_connect_note_from_plans(contact_name, org)
    if not connect_text:
        connect_text = find_connect_note_from_plans(contact.get("name", ""), org)
    if not connect_text:
        log_note = find_connect_note_from_log(contact.get("name", ""))
        if log_note:
            connect_text = log_note

    if not connect_text:
        print(f"  No connect note found for {contact_name}. Provide --connect text.", file=sys.stderr)
        return None

    # Step 2: Check for pre-written DM template
    template_dm = find_acceptance_dm_template(contact.get("name", ""), org)
    template_source = "outreach-plan" if template_dm else "protocol-generated"

    # Step 3: Generate DM
    # Always generate a Protocol-compliant version
    generated_dm = _generate_protocol_dm(contact, connect_text, agent)

    if template_dm:
        # Validate the pre-written template; fall back to generated if it fails
        template_msg = Message(
            text=template_dm, turn="outbound", phase="post_boundary",
            channel="linkedin", recipient=agent,
        )
        template_connect = Message(
            text=connect_text, turn="outbound", phase="pre_boundary", channel="linkedin",
        )
        template_report = validate_full_sequence(
            connect=template_connect, dm=template_msg,
            recipient=agent, relationship_strength=agent.relationship_strength,
        )
        if template_report.valid:
            dm_text = template_dm
        else:
            # Pre-written template fails Protocol — use generated version
            dm_text = generated_dm
            template_source = "protocol-generated (template failed validation)"
    else:
        dm_text = generated_dm

    # Step 4: Validate against Protocol
    connect_msg = Message(
        text=connect_text,
        turn="outbound",
        phase="pre_boundary",
        channel="linkedin",
    )
    dm_msg = Message(
        text=dm_text,
        turn="outbound",
        phase="post_boundary",
        channel="linkedin",
        recipient=agent,
    )

    report = validate_full_sequence(
        connect=connect_msg,
        dm=dm_msg,
        recipient=agent,
        relationship_strength=agent.relationship_strength,
    )

    # Extract hooks continued
    hooks_continued = []
    if report.p2_continuity and report.p2_continuity.hooks_referenced:
        hooks_continued = report.p2_continuity.hooks_referenced

    question = ""
    if report.p4_question and report.p4_question.question:
        question = report.p4_question.question

    return ComposedDM(
        contact_name=contact.get("name", contact_name),
        organization=org,
        connect_note=connect_text,
        dm_text=dm_text,
        template_source=template_source,
        hooks_continued=hooks_continued,
        question=question,
        protocol_valid=report.valid,
        protocol_report=report.summary(),
    )


def compose_all_pending() -> list[ComposedDM]:
    """Compose DMs for all contacts with accepted connections and pending DM follow-ups."""
    contacts = load_contacts()
    results = []
    for contact in contacts:
        next_action = contact.get("next_action", "")
        if not next_action:
            continue
        if "DM" not in next_action and "dm" not in next_action:
            continue
        # Check if most recent interaction is acceptance
        interactions = contact.get("interactions", [])
        if not interactions:
            continue
        latest = interactions[-1] if interactions else {}
        if latest.get("type") != "acceptance":
            continue

        result = compose_acceptance_dm(contact["name"])
        if result:
            results.append(result)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_result(result: ComposedDM) -> str:
    """Format a composed DM for display."""
    lines = [
        f"  {'=' * 60}",
        f"  DM for: {result.contact_name} ({result.organization})",
        f"  Source: {result.template_source}",
        f"  {'─' * 60}",
        "",
        "  CONNECT NOTE (what was sent):",
        f"  {result.connect_note}",
        "",
        f"  {'─' * 60}",
        "",
        "  COMPOSED DM:",
        "",
    ]
    for line in result.dm_text.split("\n"):
        lines.append(f"  {line}")
    lines.append("")
    lines.append(f"  {'─' * 60}")
    if result.hooks_continued:
        lines.append(f"  Hooks continued: {', '.join(h[:50] for h in result.hooks_continued)}")
    if result.question:
        lines.append(f"  Terminal question: {result.question[:80]}")
    lines.append("")
    lines.append("  PROTOCOL VALIDATION:")
    lines.append(result.protocol_report)
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="DM Composer — Protocol-driven acceptance DMs")
    parser.add_argument("--contact", help="Contact name to compose DM for")
    parser.add_argument("--target", help="Pipeline entry ID (looks up linked contacts)")
    parser.add_argument("--connect", help="Original connect note text (if not in outreach plans)")
    parser.add_argument("--all-pending", action="store_true", help="Compose for all pending DM contacts")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.all_pending:
        results = compose_all_pending()
        if not results:
            print("  No pending DM contacts found.")
            return
        for r in results:
            print(_format_result(r))
        return

    if args.contact:
        result = compose_acceptance_dm(args.contact, connect_text=args.connect)
        if result:
            if args.json:
                import json
                print(json.dumps({
                    "contact": result.contact_name,
                    "org": result.organization,
                    "connect_note": result.connect_note,
                    "dm_text": result.dm_text,
                    "source": result.template_source,
                    "hooks_continued": result.hooks_continued,
                    "question": result.question,
                    "protocol_valid": result.protocol_valid,
                }, indent=2))
            else:
                print(_format_result(result))
        return

    if args.target:
        # Find contacts linked to this entry
        contacts = load_contacts()
        linked = [
            c for c in contacts
            if args.target in c.get("pipeline_entries", [])
        ]
        if not linked:
            print(f"  No contacts linked to entry: {args.target}", file=sys.stderr)
            return
        for contact in linked:
            result = compose_acceptance_dm(contact["name"], connect_text=args.connect)
            if result:
                print(_format_result(result))
        return

    # Default: show all pending
    results = compose_all_pending()
    if not results:
        print("  No pending DM contacts found.")
        return
    for r in results:
        print(_format_result(r))


if __name__ == "__main__":
    main()
