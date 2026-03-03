#!/usr/bin/env python3
"""Shared base module for ATS portal submitters (Greenhouse, Ashby, Lever).

Extracts common patterns duplicated across greenhouse_submit.py, ashby_submit.py,
and lever_submit.py: auto-fill regex patterns, standard field sets, config loading,
and common argparse setup.
"""

import argparse
import re

from pipeline_lib import load_submit_config

# ---------------------------------------------------------------------------
# Auto-fill patterns (compiled once, shared by all portals)
# ---------------------------------------------------------------------------

# Label patterns matched against portal question text to auto-fill answers
# from the user's submit config. Each tuple is (compiled_regex, config_key).
AUTO_FILL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"website|portfolio|github|personal.*url", re.I), "portfolio_url"),
    (re.compile(r"linkedin", re.I), "linkedin"),
    (re.compile(r"pronounc|phonetic", re.I), "name_pronunciation"),
    (re.compile(r"pronoun", re.I), "pronouns"),
    (re.compile(r"address|city|location|plan on working|where.*located|where.*based", re.I), "location"),
]


# ---------------------------------------------------------------------------
# Standard field names per portal
# ---------------------------------------------------------------------------

# Greenhouse standard fields (name split into first/last, resume/cover_letter variants)
GREENHOUSE_STANDARD_FIELDS = {
    "first_name", "last_name", "email", "phone",
    "resume", "resume_text", "cover_letter", "cover_letter_text",
}

# Ashby standard fields (system field paths)
ASHBY_STANDARD_FIELDS = {
    "_systemfield_name", "_systemfield_email", "_systemfield_phone",
}

# Lever standard fields
LEVER_STANDARD_FIELDS = {
    "name", "email", "phone", "org", "resume", "urls",
}

# Unified superset of all standard field names across portals
STANDARD_FIELD_NAMES = GREENHOUSE_STANDARD_FIELDS | ASHBY_STANDARD_FIELDS | LEVER_STANDARD_FIELDS


# ---------------------------------------------------------------------------
# Auto-fill answer matching
# ---------------------------------------------------------------------------


def auto_fill_answer(label: str, config: dict, portfolio_url: str = "") -> str | None:
    """Match a question label against AUTO_FILL_PATTERNS and return the config value.

    Args:
        label: The question text/label to match against patterns.
        config: The submit config dict (from load_submit_config).
        portfolio_url: Optional portfolio URL from the entry's submission field.

    Returns:
        The matching config value as a string, or None if no pattern matches
        or the matched value is empty.
    """
    source_map = {
        "portfolio_url": portfolio_url,
        "linkedin": config.get("linkedin", ""),
        "name_pronunciation": config.get("name_pronunciation", ""),
        "pronouns": config.get("pronouns", ""),
        "location": config.get("location", ""),
    }

    for pattern, source_key in AUTO_FILL_PATTERNS:
        if pattern.search(label):
            value = source_map.get(source_key, "")
            if value:
                return value
            return None

    return None


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_config() -> dict:
    """Load personal info from .submit-config.yaml."""
    return load_submit_config(strict=True)


# ---------------------------------------------------------------------------
# Common argparse
# ---------------------------------------------------------------------------


def build_common_argparse(portal_name: str) -> argparse.ArgumentParser:
    """Build a common argument parser with standard ATS submitter flags.

    Args:
        portal_name: Display name of the portal (e.g. "Greenhouse", "Lever", "Ashby").

    Returns:
        An ArgumentParser with --target, --batch, --submit, --init-answers,
        --check-answers, and --force flags.
    """
    parser = argparse.ArgumentParser(
        description=f"Submit applications to {portal_name} API"
    )
    parser.add_argument("--target", help="Target entry ID")
    parser.add_argument("--batch", action="store_true",
                        help=f"Process all {portal_name} entries in active pipeline")
    parser.add_argument("--submit", action="store_true",
                        help=f"Actually POST to {portal_name} (default is dry-run)")
    parser.add_argument("--init-answers", action="store_true",
                        help="Generate answer template YAML for custom questions")
    parser.add_argument("--check-answers", action="store_true",
                        help="Validate that all required questions have answers")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing answer files (with --init-answers)")
    return parser
