#!/usr/bin/env python3
"""Shared base module for ATS portal submitters (Greenhouse, Ashby, Lever).

Extracts common patterns duplicated across greenhouse_submit.py, ashby_submit.py,
and lever_submit.py: auto-fill regex patterns, dynamic question matching,
option resolution, config loading, and common argparse setup.
"""

import argparse
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml
from pipeline_lib import load_submit_config

# ---------------------------------------------------------------------------
# Auto-fill patterns (compiled once, shared by all portals)
# ---------------------------------------------------------------------------

# Label patterns matched against portal question text to auto-fill answers
# from the user's submit config top-level fields. Each tuple is
# (compiled_regex, config_key).
AUTO_FILL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"website|portfolio|github|personal.*url", re.I), "portfolio_url"),
    (re.compile(r"linkedin", re.I), "linkedin"),
    (re.compile(r"pronounc|phonetic", re.I), "name_pronunciation"),
    (re.compile(r"pronoun", re.I), "pronouns"),
    (re.compile(r"address|city|location|plan on working|where.*located|where.*based", re.I), "location"),
]

# Label patterns for semantic default_answers mapping from .submit-config.yaml.
# Keys map into config["default_answers"][<key>].
DEFAULT_ANSWER_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"authorized.*work|work.*authorization|legally.*work|eligible.*work", re.I), "work_authorization"),
    (re.compile(r"visa|sponsor", re.I), "visa_sponsorship"),
    (re.compile(r"salary|compensation|pay.*expect", re.I), "salary_expectation"),
    (re.compile(r"start.*date|when.*start|earliest.*start|available.*start", re.I), "start_date"),
    (re.compile(r"how.*hear|how.*find|where.*hear|how.*learn.*about", re.I), "how_did_you_hear"),
    (re.compile(r"relocat", re.I), "willing_to_relocate"),
    (re.compile(r"\bgender\b", re.I), "gender"),
    (re.compile(r"race|ethnic", re.I), "race_ethnicity"),
    (re.compile(r"veteran|military", re.I), "veteran_status"),
    (re.compile(r"disabilit", re.I), "disability_status"),
]

_DYNAMIC_KEY_PREFIXES = ("label::", "question::", "title::", "text::", "prompt::")


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


def _is_effective_value(value: Any) -> bool:
    """Return True if value is usable as an answer (not empty / placeholder)."""
    if value is None:
        return False
    sval = str(value).strip()
    if not sval:
        return False
    if sval.upper() in {"FILL IN", "FILL_IN", "TODO"}:
        return False
    return True


def normalize_text(value: str) -> str:
    """Normalize question/answer keys for fuzzy matching across role variants."""
    lowered = value.lower().strip()
    alnum = re.sub(r"[^a-z0-9]+", " ", lowered)
    tokens = alnum.split()

    # Merge adjacent single-letter tokens ("u s" -> "us") for acronym stability.
    merged: list[str] = []
    buffer = ""
    for token in tokens:
        if len(token) == 1:
            buffer += token
            continue
        if buffer:
            merged.append(buffer)
            buffer = ""
        merged.append(token)
    if buffer:
        merged.append(buffer)

    return " ".join(merged)


def strip_dynamic_key_prefix(value: str) -> str:
    """Strip supported dynamic key prefixes, if present."""
    lowered = value.lower()
    for prefix in _DYNAMIC_KEY_PREFIXES:
        if lowered.startswith(prefix):
            return value[len(prefix):].strip()
    return value.strip()


def build_normalized_answer_index(answers: Mapping[str, Any]) -> dict[str, Any]:
    """Build normalized answer-key index once for dynamic label matching."""
    index: dict[str, Any] = {}
    for raw_key, raw_value in answers.items():
        if not _is_effective_value(raw_value):
            continue
        key_text = strip_dynamic_key_prefix(str(raw_key))
        normalized = normalize_text(key_text)
        if normalized and normalized not in index:
            index[normalized] = raw_value
    return index


def find_dynamic_answer(
    answers: Mapping[str, Any] | None,
    *,
    field_key: str,
    label: str,
    aliases: Sequence[str] | None = None,
    normalized_index: Mapping[str, Any] | None = None,
) -> Any | None:
    """Resolve an answer by field key, label, or normalized dynamic aliases.

    Args:
        answers: Raw answer mapping loaded from YAML.
        field_key: Current field identifier from live form schema.
        label: Human-visible question label/title/text from live form schema.
        aliases: Optional extra lookup aliases for portal-specific variants.
        normalized_index: Optional pre-built index from build_normalized_answer_index.

    Returns:
        Matched answer value, or None if no usable value matches.
    """
    if not answers:
        return None

    dynamic_aliases = list(aliases or [])

    # 1) Strong exact matches by current live field key / label.
    exact_keys = [field_key, label]
    exact_keys.extend(dynamic_aliases)
    for key in exact_keys:
        if key in answers and _is_effective_value(answers[key]):
            return answers[key]

    # 2) Explicit prefixed forms (e.g. label::Question text).
    prefixed_candidates = [label]
    prefixed_candidates.extend(dynamic_aliases)
    for text in prefixed_candidates:
        if not text:
            continue
        for prefix in _DYNAMIC_KEY_PREFIXES:
            prefixed_key = f"{prefix}{text}"
            if prefixed_key in answers and _is_effective_value(answers[prefixed_key]):
                return answers[prefixed_key]

    # 3) Normalized label matching handles punctuation/case/churn.
    index = normalized_index or build_normalized_answer_index(answers)
    normalized_candidates = [label]
    normalized_candidates.extend(dynamic_aliases)
    normalized_candidates.append(field_key)

    for candidate in normalized_candidates:
        if not candidate:
            continue
        normalized = normalize_text(strip_dynamic_key_prefix(str(candidate)))
        if not normalized:
            continue
        if normalized in index:
            return index[normalized]

    return None


def match_default_answer(label: str, config: Mapping[str, Any]) -> str | None:
    """Resolve semantic answer from config.default_answers using label regexes."""
    defaults = config.get("default_answers", {})
    if not isinstance(defaults, Mapping):
        return None

    for pattern, key in DEFAULT_ANSWER_PATTERNS:
        if pattern.search(label):
            value = defaults.get(key)
            if _is_effective_value(value):
                return str(value)
            return None
    return None


def auto_fill_answer(label: str, config: Mapping[str, Any], portfolio_url: str = "") -> str | None:
    """Resolve an auto-fill answer from config fields or semantic defaults.

    Search order:
      1) Direct field patterns (portfolio/linkedin/pronouns/location/etc)
      2) Semantic default_answers patterns (work auth, visa, salary, etc)

    Returns:
        Answer string or None.
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
            if _is_effective_value(value):
                return str(value)
            return None

    return match_default_answer(label, config)


def resolve_select_value(answer_value: Any, values_list: Sequence[Mapping[str, Any]]) -> Any | None:
    """Resolve user-facing answer text to a portal option value.

    Matching order:
      1) label exact/case-insensitive
      2) value exact
      3) normalized label
      4) yes/no semantic aliases
      5) unique substring label match

    Returns:
        Resolved option value for non-empty options, original answer for empty
        options, or None if options exist and no match can be found.
    """
    if not values_list:
        return answer_value
    if answer_value is None:
        return None

    answer_text = str(answer_value).strip()
    if not answer_text:
        return None
    answer_lower = answer_text.lower()
    answer_normalized = normalize_text(answer_text)

    # 1) label exact (case-insensitive)
    for option in values_list:
        label = str(option.get("label", "")).strip()
        if label and label.lower() == answer_lower:
            return option.get("value", answer_value)

    # 2) value exact (as string)
    for option in values_list:
        if str(option.get("value", "")).strip() == answer_text:
            return option.get("value", answer_value)

    # 3) normalized label match
    for option in values_list:
        label = str(option.get("label", "")).strip()
        if label and normalize_text(label) == answer_normalized:
            return option.get("value", answer_value)

    # 4) yes/no aliases (common compliance fields)
    yes_aliases = {"yes", "y", "true", "1", "authorized", "eligible"}
    no_aliases = {"no", "n", "false", "0", "not authorized", "not eligible"}
    alias_group: set[str] | None = None
    if answer_lower in yes_aliases:
        alias_group = yes_aliases
    elif answer_lower in no_aliases:
        alias_group = no_aliases
    if alias_group is not None:
        for option in values_list:
            label_lower = str(option.get("label", "")).strip().lower()
            value_lower = str(option.get("value", "")).strip().lower()
            if label_lower in alias_group or value_lower in alias_group:
                return option.get("value", answer_value)

    # 5) unique substring label match
    matched_values: list[Any] = []
    for option in values_list:
        label = str(option.get("label", "")).strip().lower()
        if not label:
            continue
        if answer_lower in label or label in answer_lower:
            matched_values.append(option.get("value", answer_value))
    if len(matched_values) == 1:
        return matched_values[0]

    return None


def load_answers_yaml(answer_path: Path) -> dict[str, Any] | None:
    """Load answer YAML dict safely and return None on parse/shape errors."""
    if not answer_path.exists():
        return None
    try:
        data = yaml.safe_load(answer_path.read_text())
    except yaml.YAMLError as exc:
        print(f"  Warning: Could not parse answer file {answer_path.name}: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        return None
    return data


def clean_answer_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    """Filter out empty/placeholder values from loaded answer mappings."""
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if _is_effective_value(value):
            cleaned[str(key)] = value
    return cleaned


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
