#!/usr/bin/env python3
"""Generate project blocks for ORGANVM repos from registry, README, and seed data.

Reads each repo's registry entry, README.md, and seed.yaml, then writes a
complete blocks/projects/{name}.md with frontmatter and tiered content.

Usage:
    python scripts/generate_project_blocks.py --dry-run          # Preview all
    python scripts/generate_project_blocks.py --report            # Coverage report
    python scripts/generate_project_blocks.py --organ ORGAN-I     # One organ
    python scripts/generate_project_blocks.py --target <name>     # Single repo
    python scripts/generate_project_blocks.py --yes               # Generate all
    python scripts/generate_project_blocks.py --yes --force       # Overwrite existing
    python scripts/generate_project_blocks.py --rebuild-index     # Also rebuild _index.yaml
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import BLOCKS_DIR, REPO_ROOT

WORKSPACE = Path.home() / "Workspace"
REGISTRY_PATH = WORKSPACE / "meta-organvm" / "organvm-corpvs-testamentvm" / "registry-v2.json"
PROJECTS_DIR = BLOCKS_DIR / "projects"

# --- Organ configuration tables ---

ORGAN_BASE_TAGS = {
    "ORGAN-I": ["formal-systems", "symbolic", "recursive"],
    "ORGAN-II": ["generative-art", "creative-coding"],
    "ORGAN-III": ["platform", "developer-tools"],
    "ORGAN-IV": ["orchestration", "agent", "governance"],
    "ORGAN-V": ["writing", "essays", "documentation"],
    "ORGAN-VI": ["community", "education", "learning"],
    "ORGAN-VII": ["automation"],
    "META-ORGANVM": ["governance", "infrastructure", "system"],
}

ORGAN_IDENTITY_MAP = {
    "ORGAN-I": {
        "primary": ["systems-artist"],
        "triggers": {"independent-engineer": ["test", "ci", "pipeline", "validation"]},
    },
    "ORGAN-II": {
        "primary": ["systems-artist", "creative-technologist"],
        "triggers": {"community-practitioner": ["queer", "community", "lgbtq"]},
    },
    "ORGAN-III": {
        "primary": ["independent-engineer"],
        "triggers": {"creative-technologist": ["ai", "game", "creative", "generative"]},
    },
    "ORGAN-IV": {
        "primary": ["independent-engineer", "creative-technologist"],
        "triggers": {},
    },
    "ORGAN-V": {
        "primary": ["systems-artist"],
        "triggers": {"educator": ["essay", "documentation", "teaching"]},
    },
    "ORGAN-VI": {
        "primary": ["community-practitioner", "educator"],
        "triggers": {},
    },
    "ORGAN-VII": {
        "primary": ["creative-technologist"],
        "triggers": {},
    },
    "META-ORGANVM": {
        "primary": ["independent-engineer", "systems-artist"],
        "triggers": {"creative-technologist": ["ai", "dashboard", "engine"]},
    },
}

ORGAN_TRACK_MAP = {
    "ORGAN-I": {"flagship": ["job", "grant", "fellowship"], "standard": ["grant", "fellowship"]},
    "ORGAN-II": {
        "flagship": ["grant", "residency", "fellowship", "prize"],
        "standard": ["grant", "residency", "fellowship"],
    },
    "ORGAN-III": {
        "flagship": ["job", "grant", "fellowship"],
        "standard": ["job"],
    },
    "ORGAN-IV": {
        "flagship": ["job", "grant", "fellowship"],
        "standard": ["job", "fellowship"],
    },
    "ORGAN-V": {"flagship": ["writing", "grant"], "standard": ["writing"]},
    "ORGAN-VI": {"flagship": ["grant", "fellowship"], "standard": ["grant"]},
    "ORGAN-VII": {"flagship": ["job"], "standard": ["job"]},
    "META-ORGANVM": {
        "flagship": ["job", "grant", "fellowship"],
        "standard": ["job", "grant"],
    },
}

ORGAN_LONG_NAMES = {
    "ORGAN-I": "Theoria",
    "ORGAN-II": "Poiesis",
    "ORGAN-III": "Ergon",
    "ORGAN-IV": "Taxis",
    "ORGAN-V": "Logos",
    "ORGAN-VI": "Koinonia",
    "ORGAN-VII": "Kerygma",
    "META-ORGANVM": "Meta",
}

# Tech patterns to detect in README text
TECH_PATTERNS = {
    "python": r"\bpython\b",
    "typescript": r"\btypescript\b",
    "react": r"\breact\b",
    "fastapi": r"\bfastapi\b",
    "three-js": r"\bthree\.?js\b",
    "supercollider": r"\bsupercollider\b",
    "docker": r"\bdocker\b",
    "testing": r"\b(?:pytest|vitest|jest|tests?\s+pass|coverage)\b",
    "ci-cd": r"\b(?:ci/cd|github\s+actions|workflow)\b",
    "database": r"\b(?:postgres|sqlite|mongodb|redis|database)\b",
    "websocket": r"\bwebsocket\b",
    "blockchain": r"\b(?:blockchain|solana|ethereum|web3)\b",
    "ai": r"\b(?:ai|llm|machine\s+learning|neural|gpt|claude|transformer)\b",
    "knowledge-graph": r"\bknowledge[\s-]graph\b",
    "nlp": r"\b(?:nlp|natural\s+language|tokeniz|linguistic)\b",
    "osc": r"\bosc\b",
    "p5js": r"\bp5\.?js\b",
    "microservices": r"\bmicroservices?\b",
    "api": r"\b(?:rest\s*api|graphql|api\s+endpoint)\b",
}

# Manual block name overrides for repos with unusual naming
BLOCK_NAME_OVERRIDES = {
    "recursive-engine--generative-entity": "recursive-engine",
    "organon-noumenon--ontogenetic-morphe": "organon-noumenon",
    "a-i-council--coliseum": "ai-council-coliseum",
    "nexus--babel-alexandria-": "nexus-babel-alexandria",
    "call-function--ontological": "call-function-ontological",
    "sema-metra--alchemica-mundi": "sema-metra-alchemica-mundi",
    "reverse-engine-recursive-run": "reverse-engine-recursive-run",
    "radix-recursiva-solve-coagula-redi": "radix-recursiva",
    "meta-source--ledger-output": "meta-source-ledger-output",
    "4-ivi374-F0Rivi4": "os-ecosystem-cartridge",
    "cog-init-1-0-": "cog-init",
    "a-mavs-olevm": "a-mavs-olevm",
    "art-from--auto-revision-epistemic-engine": "art-from-auto-revision",
    "art-from--narratological-algorithmic-lenses": "art-from-narratological-lenses",
    "life-my--midst--in": "life-my-midst-in",
    "a-i-chat--exporter": "ai-chat-exporter",
    "commerce--meta": "commerce-meta",
    "multi-camera--livestream--framework": "multi-camera-livestream",
    "my--father-mother": "my-father-mother",
    "sovereign-ecosystem--real-estate-luxury": "sovereign-ecosystem-real-estate",
    "search-local--happy-hour": "search-local-happy-hour",
    "universal-mail--automation": "universal-mail-automation",
    "peer-audited--behavioral-blockchain": "peer-audited-behavioral-blockchain",
    "parlor-games--ephemera-engine": "parlor-games-ephemera-engine",
    "a-i--skills": "ai-skills",
    "agent--claude-smith": "agent-claude-smith",
    "ivi374ivi027-05": "mfa-thesis-portfolio",
    "organvm-corpvs-testamentvm": "organvm-corpus",
    "organvm-mcp-server": "organvm-mcp-server",
}

# Map existing hand-authored blocks to their registry repo names
EXISTING_BLOCK_REPOS = {
    "recursive-engine": "recursive-engine--generative-entity",
    "agentic-titan": "agentic-titan",
    "krypto-velamen": "krypto-velamen",
    "ai-council-coliseum": "a-i-council--coliseum",
    "generative-music": "metasystem-master",  # covers example-generative-music too
    "omni-dromenon-engine": "metasystem-master",
    "organvm-system": None,  # meta block, not 1:1 with a repo
    "life-my-midst-in": "life-my--midst--in",
    "nexus-babel-alexandria": "nexus--babel-alexandria-",
    "starts-prize-art-outputs": None,  # composite block
    "classroom-rpg-aetheria": "classroom-rpg-aetheria",
}


def load_registry() -> dict:
    """Load and return the registry-v2.json."""
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def extract_repos(registry: dict) -> list[dict]:
    """Extract flat repo list from registry with organ context."""
    repos = []
    for organ_key, organ_data in registry["organs"].items():
        for repo in organ_data.get("repositories", []):
            repos.append({
                "organ": organ_key,
                "organ_name": organ_data.get("name", ""),
                "name": repo["name"],
                "org": repo["org"],
                "description": repo.get("description", ""),
                "tier": repo.get("tier", ""),
                "portfolio_relevance": repo.get("portfolio_relevance", ""),
                "implementation_status": repo.get("implementation_status", ""),
                "dependencies": repo.get("dependencies", []),
                "promotion_status": repo.get("promotion_status", ""),
            })
    return repos


def repo_to_block_name(repo_name: str) -> str:
    """Convert repo name to block filename."""
    if repo_name in BLOCK_NAME_OVERRIDES:
        return BLOCK_NAME_OVERRIDES[repo_name]
    # Default: strip trailing hyphens, collapse -- to -
    name = re.sub(r"-+$", "", repo_name)
    name = re.sub(r"--+", "-", name)
    return name


def relevance_level(relevance_str: str) -> str:
    """Extract relevance level from portfolio_relevance field."""
    if not relevance_str:
        return "NONE"
    return relevance_str.split(" - ")[0].strip()


def should_skip(repo: dict) -> str | None:
    """Return skip reason if repo should be excluded, else None."""
    if repo["tier"] == "infrastructure":
        return "infrastructure tier"
    if repo["tier"] == "archive":
        return "archive tier"
    if repo["implementation_status"] == "ARCHIVED":
        return "archived status"
    return None


def existing_block_path(block_name: str) -> Path | None:
    """Return path if block already exists."""
    path = PROJECTS_DIR / f"{block_name}.md"
    if path.exists():
        return path
    return None


def read_readme(repo: dict) -> str | None:
    """Read a repo's README.md, return full text or None."""
    readme_path = WORKSPACE / repo["org"] / repo["name"] / "README.md"
    if readme_path.exists():
        text = readme_path.read_text()
        if text.strip():
            return text
    return None


def read_seed(repo: dict) -> dict | None:
    """Read a repo's seed.yaml, return parsed dict or None."""
    seed_path = WORKSPACE / repo["org"] / repo["name"] / "seed.yaml"
    if seed_path.exists():
        try:
            return yaml.safe_load(seed_path.read_text())
        except yaml.YAMLError:
            return None
    return None


def strip_markdown_inline(text: str) -> str:
    """Strip inline markdown formatting (bold, italic, links) from text."""
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def extract_intro_paragraph(readme: str) -> str:
    """Extract the first substantive paragraph from a README.

    Skips badge lines, blockquotes, rules, and table of contents.
    Returns text between first # heading and first ## heading (or end of intro).
    """
    lines = readme.split("\n")
    collecting = False
    intro_lines = []

    for line in lines:
        stripped = line.strip()

        # Start collecting after first # heading
        if stripped.startswith("# ") and not collecting:
            collecting = True
            continue

        # Stop at next ## heading, TOC, or --- rule
        if collecting:
            if stripped.startswith("## "):
                break
            if stripped == "---":
                if intro_lines:
                    break
                continue

            # Skip non-content lines
            if stripped.startswith("[!["):
                continue
            if stripped.startswith("> **[ORGAN"):
                continue
            if stripped.startswith("> "):
                continue
            if stripped.startswith("| "):
                continue
            if re.match(r"^\d+\.\s+\[", stripped):
                continue
            if re.match(r"^-\s+\[", stripped):
                continue

            if stripped:
                intro_lines.append(stripped)

    text = " ".join(intro_lines).strip()
    return strip_markdown_inline(text)


def extract_full_content(readme: str, max_words: int = 350) -> str | None:
    """Extract substantive README content after intro for Full section.

    Looks for Architecture/Features/Technical/Core sections.
    Returns formatted text or None.
    """
    lines = readme.split("\n")
    sections_of_interest = []
    current_section = None
    current_lines = []
    past_intro = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## "):
            # Save previous section
            if current_section and current_lines:
                sections_of_interest.append((current_section, current_lines))
            current_section = stripped[3:].strip()
            current_lines = []
            past_intro = True
            continue

        if past_intro and current_section:
            # Skip badge lines and links
            if stripped.startswith("[!["):
                continue
            if stripped.startswith("| ") and "---" in stripped:
                continue
            if stripped:
                current_lines.append(stripped)

    # Save last section
    if current_section and current_lines:
        sections_of_interest.append((current_section, current_lines))

    # Prioritize sections
    priority_keywords = [
        "architecture", "feature", "technical", "core concept",
        "overview", "how it works", "design", "solution",
        "problem", "capability", "component", "system",
    ]

    selected = []
    for header, content_lines in sections_of_interest:
        header_lower = header.lower()
        # Skip meta sections
        if any(skip in header_lower for skip in [
            "install", "setup", "contributing", "license", "roadmap",
            "changelog", "cross-reference", "table of content", "badge",
            "getting started", "acknowledgment", "related work",
        ]):
            continue
        if any(kw in header_lower for kw in priority_keywords):
            selected.append((header, content_lines))

    if not selected:
        # Fall back to first non-meta sections
        for header, content_lines in sections_of_interest[:3]:
            header_lower = header.lower()
            if not any(skip in header_lower for skip in [
                "install", "setup", "contributing", "license", "roadmap",
                "changelog", "cross-reference", "table of content",
                "getting started", "acknowledgment",
            ]):
                selected.append((header, content_lines))

    if not selected:
        return None

    # Build content within word limit
    result_parts = []
    word_count = 0
    for header, content_lines in selected:
        section_text = "\n".join(content_lines)
        section_words = section_text.split()
        if word_count + len(section_words) > max_words:
            remaining = max_words - word_count
            if remaining > 20:
                trimmed = " ".join(section_words[:remaining])
                result_parts.append(f"**{header}:** {trimmed}")
            break
        result_parts.append(f"**{header}:** {' '.join(section_words)}")
        word_count += len(section_words)

    if not result_parts:
        return None

    return "\n\n".join(result_parts)


def make_one_line(description: str) -> str:
    """Generate one-line from registry description."""
    if not description:
        return "Project in the ORGANVM system."
    # Truncate at first period if >120 chars
    if len(description) > 120:
        period_idx = description.find(".")
        if 0 < period_idx < 120:
            return description[:period_idx + 1]
        # Truncate with ellipsis
        return description[:117] + "..."
    return description


def make_short(description: str, intro: str, organ: str) -> str:
    """Generate ~100 word short description."""
    organ_name = ORGAN_LONG_NAMES.get(organ, organ)
    organ_sentence = f"Part of {organ} ({organ_name})."

    parts = []
    # Start with registry description as opening
    if description:
        parts.append(description.rstrip(".") + ".")

    # Add README intro content
    if intro:
        # Avoid duplicating content already in description
        desc_words = set(description.lower().split()[:8]) if description else set()
        intro_words = set(intro.lower().split()[:8])
        overlap = len(desc_words & intro_words)
        if overlap < 4:
            parts.append(intro)

    parts.append(organ_sentence)
    text = " ".join(parts)

    # Trim to ~100 words
    words = text.split()
    if len(words) > 110:
        words = words[:100]
        text = " ".join(words)
        # Try to end at a sentence boundary
        last_period = text.rfind(".")
        if last_period > len(text) * 0.6:
            text = text[:last_period + 1]
        else:
            text = text.rstrip(".,;: ") + "."

    return text


def detect_tech_tags(readme_text: str) -> list[str]:
    """Detect technology tags from README content using regex patterns."""
    if not readme_text:
        return []
    text_lower = readme_text.lower()
    found = []
    for tag, pattern in TECH_PATTERNS.items():
        if re.search(pattern, text_lower):
            found.append(tag)
    return found


def compute_tags(repo: dict, readme_text: str | None) -> list[str]:
    """Compute merged tags from organ base + tech detection + description."""
    tags = set()

    # Layer 1: organ base tags
    organ = repo["organ"]
    for tag in ORGAN_BASE_TAGS.get(organ, []):
        tags.add(tag)

    # Layer 2: tech extraction from README
    if readme_text:
        for tag in detect_tech_tags(readme_text):
            tags.add(tag)

    # Layer 3: description-based keywords
    desc_lower = repo["description"].lower() if repo["description"] else ""
    keyword_tag_map = {
        "governance": "governance",
        "orchestrat": "orchestration",
        "education": "education",
        "pedagog": "pedagogy",
        "gamif": "gamification",
        "game": "game-design",
        "music": "music",
        "audio": "audio",
        "performan": "performance",
        "identity": "identity",
        "queer": "queer",
        "archive": "archive",
        "privacy": "privacy",
        "knowledge": "knowledge-graph",
        "visualization": "generative-art",
        "dashboard": "generative-art",
        "portfolio": "portfolio",
        "trading": "fintech",
        "defi": "fintech",
        "scraping": "data",
        "scrapper": "data",
        "lead gen": "data",
        "curriculum": "curriculum",
        "salon": "community",
        "rhetoric": "nlp",
        "alchemical": "symbolic",
        "ontolog": "symbolic",
        "epistemo": "formal-systems",
        "cognitive": "formal-systems",
        "recursive": "recursive",
    }
    for keyword, tag in keyword_tag_map.items():
        if keyword in desc_lower:
            tags.add(tag)

    return sorted(tags)


def compute_identity_positions(repo: dict, readme_text: str | None) -> list[str]:
    """Compute identity positions based on organ and README keywords."""
    organ = repo["organ"]
    config = ORGAN_IDENTITY_MAP.get(organ, {"primary": [], "triggers": {}})
    positions = set(config["primary"])

    # Check triggers against README + description
    search_text = (repo["description"] + " " + (readme_text or "")).lower()
    for position, keywords in config.get("triggers", {}).items():
        if any(kw in search_text for kw in keywords):
            positions.add(position)

    return sorted(positions)


def compute_tracks(repo: dict) -> list[str]:
    """Compute application tracks based on organ and tier."""
    organ = repo["organ"]
    tier = repo["tier"]
    track_config = ORGAN_TRACK_MAP.get(organ, {"flagship": ["job"], "standard": ["job"]})
    tier_key = "flagship" if tier == "flagship" else "standard"
    return track_config.get(tier_key, ["job"])


def compute_related_projects(repo: dict) -> list[str]:
    """Compute related projects from dependencies."""
    related = set()

    # Flagships always relate to organvm-system
    if repo["tier"] == "flagship":
        related.add("organvm-system")

    # Parse dependencies
    for dep in repo.get("dependencies", []):
        # dep format: "org/repo-name"
        dep_repo = dep.split("/")[-1] if "/" in dep else dep
        dep_block = repo_to_block_name(dep_repo)
        related.add(dep_block)

    # Remove self-reference
    self_block = repo_to_block_name(repo["name"])
    related.discard(self_block)

    return sorted(related) if related else []


def generate_block(repo: dict) -> str:
    """Generate complete block markdown for a repo."""
    block_name = repo_to_block_name(repo["name"])
    readme_text = read_readme(repo)
    intro = extract_intro_paragraph(readme_text) if readme_text else ""
    description = repo["description"]

    # Determine tier
    rel = relevance_level(repo["portfolio_relevance"])
    has_readme = readme_text is not None and len((readme_text or "").split()) > 100
    block_tier = "full" if rel in ("CRITICAL", "HIGH") and has_readme else "short"

    # Compute frontmatter fields
    tags = compute_tags(repo, readme_text)
    identity_positions = compute_identity_positions(repo, readme_text)
    tracks = compute_tracks(repo)
    related = compute_related_projects(repo)

    # Derive a human title
    if " — " in description:
        title = description.split(" — ")[0]
    elif ": " in description and len(description.split(": ")[0]) < 60:
        title = description
    else:
        title = description
    # Truncate at first sentence if too long
    if len(title) > 80:
        period_idx = title.find(".")
        if 10 < period_idx < 80:
            title = title[:period_idx]
        elif "; " in title[:80]:
            title = title[:title.index("; ")]
        elif ", " in title[40:80]:
            last_comma = title[:80].rfind(", ")
            title = title[:last_comma]
        else:
            title = title[:77] + "..."

    # Build frontmatter
    fm = {
        "title": title,
        "category": "projects",
        "tags": tags,
        "identity_positions": identity_positions,
        "tracks": tracks,
        "tier": block_tier,
        "review_status": "auto-generated",
    }
    if related:
        fm["related_projects"] = related

    # Render frontmatter as YAML
    fm_lines = ["---"]
    safe_title = fm["title"].replace('"', '\\"')
    fm_lines.append(f'title: "{safe_title}"')
    fm_lines.append(f"category: {fm['category']}")
    fm_lines.append(f"tags: [{', '.join(fm['tags'])}]")
    fm_lines.append(f"identity_positions: [{', '.join(fm['identity_positions'])}]")
    fm_lines.append(f"tracks: [{', '.join(fm['tracks'])}]")
    if related:
        fm_lines.append(f"related_projects: [{', '.join(fm['related_projects'])}]")
    fm_lines.append(f"tier: {fm['tier']}")
    fm_lines.append("review_status: auto-generated")
    fm_lines.append("---")

    # Build content
    one_line = make_one_line(description)
    short = make_short(description, intro, repo["organ"])

    content_lines = [
        "\n".join(fm_lines),
        "",
        f"# Project: {title}",
        "",
        "## One-Line",
        one_line,
        "",
        "## Short (100 words)",
        short,
    ]

    # Full section for CRITICAL/HIGH repos with substantial READMEs
    if block_tier == "full" and readme_text:
        full_content = extract_full_content(readme_text)
        if full_content:
            content_lines.extend(["", "## Full", full_content])

    # Links
    org = repo["org"]
    name = repo["name"]
    content_lines.extend([
        "",
        "## Links",
        f"- GitHub: https://github.com/{org}/{name}",
        f"- Organ: {repo['organ']} ({ORGAN_LONG_NAMES.get(repo['organ'], '')}) — {repo['organ_name']}",
    ])

    return "\n".join(content_lines) + "\n"


def coverage_report(repos: list[dict]):
    """Print coverage analysis."""
    total = len(repos)
    skipped = 0
    existing = 0
    to_generate = 0
    by_organ = {}

    for repo in repos:
        organ = repo["organ"]
        by_organ.setdefault(organ, {"total": 0, "skip": 0, "existing": 0, "new": 0})
        by_organ[organ]["total"] += 1

        skip = should_skip(repo)
        if skip:
            skipped += 1
            by_organ[organ]["skip"] += 1
            continue

        block_name = repo_to_block_name(repo["name"])
        if existing_block_path(block_name):
            existing += 1
            by_organ[organ]["existing"] += 1
        else:
            to_generate += 1
            by_organ[organ]["new"] += 1

    print(f"Coverage Report")
    print(f"{'='*60}")
    print(f"Total repos:      {total}")
    print(f"Skipped:          {skipped} (infrastructure/archive)")
    print(f"Existing blocks:  {existing}")
    print(f"To generate:      {to_generate}")
    print(f"Coverage:         {(existing + to_generate)}/{total - skipped} eligible")
    print()
    print(f"{'Organ':<14} {'Total':>5} {'Skip':>5} {'Exist':>5} {'New':>5}")
    print(f"{'-'*14} {'-'*5} {'-'*5} {'-'*5} {'-'*5}")
    for organ in sorted(by_organ):
        d = by_organ[organ]
        print(f"{organ:<14} {d['total']:>5} {d['skip']:>5} {d['existing']:>5} {d['new']:>5}")


def main():
    parser = argparse.ArgumentParser(description="Generate project blocks from ORGANVM registry")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--report", action="store_true", help="Coverage report only")
    parser.add_argument("--organ", help="Process single organ (e.g. ORGAN-I)")
    parser.add_argument("--target", help="Process single repo by name")
    parser.add_argument("--yes", action="store_true", help="Execute generation")
    parser.add_argument("--force", action="store_true", help="Overwrite existing blocks")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild _index.yaml after")
    args = parser.parse_args()

    registry = load_registry()
    all_repos = extract_repos(registry)

    # Filter by organ if specified
    if args.organ:
        all_repos = [r for r in all_repos if r["organ"] == args.organ]
        if not all_repos:
            print(f"No repos found for organ: {args.organ}")
            sys.exit(1)

    # Filter by target if specified
    if args.target:
        all_repos = [r for r in all_repos if r["name"] == args.target or repo_to_block_name(r["name"]) == args.target]
        if not all_repos:
            print(f"No repo found matching: {args.target}")
            sys.exit(1)

    if args.report:
        coverage_report(all_repos)
        return

    # Process repos
    generated = 0
    skipped_reasons = {}
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    for repo in all_repos:
        block_name = repo_to_block_name(repo["name"])

        # Check exclusions
        skip = should_skip(repo)
        if skip:
            skipped_reasons.setdefault(skip, []).append(repo["name"])
            continue

        # Check existing
        if existing_block_path(block_name) and not args.force:
            skipped_reasons.setdefault("existing block", []).append(repo["name"])
            continue

        # Generate
        content = generate_block(repo)
        output_path = PROJECTS_DIR / f"{block_name}.md"

        if args.dry_run:
            rel = relevance_level(repo["portfolio_relevance"])
            readme = read_readme(repo)
            readme_words = len(readme.split()) if readme else 0
            print(f"  [{rel:8s}] {block_name}.md  ({repo['organ']}, {readme_words}w README)")
            generated += 1
        elif args.yes:
            output_path.write_text(content)
            print(f"  Wrote {output_path.relative_to(REPO_ROOT)}")
            generated += 1
        else:
            print(f"Would generate: {block_name}.md")
            generated += 1

    # Summary
    print()
    if args.dry_run:
        print(f"Dry run: {generated} blocks would be generated")
    elif args.yes:
        print(f"Generated {generated} blocks")
    else:
        print(f"{generated} blocks ready to generate. Run with --yes to execute.")

    for reason, repos_list in sorted(skipped_reasons.items()):
        print(f"  Skipped ({reason}): {len(repos_list)}")

    # Rebuild index if requested
    if args.rebuild_index and args.yes and generated > 0:
        print("\nRebuilding block index...")
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "build_block_index.py")],
            check=True,
        )


if __name__ == "__main__":
    main()
