"""Signal-based human dimension scoring.

Extracted from score.py to keep signal logic isolated and testable.
"""

from __future__ import annotations

from pathlib import Path

from pipeline_lib import (
    BLOCKS_DIR,
    load_market_intelligence,
    load_profile,
)
from pipeline_lib import (
    load_entries as _load_entries_raw,
)
from score_constants import ROLE_FIT_TIERS
from score_text_match import (
    evidence_match_text_signal as _em_text_coverage,
)
from score_text_match import (
    mission_alignment_text_signal as _ma_text_alignment,
)
from score_text_match import (
    track_record_text_signal as _tr_text_fit,
)

# Track-position affinity: how well each identity position fits each track.
TRACK_POSITION_AFFINITY = {
    "grant": {"systems-artist": 3, "creative-technologist": 2, "community-practitioner": 2, "educator": 1, "independent-engineer": 1},
    "residency": {"systems-artist": 3, "creative-technologist": 3, "community-practitioner": 2, "educator": 1, "independent-engineer": 1},
    "prize": {"systems-artist": 3, "creative-technologist": 2, "community-practitioner": 1, "educator": 1, "independent-engineer": 1},
    "fellowship": {"systems-artist": 2, "creative-technologist": 3, "community-practitioner": 2, "educator": 2, "independent-engineer": 2},
    "program": {"systems-artist": 2, "creative-technologist": 2, "community-practitioner": 3, "educator": 2, "independent-engineer": 2},
    "writing": {"systems-artist": 1, "creative-technologist": 2, "community-practitioner": 3, "educator": 2, "independent-engineer": 1},
    "emergency": {"systems-artist": 2, "creative-technologist": 1, "community-practitioner": 3, "educator": 1, "independent-engineer": 1},
    "consulting": {"systems-artist": 1, "creative-technologist": 2, "community-practitioner": 1, "educator": 1, "independent-engineer": 3},
}

# Expected organs for each identity position.
POSITION_EXPECTED_ORGANS = {
    "systems-artist": {"I", "II", "META"},
    "creative-technologist": {"I", "III", "IV"},
    "community-practitioner": {"V", "VI", "META"},
    "educator": {"V", "VI"},
    "independent-engineer": {"III", "IV"},
}

# Credential relevance per track.
CREDENTIALS = {
    "mfa_creative_writing": {
        "writing": 4,
        "grant": 3,
        "residency": 3,
        "prize": 3,
        "program": 2,
        "fellowship": 2,
        "emergency": 2,
        "consulting": 1,
    },
    "meta_fullstack_dev": {
        "consulting": 4,
        "fellowship": 3,
        "program": 3,
        "grant": 1,
        "residency": 1,
        "prize": 1,
        "writing": 1,
        "emergency": 1,
    },
    "teaching_11yr": {
        "program": 4,
        "fellowship": 3,
        "residency": 2,
        "writing": 2,
        "grant": 2,
        "prize": 1,
        "emergency": 1,
        "consulting": 2,
    },
    "construction_pm": {
        "consulting": 3,
        "grant": 1,
        "residency": 1,
        "prize": 0,
        "fellowship": 1,
        "program": 1,
        "writing": 0,
        "emergency": 1,
    },
}


def estimate_role_fit_from_title(entry: dict) -> dict[str, int]:
    """Estimate human dimensions from job title for auto-sourced entries.

    Checks disqualifiers (tier-4) first — if a title contains both a positive
    pattern ("developer productivity") and a negative one ("android"), the
    negative wins. This prevents misclassification of roles like
    "Android Engineer, Developer Productivity" as DevEx roles.
    """
    name = (entry.get("name") or "").lower()

    # Build a map of tier name -> tier for lookup
    tier_by_name = {t["name"]: t for t in ROLE_FIT_TIERS}

    # Phase 1: Check disqualifiers first (tier-4-poor)
    poor = tier_by_name.get("tier-4-poor")
    if poor:
        for pattern in poor["title_patterns"]:
            if pattern in name:
                return {
                    "mission_alignment": poor["mission_alignment"],
                    "evidence_match": poor["evidence_match"],
                    "track_record_fit": poor["track_record_fit"],
                }

    # Phase 2: Check remaining tiers in priority order (tier-1 first)
    for tier in ROLE_FIT_TIERS:
        if tier["name"] == "tier-4-poor":
            continue  # Already checked
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
    if Path(framing_path).exists():
        return 2, f"framings/{position}.md exists -> 2"
    return 1, f"position {position} set but no framings/{position}.md -> 1"


def _tr_differentiators_coverage(entry: dict, profile: dict | None) -> tuple[int, str]:
    """Signal 4: Does the profile have enough evidence highlights?"""
    del entry
    if not profile:
        return 0, "no profile -> 0"

    highlights = profile.get("evidence_highlights") or []
    if len(highlights) >= 3:
        return 1, f"{len(highlights)} evidence_highlights >= 3 -> 1"
    return 0, f"{len(highlights)} evidence_highlights < 3 -> 0"


def compute_human_dimensions(
    entry: dict,
    all_entries: list[dict] | None = None,
    explain: bool = False,
) -> dict[str, int] | tuple[dict[str, int], dict[str, str]]:
    """Compute mission_alignment, evidence_match, track_record_fit from signals."""
    tags = entry.get("tags") or []

    if "auto-sourced" in tags:
        # Prefer corpus-driven scoring from job description
        description = (entry.get("target", {}).get("description", "") or "")
        if len(description.strip()) >= 50:
            from score_text_match import score_description_against_corpus

            base = score_description_against_corpus(description)
        else:
            # Fallback to title-pattern matching when no description available
            base = estimate_role_fit_from_title(entry)
        submission = entry.get("submission", {})
        blocks_count = len(submission.get("blocks_used", {}) or {}) if isinstance(submission, dict) else 0
        if blocks_count >= 5:
            base["evidence_match"] = min(10, base["evidence_match"] + 1)

        intel = load_market_intelligence()
        hot_skills = intel.get("skills_signals", {}).get("hot_2026", [])
        hot_match_count = 0
        if hot_skills:
            submission = entry.get("submission", {})
            block_keys = " ".join(
                (submission.get("blocks_used") or {}).keys()
            ).lower() if isinstance(submission, dict) else ""
            keywords_list = submission.get("keywords", []) if isinstance(submission, dict) else []
            keywords_str = " ".join(str(k).lower() for k in (keywords_list or []))
            job_tags = " ".join(t.lower() for t in (entry.get("tags") or []))
            hot_match_count = sum(
                1
                for skill in hot_skills
                if skill.lower() in block_keys
                or skill.lower() in keywords_str
                or skill.lower() in job_tags
            )
            if hot_match_count >= 1:
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
            for key, val in base.items():
                suffix = ""
                if key == "evidence_match" and hot_match_count >= 1:
                    suffix = f" + hot_skills_match={hot_match_count}"
                explanations[key] = f"auto-sourced, {tier_name} -> {val}{suffix}"
            return base, explanations
        return base

    if all_entries is None:
        all_entries = [e for e in _load_entries_raw()]

    entry_id = entry.get("id", "")
    profile = load_profile(entry_id)

    ma1_score, ma1_reason = _ma_position_profile_match(entry, profile)
    ma2_score, ma2_reason = _ma_track_position_affinity(entry)
    ma3_score, ma3_reason = _ma_organ_position_coherence(entry)
    ma4_score, ma4_reason = _ma_framing_specialization(entry)
    ma5_score, ma5_reason = _ma_text_alignment(entry)
    mission = max(1, min(10, ma1_score + ma2_score + ma3_score + ma4_score + ma5_score))

    em1_score, em1_reason = _em_block_portal_coverage(entry)
    em2_score, em2_reason = _em_slot_name_alignment(entry)
    em3_score, em3_reason = _em_evidence_depth(entry)
    em4_score, em4_reason = _em_materials_readiness(entry)
    em5_score, em5_reason = _em_text_coverage(entry)
    evidence = max(1, min(10, em1_score + em2_score + em3_score + em4_score + em5_score))

    tr1_score, tr1_reason = _tr_credential_track_relevance(entry)
    tr2_score, tr2_reason = _tr_track_experience(entry, all_entries)
    tr3_score, tr3_reason = _tr_position_depth(entry)
    tr4_score, tr4_reason = _tr_differentiators_coverage(entry, profile)
    tr5_score, tr5_reason = _tr_text_fit(entry)
    track_record = max(1, min(10, tr1_score + tr2_score + tr3_score + tr4_score + tr5_score))

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
                f"  text alignment:          {ma5_score}  <- {ma5_reason}",
            ]),
            "evidence_match": "\n".join([
                f"  block-portal coverage:   {em1_score}  <- {em1_reason}",
                f"  slot name alignment:     {em2_score}  <- {em2_reason}",
                f"  evidence depth:          {em3_score}  <- {em3_reason}",
                f"  materials readiness:     {em4_score}  <- {em4_reason}",
                f"  text coverage:           {em5_score}  <- {em5_reason}",
            ]),
            "track_record_fit": "\n".join([
                f"  credential-track:        {tr1_score}  <- {tr1_reason}",
                f"  track experience:        {tr2_score}  <- {tr2_reason}",
                f"  position depth:          {tr3_score}  <- {tr3_reason}",
                f"  differentiators:         {tr4_score}  <- {tr4_reason}",
                f"  text fit:                {tr5_score}  <- {tr5_reason}",
            ]),
        }
        return result, explanations

    return result
