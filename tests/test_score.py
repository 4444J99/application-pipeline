"""Tests for scripts/score.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from score import (
    WEIGHTS,
    WEIGHTS_JOB,
    PORTAL_SCORES,
    STRATEGIC_BASE,
    HIGH_PRESTIGE,
    QUALIFICATION_THRESHOLD,
    JOB_QUALIFICATION_THRESHOLD,
    ROLE_FIT_TIERS,
    get_weights,
    get_qualification_threshold,
    score_deadline_feasibility,
    score_financial_alignment,
    score_portal_friction,
    score_effort_to_value,
    score_strategic_value,
    estimate_human_dimensions,
    compute_dimensions,
    compute_composite,
    qualify,
)


def _date_offset(days: int) -> str:
    """Return an ISO date string offset from today."""
    return (date.today() + timedelta(days=days)).isoformat()


def _make_entry(
    track="grant",
    deadline_date=None,
    deadline_type="hard",
    amount_value=0,
    amount_cliff_note="",
    portal="custom",
    organization="Test Org",
    blocks_used=None,
    fit_score=5,
    framing="",
    existing_dims=None,
):
    """Build a minimal pipeline entry dict for scoring tests."""
    entry = {
        "track": track,
        "deadline": {
            "date": deadline_date,
            "type": deadline_type,
        },
        "amount": {
            "value": amount_value,
            "currency": "USD",
        },
        "target": {
            "organization": organization,
            "portal": portal,
        },
        "submission": {
            "blocks_used": blocks_used or {},
        },
        "fit": {
            "score": fit_score,
            "framing": framing,
        },
    }
    if amount_cliff_note:
        entry["amount"]["benefits_cliff_note"] = amount_cliff_note
    if existing_dims is not None:
        entry["fit"]["dimensions"] = existing_dims
    return entry


# --- WEIGHTS normalization ---


def test_weights_sum_to_one():
    """All dimension weights must sum to 1.0."""
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"


def test_weights_all_positive():
    """Every weight must be positive."""
    for dim, weight in WEIGHTS.items():
        assert weight > 0, f"Weight for {dim} is non-positive: {weight}"


def test_weights_cover_all_dimensions():
    """WEIGHTS should have exactly 8 dimensions."""
    assert len(WEIGHTS) == 8


# --- score_deadline_feasibility ---


def test_deadline_expired():
    """Expired deadlines should score 1."""
    entry = _make_entry(deadline_date=_date_offset(-5))
    assert score_deadline_feasibility(entry) == 1


def test_deadline_tomorrow():
    """Deadline tomorrow (1 day out) should score 2."""
    entry = _make_entry(deadline_date=_date_offset(1))
    assert score_deadline_feasibility(entry) == 2


def test_deadline_three_days():
    """Deadline in 3 days should score 3."""
    entry = _make_entry(deadline_date=_date_offset(3))
    assert score_deadline_feasibility(entry) == 3


def test_deadline_one_week():
    """Deadline in 5 days should score 5."""
    entry = _make_entry(deadline_date=_date_offset(5))
    assert score_deadline_feasibility(entry) == 5


def test_deadline_one_month():
    """Deadline in 20 days should score 8."""
    entry = _make_entry(deadline_date=_date_offset(20))
    assert score_deadline_feasibility(entry) == 8


def test_deadline_far_future():
    """Deadline 60+ days out should score 9."""
    entry = _make_entry(deadline_date=_date_offset(60))
    assert score_deadline_feasibility(entry) == 9


def test_deadline_rolling():
    """Rolling deadlines should score 9."""
    entry = _make_entry(deadline_type="rolling")
    assert score_deadline_feasibility(entry) == 9


def test_deadline_no_dict():
    """Non-dict deadline should return default 7."""
    entry = {"deadline": "2026-03-01"}
    assert score_deadline_feasibility(entry) == 7


# --- score_financial_alignment ---


def test_financial_zero_amount():
    """Zero amount is maximally safe (score 10)."""
    entry = _make_entry(amount_value=0)
    assert score_financial_alignment(entry) == 10


def test_financial_below_snap():
    """Amount below SNAP limit should score 9."""
    entry = _make_entry(amount_value=15000)
    assert score_financial_alignment(entry) == 9


def test_financial_between_snap_and_medicaid():
    """Amount between SNAP and Medicaid limits should score 8."""
    entry = _make_entry(amount_value=20500)
    assert score_financial_alignment(entry) == 8


def test_financial_above_essential_plan():
    """Amount above essential plan limit should score 4."""
    entry = _make_entry(amount_value=50000)
    assert score_financial_alignment(entry) == 4


def test_financial_exceeds_cliff_note():
    """Explicit 'exceeds' cliff note forces score to 4."""
    entry = _make_entry(amount_value=15000, amount_cliff_note="Exceeds SNAP threshold")
    assert score_financial_alignment(entry) == 4


def test_financial_essential_plan_cliff_note():
    """Explicit 'essential plan' cliff note forces score to 5."""
    entry = _make_entry(amount_value=15000, amount_cliff_note="Near essential plan limit")
    assert score_financial_alignment(entry) == 5


def test_financial_job_track_high_salary():
    """Job track with salary >$100K should score 8 (inverted logic)."""
    entry = _make_entry(track="job", amount_value=140000)
    assert score_financial_alignment(entry) == 8


def test_financial_job_track_very_high_salary():
    """Job track with salary >$150K should score 7."""
    entry = _make_entry(track="job", amount_value=300000)
    assert score_financial_alignment(entry) == 7


def test_financial_job_track_zero_salary():
    """Job track with unknown salary should score 6."""
    entry = _make_entry(track="job", amount_value=0)
    assert score_financial_alignment(entry) == 6


def test_financial_non_dict_amount():
    """Non-dict amount should return default 9."""
    entry = {"amount": "unknown"}
    assert score_financial_alignment(entry) == 9


# --- score_portal_friction ---


def test_portal_email():
    """Email portal is easiest (score 9)."""
    entry = _make_entry(portal="email")
    assert score_portal_friction(entry) == 9


def test_portal_slideroom():
    """SlideRoom portal is most friction (score 4)."""
    entry = _make_entry(portal="slideroom")
    assert score_portal_friction(entry) == 4


def test_portal_greenhouse():
    """Greenhouse portal should score 5."""
    entry = _make_entry(portal="greenhouse")
    assert score_portal_friction(entry) == 5


def test_portal_unknown():
    """Unknown portal type falls back to 6."""
    entry = _make_entry(portal="unknown-portal")
    assert score_portal_friction(entry) == 6


def test_portal_all_types_covered():
    """Every type in PORTAL_SCORES should return its mapped value."""
    for portal_type, expected_score in PORTAL_SCORES.items():
        entry = _make_entry(portal=portal_type)
        assert score_portal_friction(entry) == expected_score, (
            f"Portal type '{portal_type}' expected {expected_score}"
        )


# --- score_effort_to_value ---


def test_effort_emergency_track():
    """Emergency track has high base score."""
    entry = _make_entry(track="emergency")
    score = score_effort_to_value(entry)
    assert score >= 6


def test_effort_job_track():
    """Job track has moderate base score (CLI-submittable)."""
    entry = _make_entry(track="job")
    score = score_effort_to_value(entry)
    assert score >= 5


def test_effort_high_block_coverage():
    """High blocks coverage adds a bonus."""
    entry_no_blocks = _make_entry(track="grant", amount_value=10000)
    entry_with_blocks = _make_entry(
        track="grant",
        amount_value=10000,
        blocks_used={
            "artist_statement": "identity/2min",
            "project_description": "projects/organvm-system",
            "bio": "identity/60s",
            "cv": "evidence/metrics-snapshot",
            "work_samples": "evidence/work-samples",
            "methodology": "methodology/ai-conductor",
        },
    )
    score_low = score_effort_to_value(entry_no_blocks)
    score_high = score_effort_to_value(entry_with_blocks)
    assert score_high > score_low


def test_effort_high_value_boost():
    """Amount >= 50000 gets a score boost."""
    entry_low = _make_entry(track="grant", amount_value=10000)
    entry_high = _make_entry(track="grant", amount_value=50000)
    score_low = score_effort_to_value(entry_low)
    score_high = score_effort_to_value(entry_high)
    assert score_high >= score_low


# --- score_strategic_value ---


def test_strategic_high_prestige_org():
    """High-prestige org should return its mapped score."""
    entry = _make_entry(organization="Creative Capital")
    assert score_strategic_value(entry) == HIGH_PRESTIGE["Creative Capital"]


def test_strategic_high_prestige_case_insensitive():
    """Prestige matching should be case-insensitive."""
    entry = _make_entry(organization="creative capital foundation")
    assert score_strategic_value(entry) == HIGH_PRESTIGE["Creative Capital"]


def test_strategic_fallback_to_track():
    """Unknown org falls back to track-based score."""
    entry = _make_entry(organization="Unknown Org", track="prize")
    assert score_strategic_value(entry) == STRATEGIC_BASE["prize"]


def test_strategic_unknown_track():
    """Unknown track returns default 5."""
    entry = _make_entry(organization="Unknown Org", track="unknown")
    assert score_strategic_value(entry) == 5


# --- estimate_human_dimensions ---


def test_human_dims_with_framing():
    """Framing longer than 30 chars boosts mission_alignment by 1."""
    entry = _make_entry(fit_score=6, framing="A detailed framing that exceeds thirty characters")
    dims = estimate_human_dimensions(entry)
    assert dims["mission_alignment"] == 7  # 6 + 1 for framing


def test_human_dims_without_framing():
    """No framing reduces mission_alignment by 1."""
    entry = _make_entry(fit_score=6, framing="")
    dims = estimate_human_dimensions(entry)
    assert dims["mission_alignment"] == 5  # 6 - 1 for no framing


def test_human_dims_high_block_coverage():
    """5+ blocks boosts evidence_match by 1."""
    entry = _make_entry(
        fit_score=6,
        blocks_used={
            "a": "x", "b": "x", "c": "x", "d": "x", "e": "x",
        },
    )
    dims = estimate_human_dimensions(entry)
    assert dims["evidence_match"] == 7  # 6 + 1


def test_human_dims_zero_blocks():
    """Zero blocks reduces evidence_match by 2."""
    entry = _make_entry(fit_score=6)
    dims = estimate_human_dimensions(entry)
    assert dims["evidence_match"] == 4  # 6 - 2


def test_human_dims_job_track_no_penalty():
    """Job track no longer has a blanket track_record_fit penalty."""
    entry = _make_entry(fit_score=6, track="job")
    dims = estimate_human_dimensions(entry)
    assert dims["track_record_fit"] == 6  # no penalty


def test_human_dims_clamped_to_range():
    """Scores should be clamped to [1, 10]."""
    # Very low base score with penalties
    entry = _make_entry(fit_score=1, track="job")
    dims = estimate_human_dimensions(entry)
    assert dims["track_record_fit"] >= 1
    assert dims["mission_alignment"] >= 1
    assert dims["evidence_match"] >= 1

    # Very high base score with bonuses
    entry_high = _make_entry(
        fit_score=10,
        framing="A very long framing string that exceeds thirty characters easily",
        blocks_used={"a": "x", "b": "x", "c": "x", "d": "x", "e": "x"},
    )
    dims_high = estimate_human_dimensions(entry_high)
    assert dims_high["mission_alignment"] <= 10
    assert dims_high["evidence_match"] <= 10


# --- compute_dimensions ---


def test_compute_dimensions_returns_all_eight():
    """compute_dimensions should return all 8 dimension keys."""
    entry = _make_entry()
    dims = compute_dimensions(entry)
    assert set(dims.keys()) == set(WEIGHTS.keys())


def test_compute_dimensions_preserves_human_overrides():
    """Existing human-judgment dimensions should be preserved, not re-estimated."""
    entry = _make_entry(
        fit_score=5,
        existing_dims={
            "mission_alignment": 9,
            "evidence_match": 8,
            "track_record_fit": 7,
        },
    )
    dims = compute_dimensions(entry)
    assert dims["mission_alignment"] == 9
    assert dims["evidence_match"] == 8
    assert dims["track_record_fit"] == 7


def test_compute_dimensions_auto_dims_recomputed():
    """Auto-derivable dimensions should be recomputed even if existing."""
    entry = _make_entry(
        portal="email",
        existing_dims={
            "portal_friction": 1,  # stale override — should be ignored
        },
    )
    dims = compute_dimensions(entry)
    assert dims["portal_friction"] == PORTAL_SCORES["email"]  # recomputed to 9


# --- compute_composite ---


def test_composite_perfect_ten():
    """All 10s should produce composite 10.0."""
    dims = {dim: 10 for dim in WEIGHTS}
    assert compute_composite(dims) == 10.0


def test_composite_all_ones():
    """All 1s should produce composite 1.0."""
    dims = {dim: 1 for dim in WEIGHTS}
    assert compute_composite(dims) == 1.0


def test_composite_weighted_sum():
    """Verify composite is the correct weighted sum."""
    dims = {
        "mission_alignment": 8,
        "evidence_match": 7,
        "track_record_fit": 6,
        "financial_alignment": 9,
        "effort_to_value": 5,
        "strategic_value": 7,
        "deadline_feasibility": 4,
        "portal_friction": 6,
    }
    expected = round(
        8 * 0.25 + 7 * 0.20 + 6 * 0.15 + 9 * 0.10
        + 5 * 0.10 + 7 * 0.10 + 4 * 0.05 + 6 * 0.05,
        1,
    )
    assert compute_composite(dims) == expected


def test_composite_missing_dim_defaults_to_five():
    """Missing dimension should default to 5 in the weighted sum."""
    dims = {"mission_alignment": 10}  # only one dim provided
    result = compute_composite(dims)
    expected = round(10 * 0.25 + 5 * 0.75, 1)  # rest default to 5
    assert result == expected


# --- qualify ---


def test_qualification_threshold_is_reasonable():
    """QUALIFICATION_THRESHOLD should be between 1 and 10."""
    assert 1.0 <= QUALIFICATION_THRESHOLD <= 10.0


def test_qualify_above_threshold():
    """Entry scoring above threshold should return (True, reason)."""
    entry = _make_entry(
        fit_score=8,
        framing="Strong framing that exceeds thirty chars easily",
        blocks_used={"a": "x", "b": "x", "c": "x", "d": "x", "e": "x"},
        organization="Creative Capital",
        deadline_type="rolling",
    )
    should_apply, reason = qualify(entry)
    assert should_apply is True
    assert ">=" in reason


def test_qualify_below_threshold():
    """Entry scoring below threshold should return (False, reason with weak dims)."""
    entry = _make_entry(
        fit_score=1,
        track="job",
        amount_value=100000,
        portal="slideroom",
        deadline_date=_date_offset(-5),
    )
    should_apply, reason = qualify(entry)
    assert should_apply is False
    assert "<" in reason
    assert "weak:" in reason


def test_qualify_boundary():
    """Entry exactly at threshold should return APPLY."""
    # Build an entry that scores exactly at threshold — we just need to
    # verify the >= comparison handles the boundary correctly.
    entry = _make_entry(fit_score=5, deadline_type="rolling")
    dims = compute_dimensions(entry)
    composite = compute_composite(dims)

    should_apply, _ = qualify(entry)
    if composite >= QUALIFICATION_THRESHOLD:
        assert should_apply is True
    else:
        assert should_apply is False


# --- Job rubric weights ---


def test_weights_job_sum_to_one():
    """Job dimension weights must sum to 1.0."""
    total = sum(WEIGHTS_JOB.values())
    assert abs(total - 1.0) < 1e-9, f"Job weights sum to {total}, expected 1.0"


def test_weights_job_all_positive():
    """Every job weight must be positive."""
    for dim, weight in WEIGHTS_JOB.items():
        assert weight > 0, f"Job weight for {dim} is non-positive: {weight}"


def test_weights_job_cover_all_dimensions():
    """WEIGHTS_JOB should have the same 8 dimensions as WEIGHTS."""
    assert set(WEIGHTS_JOB.keys()) == set(WEIGHTS.keys())


def test_get_weights_job():
    """get_weights returns job weights for track='job'."""
    assert get_weights("job") is WEIGHTS_JOB


def test_get_weights_creative():
    """get_weights returns creative weights for non-job tracks."""
    for track in ("grant", "fellowship", "residency", "writing", ""):
        assert get_weights(track) is WEIGHTS


def test_get_qualification_threshold_job():
    """Job track uses JOB_QUALIFICATION_THRESHOLD."""
    assert get_qualification_threshold("job") == JOB_QUALIFICATION_THRESHOLD


def test_get_qualification_threshold_creative():
    """Non-job tracks use QUALIFICATION_THRESHOLD."""
    for track in ("grant", "fellowship", "residency", ""):
        assert get_qualification_threshold(track) == QUALIFICATION_THRESHOLD


# --- Job composite scoring ---


def test_composite_job_weights():
    """Job entry should use WEIGHTS_JOB for composite calculation."""
    dims = {
        "mission_alignment": 8,
        "evidence_match": 7,
        "track_record_fit": 6,
        "financial_alignment": 6,
        "effort_to_value": 5,
        "strategic_value": 8,
        "deadline_feasibility": 9,
        "portal_friction": 5,
    }
    job_score = compute_composite(dims, "job")
    creative_score = compute_composite(dims, "grant")

    # Manually compute expected job score
    expected_job = round(
        8 * 0.35 + 7 * 0.25 + 6 * 0.15 + 8 * 0.10
        + 6 * 0.05 + 5 * 0.05 + 9 * 0.03 + 5 * 0.02,
        1,
    )
    assert job_score == expected_job

    # Job and creative scores should differ with these unequal dims
    assert job_score != creative_score


def test_composite_creative_weights():
    """Non-job entry should use WEIGHTS (creative) for composite."""
    dims = {
        "mission_alignment": 8,
        "evidence_match": 7,
        "track_record_fit": 6,
        "financial_alignment": 9,
        "effort_to_value": 5,
        "strategic_value": 7,
        "deadline_feasibility": 4,
        "portal_friction": 6,
    }
    expected = round(
        8 * 0.25 + 7 * 0.20 + 6 * 0.15 + 9 * 0.10
        + 5 * 0.10 + 7 * 0.10 + 4 * 0.05 + 6 * 0.05,
        1,
    )
    assert compute_composite(dims, "grant") == expected
    assert compute_composite(dims, "") == expected
    assert compute_composite(dims) == expected


# --- Job qualification threshold ---


def test_qualify_job_threshold():
    """Job entry should use JOB_QUALIFICATION_THRESHOLD (5.5)."""
    # Build a job entry that scores between 5.0 and 5.5
    # This should SKIP under job threshold but would APPLY under creative
    entry = _make_entry(
        track="job",
        fit_score=5,
        portal="greenhouse",
        deadline_type="rolling",
        organization="Unknown Corp",
    )
    dims = compute_dimensions(entry)
    job_composite = compute_composite(dims, "job")

    should_apply, reason = qualify(entry)

    # Verify the threshold used is the job one
    assert str(JOB_QUALIFICATION_THRESHOLD) in reason or str(QUALIFICATION_THRESHOLD) not in reason.replace(str(JOB_QUALIFICATION_THRESHOLD), "")
    if job_composite >= JOB_QUALIFICATION_THRESHOLD:
        assert should_apply is True
    else:
        assert should_apply is False


def test_qualify_creative_threshold():
    """Creative entry should use QUALIFICATION_THRESHOLD (5.0)."""
    entry = _make_entry(
        track="grant",
        fit_score=5,
        deadline_type="rolling",
    )
    should_apply, reason = qualify(entry)
    assert str(QUALIFICATION_THRESHOLD) in reason


# --- Job tier scoring with job weights ---


def test_job_tier1_scores_above_threshold():
    """Tier-1 auto-sourced job (e.g. agent SDK) should score well above threshold with raised ceilings."""
    entry = _make_entry(
        track="job",
        fit_score=1,
        organization="Anthropic",
        portal="greenhouse",
        deadline_type="rolling",
    )
    entry["name"] = "Software Engineer, Agent SDK"
    entry["tags"] = ["auto-sourced"]
    # Force auto-sourced path (score <= 1)
    dims = compute_dimensions(entry)
    composite = compute_composite(dims, "job")
    # With raised tier-1 ceilings (9/9/7), composite should be >= 8.0
    assert composite >= 8.0, (
        f"Tier-1 job scored {composite}, expected >= 8.0"
    )


def test_job_tier1_with_blocks_scores_high():
    """Tier-1 auto-sourced job with 5 blocks wired should get evidence bonus."""
    entry = _make_entry(
        track="job",
        fit_score=1,
        organization="Anthropic",
        portal="greenhouse",
        deadline_type="rolling",
        blocks_used={
            "framing": "framings/independent-engineer",
            "evidence": "evidence/differentiators",
            "work_samples": "evidence/work-samples",
            "credentials": "pitches/credentials-creative-tech",
            "methodology": "methodology/ai-conductor",
        },
    )
    entry["name"] = "Software Engineer, Agent SDK"
    entry["tags"] = ["auto-sourced"]
    dims = compute_dimensions(entry)
    composite = compute_composite(dims, "job")
    # With blocks wired (5 blocks → evidence bonus) + raised ceilings, composite >= 8.5
    # Auto-derived dims (financial=6, portal=5) pull the composite below 9.0
    assert composite >= 8.5, (
        f"Tier-1 job with blocks scored {composite}, expected >= 8.5"
    )


def test_job_tier1_dimension_values():
    """Tier-1 dimension values should reflect raised ceilings (9/9/7)."""
    tier1 = next(t for t in ROLE_FIT_TIERS if t["name"] == "tier-1-strong")
    assert tier1["mission_alignment"] == 9
    assert tier1["evidence_match"] == 9
    assert tier1["track_record_fit"] == 7


def test_job_tier2_dimension_values():
    """Tier-2 dimension values should reflect raised ceilings (7/6/5)."""
    tier2 = next(t for t in ROLE_FIT_TIERS if t["name"] == "tier-2-moderate")
    assert tier2["mission_alignment"] == 7
    assert tier2["evidence_match"] == 6
    assert tier2["track_record_fit"] == 5


def test_job_tier4_scores_below_threshold():
    """Tier-4 auto-sourced job (e.g. iOS) should score below 5.5 with job weights."""
    entry = _make_entry(
        track="job",
        fit_score=1,
        organization="Anthropic",
        portal="greenhouse",
        deadline_type="rolling",
    )
    entry["name"] = "Software Engineer, iOS"
    entry["tags"] = ["auto-sourced"]
    dims = compute_dimensions(entry)
    composite = compute_composite(dims, "job")
    assert composite < JOB_QUALIFICATION_THRESHOLD, (
        f"Tier-4 job scored {composite}, expected < {JOB_QUALIFICATION_THRESHOLD}"
    )
