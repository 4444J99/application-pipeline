#!/usr/bin/env python3
"""LinkedIn Content Engine — generate optimized posts from narrative blocks.

Usage:
    python scripts/linkedin_composer.py --block methodology/ai-conductor
    python scripts/linkedin_composer.py --block methodology/process-as-product --position systems-artist
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
IDENTITY_FILE = REPO_ROOT / "strategy" / "identity-positions.md"
OUTPUT_DIR = REPO_ROOT / "pipeline" / "drafts" / "linkedin"

# LinkedIn character limits
MAX_CHARS = 3000
IDEAL_MIN = 800
IDEAL_MAX = 1600

# Truncation patterns from tailor_resume.py
_TRUNCATION_TAIL = re.compile(
    r'\b(and|to|the|of|for|in|with|across|through|from|into|by|or|a|an)\.\s*$'
)
_COMMA_PERIOD = re.compile(r',\.\s*$')


class BlockLoader:
    """Parses narrative blocks from markdown files with YAML frontmatter."""

    @staticmethod
    def load(block_rel_path: str) -> dict[str, Any]:
        path = BLOCKS_DIR / f"{block_rel_path}.md"
        if not path.exists():
            raise FileNotFoundError(f"Block not found: {path}")

        content = path.read_text()
        parts = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)

        if len(parts) < 3:
            return {"frontmatter": {}, "body": content}

        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            frontmatter = {}

        return {"frontmatter": frontmatter, "body": parts[2].strip()}


class IdentityMapper:
    """Extracts framing rules and templates from identity-positions.md."""

    # Manual mapping from block metadata slugs to identity-positions.md slugs
    MAPPING = {
        "independent-engineer": "software-engineer-at-organvm",
        "educator": "educator-learning-architect",
        "founder-operator": "founder-operator",
        "governance-architect": "governance-compliance-architect",
    }

    def __init__(self):
        self.identities = self._parse_identities()

    def _parse_identities(self) -> dict[str, dict]:
        if not IDENTITY_FILE.exists():
            return {}

        content = IDENTITY_FILE.read_text()
        # Regex to find "## N. Name" headers
        sections = re.split(r"^##\s+\d+\.\s+", content, flags=re.MULTILINE)
        identities = {}

        for section in sections[1:]:  # Skip the preamble
            lines = section.strip().split("\n")
            name_line = lines[0].strip()
            # Slugify the name (e.g., "Systems Artist" -> "systems-artist")
            slug = name_line.lower().replace(" / ", "-").replace(" @ ", "-at-").replace(" ", "-")
            
            template_match = re.search(r"> (.*?)(?:\n\n|\Z)", section, re.DOTALL)
            opening_template = template_match.group(1).strip() if template_match else ""
            
            identities[slug] = {
                "name": name_line,
                "opening": opening_template,
            }
        return identities

    def get_template(self, slug: str) -> str:
        # Check mapping first, then try the slug itself
        mapped_slug = self.MAPPING.get(slug, slug)
        return self.identities.get(mapped_slug, {}).get("opening", "")


class LinkedInComposer:
    """Orchestrates the generation of LinkedIn-optimized posts."""

    def __init__(self):
        self.loader = BlockLoader()
        self.mapper = IdentityMapper()

    def validate_draft(self, text: str) -> list[str]:
        """Check for LinkedIn-specific violations."""
        warnings = []
        char_count = len(text)
        
        if char_count > MAX_CHARS:
            warnings.append(f"CRITICAL: Post exceeds LinkedIn limit ({char_count}/{MAX_CHARS} chars)")
        elif char_count < IDEAL_MIN:
            warnings.append(f"ADVISORY: Post might be too short for high engagement ({char_count} chars)")
        elif char_count > IDEAL_MAX:
            warnings.append(f"ADVISORY: Post is on the long side ({char_count} chars)")

        # Sentence completeness check
        lines = text.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            if _TRUNCATION_TAIL.search(line) or _COMMA_PERIOD.search(line):
                warnings.append(f"WARNING: Potential truncation at line {i+1}: '{line[-30:]}'")

        return warnings

    def compose(self, block_id: str, position: str = None) -> None:
        """Generate and save LinkedIn drafts."""
        block = self.loader.load(block_id)
        fm = block["frontmatter"]
        body = block["body"]

        # Determine which positions to generate for
        positions_to_gen = [position] if position else fm.get("identity_positions", ["independent-engineer"])
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"\n🚀 Composing LinkedIn drafts for block: {block_id}")
        
        for pos in positions_to_gen:
            opening = self.mapper.get_template(pos)
            if not opening:
                print(f"  ⚠️  No opening template found for position: {pos}")
                continue

            # Basic "Scale-first" composition
            draft = self._generate_scale_first(opening, body, fm)
            
            warnings = self.validate_draft(draft)
            
            filename = f"{block_id.replace('/', '--')}-{pos}.md"
            filepath = OUTPUT_DIR / filename
            filepath.write_text(draft)
            
            print(f"  ✅ Generated: {filename}")
            for w in warnings:
                print(f"     - {w}")

    def _generate_scale_first(self, opening: str, body: str, fm: dict) -> str:
        """Lead with evidence/metrics, followed by narrative."""
        # Clean markdown headers and formatting for LinkedIn
        # Remove structural headers like "## One-Line", "## Short (150 words)", etc.
        body = re.sub(r"^#+\s+(One-Line|Short|Key Metric).*$", "", body, flags=re.MULTILINE | re.IGNORECASE)
        
        # Clean up remaining headers
        clean_body = re.sub(r"^#+\s+", "", body, flags=re.MULTILINE)
        
        # LinkedIn doesn't support markdown bold/italic in most clients, but some symbols work.
        # We'll just strip the bold markers for now to keep it clean.
        clean_body = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean_body)
        
        # Ensure no more than two consecutive newlines
        clean_body = re.sub(r"\n{3,}", "\n\n", clean_body).strip()
        
        tags = " ".join([f"#{t}" for t in fm.get("tags", [])[:5]])
        
        # Structure the post
        sections = [
            opening,
            "\n\n",
            clean_body,
            "\n\n",
            "Check out the full ORGANVM project: https://4444j99.github.io/portfolio/",
            "\n\n",
            tags
        ]
        
        return "".join(sections).strip()


def main():
    parser = argparse.ArgumentParser(description="Compose LinkedIn posts from narrative blocks.")
    parser.add_argument("--block", required=True, help="Block ID (e.g., methodology/ai-conductor)")
    parser.add_argument("--position", help="Optional identity position to force")
    
    args = parser.parse_args()
    
    composer = LinkedInComposer()
    try:
        composer.compose(args.block, args.position)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
