"""Tests for scripts/funding_scorer.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from funding_scorer import (
    CANONICAL_METRICS,
    DIFF_WEIGHTS,
    VIABILITY_WEIGHTS,
    display_blindspots,
    display_differentiation,
    display_pathways,
    display_viability,
    load_market_intelligence,
    load_startup_profile,
    run_pathway_scorer,
    score_ai_funding,
    score_arts_grants,
    score_blindspots,
    score_bootstrap,
    score_cloud_credits,
    score_competitions,
    score_consulting,
    score_crypto_grants,
    score_differentiation,
    score_fellowships,
    score_rbf,
    score_seed_vc,
    score_series_a,
    score_viability,
)

# --- Fixtures ---

EMPTY_PROFILE = {
    "revenue": {"mrr_usd": 0, "arr_usd": 0, "months_history": 0, "model": None, "burn_rate_monthly_usd": 0},
    "startup": {
        "ai_native": False, "sector": None, "open_source": False,
        "artistic_merit": False, "part_time_viable": False,
        "incorporated": False, "warm_intros_available": False,
        "prototype_ready": False, "vertical_ai": False,
        "proprietary_data": False, "multimodal": False,
        "defense_health_fintech": False, "public_benefit": False,
        "prior_grant_history": False, "exhibition_history": False,
        "institutional_partnership": False, "consulting_covers_expenses": False,
    },
    "founder": {
        "solo": True, "prior_exit": False, "technical": True,
        "years_experience": 0, "leadership_experience": False,
        "ai_ml_expertise": False, "domain_expert_advisor": False,
        "published_exhibited": False,
    },
    "runway": {"months": 0, "funding_source": "savings"},
    "legal": {
        "eighty_three_b_filed": False, "eighty_three_b_deadline_approaching": False,
        "delaware_franchise_tax_method": None, "ip_assignment_signed": False,
        "d_and_o_insurance": False,
    },
    "health": {"structured_breaks": False, "peer_support_group": False, "professional_support": False},
    "strategic": {
        "warm_intro_audit_done": False, "documentation_as_leverage": False,
        "open_source_strategy": False, "academic_partnership": False,
        "disability_grant_eligible": False, "climate_esg_framing": False,
        "eu_ai_act_compliant": False,
    },
}

EMPTY_INTEL = {}


# --- Pathway Scorers: valid score range ---


def test_score_rbf_returns_valid_range():
    result = score_rbf(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10
    assert "pathway" in result
    assert "eligible" in result


def test_score_rbf_high_mrr():
    profile = {**EMPTY_PROFILE, "revenue": {"mrr_usd": 50000, "arr_usd": 600000, "months_history": 24, "model": "saas", "burn_rate_monthly_usd": 5000}}
    result = score_rbf(profile, EMPTY_INTEL)
    assert result["score"] >= 7.0
    assert result["eligible"] is True
    assert len(result["providers"]) > 0


def test_score_seed_vc_returns_valid_range():
    result = score_seed_vc(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_seed_vc_ai_native_boost():
    profile = {
        **EMPTY_PROFILE,
        "startup": {**EMPTY_PROFILE["startup"], "ai_native": True, "warm_intros_available": True},
        "runway": {"months": 12, "funding_source": "savings"},
    }
    result = score_seed_vc(profile, EMPTY_INTEL)
    assert result["score"] >= 6.0


def test_score_series_a_returns_valid_range():
    result = score_series_a(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_ai_funding_returns_valid_range():
    result = score_ai_funding(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_ai_funding_vertical_boost():
    profile = {**EMPTY_PROFILE, "startup": {**EMPTY_PROFILE["startup"], "ai_native": True, "vertical_ai": True, "proprietary_data": True}}
    result = score_ai_funding(profile, EMPTY_INTEL)
    assert result["score"] >= 8.0


def test_score_crypto_grants_returns_valid_range():
    result = score_crypto_grants(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_arts_grants_returns_valid_range():
    result = score_arts_grants(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_bootstrap_returns_valid_range():
    result = score_bootstrap(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_cloud_credits_always_high():
    result = score_cloud_credits(EMPTY_PROFILE, EMPTY_INTEL)
    assert result["score"] == 9.0
    assert result["eligible"] is True


def test_score_fellowships_returns_valid_range():
    result = score_fellowships(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_competitions_returns_valid_range():
    result = score_competitions(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_consulting_returns_valid_range():
    result = score_consulting(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["score"] <= 10


def test_score_consulting_experienced():
    profile = {**EMPTY_PROFILE, "founder": {**EMPTY_PROFILE["founder"], "years_experience": 12, "leadership_experience": True, "ai_ml_expertise": True}}
    result = score_consulting(profile, EMPTY_INTEL)
    assert result["score"] == 10.0


# --- Pathway scorer: ranked output ---


def test_run_pathway_scorer_returns_11_results():
    results = run_pathway_scorer(EMPTY_PROFILE, EMPTY_INTEL)
    assert len(results) == 11


def test_run_pathway_scorer_sorted_descending():
    results = run_pathway_scorer(EMPTY_PROFILE, EMPTY_INTEL)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


# --- Viability Scorer ---


def test_viability_returns_0_to_100():
    result = score_viability(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["composite"] <= 100
    assert result["max"] == 100
    assert "band" in result


def test_viability_has_all_dimensions():
    result = score_viability(EMPTY_PROFILE, EMPTY_INTEL)
    for dim in VIABILITY_WEIGHTS:
        assert dim in result["dimensions"]


def test_viability_strong_profile():
    profile = {
        **EMPTY_PROFILE,
        "startup": {**EMPTY_PROFILE["startup"], "ai_native": True, "vertical_ai": True, "proprietary_data": True, "warm_intros_available": True},
        "founder": {**EMPTY_PROFILE["founder"], "prior_exit": True, "domain_expert_advisor": True},
        "revenue": {**EMPTY_PROFILE["revenue"], "model": "saas"},
        "runway": {"months": 24, "funding_source": "savings"},
        "strategic": {**EMPTY_PROFILE["strategic"], "eu_ai_act_compliant": True},
    }
    result = score_viability(profile, EMPTY_INTEL)
    assert result["composite"] >= 80
    assert "STRONG" in result["band"]


def test_viability_weights_sum_to_one():
    total = sum(VIABILITY_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001


# --- Differentiation Rubric ---


def test_differentiation_returns_7_dimensions():
    result = score_differentiation(EMPTY_PROFILE, EMPTY_INTEL)
    assert len(result["dimensions"]) == 7
    for dim in DIFF_WEIGHTS:
        assert dim in result["dimensions"]


def test_differentiation_dimensions_in_range():
    result = score_differentiation(EMPTY_PROFILE, EMPTY_INTEL)
    for dim, score in result["dimensions"].items():
        assert 0 <= score <= 10, f"{dim} out of range: {score}"


def test_differentiation_composite_in_range():
    result = score_differentiation(EMPTY_PROFILE, EMPTY_INTEL)
    assert 0 <= result["composite"] <= 10.0


def test_differentiation_gaps_returns_weakest():
    result = score_differentiation(EMPTY_PROFILE, EMPTY_INTEL)
    assert len(result["gaps"]) == 3
    gap_scores = [g[1] for g in result["gaps"]]
    assert gap_scores == sorted(gap_scores)


def test_differentiation_weights_sum_to_one():
    total = sum(DIFF_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001


# --- Blind Spots ---


def test_blindspots_returns_nonempty():
    result = score_blindspots(EMPTY_PROFILE, EMPTY_INTEL)
    assert result["total"] > 0
    assert len(result["categories"]) == 3


def test_blindspots_has_all_categories():
    result = score_blindspots(EMPTY_PROFILE, EMPTY_INTEL)
    assert "Legal & Financial" in result["categories"]
    assert "Health & Sustainability" in result["categories"]
    assert "Strategic" in result["categories"]


def test_blindspots_counts_correct():
    result = score_blindspots(EMPTY_PROFILE, EMPTY_INTEL)
    total = sum(len(items) for items in result["categories"].values())
    assert result["total"] == total


def test_blindspots_urgent_when_83b_approaching():
    profile = {**EMPTY_PROFILE, "legal": {**EMPTY_PROFILE["legal"], "eighty_three_b_deadline_approaching": True}}
    result = score_blindspots(profile, EMPTY_INTEL)
    assert len(result["urgent"]) > 0


# --- Profile Loading ---


def test_load_startup_profile_returns_all_sections():
    profile = load_startup_profile()
    for section in ("revenue", "startup", "founder", "runway", "legal", "health", "strategic"):
        assert section in profile


def test_load_startup_profile_missing_file_returns_defaults(monkeypatch, tmp_path):
    import funding_scorer as fs
    monkeypatch.setattr(fs, "PROFILE_FILE", tmp_path / "nonexistent.yaml")
    profile = load_startup_profile()
    assert profile["revenue"]["mrr_usd"] == 0
    assert profile["founder"]["solo"] is True


# --- Market Intelligence Loading ---


def test_load_market_intelligence_returns_dict():
    intel = load_market_intelligence()
    assert isinstance(intel, dict)


# --- Canonical Metrics ---


def test_canonical_metrics_values():
    assert CANONICAL_METRICS["repos"] == 103
    assert CANONICAL_METRICS["tests"] == 2349
    assert CANONICAL_METRICS["words"] == 810000
    assert CANONICAL_METRICS["essays"] == 42
    assert CANONICAL_METRICS["sprints"] == 33


# --- Display Function Smoke Tests ---


def test_display_pathways_no_crash(capsys):
    results = run_pathway_scorer(EMPTY_PROFILE, EMPTY_INTEL)
    display_pathways(results)
    captured = capsys.readouterr()
    assert "FUNDING PATHWAY DECISION TREE" in captured.out


def test_display_viability_no_crash(capsys):
    result = score_viability(EMPTY_PROFILE, EMPTY_INTEL)
    display_viability(result)
    captured = capsys.readouterr()
    assert "STARTUP VIABILITY SCORER" in captured.out


def test_display_differentiation_no_crash(capsys):
    result = score_differentiation(EMPTY_PROFILE, EMPTY_INTEL)
    display_differentiation(result)
    captured = capsys.readouterr()
    assert "DIFFERENTIATION RUBRIC" in captured.out


def test_display_blindspots_no_crash(capsys):
    result = score_blindspots(EMPTY_PROFILE, EMPTY_INTEL)
    display_blindspots(result)
    captured = capsys.readouterr()
    assert "BLIND SPOTS CHECKLIST" in captured.out
