"""Shared utilities for the application pipeline scripts.

Consolidates load_entries, parse_date, format_amount, get_effort, get_score,
get_deadline, and common constants that were previously duplicated across
pipeline_status.py, standup.py, daily_batch.py, conversion_report.py, and score.py.
"""

from datetime import date, datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

PIPELINE_DIR_ACTIVE = REPO_ROOT / "pipeline" / "active"
PIPELINE_DIR_SUBMITTED = REPO_ROOT / "pipeline" / "submitted"
PIPELINE_DIR_CLOSED = REPO_ROOT / "pipeline" / "closed"

ALL_PIPELINE_DIRS = [PIPELINE_DIR_ACTIVE, PIPELINE_DIR_SUBMITTED, PIPELINE_DIR_CLOSED]

BLOCKS_DIR = REPO_ROOT / "blocks"
VARIANTS_DIR = REPO_ROOT / "variants"
SIGNALS_DIR = REPO_ROOT / "signals"
SUBMISSIONS_DIR = REPO_ROOT / "pipeline" / "submissions"

VALID_TRACKS = {"grant", "residency", "job", "fellowship", "writing", "emergency", "prize", "program", "consulting"}
VALID_STATUSES = {"research", "qualified", "drafting", "staged", "submitted", "acknowledged", "interview", "outcome"}
ACTIONABLE_STATUSES = {"research", "qualified", "drafting", "staged"}

STATUS_ORDER = [
    "research", "qualified", "drafting", "staged",
    "submitted", "acknowledged", "interview", "outcome",
]

EFFORT_MINUTES = {
    "quick": 30,
    "standard": 90,
    "deep": 270,
    "complex": 720,
}


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
