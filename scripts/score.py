#!/usr/bin/env python3
"""Score pipeline entries against the multi-dimensional rubric.

Auto-derives scores for deadline_feasibility, financial_alignment,
portal_friction, and effort_to_value from existing data. Computes
mission_alignment, evidence_match, and track_record_fit from structured
signals (profiles, blocks, portal fields, cross-pipeline history).
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    ALL_PIPELINE_DIRS_WITH_POOL,
    PIPELINE_DIR_ACTIVE,
    PIPELINE_DIR_RESEARCH_POOL,
    BLOCKS_DIR,
    load_entries as _load_entries_raw,
    load_entry_by_id,
    load_profile,
    parse_date, days_until,
    update_yaml_field,
)

# Dimension weights (must sum to 1.0)
WEIGHTS = {
    "mission_alignment": 0.25,
    "evidence_match": 0.20,
    "track_record_fit": 0.15,
    "financial_alignment": 0.10,
    "effort_to_value": 0.10,
    "strategic_value": 0.10,
    "deadline_feasibility": 0.05,
    "portal_friction": 0.05,
}

# Job-specific weights: human-judgment dimensions get 75% (vs 60% creative)
# because auto-derived dimensions don't differentiate between auto-sourced jobs.
WEIGHTS_JOB = {
    "mission_alignment": 0.35,
    "evidence_match": 0.25,
    "track_record_fit": 0.15,
    "strategic_value": 0.10,
    "financial_alignment": 0.05,
    "effort_to_value": 0.05,
    "deadline_feasibility": 0.03,
    "portal_friction": 0.02,
}

# Benefits cliff thresholds (annual USD)
SNAP_LIMIT = 20352
MEDICAID_LIMIT = 21597
ESSENTIAL_PLAN_LIMIT = 39125

# Portal friction scores by portal type
PORTAL_SCORES = {
    "email": 9,
    "custom": 6,
    "web": 6,
    "submittable": 5,
    "greenhouse": 5,
    "lever": 5,
    "ashby": 5,
    "workable": 5,
    "slideroom": 4,
}

# Strategic value by track (base estimates, individual overrides possible)
STRATEGIC_BASE = {
    "grant": 7,
    "prize": 8,
    "fellowship": 7,
    "residency": 6,
    "program": 5,
    "writing": 5,
    "emergency": 3,
    "job": 6,
    "consulting": 3,
}

# High-prestige organizations that get strategic_value boost
HIGH_PRESTIGE = {
    "Creative Capital": 10,
    "Doris Duke Charitable Foundation": 9,
    "LACMA": 9,
    "Whiting Foundation": 9,
    "Prix Ars Electronica": 9,
    "S+T+ARTS Prize": 8,
    "Google": 8,
    "Anthropic": 8,
    "Eyebeam": 8,
    "Pioneer Works": 7,
    "Rauschenberg Foundation": 8,
    "ZKM": 8,
    "Headlands Center for the Arts": 7,
    "NEW INC": 7,
    "Lambda Literary": 6,
    "Tulsa Artist Fellowship": 8,
    "Processing Foundation": 6,
    "Watermill Center": 7,
    "Cohere": 6,
    "Together AI": 5,
    "Runway": 6,
    "HuggingFace": 6,
    "Hugging Face": 6,
    "Mistral": 7,
    "Perplexity": 7,
    "Cursor": 7,
    "Anysphere": 7,
    "Replit": 6,
    "Vercel": 6,
    "Scale AI": 6,
    "Weights & Biases": 5,
    "Modal": 5,
    "Replicate": 5,
    "GitLab": 6,
    "Twilio": 6,
    "MongoDB": 6,
    "Elastic": 5,
    "Grafana Labs": 6,
    "Netlify": 6,
    "PlanetScale": 5,
    "Airtable": 6,
    "Resend": 5,
    "ElevenLabs": 7,
    "Neon": 5,
    "Warp": 5,
}

# Title-based role-fit tiers for auto-sourced entries.
# Derived from 20 manually-scored submitted entries.
# Order matters: specific patterns (tier-1, tier-4, tier-3) are checked
# before generic catch-alls (tier-2 "software engineer") so that
# "Software Engineer, iOS" matches tier-4 not tier-2.
ROLE_FIT_TIERS = [
    {
        "name": "tier-1-strong",
        "title_patterns": [
            "developer experience", "developer tools", "devtools", "devex",
            "developer relations", "devrel", "developer advocate", "developer community",
            "developer education", "education engineer", "education platform",
            "technical writer", "documentation engineer",
            "cli ", "client infrastructure",
            "agent sdk", "agentic",
            "claude code",
        ],
        "mission_alignment": 9,
        "evidence_match": 9,
        "track_record_fit": 7,
    },
    {
        "name": "tier-4-poor",
        "title_patterns": [
            "machine learning", "ml engineer", "reinforcement learning",
            "security", "cybersecurity",
            "data engineer", "data infrastructure", "databases",
            "ios", "android", "mobile",
            "accelerator", "compute efficiency", "networking",
            "encoding", "inference",
            "recruiting", "audiovisual",
            "account abuse", "safeguard",
            "people product", "human data",
            "windows",
        ],
        "mission_alignment": 3,
        "evidence_match": 2,
        "track_record_fit": 2,
    },
    {
        "name": "tier-3-weak",
        "title_patterns": [
            "forward deployed", "applied ai",
            "growth", "enterprise",
            "business technology",
            "public sector",
        ],
        "mission_alignment": 5,
        "evidence_match": 4,
        "track_record_fit": 3,
    },
    {
        "name": "tier-2-moderate",
        "title_patterns": [
            "software engineer",
            "full stack", "fullstack",
            "frontend", "backend",
            "platform engineer", "infrastructure engineer",
            "solutions engineer",
            "integrations",
            "product engineer",
        ],
        "mission_alignment": 7,
        "evidence_match": 6,
        "track_record_fit": 5,
    },
]


def estimate_role_fit_from_title(entry: dict) -> dict[str, int]:
    """Estimate human dimensions from job title for auto-sourced entries.

    Returns dimension dict based on title-pattern tier matching.
    Uses patterns derived from 20 manually-scored submitted entries.
    """
    name = (entry.get("name") or "").lower()

    for tier in ROLE_FIT_TIERS:
        for pattern in tier["title_patterns"]:
            if pattern in name:
                return {
                    "mission_alignment": tier["mission_alignment"],
                    "evidence_match": tier["evidence_match"],
                    "track_record_fit": tier["track_record_fit"],
                }

    # No match — neutral defaults instead of broken 0-based estimate
    return {
        "mission_alignment": 5,
        "evidence_match": 4,
        "track_record_fit": 4,
    }


# --- Signal-based dimension constants ---

# Track-position affinity: how well each identity position fits each track.
TRACK_POSITION_AFFINITY = {
    "grant":      {"systems-artist": 3, "creative-technologist": 2, "community-practitioner": 2, "educator": 1, "independent-engineer": 1},
    "residency":  {"systems-artist": 3, "creative-technologist": 3, "community-practitioner": 2, "educator": 1, "independent-engineer": 1},
    "prize":      {"systems-artist": 3, "creative-technologist": 2, "community-practitioner": 1, "educator": 1, "independent-engineer": 1},
    "fellowship": {"systems-artist": 2, "creative-technologist": 3, "community-practitioner": 2, "educator": 2, "independent-engineer": 2},
    "program":    {"systems-artist": 2, "creative-technologist": 2, "community-practitioner": 3, "educator": 2, "independent-engineer": 2},
    "writing":    {"systems-artist": 1, "creative-technologist": 2, "community-practitioner": 3, "educator": 2, "independent-engineer": 1},
    "emergency":  {"systems-artist": 2, "creative-technologist": 1, "community-practitioner": 3, "educator": 1, "independent-engineer": 1},
    "consulting": {"systems-artist": 1, "creative-technologist": 2, "community-practitioner": 1, "educator": 1, "independent-engineer": 3},
}

# Expected organs for each identity position.
POSITION_EXPECTED_ORGANS = {
    "systems-artist":          {"I", "II", "META"},
    "creative-technologist":   {"I", "III", "IV"},
    "community-practitioner":  {"V", "VI", "META"},
    "educator":                {"V", "VI"},
    "independent-engineer":    {"III", "IV"},
}

# Credential relevance per track.
CREDENTIALS = {
    "mfa_creative_writing": {
        "writing": 4, "grant": 3, "residency": 3, "prize": 3,
        "program": 2, "fellowship": 2, "emergency": 2, "consulting": 1,
    },
    "meta_fullstack_dev": {
        "consulting": 4, "fellowship": 3, "program": 3,
        "grant": 1, "residency": 1, "prize": 1, "writing": 1, "emergency": 1,
    },
    "teaching_11yr": {
        "program": 4, "fellowship": 3, "residency": 2,
        "writing": 2, "grant": 2, "prize": 1, "emergency": 1, "consulting": 2,
    },
    "construction_pm": {
        "consulting": 3, "grant": 1, "residency": 1, "prize": 0,
        "fellowship": 1, "program": 1, "writing": 0, "emergency": 1,
    },
}


# --- Mission Alignment signal functions ---


def _ma_position_profile_match(entry: dict, profile: dict | None) -> tuple[int, str]:
    """Signal 1: Does the entry's identity position match the profile's primary/secondary?"""
    fit = entry.get("fit", {})
    if not isinstance(fit, dict):
        fit = {}
    position = fit.get("identity_position", "")

    if not profile:
        return 2, "no profile available -> 2 (neutral)"

    primary = profile.get("primary_position", "")
    secondary = profile.get("secondary_position", "")

    if position and position == primary:
        return 4, f"{position} = profile primary_position -> 4"
    if position and position == secondary:
        return 2, f"{position} = profile secondary_position -> 2"
    if not position:
        return 2, "no identity_position set -> 2 (neutral)"
    return 0, f"{position} != primary ({primary}) or secondary ({secondary}) -> 0"


def _ma_track_position_affinity(entry: dict) -> tuple[int, str]:
    """Signal 2: How well does the identity position fit the track?"""
    track = entry.get("track", "")
    fit = entry.get("fit", {})
    if not isinstance(fit, dict):
        fit = {}
    position = fit.get("identity_position", "")

    track_affinities = TRACK_POSITION_AFFINITY.get(track, {})
    score = track_affinities.get(position, 1)  # default 1 for unknown
    return score, f"({track}, {position or 'none'}) -> {score}"


def _ma_organ_position_coherence(entry: dict) -> tuple[int, str]:
    """Signal 3: Do lead_organs match the position's expected organs?"""
    fit = entry.get("fit", {})
    if not isinstance(fit, dict):
        fit = {}
    position = fit.get("identity_position", "")
    lead_organs = fit.get("lead_organs") or []

    if not lead_organs or not position:
        return 1, f"missing data (organs={lead_organs}, pos={position}) -> 1"

    expected = POSITION_EXPECTED_ORGANS.get(position, set())
    if not expected:
        return 1, f"unknown position {position} -> 1"

    lead_set = set(lead_organs)
    overlap = len(lead_set & expected)
    score = round(overlap / len(lead_set) * 2)
    return score, f"lead {list(lead_set)} & expected {sorted(expected)} = {overlap}/{len(lead_set)} -> {score}"


def _ma_framing_specialization(entry: dict) -> tuple[int, str]:
    """Signal 4: Does the entry use a dedicated framing block?"""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return 0, "no submission data -> 0"

    blocks_used = submission.get("blocks_used", {}) or {}
    for key, path in blocks_used.items():
        if isinstance(path, str) and path.startswith("framings/"):
            return 1, f"has framings/ block ({path}) -> 1"
    return 0, "no framings/* block -> 0"


# --- Evidence Match signal functions ---


def _em_block_portal_coverage(entry: dict) -> tuple[int, str]:
    """Signal 1: Ratio of blocks_used to portal_fields."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        submission = {}
    blocks_used = submission.get("blocks_used", {}) or {}
    blocks_count = len(blocks_used)

    portal_fields = entry.get("portal_fields", {})
    if not isinstance(portal_fields, dict):
        portal_fields = {}
    fields = portal_fields.get("fields") or []
    fields_count = len(fields)

    if blocks_count == 0 or fields_count == 0:
        return 0, f"{blocks_count} blocks / {fields_count} fields -> 0"

    ratio = blocks_count / fields_count
    if ratio >= 1.0:
        score = 3
    elif ratio >= 0.5:
        score = 2
    else:
        score = 1
    return score, f"{blocks_count} blocks / {fields_count} fields = {ratio:.2f} -> {score}"


def _em_slot_name_alignment(entry: dict) -> tuple[int, str]:
    """Signal 2: How many block keys match portal field names (fuzzy)."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        submission = {}
    blocks_used = submission.get("blocks_used", {}) or {}
    block_keys = set(blocks_used.keys())

    portal_fields = entry.get("portal_fields", {})
    if not isinstance(portal_fields, dict):
        portal_fields = {}
    fields = portal_fields.get("fields") or []
    field_names = {f.get("name", "") for f in fields if isinstance(f, dict)}

    if not field_names:
        return 0, "no portal fields -> 0"

    # Fuzzy matching: check if field name is substring of block key or vice versa
    matches = 0
    for fname in field_names:
        for bkey in block_keys:
            # Normalize: artist_statement matches statement, bio matches bio
            if fname in bkey or bkey in fname:
                matches += 1
                break

    score = min(3, round(matches / len(field_names) * 3))
    return score, f"{matches} matches / {len(field_names)} fields -> {score}"


def _em_evidence_depth(entry: dict) -> tuple[int, str]:
    """Signal 3: Has evidence/* or methodology/* blocks."""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return 0, "no submission data -> 0"

    blocks_used = submission.get("blocks_used", {}) or {}
    score = 0
    parts = []
    for key, path in blocks_used.items():
        if isinstance(path, str):
            if path.startswith("evidence/") and "evidence" not in parts:
                score += 1
                parts.append("evidence")
            elif path.startswith("methodology/") and "methodology" not in parts:
                score += 1
                parts.append("methodology")

    if parts:
        return score, f"has {'+'.join(parts)} blocks -> {score}"
    return 0, "no evidence/* or methodology/* blocks -> 0"


def _em_materials_readiness(entry: dict) -> tuple[int, str]:
    """Signal 4: Are materials attached and portfolio URL set?"""
    submission = entry.get("submission", {})
    if not isinstance(submission, dict):
        return 0, "no submission data -> 0"

    score = 0
    parts = []

    materials = submission.get("materials_attached") or []
    if materials:
        score += 1
        parts.append("materials_attached")

    portfolio = submission.get("portfolio_url") or ""
    if portfolio:
        score += 1
        parts.append("portfolio_url")

    if parts:
        return score, f"{'+'.join(parts)} set -> {score}"
    return 0, "no materials or portfolio_url -> 0"


# --- Track Record Fit signal functions ---


def _tr_credential_track_relevance(entry: dict) -> tuple[int, str]:
    """Signal 1: Best credential score for this entry's track."""
    track = entry.get("track", "")
    best_score = 0
    best_cred = ""

    for cred_name, track_scores in CREDENTIALS.items():
        cred_score = track_scores.get(track, 0)
        if cred_score > best_score:
            best_score = cred_score
            best_cred = cred_name

    if best_cred:
        return best_score, f"{best_cred} for {track} -> {best_score}"
    return 0, f"no credential scores for track={track} -> 0"


def _tr_track_experience(entry: dict, all_entries: list[dict]) -> tuple[int, str]:
    """Signal 2: How many entries in the same track have been submitted+."""
    track = entry.get("track", "")
    submitted_statuses = {"submitted", "acknowledged", "interview", "outcome"}

    count = 0
    for e in all_entries:
        if e.get("track") == track and e.get("status") in submitted_statuses:
            # Don't count the entry itself
            if e.get("id") != entry.get("id"):
                count += 1

    if count >= 3:
        score = 3
    elif count == 2:
        score = 2
    elif count == 1:
        score = 1
    else:
        score = 0
    return score, f"{count} submitted {track} entries -> {score}"


def _tr_position_depth(entry: dict) -> tuple[int, str]:
    """Signal 3: Does the position have a dedicated framing block on disk?"""
    fit = entry.get("fit", {})
    if not isinstance(fit, dict):
        fit = {}
    position = fit.get("identity_position", "")

    if not position:
        return 0, "no position set -> 0"

    framing_path = BLOCKS_DIR / "framings" / f"{position}.md"
    if framing_path.exists():
        return 2, f"framings/{position}.md exists -> 2"
    return 1, f"position {position} set but no framings/{position}.md -> 1"


def _tr_differentiators_coverage(entry: dict, profile: dict | None) -> tuple[int, str]:
    """Signal 4: Does the profile have enough evidence highlights?"""
    if not profile:
        return 0, "no profile -> 0"

    highlights = profile.get("evidence_highlights") or []
    if len(highlights) >= 3:
        return 1, f"{len(highlights)} evidence_highlights >= 3 -> 1"
    return 0, f"{len(highlights)} evidence_highlights < 3 -> 0"


def load_entries(entry_id: str | None = None, include_pool: bool = False) -> list[tuple[Path, dict]]:
    """Load pipeline entries as (filepath, data) tuples.

    If entry_id given, load only that one.
    If include_pool, also scan research_pool/ (for --all scoring).
    """
    if entry_id:
        filepath, data = load_entry_by_id(entry_id)
        if filepath and data:
            return [(filepath, data)]
        return []

    dirs = ALL_PIPELINE_DIRS_WITH_POOL if include_pool else None
    entries = _load_entries_raw(dirs=dirs, include_filepath=True)
    return [(e.pop("_filepath"), e) for e in entries if "_filepath" in e]


def score_deadline_feasibility(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Score deadline feasibility from deadline data.

    Uses date.today() (not datetime.now()) for consistent day-boundary
    calculations that match pipeline_lib.days_until().
    """
    deadline = entry.get("deadline", {})
    if not isinstance(deadline, dict):
        result = 7
        if explain:
            return result, "deadline is not a dict -> default 7"
        return result

    dtype = deadline.get("type", "")
    date_str = deadline.get("date")

    if dtype in ("rolling", "tba") or not date_str:
        result = 9
        if explain:
            return result, f"type={dtype or 'no date'} -> 9 (no pressure)"
        return result

    deadline_date = parse_date(date_str)
    if not deadline_date:
        result = 7
        if explain:
            return result, f"unparseable date '{date_str}' -> default 7"
        return result

    days_left = days_until(deadline_date)

    if days_left < 0:
        result = 1
    elif days_left <= 1:
        result = 2
    elif days_left <= 3:
        result = 3
    elif days_left <= 7:
        result = 5
    elif days_left <= 14:
        result = 6
    elif days_left <= 30:
        result = 8
    else:
        result = 9

    if explain:
        return result, f"{days_left}d left (date: {date_str}) -> {result}"
    return result


def score_financial_alignment(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Score financial alignment from amount and cliff notes.

    For job-track entries, higher salary scores higher.
    For grants/fellowships, benefits-cliff-aware scoring applies.
    """
    amount = entry.get("amount", {})
    if not isinstance(amount, dict):
        result = 9
        if explain:
            return result, "amount is not a dict -> default 9"
        return result

    value = amount.get("value", 0)
    track = entry.get("track", "")

    # Job track: higher salary = higher score
    if track == "job":
        if value == 0:
            result = 5  # unknown salary — slight penalty
            reason = f"${value:,} (unknown) -> {result}"
        elif value > 150000:
            result = 9  # strong comp
            reason = f"${value:,} (>$150K) -> {result}"
        elif value > 100000:
            result = 8  # good comp
            reason = f"${value:,} (>$100K) -> {result}"
        elif value > 50000:
            result = 7  # adequate comp
            reason = f"${value:,} (>$50K) -> {result}"
        else:
            result = 6  # low comp
            reason = f"${value:,} (low) -> {result}"
        if explain:
            return result, reason
        return result

    cliff_note = amount.get("benefits_cliff_note") or ""

    if value == 0:
        result = 10
        reason = "$0 (no cliff risk) -> 10"
    elif "exceeds" in cliff_note.lower() or "nylag" in cliff_note.lower():
        result = 4
        reason = f"${value:,} cliff note '{cliff_note}' -> 4"
    elif "essential plan" in cliff_note.lower():
        result = 5
        reason = f"${value:,} cliff note '{cliff_note}' -> 5"
    elif value <= SNAP_LIMIT:
        result = 9
        reason = f"${value:,} <= SNAP ${SNAP_LIMIT:,} -> 9"
    elif value <= MEDICAID_LIMIT:
        result = 8
        reason = f"${value:,} <= Medicaid ${MEDICAID_LIMIT:,} -> 8"
    elif value <= ESSENTIAL_PLAN_LIMIT:
        result = 6
        reason = f"${value:,} <= Essential Plan ${ESSENTIAL_PLAN_LIMIT:,} -> 6"
    elif value <= 100000:
        result = 4
        reason = f"${value:,} > Essential Plan -> 4"
    else:
        result = 3
        reason = f"${value:,} > $100K -> 3 (severe cliff risk)"

    if explain:
        return result, reason
    return result


def score_portal_friction(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Score portal friction from portal type."""
    target = entry.get("target", {})
    if not isinstance(target, dict):
        result = 6
        if explain:
            return result, "target is not a dict -> default 6"
        return result
    portal = target.get("portal", "custom")
    result = PORTAL_SCORES.get(portal, 6)
    if explain:
        mapped = "mapped" if portal in PORTAL_SCORES else "default"
        return result, f"portal={portal} -> {result} ({mapped})"
    return result


def score_effort_to_value(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Estimate effort-to-value from amount, track, and blocks coverage."""
    amount = entry.get("amount", {})
    value = amount.get("value", 0) if isinstance(amount, dict) else 0
    track = entry.get("track", "")

    submission = entry.get("submission", {})
    blocks_count = len(submission.get("blocks_used", {}) or {}) if isinstance(submission, dict) else 0

    # Higher blocks coverage = lower effort
    coverage_bonus = min(blocks_count / 6, 1.0) * 2  # 0-2 bonus for block readiness

    # Base by track
    track_bases = {
        "emergency": 8,  # low effort, high urgency
        "writing": 7,    # moderate effort, direct value
        "prize": 6,      # moderate effort, prestige value
        "grant": 5,      # higher effort, high value
        "fellowship": 5,
        "residency": 5,
        "program": 5,
        "consulting": 6,
        "job": 6,        # CLI-submittable jobs are moderate effort
    }
    base = track_bases.get(track, 5)
    explain_parts = [f"track={track} base={base}"]

    # Value adjustment
    if value >= 50000:
        base += 1
        explain_parts.append(f"${value:,}>=50K (+1)")
    elif value == 0 and track not in ("residency", "program"):
        base -= 1
        explain_parts.append("$0 (-1)")

    explain_parts.append(f"{blocks_count} blocks (+{coverage_bonus:.1f})")

    score = base + coverage_bonus

    # Location accessibility penalty: international-only roles require
    # visa sponsorship and relocation, significantly increasing effort
    target = entry.get("target", {})
    location_class = target.get("location_class", "") if isinstance(target, dict) else ""
    if location_class == "international":
        score -= 3
        explain_parts.append("international (-3)")

    result = max(1, min(10, round(score)))

    if explain:
        return result, f"{' | '.join(explain_parts)} = {result}"
    return result


def score_strategic_value(entry: dict, explain: bool = False) -> int | tuple[int, str]:
    """Score strategic value from organization prestige and track."""
    org = ""
    target = entry.get("target", {})
    if isinstance(target, dict):
        org = target.get("organization") or ""

    # Check high-prestige overrides
    for name, prestige_score in HIGH_PRESTIGE.items():
        if org and name.lower() in org.lower():
            if explain:
                return prestige_score, f'org "{org}" matched "{name}" -> {prestige_score} (prestige list)'
            return prestige_score

    # Fall back to track-based estimate
    track = entry.get("track", "")
    result = STRATEGIC_BASE.get(track, 5)
    if explain:
        source = "track base" if track in STRATEGIC_BASE else "default"
        return result, f'org "{org}" not in prestige list, track={track} -> {result} ({source})'
    return result


def compute_human_dimensions(
    entry: dict,
    all_entries: list[dict] | None = None,
    explain: bool = False,
) -> dict[str, int] | tuple[dict[str, int], dict[str, str]]:
    """Compute mission_alignment, evidence_match, track_record_fit from signals.

    For auto-sourced job entries, uses title-based tier estimation (unchanged).
    For everything else, uses 12 signal functions that analyze profiles, blocks,
    portal fields, and cross-pipeline history. No gut-feel input.
    """
    tags = entry.get("tags") or []

    # Auto-sourced job entries: always use title-based tier estimation
    if "auto-sourced" in tags:
        base = estimate_role_fit_from_title(entry)
        submission = entry.get("submission", {})
        blocks_count = len(submission.get("blocks_used", {}) or {}) if isinstance(submission, dict) else 0
        if blocks_count >= 5:
            base["evidence_match"] = min(10, base["evidence_match"] + 1)
        if explain:
            name = (entry.get("name") or "").lower()
            tier_name = "no match"
            for tier in ROLE_FIT_TIERS:
                for pattern in tier["title_patterns"]:
                    if pattern in name:
                        tier_name = tier["name"]
                        break
                if tier_name != "no match":
                    break
            explanations = {}
            for k, v in base.items():
                explanations[k] = f"auto-sourced, {tier_name} -> {v}"
            return base, explanations
        return base

    # Load cross-pipeline entries for track experience signal
    if all_entries is None:
        all_entries = [e for e in _load_entries_raw()]

    # Load profile for this entry
    entry_id = entry.get("id", "")
    profile = load_profile(entry_id)

    # --- Mission Alignment (4 signals, 0-10) ---
    ma1_score, ma1_reason = _ma_position_profile_match(entry, profile)
    ma2_score, ma2_reason = _ma_track_position_affinity(entry)
    ma3_score, ma3_reason = _ma_organ_position_coherence(entry)
    ma4_score, ma4_reason = _ma_framing_specialization(entry)
    mission = max(1, min(10, ma1_score + ma2_score + ma3_score + ma4_score))

    # --- Evidence Match (4 signals, 0-10) ---
    em1_score, em1_reason = _em_block_portal_coverage(entry)
    em2_score, em2_reason = _em_slot_name_alignment(entry)
    em3_score, em3_reason = _em_evidence_depth(entry)
    em4_score, em4_reason = _em_materials_readiness(entry)
    evidence = max(1, min(10, em1_score + em2_score + em3_score + em4_score))

    # --- Track Record Fit (4 signals, 0-10) ---
    tr1_score, tr1_reason = _tr_credential_track_relevance(entry)
    tr2_score, tr2_reason = _tr_track_experience(entry, all_entries)
    tr3_score, tr3_reason = _tr_position_depth(entry)
    tr4_score, tr4_reason = _tr_differentiators_coverage(entry, profile)
    track_record = max(1, min(10, tr1_score + tr2_score + tr3_score + tr4_score))

    result = {
        "mission_alignment": mission,
        "evidence_match": evidence,
        "track_record_fit": track_record,
    }

    if explain:
        explanations = {
            "mission_alignment": "\n".join([
                f"  position-profile match:  {ma1_score}  <- {ma1_reason}",
                f"  track-position affinity: {ma2_score}  <- {ma2_reason}",
                f"  organ-position coherence:{ma3_score}  <- {ma3_reason}",
                f"  framing specialization:  {ma4_score}  <- {ma4_reason}",
            ]),
            "evidence_match": "\n".join([
                f"  block-portal coverage:   {em1_score}  <- {em1_reason}",
                f"  slot name alignment:     {em2_score}  <- {em2_reason}",
                f"  evidence depth:          {em3_score}  <- {em3_reason}",
                f"  materials readiness:     {em4_score}  <- {em4_reason}",
            ]),
            "track_record_fit": "\n".join([
                f"  credential-track:        {tr1_score}  <- {tr1_reason}",
                f"  track experience:        {tr2_score}  <- {tr2_reason}",
                f"  position depth:          {tr3_score}  <- {tr3_reason}",
                f"  differentiators:         {tr4_score}  <- {tr4_reason}",
            ]),
        }
        return result, explanations

    return result


# Keep backward-compatible alias for any external callers
estimate_human_dimensions = compute_human_dimensions


def compute_dimensions(entry: dict, all_entries: list[dict] | None = None) -> dict[str, int]:
    """Compute all 8 dimension scores for an entry.

    All dimensions are always recomputed from data. No human overrides.
    Signal-based dimensions replace the old gut-feel estimation.
    """
    dims = {}

    # Auto-derivable (always recompute)
    dims["deadline_feasibility"] = score_deadline_feasibility(entry)
    dims["financial_alignment"] = score_financial_alignment(entry)
    dims["portal_friction"] = score_portal_friction(entry)
    dims["effort_to_value"] = score_effort_to_value(entry)
    dims["strategic_value"] = score_strategic_value(entry)

    # Signal-based (replaces estimate + override)
    human = compute_human_dimensions(entry, all_entries)
    dims.update(human)

    return dims


def compute_composite(dimensions: dict[str, int], track: str = "") -> float:
    """Compute weighted composite score from dimensions.

    Uses job-specific weights when track is "job", creative weights otherwise.
    """
    weights = get_weights(track)
    total = 0.0
    for dim, weight in weights.items():
        val = dimensions.get(dim, 5)
        total += val * weight
    return round(total, 1)


DIMENSION_ORDER = [
    "mission_alignment", "evidence_match", "track_record_fit",
    "financial_alignment", "effort_to_value", "strategic_value",
    "deadline_feasibility", "portal_friction",
]

# Below this composite score, recommend skipping the application
QUALIFICATION_THRESHOLD = 5.0
JOB_QUALIFICATION_THRESHOLD = 5.5


def get_weights(track: str) -> dict:
    """Return the weight config appropriate for the entry's track."""
    return WEIGHTS_JOB if track == "job" else WEIGHTS


def get_qualification_threshold(track: str) -> float:
    """Return the qualification threshold appropriate for the entry's track."""
    return JOB_QUALIFICATION_THRESHOLD if track == "job" else QUALIFICATION_THRESHOLD


def qualify(entry: dict, all_entries: list[dict] | None = None) -> tuple[bool, str]:
    """Return (should_apply, reason) based on composite score.

    Uses track-appropriate weights and threshold: job entries use
    JOB_QUALIFICATION_THRESHOLD (5.5) with job weights, creative entries
    use QUALIFICATION_THRESHOLD (5.0) with creative weights.
    """
    track = entry.get("track", "")
    threshold = get_qualification_threshold(track)
    dimensions = compute_dimensions(entry, all_entries)
    composite = compute_composite(dimensions, track)

    if composite >= threshold:
        return True, f"composite {composite:.1f} >= {threshold}"

    # Find the weakest dimensions to explain why
    weak = sorted(
        ((dim, dimensions[dim]) for dim in DIMENSION_ORDER),
        key=lambda x: x[1],
    )
    weak_names = [f"{dim}={val}" for dim, val in weak[:3]]
    return False, f"composite {composite:.1f} < {threshold} (weak: {', '.join(weak_names)})"


def update_entry_file(filepath: Path, dimensions: dict[str, int], composite: float, dry_run: bool = False):
    """Update a pipeline YAML file with new dimensions and composite score.

    Preserves original_score for manual entries (non-auto-sourced) to break
    the circular dependency between fit.score and dimension estimation.
    Uses targeted regex to preserve file formatting while verifying
    the result is still valid YAML after each modification.
    """
    import re
    from pipeline_lib import update_yaml_field

    with open(filepath) as f:
        content = f.read()

    data = yaml.safe_load(content)
    fit = data.get("fit", {}) if isinstance(data.get("fit"), dict) else {}
    old_score = fit.get("score")
    tags = data.get("tags") or []

    if dry_run:
        return old_score, composite

    # Backfill original_score for manual entries that don't have it yet.
    # Only for non-auto-sourced entries with existing dimensions (already scored once).
    has_original = fit.get("original_score") is not None
    has_dimensions = isinstance(fit.get("dimensions"), dict)
    is_auto = "auto-sourced" in tags

    if not has_original and not is_auto and has_dimensions and old_score is not None:
        # Insert original_score line right after the score line
        score_pattern = re.compile(r"^(\s+)(score:\s+\S+)\s*$", re.MULTILINE)
        match = score_pattern.search(content)
        if match:
            indent = match.group(1)
            insert_after = match.end()
            original_line = f"\n{indent}original_score: {old_score}"
            content = content[:insert_after] + original_line + content[insert_after:]

    # Update score via safe helper
    content = update_yaml_field(content, "score", str(composite), nested=True)

    # Build new dimensions block
    # Detect the indentation used in the file for fit sub-keys
    fit_indent_match = re.search(r"^(\s+)score:", content, re.MULTILINE)
    indent = fit_indent_match.group(1) if fit_indent_match else "  "
    dim_indent = indent + "  "

    new_dims_lines = [f"{indent}dimensions:"]
    for key in DIMENSION_ORDER:
        new_dims_lines.append(f"{dim_indent}{key}: {dimensions[key]}")
    new_dims_block = "\n".join(new_dims_lines)

    # Replace existing dimensions block or insert before next top-level key after fit
    dims_pattern = re.compile(
        r"^(\s+dimensions:\s*\n)"  # dimensions: header
        r"(?:\s+\w+:\s*\d+\s*\n)*",  # dimension key-value lines
        re.MULTILINE,
    )

    if dims_pattern.search(content):
        content = dims_pattern.sub(new_dims_block + "\n", content, count=1)
    else:
        # No dimensions block exists — insert after the last fit sub-key
        # Find the fit section and its last indented line
        fit_section = re.search(
            r"^fit:\s*\n((?:\s+\S.*\n)*)",
            content,
            re.MULTILINE,
        )
        if fit_section:
            insert_pos = fit_section.end()
            content = content[:insert_pos] + new_dims_block + "\n" + content[insert_pos:]

    # Verify the final content is still valid YAML
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML became invalid after scoring update: {e}")

    with open(filepath, "w") as f:
        f.write(content)

    return old_score, composite


def _print_qualify_group(label: str, threshold: float,
                         apply_list: list, skip_list: list):
    """Print a single qualification group (job or creative)."""
    print(f"{label} (threshold: {threshold})")
    print(f"{'-' * 50}")

    if apply_list:
        print("APPLY:")
        for eid, reason in sorted(apply_list, key=lambda x: x[1], reverse=True):
            print(f"  {eid:<40s} {reason}")

    if skip_list:
        print("SKIP:")
        for eid, reason in sorted(skip_list, key=lambda x: x[1]):
            print(f"  {eid:<40s} {reason}")

    print(f"  {len(apply_list)} APPLY | {len(skip_list)} SKIP")
    print()


def run_qualify(entries: list[tuple[Path, dict]]):
    """Print APPLY/SKIP recommendations grouped by track type."""
    job_apply = []
    job_skip = []
    creative_apply = []
    creative_skip = []

    for filepath, data in entries:
        entry_id = data.get("id", filepath.stem)
        track = data.get("track", "")
        should_apply, reason = qualify(data)

        if track == "job":
            (job_apply if should_apply else job_skip).append((entry_id, reason))
        else:
            (creative_apply if should_apply else creative_skip).append((entry_id, reason))

    if job_apply or job_skip:
        _print_qualify_group(
            "JOB ENTRIES", JOB_QUALIFICATION_THRESHOLD,
            job_apply, job_skip,
        )

    if creative_apply or creative_skip:
        _print_qualify_group(
            "CREATIVE ENTRIES", QUALIFICATION_THRESHOLD,
            creative_apply, creative_skip,
        )

    print(f"{'=' * 50}")
    total_apply = len(job_apply) + len(creative_apply)
    total_skip = len(job_skip) + len(creative_skip)
    print(f"Total: {total_apply} APPLY | {total_skip} SKIP")


def run_auto_qualify(dry_run: bool = False):
    """Batch-advance qualifying research_pool entries to qualified in active/.

    Loads entries from research_pool/, runs qualify() on each, and moves
    qualifying entries back to active/ with status=qualified.
    """
    import shutil

    pool_entries = _load_entries_raw(
        dirs=[PIPELINE_DIR_RESEARCH_POOL], include_filepath=True,
    )
    if not pool_entries:
        print("No entries in research_pool/.")
        return

    # Pre-load all raw entries for cross-pipeline scoring signals
    all_raw = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)

    qualified_list = []
    skipped = 0

    for entry in pool_entries:
        filepath = entry.get("_filepath")
        if not filepath:
            continue
        entry_id = entry.get("id", filepath.stem)
        should_apply, reason = qualify(entry, all_raw)

        if should_apply:
            qualified_list.append((filepath, entry_id, entry, reason))
        else:
            skipped += 1

    print(f"Research pool: {len(pool_entries)} entries")
    print(f"Qualify: {len(qualified_list)} | Skip: {skipped}")
    print()

    if not qualified_list:
        print("No entries meet the qualification threshold.")
        return

    PIPELINE_DIR_ACTIVE.mkdir(parents=True, exist_ok=True)
    moved = 0
    for filepath, entry_id, entry, reason in qualified_list:
        dest = PIPELINE_DIR_ACTIVE / filepath.name

        if dry_run:
            score = entry.get("fit", {}).get("score", 0) if isinstance(entry.get("fit"), dict) else 0
            print(f"  [dry-run] {entry_id} ({reason}) -> active/ as qualified")
        else:
            # Update status to qualified in the file
            content = filepath.read_text()
            content = update_yaml_field(content, "status", "qualified")
            filepath.write_text(content)
            # Move to active/
            shutil.move(str(filepath), str(dest))
            print(f"  {entry_id} -> active/ (qualified, {reason})")
        moved += 1

    print(f"\n{'=' * 50}")
    if dry_run:
        print(f"Would auto-qualify {moved} entries (dry run)")
    else:
        print(f"Auto-qualified {moved} entries to active/")


RUBRIC_DESCRIPTIONS = {
    "mission_alignment": {
        (1, 2): "Work doesn't fit their stated mission",
        (3, 4): "Tangential connection requiring significant stretching",
        (5, 6): "Plausible fit with some reframing needed",
        (7, 8): "Clear alignment, work fits naturally",
        (9, 10): "Work exemplifies their mission; target applicant",
    },
    "evidence_match": {
        (1, 2): "They want things we can't demonstrate",
        (3, 4): "Most evidence is indirect or requires heavy reframing",
        (5, 6): "Some direct evidence, some gaps",
        (7, 8): "Strong evidence for most requirements",
        (9, 10): "Every requirement has verifiable proof",
    },
    "track_record_fit": {
        (1, 2): "Credentials we don't have and can't reframe",
        (3, 4): "Major gaps (exhibitions, affiliations, team leadership)",
        (5, 6): "Some gaps but reframeable via ORGANVM scale",
        (7, 8): "Credentials match with minor gaps",
        (9, 10): "Credentials exceed expectations",
    },
}


def _rubric_desc(dim: str, score: int) -> str:
    """Return the rubric description for a dimension at a given score."""
    descs = RUBRIC_DESCRIPTIONS.get(dim, {})
    for (lo, hi), desc in descs.items():
        if lo <= score <= hi:
            return desc
    return ""


def explain_entry(entry: dict, all_entries: list[dict] | None = None) -> str:
    """Generate a detailed score derivation for a single entry."""
    entry_id = entry.get("id", "unknown")
    track = entry.get("track", "")
    rubric = "JOB" if track == "job" else "CREATIVE"
    weights = get_weights(track)
    fit = entry.get("fit", {}) if isinstance(entry.get("fit"), dict) else {}
    tags = entry.get("tags") or []

    lines = []

    # Header
    dimensions = compute_dimensions(entry, all_entries)
    composite = compute_composite(dimensions, track)
    lines.append(f"{entry_id}: {composite} [{rubric} rubric]")
    lines.append("")

    # Show original_score if present (historical reference)
    original = fit.get("original_score")
    current = fit.get("score")
    if original:
        lines.append(f"  original_score: {original} (historical baseline, no longer feeds computation)")
        lines.append(f"  fit.score:      {current} (computed composite)")
    else:
        lines.append(f"  fit.score: {current}")
    lines.append("")

    # Signal-based dimensions section
    human_keys = ["mission_alignment", "evidence_match", "track_record_fit"]
    computed, signal_explanations = compute_human_dimensions(entry, all_entries, explain=True)

    lines.append("SIGNAL-BASED DIMENSIONS:")
    for key in human_keys:
        dim_val = dimensions[key]
        weight = weights[key]
        lines.append(f"  {key:<25s} {int(dim_val):>2d}  x{weight:.0%}")
        detail = signal_explanations.get(key, "")
        if detail:
            lines.append(detail)

    lines.append("")

    # Auto dimensions section
    auto_funcs = [
        ("financial_alignment", score_financial_alignment),
        ("effort_to_value", score_effort_to_value),
        ("strategic_value", score_strategic_value),
        ("deadline_feasibility", score_deadline_feasibility),
        ("portal_friction", score_portal_friction),
    ]

    lines.append("AUTO DIMENSIONS:")
    for dim_name, func in auto_funcs:
        val, reason = func(entry, explain=True)
        weight = weights[dim_name]
        lines.append(f"  {dim_name:<25s} {val:>2d}  x{weight:.0%}  <- {reason}")

    lines.append("")

    # Weighted sum breakdown
    terms = []
    for dim in DIMENSION_ORDER:
        val = dimensions[dim]
        weight = weights[dim]
        terms.append(f"{val}x{weight:.2f}")
    lines.append(f"COMPOSITE: {' + '.join(terms)} = {composite}")

    return "\n".join(lines)


def review_compressed(entries: list[tuple[Path, dict]], lo: float = 6.5, hi: float = 7.5):
    """Print entries in a compressed score band for manual dimension review."""
    compressed = []

    for filepath, data in entries:
        track = data.get("track", "")
        tags = data.get("tags") or []
        if "auto-sourced" in tags:
            continue  # only manual entries need review
        fit = data.get("fit", {}) if isinstance(data.get("fit"), dict) else {}
        score = fit.get("score", 0)
        if lo <= score <= hi:
            compressed.append((filepath, data))

    if not compressed:
        print(f"No entries in the {lo}-{hi} composite band need review.")
        return

    print(f"COMPRESSED SCORE REVIEW ({lo} - {hi} band)")
    print(f"{len(compressed)} entries need human dimension review:\n")

    for filepath, data in sorted(compressed, key=lambda x: x[1].get("fit", {}).get("score", 0), reverse=True):
        entry_id = data.get("id", filepath.stem)
        track = data.get("track", "")
        fit = data.get("fit", {})
        score = fit.get("score", 0)
        position = fit.get("identity_position", "—")
        dims = fit.get("dimensions", {}) or {}

        print(f"  {entry_id} ({score}) — {track} — {position}")

        for key in ["mission_alignment", "evidence_match", "track_record_fit"]:
            val = dims.get(key, "?")
            desc = _rubric_desc(key, val) if isinstance(val, int) else ""
            desc_str = f'  ({val}-range: "{desc}")' if desc else ""
            print(f"    {key:<25s} {val}{desc_str}")

        print(f"    -> Review: Are these accurate for {data.get('name', entry_id)} specifically?")
        print()

    print("Edit each YAML's fit.dimensions fields, then run `score.py --all` to recalculate composites.")


def main():
    parser = argparse.ArgumentParser(description="Score pipeline entries against rubric")
    parser.add_argument("--target", help="Score a single entry by ID")
    parser.add_argument("--all", action="store_true", help="Score all entries")
    parser.add_argument("--qualify", action="store_true",
                        help="Show APPLY/SKIP recommendations based on score threshold")
    parser.add_argument("--explain", action="store_true",
                        help="Show detailed score derivation for a single entry (requires --target)")
    parser.add_argument("--review-compressed", action="store_true",
                        help="List entries in compressed score band for manual dimension review")
    parser.add_argument("--auto-qualify", action="store_true",
                        help="Batch-advance qualifying research_pool entries to active/qualified")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show scores without writing changes")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-dimension breakdowns")
    args = parser.parse_args()

    if not args.target and not args.all and not args.qualify and not args.explain and not args.review_compressed and not args.auto_qualify:
        parser.error("Specify --target <id>, --all, --qualify, --explain, --review-compressed, or --auto-qualify")

    if args.explain and not args.target:
        parser.error("--explain requires --target <id>")

    # --qualify implies --all unless --target is given
    if args.qualify and not args.target:
        args.all = True

    # --auto-qualify is a standalone command
    if args.auto_qualify:
        run_auto_qualify(dry_run=args.dry_run)
        return

    # --review-compressed implies --all
    if args.review_compressed:
        args.all = True

    # --all includes research pool for full-dataset scoring
    include_pool = args.all and not args.target
    entries = load_entries(args.target if args.target else None, include_pool=include_pool)
    if not entries:
        print(f"No entries found.", file=sys.stderr)
        sys.exit(1)

    # Pre-load all raw entries for cross-pipeline signals (track experience)
    all_raw = _load_entries_raw(dirs=ALL_PIPELINE_DIRS_WITH_POOL)

    if args.explain:
        _, data = entries[0]
        print(explain_entry(data, all_raw))
        return

    if args.review_compressed:
        review_compressed(entries)
        return

    if args.qualify:
        run_qualify(entries)
        return

    changes = []
    for filepath, data in entries:
        entry_id = data.get("id", filepath.stem)
        track = data.get("track", "")
        dimensions = compute_dimensions(data, all_raw)
        composite = compute_composite(dimensions, track)

        old_score, new_score = update_entry_file(filepath, dimensions, composite, dry_run=args.dry_run)

        delta = ""
        if old_score is not None:
            diff = new_score - old_score
            if abs(diff) >= 0.5:
                delta = f" (was {old_score}, delta {diff:+.1f})"
            else:
                delta = f" (was {old_score}, ~same)"

        changes.append((entry_id, old_score, new_score, dimensions))

        rubric = "JOB" if track == "job" else "CREATIVE"
        weights = get_weights(track)

        if args.verbose:
            print(f"\n{'=' * 50}")
            print(f"{entry_id}: {new_score}{delta}  [{rubric} rubric]")
            print(f"  {'Dimension':<25s} {'Score':>5s}  {'Weight':>6s}  {'Contrib':>7s}")
            print(f"  {'-' * 25} {'-' * 5}  {'-' * 6}  {'-' * 7}")
            for dim in DIMENSION_ORDER:
                val = dimensions[dim]
                weight = weights[dim]
                contrib = val * weight
                print(f"  {dim:<25s} {int(val):>5d}  {weight:>5.0%}  {contrib:>7.2f}")
            print(f"  {'COMPOSITE':<25s}        {'':>6s}  {new_score:>7.1f}")
        else:
            print(f"  {entry_id:<40s} {new_score:>5.1f}{delta}  [{rubric}]")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Scored {len(changes)} entries" + (" (dry run)" if args.dry_run else ""))

    if not args.dry_run:
        significant = [(eid, old, new, d) for eid, old, new, d in changes
                        if old is not None and abs(new - old) >= 1.0]
        if significant:
            print(f"\nSignificant changes (>= 1.0 delta):")
            for eid, old, new, _ in sorted(significant, key=lambda x: abs(x[2] - x[1]), reverse=True):
                print(f"  {eid:<40s} {old} -> {new} ({new - old:+.1f})")


if __name__ == "__main__":
    main()
