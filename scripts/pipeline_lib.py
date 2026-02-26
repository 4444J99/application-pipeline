"""Shared utilities for the application pipeline scripts.

Consolidates load_entries, parse_date, format_amount, get_effort, get_score,
get_deadline, and common constants that were previously duplicated across
pipeline_status.py, standup.py, daily_batch.py, conversion_report.py, and score.py.
"""

from datetime import date, datetime
from pathlib import Path

import json
import re

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

PIPELINE_DIR_ACTIVE = REPO_ROOT / "pipeline" / "active"
PIPELINE_DIR_SUBMITTED = REPO_ROOT / "pipeline" / "submitted"
PIPELINE_DIR_CLOSED = REPO_ROOT / "pipeline" / "closed"

ALL_PIPELINE_DIRS = [PIPELINE_DIR_ACTIVE, PIPELINE_DIR_SUBMITTED, PIPELINE_DIR_CLOSED]

BLOCKS_DIR = REPO_ROOT / "blocks"
VARIANTS_DIR = REPO_ROOT / "variants"
PROFILES_DIR = REPO_ROOT / "targets" / "profiles"
DRAFTS_DIR = REPO_ROOT / "pipeline" / "drafts"
SIGNALS_DIR = REPO_ROOT / "signals"
SUBMISSIONS_DIR = REPO_ROOT / "pipeline" / "submissions"
LEGACY_DIR = REPO_ROOT / "scripts" / "legacy-submission"
MATERIALS_DIR = REPO_ROOT / "materials"

# Maps entry IDs to profile file IDs where naming conventions differ.
PROFILE_ID_MAP = {
    "creative-capital-2027": "creative-capital",
    "doris-duke-amt": "doris-duke",
    "eyebeam-plurality": "eyebeam",
    "fire-island-residency": "fire-island",
    "google-creative-lab-five": "google-cl5",
    "google-creative-fellowship": "google-fellowship",
    "headlands-center": "headlands",
    "huggingface-dev-advocate": "huggingface",
    "mit-tr-wired-aeon": "mit-tech-review",
    "noema-magazine": "noema",
    "openai-se-evals": "openai-evals",
    "prix-ars-digital-humanity": "prix-ars",
    "prix-ars-electronica": "prix-ars",
    "rauschenberg-cycle-36": "rauschenberg-emergency",
}

# Maps legacy script filenames to entry IDs where naming conventions differ.
LEGACY_ID_MAP = {
    "cc-creative-capital": "creative-capital-2027",
    "doris-duke": "doris-duke-amt",
    "eyebeam": "eyebeam-plurality",
    "fire-island": "fire-island-residency",
    "google-cl5": "google-creative-lab-five",
    "google-fellowship": "google-creative-fellowship",
    "headlands": "headlands-center",
    "prix-ars-starts": "prix-ars-electronica",
    "rauschenberg-emergency": "rauschenberg-cycle-36",
}

VALID_TRACKS = {"grant", "residency", "job", "fellowship", "writing", "emergency", "prize", "program", "consulting"}
VALID_STATUSES = {"research", "qualified", "drafting", "staged", "deferred", "submitted", "acknowledged", "interview", "outcome"}
ACTIONABLE_STATUSES = {"research", "qualified", "drafting", "staged"}

STATUS_ORDER = [
    "research", "qualified", "drafting", "staged", "deferred",
    "submitted", "acknowledged", "interview", "outcome",
]

EFFORT_MINUTES = {
    "quick": 30,
    "standard": 90,
    "deep": 270,
    "complex": 720,
}

# Valid status transitions: each status maps to the set of statuses it can reach.
# Single source of truth — imported by validate.py and advance.py.
VALID_TRANSITIONS = {
    "research": {"qualified", "withdrawn"},
    "qualified": {"drafting", "staged", "deferred", "withdrawn"},
    "drafting": {"staged", "qualified", "deferred", "withdrawn"},
    "staged": {"submitted", "drafting", "deferred", "withdrawn"},
    "deferred": {"staged", "qualified", "withdrawn"},
    "submitted": {"acknowledged", "interview", "outcome", "withdrawn"},
    "acknowledged": {"interview", "outcome", "withdrawn"},
    "interview": {"outcome", "withdrawn"},
    "outcome": set(),  # terminal
}


# --- Safe YAML field mutation helpers ---


def update_yaml_field(
    content: str,
    field: str,
    new_value: str,
    *,
    nested: bool = False,
) -> str:
    """Replace a scalar YAML field's value in raw text with verification.

    Uses targeted regex to preserve file formatting (comments, key order,
    quoting style) while validating the result is still parseable YAML.

    Args:
        content: Raw YAML text.
        field: Field name (e.g. "status", "score", "submitted").
        new_value: Replacement value string (caller handles quoting).
        nested: If True, field is expected to be indented under a parent key.

    Returns:
        Modified YAML text.

    Raises:
        ValueError: If the field is not found or the result is invalid YAML.
    """
    if nested:
        pattern = rf'^([ \t]+{re.escape(field)}:[ \t]+).*$'
    else:
        pattern = rf'^({re.escape(field)}:[ \t]+).*$'

    if not re.search(pattern, content, re.MULTILINE):
        raise ValueError(f"Field '{field}' not found in YAML (nested={nested})")

    new_content = re.sub(
        pattern,
        rf'\g<1>{new_value}',
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Verify the result is still valid YAML
    try:
        yaml.safe_load(new_content)
    except yaml.YAMLError as e:
        raise ValueError(
            f"YAML became invalid after updating '{field}' to '{new_value}': {e}"
        )

    return new_content


def ensure_yaml_field(content: str, field: str, value: str) -> str:
    """Update a top-level field if it exists, or append it if missing."""
    if re.search(rf'^{re.escape(field)}:', content, re.MULTILINE):
        return update_yaml_field(content, field, value, nested=False)
    return content.rstrip() + f'\n{field}: {value}\n'


def update_last_touched(content: str) -> str:
    """Set last_touched to today's ISO date string."""
    today_str = date.today().isoformat()
    return ensure_yaml_field(content, "last_touched", f'"{today_str}"')


def load_entries(
    dirs: list[Path] | None = None,
    include_filepath: bool = False,
) -> list[dict]:
    """Load pipeline YAML entries from given directories.

    Args:
        dirs: Directories to scan. Defaults to all pipeline dirs.
        include_filepath: If True, adds _filepath key to each entry.

    Returns:
        List of parsed YAML dicts with _dir and _file metadata.
    """
    entries = []
    for pipeline_dir in (dirs or ALL_PIPELINE_DIRS):
        if not pipeline_dir.exists():
            continue
        for filepath in sorted(pipeline_dir.glob("*.yaml")):
            if filepath.name.startswith("_"):
                continue
            with open(filepath) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                data["_dir"] = pipeline_dir.name
                data["_file"] = filepath.name
                if include_filepath:
                    data["_filepath"] = filepath
                entries.append(data)
    return entries


def load_entry_by_id(entry_id: str) -> tuple[Path | None, dict | None]:
    """Load a single pipeline entry by ID. Returns (filepath, data) or (None, None)."""
    for pipeline_dir in ALL_PIPELINE_DIRS:
        filepath = pipeline_dir / f"{entry_id}.yaml"
        if filepath.exists():
            with open(filepath) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                return filepath, data
    return None, None


def parse_date(date_str) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD) into a date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_datetime(date_str) -> datetime | None:
    """Parse an ISO date string into a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), "%Y-%m-%d")
    except ValueError:
        return None


def format_amount(amount: dict | None) -> str:
    """Format an amount dict for display."""
    if not amount or not isinstance(amount, dict):
        return "—"
    value = amount.get("value", 0)
    currency = amount.get("currency", "USD")
    if value == 0:
        atype = amount.get("type", "")
        if atype == "in_kind":
            return "In-kind"
        if atype == "variable":
            return "Variable"
        return "—"
    if currency == "EUR":
        return f"EUR {value:,}"
    return f"${value:,}"


def get_effort(entry: dict) -> str:
    """Get effort level from submission, defaulting to 'standard'."""
    sub = entry.get("submission", {})
    if isinstance(sub, dict):
        return sub.get("effort_level", "standard") or "standard"
    return "standard"


def get_score(entry: dict) -> float:
    """Get composite fit score."""
    fit = entry.get("fit", {})
    if isinstance(fit, dict):
        return float(fit.get("score", 0))
    return 0.0


def get_deadline(entry: dict) -> tuple[date | None, str]:
    """Return (deadline_date, deadline_type)."""
    dl = entry.get("deadline", {})
    if not isinstance(dl, dict):
        return None, "unknown"
    return parse_date(dl.get("date")), dl.get("type", "unknown")


def days_until(d: date) -> int:
    """Days from today until the given date (negative = past)."""
    return (d - date.today()).days


def load_profile(target_id: str) -> dict | None:
    """Load a target profile JSON by ID, falling back to PROFILE_ID_MAP."""
    filepath = PROFILES_DIR / f"{target_id}.json"
    if not filepath.exists():
        mapped = PROFILE_ID_MAP.get(target_id)
        if mapped:
            filepath = PROFILES_DIR / f"{mapped}.json"
    if filepath.exists():
        return json.loads(filepath.read_text())
    return None


def _build_reverse_legacy_map() -> dict[str, str]:
    """Build entry_id → legacy_filename map from LEGACY_ID_MAP."""
    reverse = {}
    for legacy_name, entry_id in LEGACY_ID_MAP.items():
        reverse[entry_id] = legacy_name
    return reverse


_REVERSE_LEGACY_MAP = _build_reverse_legacy_map()


def load_legacy_script(target_id: str) -> dict | None:
    """Load and parse a legacy submission script into field sections.

    Returns a dict mapping canonical field names to paste-ready content,
    or None if no legacy script exists.
    """
    # Try direct match first, then reverse legacy map
    filepath = LEGACY_DIR / f"{target_id}.md"
    if not filepath.exists():
        legacy_name = _REVERSE_LEGACY_MAP.get(target_id)
        if legacy_name:
            filepath = LEGACY_DIR / f"{legacy_name}.md"
    if not filepath.exists():
        return None

    return _parse_legacy_markdown(filepath.read_text())


# Map legacy section headers to canonical field names
_LEGACY_SECTION_MAP = {
    "artist statement": "artist_statement",
    "artistic statement": "artist_statement",
    "bio": "bio",
    "bio / cv summary": "bio",
    "bio/cv summary": "bio",
    "cv summary": "bio",
    "project description": "project_description",
    "project description / why this opportunity": "project_description",
    "project summary / abstract": "project_description",
    "project summary": "project_description",
    "project title": "project_title",
    "project narrative": "project_description",
    "proposal narrative": "project_description",
    "cover letter": "cover_letter",
    "work samples": "work_samples",
    "work samples — descriptions": "work_samples",
    "links to submit": "links",
    "performing arts connection statement": "performing_arts_connection",
    "financial hardship statement": "financial_hardship",
    "documentation of need": "documentation_of_need",
    "budget": "budget",
    "budget outline": "budget",
    "methodology": "methodology",
    "technical plan": "technical_plan",
}


def _parse_legacy_markdown(text: str) -> dict:
    """Parse a legacy submission script markdown into sections.

    Extracts content from between --- delimiters within each ## section.
    Falls back to raw section content if no delimiters found.
    """
    sections = {}
    current_header = None
    current_lines = []

    for line in text.split("\n"):
        if line.startswith("## "):
            # Save previous section
            if current_header is not None:
                content = _extract_section_content("\n".join(current_lines))
                if content:
                    sections[current_header] = content

            header_text = line[3:].strip()
            # Map to canonical name
            header_lower = header_text.lower()
            current_header = _LEGACY_SECTION_MAP.get(header_lower, header_lower)
            current_lines = []
        elif current_header is not None:
            current_lines.append(line)

    # Save last section
    if current_header is not None:
        content = _extract_section_content("\n".join(current_lines))
        if content:
            sections[current_header] = content

    # Skip non-content sections
    for skip in ("pre-flight (2 minutes)", "pre-flight (3 minutes)",
                 "pre-flight (5 minutes)", "post-submission checklist",
                 "if something goes wrong", "fit assessment — 7/10",
                 "fit assessment"):
        sections.pop(skip, None)

    return sections


def _extract_section_content(text: str) -> str | None:
    """Extract paste-ready content from between --- delimiters.

    If delimiters found, extracts content between them (skipping metadata).
    If no delimiters, returns the full text stripped of metadata lines.
    """
    parts = text.split("---")

    # If we have delimiter-separated parts, look for the substantive one
    # Skip the first part (usually metadata like word counts) and empty parts
    if len(parts) >= 3:
        # Try parts between delimiters (index 1, 3, 5...)
        for i in range(1, len(parts)):
            stripped = parts[i].strip()
            if not stripped:
                continue
            lines = stripped.split("\n")
            non_meta = [
                l for l in lines
                if l.strip()
                and not l.strip().startswith("**")
                and not l.strip().startswith(">")
                and not l.strip().startswith("- [ ]")
                and not l.strip().startswith("Copy")
            ]
            if non_meta:
                result = "\n".join(non_meta).strip()
                if result:
                    return result

    # Fallback: no delimiters or nothing found between them
    lines = text.strip().split("\n")
    non_meta = [
        l for l in lines
        if l.strip()
        and not l.strip().startswith("**")
        and not l.strip().startswith(">")
        and not l.strip().startswith("- [ ]")
        and not l.strip().startswith("Copy")
        and l.strip() != "---"
    ]
    if non_meta:
        result = "\n".join(non_meta).strip()
        if len(result) > 10:
            return result

    return None


# --- Block/variant loading (shared by compose.py, submit.py, draft.py) ---


def load_block(block_path: str) -> str | None:
    """Load a block file by its reference path relative to BLOCKS_DIR."""
    full_path = BLOCKS_DIR / block_path
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if full_path.exists():
        return full_path.read_text().strip()
    return None


def load_variant(variant_path: str) -> str | None:
    """Load a variant file by its reference path relative to VARIANTS_DIR."""
    full_path = VARIANTS_DIR / variant_path
    if not full_path.suffix:
        full_path = full_path.with_suffix(".md")
    if full_path.exists():
        return full_path.read_text().strip()
    return None


# --- Text utilities (shared by compose.py, draft.py) ---


def strip_markdown(text: str) -> str:
    """Strip markdown formatting for plain text output."""
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def count_words(text: str) -> int:
    """Count words in a text string."""
    return len(text.split())


def count_chars(text: str) -> int:
    """Count characters (excluding leading/trailing whitespace)."""
    return len(text.strip())


# --- Portal URL detection ---


PORTAL_URL_PATTERNS = [
    (re.compile(r'(?:job-)?boards(?:-api)?\.greenhouse\.io'), 'greenhouse'),
    (re.compile(r'jobs\.(?:eu\.)?lever\.co'), 'lever'),
    (re.compile(r'jobs\.ashbyhq\.com'), 'ashby'),
    (re.compile(r'apply\.workable\.com'), 'workable'),
    (re.compile(r'jobs\.smartrecruiters\.com'), 'smartrecruiters'),
    (re.compile(r'\.submittable\.com'), 'submittable'),
    (re.compile(r'slideroom\.com'), 'slideroom'),
]


def detect_portal(url: str) -> str | None:
    """Detect the portal type from an application URL.

    Returns the portal name string or None if no pattern matches.
    """
    if not url:
        return None
    for pattern, portal in PORTAL_URL_PATTERNS:
        if pattern.search(url):
            return portal
    return None
