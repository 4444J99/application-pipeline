#!/usr/bin/env python3
"""LinkedIn Content Engine — audit, manage, and compose posts with Testament discipline.

This tool manages the LinkedIn content pipeline in strategy/linkedin-content/.
It does NOT generate posts from blocks by concatenation — Testament-quality posts
require human-directed composition. Instead it:

1. Audits drafts against the 13 Testament articles
2. Lists available blocks and their identity position mappings
3. Shows posting history and series continuity
4. Plans the next post in the series based on dimension rotation

Usage:
    python scripts/linkedin_composer.py --audit strategy/linkedin-content/post-004-ai-conductor.md
    python scripts/linkedin_composer.py --list
    python scripts/linkedin_composer.py --history
    python scripts/linkedin_composer.py --next
    python scripts/linkedin_composer.py --validate-all

Quick commands via run.py:
    python scripts/run.py linkedin          # Show history + next recommendation
    python scripts/run.py linkedinaudit     # Audit all DRAFT/READY posts
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import REPO_ROOT

BLOCKS_DIR = REPO_ROOT / "blocks"
CONTENT_DIR = REPO_ROOT / "strategy" / "linkedin-content"
IDENTITY_FILE = REPO_ROOT / "strategy" / "identity-positions.md"

# LinkedIn constraints
MAX_CHARS = 3000
IDEAL_MIN = 800
IDEAL_MAX = 1600
VISIBLE_BEFORE_FOLD = 210  # chars visible before "...see more"

# Testament causation connectors (Art. II)
CAUSATION_WORDS = {"but", "therefore", "so", "because", "however", "yet", "instead",
                   "consequently", "thus", "hence", "rather", "nevertheless"}
SEQUENTIAL_WORDS = {"and then", "also", "additionally", "furthermore", "moreover", "next"}

# AI hallmark phrases to flag (Art. XII)
AI_HALLMARKS = [
    "in today's", "landscape", "it's worth noting", "at the end of the day",
    "game-changer", "cutting-edge", "leverage", "synergy", "deep dive",
    "let's unpack", "buckle up", "here's the thing", "in conclusion",
    "passionate about", "excited to share", "thrilled to announce",
    "journey", "pivotal", "robust", "comprehensive", "holistic",
    "navigate", "harness", "empower", "unlock", "revolutionize",
]


def load_post(path: Path) -> dict[str, Any]:
    """Load a LinkedIn post file with YAML frontmatter."""
    content = path.read_text()
    parts = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)

    if len(parts) >= 3:
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            fm = {}
        body = parts[2].strip()
    else:
        fm = {}
        body = content.strip()

    # Extract just the post text (between --- markers in body, or first ## Post Text section)
    post_match = re.search(r"^---\s*\n(.*?)\n---\s*$", body, re.DOTALL | re.MULTILINE)
    if post_match:
        post_text = post_match.group(1).strip()
    else:
        # Try ## Post Text / ## Revised Post Text section
        section_match = re.search(
            r"^##\s+(?:Revised )?Post Text\s*\n(.*?)(?=\n##\s|\Z)",
            body, re.DOTALL | re.MULTILINE
        )
        post_text = section_match.group(1).strip() if section_match else body

    return {"frontmatter": fm, "body": body, "post_text": post_text, "path": path}


def load_block(block_rel_path: str) -> dict[str, Any]:
    """Load a narrative block with YAML frontmatter."""
    path = BLOCKS_DIR / f"{block_rel_path}.md"
    if not path.exists():
        raise FileNotFoundError(f"Block not found: {path}")

    content = path.read_text()
    parts = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)

    if len(parts) < 3:
        return {"frontmatter": {}, "body": content, "path": path}

    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}

    return {"frontmatter": fm, "body": parts[2].strip(), "path": path}


# ---------------------------------------------------------------------------
# Testament Audit Engine
# ---------------------------------------------------------------------------

def audit_causation(text: str) -> dict:
    """Art. II — Cascading Causation. BUT/THEREFORE > AND_THEN."""
    # Check both lowercase and uppercase (Testament posts use uppercase BUT/THEREFORE)
    causation_count = 0
    for w in CAUSATION_WORDS:
        causation_count += len(re.findall(rf'\b{w}\b', text, re.IGNORECASE))
    sequential_count = 0
    for w in SEQUENTIAL_WORDS:
        sequential_count += len(re.findall(rf'\b{w}\b', text, re.IGNORECASE))

    sentences = re.split(r'[.!?]+', text)
    sentence_count = len([s for s in sentences if s.strip()])

    ratio = causation_count / max(sentence_count, 1)

    if causation_count == 0:
        grade = "FAIL"
        note = "Zero causation connectors. Every sentence follows the last without causing it."
    elif ratio < 0.15:
        grade = "WEAK"
        note = f"Only {causation_count} causation connectors across {sentence_count} sentences ({ratio:.0%}). Need more BUT/THEREFORE structure."
    else:
        grade = "PASS"
        note = f"{causation_count} causation connectors across {sentence_count} sentences ({ratio:.0%})."

    if sequential_count > causation_count:
        grade = "FAIL" if grade != "PASS" else "WEAK"
        note += f" Sequential connectors ({sequential_count}) outnumber causal ones."

    return {"article": "II", "name": "Cascading Causation", "grade": grade, "note": note}


def audit_triple_layer(text: str) -> dict:
    """Art. III — Triple Layer. Each section must carry pathos + ethos + logos."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 30]

    # Heuristic signals for each dimension
    has_numbers = bool(re.search(r'\d{2,}', text))  # ethos: specific numbers
    has_personal = bool(re.search(r'\b(I |my |me |we |our )', text, re.IGNORECASE))  # pathos
    has_argument = bool(re.search(r'\b(because|therefore|proves?|demonstrates?|not .* but)\b', text, re.IGNORECASE))  # logos

    missing = []
    if not has_numbers:
        missing.append("ethos (no specific numbers/evidence)")
    if not has_personal:
        missing.append("pathos (no personal voice)")
    if not has_argument:
        missing.append("logos (no argumentative structure)")

    if not missing:
        return {"article": "III", "name": "Triple Layer", "grade": "PASS",
                "note": f"All three dimensions present across {len(paragraphs)} paragraphs."}
    elif len(missing) == 1:
        return {"article": "III", "name": "Triple Layer", "grade": "WEAK",
                "note": f"Missing: {missing[0]}."}
    else:
        return {"article": "III", "name": "Triple Layer", "grade": "FAIL",
                "note": f"Missing: {'; '.join(missing)}."}


def audit_collision(text: str) -> dict:
    """Art. V — Collision Geometry. Two threads must converge through a bridge element."""
    # Check for subheadings (structural indicator of multiple threads)
    subheadings = re.findall(r'^###?\s+(.+)$', text, re.MULTILINE)

    # Check for bridge language
    bridge_patterns = [
        r'\b(same|identical|converge|bridge|connects?|unif(?:y|ies)|shared|both)\b',
        r"isn't a .+ — it's a",
        r'\bnot .+ but\b',
    ]
    bridge_count = sum(1 for p in bridge_patterns if re.search(p, text, re.IGNORECASE))

    if len(subheadings) >= 2 and bridge_count >= 2:
        return {"article": "V", "name": "Collision Geometry", "grade": "PASS",
                "note": f"{len(subheadings)} sections with {bridge_count} bridge elements."}
    elif bridge_count >= 1:
        return {"article": "V", "name": "Collision Geometry", "grade": "WEAK",
                "note": f"Bridge language present ({bridge_count}) but thread separation unclear."}
    else:
        return {"article": "V", "name": "Collision Geometry", "grade": "FAIL",
                "note": "No collision detected. Content is parallel, never converging."}


def audit_opening(text: str) -> dict:
    """Art. X — Opening Architecture. First line must be a hook, not a credential."""
    first_line = text.strip().split("\n")[0].strip()

    # Bad openings: start with "I am", "I build", "I have", credential dumps
    bad_patterns = [
        r'^I (am|build|have|create|develop|work|manage|maintain)\b',
        r'^(As a|With \d+ years|Over the past)',
        r'^(Excited|Thrilled|Passionate|Happy|Proud) to',
    ]
    for pattern in bad_patterns:
        if re.search(pattern, first_line, re.IGNORECASE):
            return {"article": "X", "name": "Opening Architecture", "grade": "FAIL",
                    "note": f"Opens with credential/announcement: \"{first_line[:60]}...\""}

    # Good openings: thesis statement, tension, reframe
    if len(first_line) < 80 and ("—" in first_line or "isn't" in first_line or "not" in first_line.lower()):
        return {"article": "X", "name": "Opening Architecture", "grade": "PASS",
                "note": f"Strong hook with tension: \"{first_line[:60]}\""}

    return {"article": "X", "name": "Opening Architecture", "grade": "WEAK",
            "note": f"Opening may not hook: \"{first_line[:60]}\""}


def audit_language(text: str) -> dict:
    """Art. XII — Charged Language. No AI hallmarks, no none-words."""
    found = [h for h in AI_HALLMARKS if h.lower() in text.lower()]

    if found:
        return {"article": "XII", "name": "Charged Language", "grade": "FAIL",
                "note": f"AI hallmark phrases detected: {', '.join(found[:5])}"}

    # Check for density: ratio of unique words to total
    words = re.findall(r'\b\w+\b', text.lower())
    if words:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.4:
            return {"article": "XII", "name": "Charged Language", "grade": "WEAK",
                    "note": f"Low lexical density ({unique_ratio:.0%}). Consider tightening."}

    return {"article": "XII", "name": "Charged Language", "grade": "PASS",
            "note": "No AI hallmarks. Language is charged."}


def audit_power_positions(text: str) -> dict:
    """Art. XIII — Power Position Heartbeat. Line-final words should carry weight."""
    lines = [l.strip() for l in text.split("\n") if l.strip() and not l.strip().startswith("#")]

    # Get final word of each line
    final_words = []
    for line in lines:
        words = re.findall(r'\b\w+\b', line)
        if words:
            final_words.append(words[-1].lower())

    if not final_words:
        return {"article": "XIII", "name": "Power Positions", "grade": "FAIL",
                "note": "No content lines found."}

    # Weak final words (articles, prepositions, etc.)
    weak_words = {"the", "a", "an", "of", "to", "in", "for", "and", "or", "is", "it", "that",
                  "this", "with", "on", "at", "by", "from", "as", "are", "was", "be", "has"}
    weak_count = sum(1 for w in final_words if w in weak_words)
    weak_ratio = weak_count / len(final_words)

    # Check for repetition (intentional echoing)
    repeated = [w for w in set(final_words) if final_words.count(w) > 1]

    note_parts = [f"{len(final_words)} lines analyzed. Weak endings: {weak_count} ({weak_ratio:.0%})."]
    if repeated:
        note_parts.append(f"Repeated: {', '.join(repeated[:3])} (check if intentional echo).")
    note_parts.append(f"Arc: {' -> '.join(final_words[:3])} ... {' -> '.join(final_words[-3:])}")

    if weak_ratio > 0.4:
        grade = "FAIL"
    elif weak_ratio > 0.25:
        grade = "WEAK"
    else:
        grade = "PASS"

    return {"article": "XIII", "name": "Power Positions", "grade": grade,
            "note": " ".join(note_parts)}


def audit_char_count(text: str) -> dict:
    """LinkedIn character limits and fold analysis."""
    char_count = len(text)
    first_line = text.split("\n")[0] if text else ""

    if char_count > MAX_CHARS:
        grade = "FAIL"
        note = f"Exceeds LinkedIn limit: {char_count}/{MAX_CHARS} chars."
    elif char_count > IDEAL_MAX:
        grade = "WEAK"
        note = f"Long ({char_count} chars). May lose readers. Ideal: {IDEAL_MIN}-{IDEAL_MAX}."
    elif char_count < IDEAL_MIN:
        grade = "WEAK"
        note = f"Short ({char_count} chars). May lack depth. Ideal: {IDEAL_MIN}-{IDEAL_MAX}."
    else:
        grade = "PASS"
        note = f"{char_count} chars (ideal range). ~{char_count // 250} min read."

    # Fold analysis
    if len(first_line) > VISIBLE_BEFORE_FOLD:
        note += f" First line ({len(first_line)} chars) exceeds fold ({VISIBLE_BEFORE_FOLD})."

    return {"article": "FORM", "name": "Character Count", "grade": grade, "note": note}


def audit_citations(text: str) -> dict:
    """Check for academic-style citations (Testament convention)."""
    # Detect superscript markers: ¹ ² ³ ⁴ ⁵ ⁶ ⁷ ⁸ ⁹ or plain digits used as footnotes
    unicode_sups = re.findall(r'[\u00b9\u00b2\u00b3\u2070\u2074-\u2079\u2080-\u2089]', text)
    # Also detect patterns like "text.¹" or "text. ²" or "word¹" or trailing digits after punctuation
    ascii_refs = re.findall(r'(?<=[.!?"\'])\s*(\d+)(?=\s|$|\n)', text)

    citation_count = len(set(unicode_sups)) + len(set(ascii_refs))

    if citation_count >= 3:
        return {"article": "CITE", "name": "Citations", "grade": "PASS",
                "note": f"{citation_count} citation markers found. Scholarly credibility."}
    elif citation_count >= 1:
        return {"article": "CITE", "name": "Citations", "grade": "WEAK",
                "note": f"{citation_count} citation(s). Testament convention: 3+ with named sources."}
    else:
        return {"article": "CITE", "name": "Citations", "grade": "FAIL",
                "note": "No citations. Testament posts use academic-style footnotes."}


def run_full_audit(text: str) -> list[dict]:
    """Run all Testament audit checks against post text."""
    return [
        audit_causation(text),
        audit_triple_layer(text),
        audit_collision(text),
        audit_opening(text),
        audit_language(text),
        audit_power_positions(text),
        audit_char_count(text),
        audit_citations(text),
    ]


def format_audit(results: list[dict], path: Path = None) -> str:
    """Format audit results for display."""
    lines = []
    if path:
        lines.append(f"\n  Testament Audit: {path.name}")
        lines.append("  " + "=" * 55)

    pass_count = sum(1 for r in results if r["grade"] == "PASS")
    total = len(results)

    for r in results:
        icon = {"PASS": "+", "WEAK": "~", "FAIL": "!"}[r["grade"]]
        lines.append(f"  [{icon}] Art. {r['article']:>4s} {r['name']:<22s} {r['grade']}")
        lines.append(f"        {r['note']}")

    lines.append(f"\n  Score: {pass_count}/{total} PASS")
    grade = "READY" if pass_count >= 6 else "NEEDS WORK" if pass_count >= 4 else "NOT READY"
    lines.append(f"  Verdict: {grade}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Content Pipeline Commands
# ---------------------------------------------------------------------------

def cmd_history():
    """Show posting history and series state."""
    if not CONTENT_DIR.exists():
        print("  No linkedin-content directory found.")
        return

    posts = sorted(CONTENT_DIR.glob("post-*.md"))
    if not posts:
        print("  No posts found in strategy/linkedin-content/")
        return

    print("\n  LinkedIn Content Pipeline")
    print("  " + "=" * 55)

    for p in posts:
        data = load_post(p)
        fm = data["frontmatter"]
        status = fm.get("status", "UNKNOWN")
        date = fm.get("date", "???")
        title = fm.get("title", p.stem)

        icon = {"PUBLISHED": "+", "READY": ">", "DRAFT": "~"}.get(status, "?")
        print(f"  [{icon}] {p.name}")
        print(f"       {title}")
        print(f"       Status: {status} | Date: {date}")

        # Show engagement if published
        engagement = fm.get("engagement")
        if engagement:
            print(f"       Engagement: {engagement}")
        print()

    # Dimension rotation analysis
    print("  Dimension Rotation:")
    print("  Post #001: Ethos (credentials) — PUBLISHED")
    print("  Post #002: Logos (formalization proof) — READY/DRAFT")
    print("  Post #003: Pathos (teaching story) — DRAFT")
    print("  Post #004: Ethos+Logos (AI-Conductor methodology) — DRAFT")
    print()
    print("  Next dimension gap: Pathos-led or Collision-led post")


def cmd_list_blocks():
    """Show blocks available for LinkedIn adaptation."""
    print("\n  Blocks Available for LinkedIn Content")
    print("  " + "=" * 55)

    categories = sorted(set(p.parent.name for p in BLOCKS_DIR.rglob("*.md") if p.name != "README.md"))

    for cat in categories:
        cat_dir = BLOCKS_DIR / cat
        if not cat_dir.is_dir():
            continue
        blocks = sorted(cat_dir.glob("*.md"))
        if not blocks:
            continue

        print(f"\n  {cat}/")
        for b in blocks[:10]:  # cap at 10 per category
            data = load_block(f"{cat}/{b.stem}")
            fm = data["frontmatter"]
            positions = fm.get("identity_positions", [])
            tier = fm.get("tier", "?")
            pos_str = ", ".join(positions[:3]) if positions else "untagged"
            print(f"    {b.stem:<40s} [{tier}] {pos_str}")

        if len(blocks) > 10:
            print(f"    ... and {len(blocks) - 10} more")


def cmd_next():
    """Recommend the next post based on series analysis."""
    print("\n  Next Post Recommendation")
    print("  " + "=" * 55)

    posts = sorted(CONTENT_DIR.glob("post-*.md"))
    ready = [p for p in posts if "READY" in p.read_text()[:200]]
    drafts = [p for p in posts if "DRAFT" in p.read_text()[:200]]

    if ready:
        print(f"\n  READY to ship ({len(ready)}):")
        for p in ready:
            print(f"    > {p.name}")

    if drafts:
        print(f"\n  DRAFTS needing work ({len(drafts)}):")
        for p in drafts:
            print(f"    ~ {p.name}")

    print("\n  Series Progression:")
    print("  1. Edit existing post #001 with revised text (post-001-revision.md)")
    print("  2. Ship post-002 (bridge-audit or testament-revision — pick one)")
    print("  3. Ship post-003 (teaching-story) or post-004 (ai-conductor)")
    print("  4. Each post should rotate the lead dimension (ethos/logos/pathos)")
    print()
    print("  Posting Protocol:")
    print("  - Monday morning 8-10am ET for algorithm boost")
    print("  - Max 1 post per week (quality > frequency)")
    print("  - First comment: link to relevant essay or portfolio page")
    print("  - Tag specific people ONLY if prior relationship exists")


def cmd_audit(path_str: str):
    """Audit a specific post file against Testament articles."""
    path = Path(path_str)
    if not path.exists():
        # Try relative to CONTENT_DIR
        path = CONTENT_DIR / path_str
    if not path.exists():
        # Try relative to repo root
        path = REPO_ROOT / path_str
    if not path.exists():
        print(f"  File not found: {path_str}")
        sys.exit(1)

    data = load_post(path)
    post_text = data["post_text"]

    if not post_text or len(post_text) < 50:
        print(f"  Could not extract post text from {path.name}")
        print(f"  Body length: {len(data['body'])} chars")
        sys.exit(1)

    results = run_full_audit(post_text)
    print(format_audit(results, path))


def cmd_audit_all():
    """Audit all DRAFT and READY posts."""
    if not CONTENT_DIR.exists():
        print("  No linkedin-content directory found.")
        return

    posts = sorted(CONTENT_DIR.glob("post-*.md"))
    for p in posts:
        content = p.read_text()[:300]
        if "DRAFT" in content or "READY" in content:
            data = load_post(p)
            post_text = data["post_text"]
            if post_text and len(post_text) > 50:
                results = run_full_audit(post_text)
                print(format_audit(results, p))
                print()


def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Content Engine — Testament-disciplined content pipeline."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit", metavar="FILE", help="Audit a post file against Testament articles")
    group.add_argument("--audit-all", action="store_true", help="Audit all DRAFT/READY posts")
    group.add_argument("--list", action="store_true", help="List blocks available for LinkedIn adaptation")
    group.add_argument("--history", action="store_true", help="Show posting history and series state")
    group.add_argument("--next", action="store_true", help="Recommend next post based on series analysis")

    args = parser.parse_args()

    if args.audit:
        cmd_audit(args.audit)
    elif args.audit_all:
        cmd_audit_all()
    elif args.list:
        cmd_list_blocks()
    elif args.history:
        cmd_history()
    elif args.next:
        cmd_next()


if __name__ == "__main__":
    main()
