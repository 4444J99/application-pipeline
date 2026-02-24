#!/usr/bin/env python3
"""Full-pipeline application orchestrator.

Assembles research, identity mapping, and a structured synthesis prompt
for pipeline entries across all portal types. After the user generates
output via Claude, integrates the results back into the pipeline.

Usage:
    python scripts/alchemize.py --target anthropic-fde                    # Full pipeline → prompt.md
    python scripts/alchemize.py --target anthropic-fde --phase research   # Stop after research
    python scripts/alchemize.py --target anthropic-fde --phase map        # Stop after mapping
    python scripts/alchemize.py --target anthropic-fde --integrate        # Integrate output.md back
    python scripts/alchemize.py --target anthropic-fde --submit           # Submit via greenhouse_submit.py
    python scripts/alchemize.py --batch                                   # Phases 1-4 for all Greenhouse entries
    python scripts/alchemize.py --batch-all                               # Phases 1-4 for all portal types
    python scripts/alchemize.py --batch-all --portal greenhouse           # Same as --batch
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml

from pipeline_lib import (
    ACTIONABLE_STATUSES,
    BLOCKS_DIR,
    MATERIALS_DIR,
    REPO_ROOT,
    VARIANTS_DIR,
    load_entries,
    load_entry_by_id,
    load_profile,
    strip_markdown,
    count_words,
    PIPELINE_DIR_ACTIVE,
    PROFILE_ID_MAP,
)
from greenhouse_submit import (
    fetch_job_data,
    parse_greenhouse_url,
    resolve_cover_letter,
    get_custom_questions,
    field_type_label,
    STANDARD_FIELD_NAMES,
    ANSWERS_DIR,
)
from enrich import RESUME_BY_IDENTITY, select_resume

WORK_DIR = Path(__file__).resolve().parent / ".alchemize-work"
STRATEGY_DIR = REPO_ROOT / "strategy"
TARGETS_DIR = REPO_ROOT / "targets"

PHASES = ("intake", "research", "map", "synthesize")

# Keyword → block file mapping for evidence selection
METHODOLOGY_KEYWORDS = {
    "ai": "methodology/ai-conductor.md",
    "artificial intelligence": "methodology/ai-conductor.md",
    "machine learning": "methodology/ai-conductor.md",
    "llm": "methodology/ai-conductor.md",
    "agent": "methodology/ai-conductor.md",
    "governance": "methodology/governance-as-art.md",
    "policy": "methodology/governance-as-art.md",
    "compliance": "methodology/governance-as-art.md",
    "process": "methodology/process-as-product.md",
    "methodology": "methodology/process-as-product.md",
    "documentation": "methodology/process-as-product.md",
}

PROJECT_KEYWORDS = {
    "agent": "projects/agentic-titan.md",
    "orchestration": "projects/agentic-titan.md",
    "multi-agent": "projects/agentic-titan.md",
    "recursive": "projects/recursive-engine.md",
    "symbolic": "projects/recursive-engine.md",
    "dsl": "projects/recursive-engine.md",
    "music": "projects/generative-music.md",
    "audio": "projects/generative-music.md",
    "generative art": "projects/omni-dromenon-engine.md",
    "creative coding": "projects/omni-dromenon-engine.md",
    "performance": "projects/omni-dromenon-engine.md",
    "identity": "projects/life-my-midst-in.md",
    "interview": "projects/life-my-midst-in.md",
    "system": "projects/organvm-system.md",
    "infrastructure": "projects/organvm-system.md",
    "repository": "projects/organvm-system.md",
    "queer": "projects/krypto-velamen.md",
    "lgbtq": "projects/krypto-velamen.md",
    "privacy": "projects/krypto-velamen.md",
}


# ---------------------------------------------------------------------------
# HTML text extraction (stdlib only)
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """Extract visible text from HTML, preferring <main> or <article> content."""

    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript", "svg", "head"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._text.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._text)


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML using stdlib html.parser."""
    import html as html_module

    # Unescape HTML entities first (Greenhouse API returns &lt; etc.)
    html = html_module.unescape(html)

    # Try to isolate <main> or <article> content first
    for tag in ("main", "article"):
        pattern = re.compile(
            rf"<{tag}[^>]*>(.*?)</{tag}>", re.DOTALL | re.IGNORECASE
        )
        match = pattern.search(html)
        if match:
            html = match.group(1)
            break

    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    text = parser.get_text()
    # Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Truncate to avoid giant pages
    if len(text) > 8000:
        text = text[:8000] + "\n\n[...truncated]"
    return text


def fetch_page_text(url: str) -> str | None:
    """Fetch a URL and extract readable text. Returns None on failure."""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; application-pipeline/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type.lower() and "text" not in content_type.lower():
                return None
            html = resp.read().decode("utf-8", errors="replace")
        return extract_text_from_html(html)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Phase 1: INTAKE
# ---------------------------------------------------------------------------


def phase_intake_general(entry: dict, no_web: bool = False) -> dict | None:
    """Generic intake for non-Greenhouse entries.

    Scrapes the application URL page text and returns a dict with
    'content' (page text) and 'title' (entry name). Returns None
    if no URL is available or the scrape fails.
    """
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    app_url = entry.get("target", {}).get("application_url", "")
    if not app_url:
        print(f"  No application_url for {entry_id}")
        return {"_portal": "general", "title": name}

    if no_web:
        print(f"  Web fetching disabled, skipping scrape for {entry_id}")
        return {"_portal": "general", "title": name}

    print(f"  Fetching application page: {app_url}")
    page_text = fetch_page_text(app_url)
    if page_text:
        return {
            "_portal": "general",
            "title": name,
            "content": page_text,
            "_application_url": app_url,
        }

    print(f"  Warning: Could not fetch application page for {entry_id}")
    return {"_portal": "general", "title": name}


def phase_intake(entry: dict, no_web: bool = False) -> dict | None:
    """Parse entry and fetch data. Returns data dict or None.

    For Greenhouse entries, fetches via the Greenhouse Job Board API.
    For all other portal types, scrapes the application URL page.
    """
    entry_id = entry.get("id", "?")

    portal = entry.get("target", {}).get("portal", "")
    if portal != "greenhouse":
        return phase_intake_general(entry, no_web=no_web)

    app_url = entry.get("target", {}).get("application_url", "")
    parsed = parse_greenhouse_url(app_url)
    if not parsed:
        print(f"  Error: Cannot parse Greenhouse URL for {entry_id}: {app_url}")
        return None

    board_token, job_id = parsed
    print(f"  Fetching job data for {board_token}/{job_id}...")
    job_data = fetch_job_data(board_token, job_id)
    if not job_data:
        print(f"  Warning: Could not fetch job data from Greenhouse API")
        return {"_board_token": board_token, "_job_id": job_id}

    job_data["_board_token"] = board_token
    job_data["_job_id"] = job_id
    return job_data


# ---------------------------------------------------------------------------
# Phase 2: RESEARCH
# ---------------------------------------------------------------------------


def find_existing_research(entry: dict) -> str | None:
    """Search targets/ for markdown files mentioning the organization."""
    org = entry.get("target", {}).get("organization", "")
    if not org:
        return None

    org_lower = org.lower()
    found_parts = []

    for subdir in ("jobs", "grants", "residencies", "writing"):
        target_dir = TARGETS_DIR / subdir
        if not target_dir.exists():
            continue
        for md_file in target_dir.glob("*.md"):
            content = md_file.read_text()
            if org_lower in content.lower():
                found_parts.append(f"### From {subdir}/{md_file.name}\n\n{content[:3000]}")

    return "\n\n".join(found_parts) if found_parts else None


def phase_research(entry: dict, job_data: dict | None, no_web: bool = False) -> str:
    """Assemble research from all available sources. Returns research.md content."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    org = entry.get("target", {}).get("organization", "")
    is_greenhouse = entry.get("target", {}).get("portal") == "greenhouse"

    sections = [f"# Research: {name}\n"]

    # Opportunity description
    if is_greenhouse:
        sections.append("## Job Description\n")
    else:
        sections.append("## Opportunity Description\n")

    if job_data:
        title = job_data.get("title", "Unknown")
        sections.append(f"**Title:** {title}\n")

        location = job_data.get("location", {})
        if isinstance(location, dict) and location.get("name"):
            sections.append(f"**Location:** {location['name']}\n")

        departments = job_data.get("departments", [])
        if departments:
            dept_names = [d.get("name", "") for d in departments if d.get("name")]
            if dept_names:
                sections.append(f"**Departments:** {', '.join(dept_names)}\n")

        content_html = job_data.get("content", "")
        page_content = job_data.get("content", "") if is_greenhouse else ""
        general_content = job_data.get("content", "") if not is_greenhouse else ""

        if is_greenhouse and content_html:
            jd_text = extract_text_from_html(content_html)
            sections.append(f"\n{jd_text}\n")
        elif general_content:
            sections.append(f"\n{general_content}\n")
        elif not is_greenhouse:
            app_url = job_data.get("_application_url", "")
            if app_url:
                sections.append(f"*Application page scraped from {app_url}.*\n")
            else:
                sections.append("*No opportunity description available.*\n")
        else:
            sections.append("*No job description content returned from API.*\n")
    else:
        if is_greenhouse:
            sections.append("*Could not fetch from Greenhouse API.*\n")
        else:
            sections.append("*No opportunity data available.*\n")

    # Custom questions (Greenhouse only)
    if is_greenhouse:
        sections.append("## Custom Questions\n")
        if job_data:
            questions = job_data.get("questions", [])
            custom_qs = get_custom_questions(questions)
            if custom_qs:
                for q in custom_qs:
                    label = q.get("label", "?")
                    required = q.get("required", False)
                    req_tag = " (REQUIRED)" if required else ""
                    sections.append(f"### {label}{req_tag}\n")
                    for field in q.get("fields", []):
                        fname = field.get("name", "")
                        if fname in STANDARD_FIELD_NAMES:
                            continue
                        ftype = field_type_label(field)
                        values = field.get("values", [])
                        sections.append(f"- **Field:** `{fname}`")
                        sections.append(f"- **Type:** {ftype}")
                        if values:
                            opts = ", ".join(v.get("label", "?") for v in values)
                            sections.append(f"- **Options:** {opts}")
                        sections.append("")
            else:
                sections.append("*No custom questions (standard fields only).*\n")
        else:
            sections.append("*Could not fetch questions.*\n")

    # Company overview from web
    sections.append("## Company Overview\n")
    company_url = entry.get("target", {}).get("url", "")
    web_content = None
    if company_url and not no_web:
        print(f"  Fetching company page: {company_url}")
        web_content = fetch_page_text(company_url)
        if web_content:
            # Truncate for readability
            if len(web_content) > 4000:
                web_content = web_content[:4000] + "\n\n[...truncated]"
            sections.append(web_content + "\n")

    if not web_content:
        if no_web:
            sections.append("*Web fetching disabled (--no-web).*\n")
        elif company_url:
            sections.append(f"*Could not fetch {company_url}.*\n")
        else:
            sections.append("*No company URL in pipeline entry.*\n")

    # Existing research files
    existing = find_existing_research(entry)
    if existing:
        sections.append("## Existing Research\n")
        sections.append(existing + "\n")

    # Existing target profile
    sections.append("## Existing Target Profile\n")
    profile = load_profile(entry_id)
    if profile:
        sections.append(f"**Position:** {profile.get('position_label', 'N/A')}")
        narrative = profile.get("identity_narrative", "")
        if narrative:
            sections.append(f"\n**Identity Narrative:**\n{narrative}\n")
        diffs = profile.get("differentiators", [])
        if diffs:
            sections.append("**Differentiators:**")
            for d in diffs:
                if isinstance(d, str):
                    sections.append(f"- {d}")
                elif isinstance(d, dict):
                    sections.append(f"- {d.get('name', '')}: {d.get('description', '')}")
            sections.append("")
    else:
        sections.append(f"*No profile found for {entry_id}.*\n")

    # Research gaps
    gaps = []
    if not job_data or not job_data.get("content"):
        gaps.append("Job description not available from API")
    if not web_content:
        gaps.append(f"Company page not fetched — try: tavily_research '{org}'")
    if not existing:
        gaps.append(f"No existing research files found for {org}")
    if not profile:
        gaps.append(f"No target profile — create targets/profiles/{entry_id}.json")

    if gaps:
        sections.append("## Research Gaps\n")
        for gap in gaps:
            sections.append(f"- {gap}")
        sections.append("")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Phase 3: MAP
# ---------------------------------------------------------------------------


def select_identity_position(entry: dict) -> str:
    """Get identity position from entry fit data."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        pos = fit.get("identity_position", "")
        if pos:
            return pos
    return "creative-technologist"


def load_framing_block(position: str) -> str:
    """Load framing block content for an identity position."""
    # Map position names to filenames
    filename_map = {
        "systems-artist": "systems-artist.md",
        "educator": "educator-researcher.md",
        "creative-technologist": "creative-technologist.md",
        "community-practitioner": "community-practitioner.md",
    }
    filename = filename_map.get(position, f"{position}.md")
    path = BLOCKS_DIR / "framings" / filename
    if path.exists():
        return path.read_text().strip()
    # Try direct match
    path = BLOCKS_DIR / "framings" / f"{position}.md"
    if path.exists():
        return path.read_text().strip()
    return f"*Framing block not found for position: {position}*"


def select_evidence_blocks(job_desc: str, entry: dict) -> list[tuple[str, str]]:
    """Select relevant evidence blocks based on job description keywords.

    Returns list of (block_path, content) tuples.
    """
    selected = {}
    job_lower = job_desc.lower()

    # Always include core evidence
    for core in ("evidence/metrics-snapshot.md", "evidence/differentiators.md"):
        path = BLOCKS_DIR / core
        if path.exists():
            selected[core] = path.read_text().strip()

    # Match methodology blocks
    for keyword, block_path in METHODOLOGY_KEYWORDS.items():
        if keyword in job_lower and block_path not in selected:
            path = BLOCKS_DIR / block_path
            if path.exists():
                selected[block_path] = path.read_text().strip()

    # Match project blocks
    for keyword, block_path in PROJECT_KEYWORDS.items():
        if keyword in job_lower and block_path not in selected:
            path = BLOCKS_DIR / block_path
            if path.exists():
                selected[block_path] = path.read_text().strip()

    # Check lead_organs for additional matches
    lead_organs = entry.get("fit", {}).get("lead_organs", [])
    if "IV" in lead_organs or "III" in lead_organs:
        for block_path in ("projects/agentic-titan.md", "methodology/ai-conductor.md"):
            if block_path not in selected:
                path = BLOCKS_DIR / block_path
                if path.exists():
                    selected[block_path] = path.read_text().strip()

    return list(selected.items())


def select_work_samples(profile: dict | None, job_desc: str) -> list[dict]:
    """Select 3-5 most relevant work samples based on keyword overlap."""
    if not profile:
        return []

    samples = profile.get("work_samples", [])
    if not samples:
        return []

    job_words = set(job_desc.lower().split())
    scored = []
    for sample in samples:
        desc = sample.get("description", "").lower()
        name = sample.get("name", "").lower()
        sample_words = set(desc.split()) | set(name.split())
        overlap = len(job_words & sample_words)
        scored.append((overlap, sample))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:5]]


def phase_map(entry: dict, research: str, profile: dict | None) -> str:
    """Build identity mapping. Returns mapping.md content."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    position = select_identity_position(entry)
    framing_content = load_framing_block(position)

    # Extract job description from research for keyword matching
    job_desc = research

    evidence_blocks = select_evidence_blocks(job_desc, entry)
    work_samples = select_work_samples(profile, job_desc)

    sections = [f"# Identity Mapping: {name}\n"]

    sections.append(f"## Selected Position: {position}\n")

    sections.append("## Framing Block\n")
    sections.append(framing_content + "\n")

    sections.append("## Elevator Pitch\n")
    pitch_path = BLOCKS_DIR / "identity" / "60s.md"
    if pitch_path.exists():
        sections.append(pitch_path.read_text().strip() + "\n")

    sections.append(f"## Relevant Evidence ({len(evidence_blocks)} blocks)\n")
    for block_path, content in evidence_blocks:
        sections.append(f"### {block_path}\n")
        sections.append(content + "\n")

    sections.append(f"## Relevant Projects ({len(work_samples)} samples)\n")
    if work_samples:
        for sample in work_samples:
            name_s = sample.get("name", "?")
            url = sample.get("url", "")
            desc = sample.get("description", "")
            sections.append(f"### {name_s}")
            if url:
                sections.append(f"- **URL:** {url}")
            sections.append(f"- **Description:** {desc}")
            sections.append("")
    else:
        sections.append("*No profile with work samples available.*\n")

    # Resume selection
    sections.append("## Resume Selection\n")
    resume = select_resume(entry)
    position = select_identity_position(entry)
    sections.append(f"**Selected resume:** {resume}")
    sections.append(f"**Identity position:** {position}")
    if position in RESUME_BY_IDENTITY:
        sections.append(f"**Resume framing:** {position.replace('-', ' ').title()} variant")
    else:
        sections.append("**Resume framing:** Default (multimedia specialist)")
    sections.append("")

    # Storefront translation notes
    sections.append("## Storefront Translation Notes\n")
    playbook_path = STRATEGY_DIR / "storefront-playbook.md"
    if playbook_path.exists():
        playbook = playbook_path.read_text().strip()
        sections.append(playbook + "\n")
    else:
        sections.append("*storefront-playbook.md not found.*\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Phase 4: SYNTHESIZE
# ---------------------------------------------------------------------------


def _extract_research_section(research: str, header: str) -> str:
    """Extract a section from research markdown by ## header name."""
    full_header = f"## {header}"
    if full_header not in research:
        return ""
    start = research.index(full_header)
    rest = research[start + len(full_header):]
    next_section = rest.find("\n## ")
    if next_section >= 0:
        return rest[:next_section].strip()
    return rest.strip()


def phase_synthesize(
    entry: dict, research: str, mapping: str, existing_cl: str | None
) -> str:
    """Assemble the structured prompt for Claude. Returns prompt.md content."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)
    org = entry.get("target", {}).get("organization", "")
    is_greenhouse = entry.get("target", {}).get("portal") == "greenhouse"
    deadline = entry.get("deadline", {})
    dl_date = deadline.get("date", "Rolling") if isinstance(deadline, dict) else "Rolling"
    dl_type = deadline.get("type", "unknown") if isinstance(deadline, dict) else "unknown"
    amount = entry.get("amount", {})
    salary = ""
    if isinstance(amount, dict):
        val = amount.get("value", 0)
        currency = amount.get("currency", "USD")
        if val:
            salary = f"${val:,}" if currency == "USD" else f"{currency} {val:,}"

    # Extract sections from research
    jd_section = (
        _extract_research_section(research, "Job Description")
        or _extract_research_section(research, "Opportunity Description")
    )
    questions_section = _extract_research_section(research, "Custom Questions")
    company_section = _extract_research_section(research, "Company Overview")

    # Extract sections from mapping
    position = select_identity_position(entry)
    framing_section = _extract_research_section(mapping, "Framing Block")
    evidence_section = _extract_research_section(mapping, "Relevant Evidence")
    projects_section = _extract_research_section(mapping, "Relevant Projects")
    resume_section = _extract_research_section(mapping, "Resume Selection")
    storefront_section = _extract_research_section(mapping, "Storefront Translation Notes")

    # Build prompt
    lines = [
        "# Application Synthesis Prompt\n",
        "## Target\n",
        f"- **Name:** {name}",
        f"- **Organization:** {org}",
        f"- **Entry ID:** {entry_id}",
        f"- **Deadline:** {dl_date} ({dl_type})",
    ]
    if salary:
        lines.append(f"- **Salary:** {salary}")
    lines.append("")

    desc_label = "Job Description" if is_greenhouse else "Opportunity Description"
    lines.append(f"## {desc_label}\n")
    lines.append(jd_section if jd_section else "*Not available.*")
    lines.append("")

    if is_greenhouse and questions_section and "*No custom questions" not in questions_section:
        lines.append("## Custom Questions Requiring Answers\n")
        lines.append(questions_section)
        lines.append("")

    lines.append("## Organization Philosophy & Values\n")
    lines.append(company_section if company_section else "*Not available — research manually.*")
    lines.append("")

    lines.append(f"## Your Identity Position: {position}\n")
    lines.append(framing_section if framing_section else "*Not available.*")
    lines.append("")

    lines.append("## Your Evidence\n")
    lines.append(evidence_section if evidence_section else "*No evidence blocks selected.*")
    lines.append("")

    lines.append("## Your Relevant Projects\n")
    lines.append(projects_section if projects_section else "*No projects selected.*")
    lines.append("")

    # Resume note
    if resume_section:
        lines.append("## Resume Attached\n")
        lines.append(resume_section)
        lines.append("")

    lines.append("## Storefront Rules\n")
    lines.append(storefront_section if storefront_section else "*storefront-playbook.md not found.*")
    lines.append("")

    if existing_cl:
        lines.append("## Existing Cover Letter (for reference/revision)\n")
        lines.append(existing_cl)
        lines.append("")

    lines.append("---\n")
    lines.append("## Instructions\n")
    lines.append("Generate the following, each clearly delimited:\n")

    lines.append("### COVER_LETTER")
    lines.append("Write a cover letter following the storefront-playbook rules. Lead with numbers,")
    lines.append("one claim per sentence, match the reviewer's vocabulary. 400-600 words.")
    if resume_section:
        lines.append("The attached resume is noted above. Ensure the cover letter complements its framing.")
    lines.append("Use the existing cover letter as a starting point if provided above.")
    lines.append("")

    if is_greenhouse and questions_section and "*No custom questions" not in questions_section:
        lines.append("### GREENHOUSE_ANSWERS")
        lines.append("For each custom question above, provide the answer in this exact format:")
        lines.append("```yaml")
        lines.append("field_name: |")
        lines.append("  answer text here")
        lines.append("```")
        lines.append("")

    lines.append("### IDENTITY_FRAMING")
    lines.append("A 1-2 sentence framing for this specific application (goes in pipeline YAML fit.framing).")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase 5: INTEGRATE
# ---------------------------------------------------------------------------


def parse_output(text: str) -> dict:
    """Parse output.md into sections by ### delimiters."""
    sections = {}
    current_key = None
    current_lines = []

    for line in text.split("\n"):
        if line.startswith("### "):
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line[4:].strip().upper().replace(" ", "_")
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def write_cover_letter_variant(entry_id: str, entry: dict, cl_text: str) -> Path:
    """Write cover letter to variants/cover-letters/{id}-alchemized.md."""
    name = entry.get("name", entry_id)
    app_url = entry.get("target", {}).get("application_url", "")
    amount = entry.get("amount", {})
    salary = ""
    if isinstance(amount, dict):
        val = amount.get("value", 0)
        currency = amount.get("currency", "USD")
        if val:
            salary = f"${val:,}" if currency == "USD" else f"{currency} {val:,}"

    header = f"# Cover Letter: {name}\n\n"
    header += f"**Role:** {name}\n"
    if app_url:
        header += f"**Apply:** {app_url}\n"
    if salary:
        header += f"**Salary:** {salary}\n"
    header += "\n---\n\n"

    variant_dir = VARIANTS_DIR / "cover-letters"
    variant_dir.mkdir(parents=True, exist_ok=True)
    variant_path = variant_dir / f"{entry_id}-alchemized.md"
    variant_path.write_text(header + cl_text.strip() + "\n")
    return variant_path


def write_greenhouse_answers(entry_id: str, answers_text: str) -> Path | None:
    """Parse YAML from answers text and write to .greenhouse-answers/{id}.yaml."""
    # Extract YAML block if wrapped in ```yaml ... ```
    yaml_match = re.search(r"```yaml\s*\n(.*?)```", answers_text, re.DOTALL)
    if yaml_match:
        yaml_text = yaml_match.group(1)
    else:
        # Try to parse the whole thing as YAML
        yaml_text = answers_text

    # Also handle multiple ```yaml blocks
    all_blocks = re.findall(r"```yaml\s*\n(.*?)```", answers_text, re.DOTALL)
    if all_blocks:
        yaml_text = "\n".join(all_blocks)

    try:
        answers = yaml.safe_load(yaml_text)
        if not isinstance(answers, dict):
            print(f"  Warning: Could not parse GREENHOUSE_ANSWERS as YAML dict")
            return None
    except yaml.YAMLError as e:
        print(f"  Warning: YAML parse error in GREENHOUSE_ANSWERS: {e}")
        # Write raw text as fallback
        ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
        answer_path = ANSWERS_DIR / f"{entry_id}.yaml"
        answer_path.write_text(f"# Auto-generated — review and fix YAML\n{yaml_text}\n")
        return answer_path

    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    answer_path = ANSWERS_DIR / f"{entry_id}.yaml"

    lines = [f"# Generated by alchemize.py for {entry_id}", ""]
    for key, value in answers.items():
        sv = str(value).strip()
        if "\n" in sv:
            lines.append(f"{key}: |")
            for vline in sv.split("\n"):
                lines.append(f"  {vline}")
        else:
            # Quote strings that might be ambiguous YAML
            if any(c in sv for c in ":#{}[]|>&"):
                lines.append(f'{key}: "{sv}"')
            else:
                lines.append(f"{key}: {sv}")
        lines.append("")

    answer_path.write_text("\n".join(lines))
    return answer_path


def update_pipeline_yaml(
    entry_id: str, variant_ref: str | None, framing: str | None
) -> bool:
    """Update pipeline YAML with new variant reference and framing."""
    filepath, data = load_entry_by_id(entry_id)
    if not filepath or not data:
        print(f"  Error: Could not load pipeline entry for {entry_id}")
        return False

    changed = False

    if variant_ref:
        submission = data.get("submission", {})
        if not isinstance(submission, dict):
            submission = {}
        variant_ids = submission.get("variant_ids", {})
        if not isinstance(variant_ids, dict):
            variant_ids = {}
        variant_ids["cover_letter"] = variant_ref
        submission["variant_ids"] = variant_ids
        data["submission"] = submission
        changed = True

    if framing:
        fit = data.get("fit", {})
        if not isinstance(fit, dict):
            fit = {}
        fit["framing"] = framing
        data["fit"] = fit
        changed = True

    data["last_touched"] = str(date.today())
    changed = True

    if changed:
        # Remove internal metadata keys before writing
        clean_data = {k: v for k, v in data.items() if not k.startswith("_")}
        filepath.write_text(yaml.dump(clean_data, default_flow_style=False, allow_unicode=True, sort_keys=False))
        return True
    return False


def phase_integrate(entry_id: str, work_dir: Path) -> bool:
    """Parse output.md and write results to pipeline files."""
    output_path = work_dir / "output.md"
    if not output_path.exists():
        print(f"  Error: {output_path} not found")
        print(f"  Generate output and save it to {output_path}")
        return False

    output_text = output_path.read_text()
    if not output_text.strip():
        print(f"  Error: {output_path} is empty")
        return False

    sections = parse_output(output_text)
    if not sections:
        print(f"  Error: No ### sections found in {output_path}")
        print("  Expected: ### COVER_LETTER, ### GREENHOUSE_ANSWERS, ### IDENTITY_FRAMING")
        return False

    filepath, entry = load_entry_by_id(entry_id)
    if not entry:
        print(f"  Error: Pipeline entry not found for {entry_id}")
        return False

    log_lines = [f"Integration log for {entry_id}", f"Date: {date.today()}", ""]
    variant_ref = None

    # Cover letter
    cl_text = sections.get("COVER_LETTER")
    if cl_text:
        cl_path = write_cover_letter_variant(entry_id, entry, cl_text)
        variant_ref = f"cover-letters/{entry_id}-alchemized"
        print(f"  Wrote cover letter: {cl_path}")
        log_lines.append(f"Cover letter: {cl_path}")
    else:
        print("  No COVER_LETTER section found in output")

    # Greenhouse answers
    answers_text = sections.get("GREENHOUSE_ANSWERS")
    if answers_text:
        answer_path = write_greenhouse_answers(entry_id, answers_text)
        if answer_path:
            print(f"  Wrote answers: {answer_path}")
            log_lines.append(f"Answers: {answer_path}")
    else:
        print("  No GREENHOUSE_ANSWERS section found in output (may not be needed)")

    # Identity framing
    framing = sections.get("IDENTITY_FRAMING")
    if framing:
        # Clean up — remove markdown formatting
        framing = framing.strip().strip('"').strip("'")
        # Take first 1-2 sentences only
        sentences = re.split(r"(?<=[.!?])\s+", framing)
        framing = " ".join(sentences[:2]).strip()
        log_lines.append(f"Framing: {framing}")

    # Update pipeline YAML
    if variant_ref or framing:
        ok = update_pipeline_yaml(entry_id, variant_ref, framing)
        if ok:
            print(f"  Updated pipeline YAML for {entry_id}")
            log_lines.append("Pipeline YAML updated")
        else:
            print(f"  Warning: Could not update pipeline YAML")

    # Write integration log
    log_path = work_dir / "integration.log"
    log_path.write_text("\n".join(log_lines) + "\n")
    print(f"  Integration log: {log_path}")

    return True


# ---------------------------------------------------------------------------
# Phase 6: SUBMIT
# ---------------------------------------------------------------------------


def phase_submit(entry_id: str, do_submit: bool) -> bool:
    """Shell out to greenhouse_submit.py."""
    script = Path(__file__).resolve().parent / "greenhouse_submit.py"
    cmd = [sys.executable, str(script), "--target", entry_id]
    if do_submit:
        cmd.append("--submit")

    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def process_entry(
    entry: dict,
    phase: str | None,
    integrate: bool,
    submit: bool,
    force: bool,
    no_web: bool,
) -> bool:
    """Run the alchemize pipeline for a single entry."""
    entry_id = entry.get("id", "?")
    name = entry.get("name", entry_id)

    work_dir = WORK_DIR / entry_id
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"ALCHEMIZE: {name}")
    print(f"{'=' * 60}")

    # Integration mode
    if integrate:
        print("\nPhase 5: INTEGRATE")
        return phase_integrate(entry_id, work_dir)

    # Submit mode
    if submit:
        print("\nPhase 6: SUBMIT")
        return phase_submit(entry_id, do_submit=True)

    # Phase 1: INTAKE
    print("\nPhase 1: INTAKE")
    job_data = phase_intake(entry, no_web=no_web)
    if phase == "intake":
        print(f"\n  Stopped after intake phase.")
        return job_data is not None

    # Phase 2: RESEARCH
    print("\nPhase 2: RESEARCH")
    research_content = phase_research(entry, job_data, no_web=no_web)
    research_path = work_dir / "research.md"
    if force or not research_path.exists():
        research_path.write_text(research_content)
        print(f"  Wrote: {research_path}")
    else:
        print(f"  {research_path} exists (use --force to overwrite)")
        research_content = research_path.read_text()

    if phase == "research":
        print(f"\n  Stopped after research phase.")
        print(f"  Review: {research_path}")
        return True

    # Phase 3: MAP
    print("\nPhase 3: MAP")
    profile = load_profile(entry_id)
    mapping_content = phase_map(entry, research_content, profile)
    mapping_path = work_dir / "mapping.md"
    if force or not mapping_path.exists():
        mapping_path.write_text(mapping_content)
        print(f"  Wrote: {mapping_path}")
    else:
        print(f"  {mapping_path} exists (use --force to overwrite)")
        mapping_content = mapping_path.read_text()

    if phase == "map":
        print(f"\n  Stopped after map phase.")
        print(f"  Review: {mapping_path}")
        return True

    # Phase 4: SYNTHESIZE
    print("\nPhase 4: SYNTHESIZE")
    existing_cl = resolve_cover_letter(entry)
    prompt_content = phase_synthesize(entry, research_content, mapping_content, existing_cl)
    prompt_path = work_dir / "prompt.md"
    if force or not prompt_path.exists():
        prompt_path.write_text(prompt_content)
        print(f"  Wrote: {prompt_path}")
    else:
        print(f"  {prompt_path} exists (use --force to overwrite)")

    print(f"\n  Prompt ready: {prompt_path}")
    print(f"  Run through Claude, save output to: {work_dir}/output.md")
    print(f"  Then: python scripts/alchemize.py --target {entry_id} --integrate")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Full-pipeline application orchestrator"
    )
    parser.add_argument("--target", help="Target entry ID")
    parser.add_argument("--batch", action="store_true",
                        help="Run phases 1-4 for all Greenhouse entries")
    parser.add_argument("--batch-all", action="store_true",
                        help="Run phases 1-4 for all entries (any portal type)")
    parser.add_argument("--portal",
                        help="Filter batch by portal type (e.g. greenhouse, custom)")
    parser.add_argument("--phase", choices=PHASES,
                        help="Stop after this phase (default: synthesize)")
    parser.add_argument("--integrate", action="store_true",
                        help="Run phase 5: integrate output.md back into pipeline")
    parser.add_argument("--submit", action="store_true",
                        help="Run phase 6: submit via greenhouse_submit.py")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing work files")
    parser.add_argument("--no-web", action="store_true",
                        help="Skip web fetching (use only existing files + API)")
    args = parser.parse_args()

    if not args.target and not args.batch and not args.batch_all:
        parser.error("Specify --target <id>, --batch, or --batch-all")

    if (args.batch or args.batch_all) and (args.integrate or args.submit):
        parser.error("--integrate and --submit cannot be used with --batch/--batch-all")

    # Resolve entries
    if args.batch or args.batch_all:
        entries = load_entries(dirs=[PIPELINE_DIR_ACTIVE])
        # Filter to actionable statuses
        entries = [
            e for e in entries
            if e.get("status") in ACTIONABLE_STATUSES
        ]
        # Portal filter
        if args.batch and not args.batch_all:
            # Legacy --batch: Greenhouse only
            portal_filter = args.portal or "greenhouse"
        elif args.portal:
            portal_filter = args.portal
        else:
            portal_filter = None

        if portal_filter:
            entries = [
                e for e in entries
                if e.get("target", {}).get("portal") == portal_filter
            ]

        if not entries:
            portal_msg = f" (portal={portal_filter})" if portal_filter else ""
            print(f"No actionable entries found in active pipeline{portal_msg}.")
            sys.exit(1)
        print(f"Found {len(entries)} entries:")
        for e in entries:
            portal = e.get("target", {}).get("portal", "?")
            print(f"  - {e.get('id')}: {e.get('name')} [{portal}]")
    else:
        _, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Error: No pipeline entry found for '{args.target}'", file=sys.stderr)
            sys.exit(1)
        entries = [entry]

    # Process
    results = []
    for entry in entries:
        ok = process_entry(
            entry,
            phase=args.phase,
            integrate=args.integrate,
            submit=args.submit,
            force=args.force,
            no_web=args.no_web,
        )
        results.append((entry.get("id"), ok))

    # Summary for batch
    if len(results) > 1:
        print(f"\n{'=' * 60}")
        print("BATCH SUMMARY:")
        for eid, ok in results:
            status = "OK" if ok else "FAILED"
            print(f"  {eid}: {status}")
        failed = sum(1 for _, ok in results if not ok)
        if failed:
            sys.exit(1)


if __name__ == "__main__":
    main()
