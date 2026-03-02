#!/usr/bin/env python3
"""Funding pathway scorer — executable decision frameworks from research data.

Implements four algorithmic frameworks synthesized from 262 sources
(see strategy/funding-landscape-2026.md). All parameters are read from
strategy/market-intelligence-2026.json with conservative fallback defaults.

Usage:
    python scripts/funding_scorer.py --pathway          # Ranked funding pathways
    python scripts/funding_scorer.py --viability         # Startup viability (0-100)
    python scripts/funding_scorer.py --differentiation   # Differentiation rubric (0-10)
    python scripts/funding_scorer.py --blindspots        # Blind spots checklist
    python scripts/funding_scorer.py --all               # All four reports
"""

import argparse
import sys
from pathlib import Path

import yaml
from score import load_market_intelligence

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
PROFILE_FILE = REPO_ROOT / "strategy" / "startup-profile.yaml"


def load_startup_profile() -> dict:
    """Load strategy/startup-profile.yaml, return defaults when missing."""
    defaults = {
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
    if not PROFILE_FILE.exists():
        return defaults
    try:
        with open(PROFILE_FILE) as f:
            data = yaml.safe_load(f) or {}
        # Merge loaded data over defaults (one level deep)
        for section, section_defaults in defaults.items():
            if section in data and isinstance(data[section], dict):
                merged = dict(section_defaults)
                merged.update(data[section])
                defaults[section] = merged
        return defaults
    except Exception:
        return defaults


def _g(d: dict, *keys, default=None):
    """Nested dict getter: _g(d, 'a', 'b') == d.get('a', {}).get('b', default)."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
        if d is default:
            return default
    return d


# --- 1. Funding Pathway Decision Tree ---

def score_rbf(profile: dict, intel: dict) -> dict:
    """Revenue-Based Financing score (Section 3.1)."""
    rev = profile.get("revenue", {})
    mrr = rev.get("mrr_usd", 0) or 0
    months = rev.get("months_history", 0) or 0
    burn = rev.get("burn_rate_monthly_usd", 0) or 0
    model = rev.get("model")

    score = 6.0
    score += min((mrr / 10000) * 0.5, 2.0)
    score += min((months / 12) * 1.0, 1.0)
    if mrr > 0:
        score -= min((burn / mrr) * 0.5, 1.5)
    if model == "saas":
        score += 0.5

    providers = []
    if mrr >= 10000:
        providers.append("Pipe ($25K-$100M, 1% fee)")
    arr = rev.get("arr_usd", 0) or 0
    if arr >= 1000000 and months >= 8:
        providers.append("Capchase ($25K-$10M)")
    elif arr >= 100000 and months >= 8:
        providers.append("Capchase (basic tier)")
    if mrr * 12 >= 100000 and months >= 12:
        providers.append("Clearco (6-12.5% fee)")

    eligible = mrr >= 10000
    return {
        "pathway": "Revenue-Based Financing",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": eligible,
        "providers": providers,
        "action": "Apply to matched RBF providers" if eligible else "Need $10K+ MRR first",
    }


def score_seed_vc(profile: dict, intel: dict) -> dict:
    """Seed VC score (Section 3.2)."""
    rev = profile.get("revenue", {})
    startup = profile.get("startup", {})
    founder = profile.get("founder", {})
    runway = profile.get("runway", {})

    score = 4.0
    if startup.get("ai_native"):
        score += 2.0
    if startup.get("warm_intros_available"):
        score += 1.5
    arr = rev.get("arr_usd", 0) or 0
    if 300000 <= arr <= 500000:
        score += 1.0
    if founder.get("solo") and founder.get("prior_exit"):
        score += 0.5
    if not startup.get("ai_native") and not startup.get("vertical_ai"):
        score -= 1.0
    runway_months = runway.get("months", 0) or 0
    if runway_months < 6:
        score -= 0.5 * (6 - runway_months)

    seed = _g(intel, "startup_funding_landscape", "seed_metrics", default={})
    closing_days = seed.get("closing_days_median", 142)

    final_score = round(max(0, min(score, 10)), 1)
    return {
        "pathway": "Seed VC",
        "score": final_score,
        "eligible": final_score >= 6.0,
        "providers": [],
        "action": f"Pursue actively (plan {closing_days}-day close)" if final_score >= 6.0 else "Strengthen position first",
    }


def score_series_a(profile: dict, intel: dict) -> dict:
    """Series A score (Section 3.3)."""
    rev = profile.get("revenue", {})
    startup = profile.get("startup", {})

    score = 3.0
    arr = rev.get("arr_usd", 0) or 0
    if 1000000 <= arr <= 5000000:
        score += 2.5
    if startup.get("ai_native"):
        score += 1.0

    return {
        "pathway": "Series A",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": score >= 7.0,
        "providers": [],
        "action": "Pursue actively" if score >= 7.0 else "Hit $1M+ ARR first",
    }


def score_ai_funding(profile: dict, intel: dict) -> dict:
    """AI-Specific Funding score (Section 3.4)."""
    startup = profile.get("startup", {})
    founder = profile.get("founder", {})

    score = 7.0
    if startup.get("vertical_ai"):
        score += 1.5
    if startup.get("proprietary_data"):
        score += 1.0
    if startup.get("multimodal"):
        score += 0.5
    if startup.get("defense_health_fintech"):
        score += 0.5
    if not startup.get("vertical_ai") and not startup.get("proprietary_data"):
        score -= 3.0  # wrapper penalty
    if not founder.get("technical") and not founder.get("domain_expert_advisor"):
        score -= 1.0

    credits = _g(intel, "non_dilutive_funding", "cloud_credits", default={})
    cloud_total = sum([
        credits.get("microsoft_founders_hub_usd", 150000),
        credits.get("aws_activate_ai_usd", 300000),
        credits.get("google_cloud_ai_usd", 350000),
        credits.get("nvidia_inception_aws_usd", 100000),
    ])

    return {
        "pathway": "AI-Specific Funding",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": startup.get("ai_native", False),
        "providers": [f"Cloud credits: ${cloud_total:,} available"],
        "action": "Apply to all cloud credit programs simultaneously",
    }


def score_crypto_grants(profile: dict, intel: dict) -> dict:
    """Crypto / Web3 Grants score (Section 3.5)."""
    startup = profile.get("startup", {})

    score = 5.0
    if startup.get("open_source") and startup.get("public_benefit"):
        score += 2.0
    if startup.get("prior_grant_history"):
        score += 1.0
    if not startup.get("public_benefit"):
        score -= 2.0

    providers = ["Gitcoin (quadratic funding, through ~2029)", "Ethereum ESP ($5K-$500K, rolling)", "Optimism RPGF (retroactive)"]
    return {
        "pathway": "Crypto / Web3 Grants",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": startup.get("open_source", False) and startup.get("public_benefit", False),
        "providers": providers,
        "action": "Apply to Ethereum ESP + build for Optimism RPGF",
    }


def score_arts_grants(profile: dict, intel: dict) -> dict:
    """Arts/Creative Grants score (Section 3.6)."""
    startup = profile.get("startup", {})
    founder = profile.get("founder", {})

    score = 5.0
    if startup.get("artistic_merit") and startup.get("public_benefit"):
        score += 2.0  # dual alignment
    if founder.get("published_exhibited"):
        score += 1.5
    if startup.get("prior_grant_history"):
        score += 1.0
    if startup.get("institutional_partnership"):
        score += 0.5
    if not startup.get("prior_grant_history"):
        score -= 1.0
    if not startup.get("exhibition_history"):
        score -= 0.5

    # Read deadlines from grant calendar if available
    cal = intel.get("grant_calendar", {})
    cc_closes = _g(cal, "creative_capital_2027", "closes", default="TBD")
    lacma_closes = _g(cal, "lacma_art_tech_2026", "closes", default="TBD")

    return {
        "pathway": "Arts / Creative Grants",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": startup.get("artistic_merit", False),
        "providers": ["Creative Capital (~5%)", "LACMA Art+Tech (3-5 projects)", "S+T+ARTS (2 prizes)", "Awesome Foundation (20-30%)"],
        "action": f"Apply to Creative Capital (closes {cc_closes}) + LACMA (closes {lacma_closes})",
    }


def score_bootstrap(profile: dict, intel: dict) -> dict:
    """Bootstrap score (Section 3.7)."""
    startup = profile.get("startup", {})
    founder = profile.get("founder", {})

    score = 6.0
    if startup.get("consulting_covers_expenses"):
        score += 2.0
    if startup.get("ai_native"):
        score += 1.5  # AI reduces build time
    if startup.get("part_time_viable"):
        score += 1.0
    if founder.get("solo"):
        score += 0.5  # 42% of $1M+ companies

    return {
        "pathway": "Bootstrap",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": True,
        "providers": [],
        "action": "Build MVP in 2-4 weeks with AI assistance",
    }


def score_cloud_credits(profile: dict, intel: dict) -> dict:
    """Cloud Credits score (Section 3.8) — always pursue."""
    credits = _g(intel, "non_dilutive_funding", "cloud_credits", default={})
    total = sum([
        credits.get("microsoft_founders_hub_usd", 150000),
        credits.get("aws_activate_usd", 100000),
        credits.get("google_cloud_ai_usd", 350000),
        credits.get("nvidia_inception_aws_usd", 100000),
    ])

    return {
        "pathway": "Cloud Credits",
        "score": 9.0,  # always high — non-exclusive, additive
        "eligible": True,
        "providers": [
            f"Microsoft Founders Hub: ${credits.get('microsoft_founders_hub_usd', 150000):,}",
            f"AWS Activate: ${credits.get('aws_activate_usd', 100000):,} (AI: ${credits.get('aws_activate_ai_usd', 300000):,})",
            f"Google Cloud: ${credits.get('google_cloud_ai_usd', 350000):,}",
            f"NVIDIA Inception: ${credits.get('nvidia_inception_aws_usd', 100000):,}",
        ],
        "action": f"Apply to all 4 simultaneously — ${total:,}+ available",
    }


def score_fellowships(profile: dict, intel: dict) -> dict:
    """Fellowship score (Section 3.9)."""
    startup = profile.get("startup", {})
    founder = profile.get("founder", {})

    score = 5.0
    if founder.get("published_exhibited"):
        score += 2.0
    if startup.get("public_benefit"):
        score += 1.0
    if founder.get("published_exhibited") and startup.get("public_benefit"):
        score += 0.5  # extra for domain + social change combined

    return {
        "pathway": "Fellowships",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": True,
        "providers": [
            "Shuttleworth: $275K/yr (1% acceptance)",
            "Mozilla: $100K total (nominations closed 2026)",
            "Ashoka: living stipend (rolling)",
            "Echoing Green: 18 months (watch for 2027 cycle)",
        ],
        "action": "Monitor Shuttleworth (Sept 2026) + Echoing Green (Oct 2026)",
    }


def score_competitions(profile: dict, intel: dict) -> dict:
    """Competition score (Section 3.10)."""
    startup = profile.get("startup", {})

    score = 4.0
    if startup.get("prototype_ready"):
        score += 2.0
    if startup.get("public_benefit"):
        score += 1.0

    return {
        "pathway": "Competitions",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": startup.get("prototype_ready", False),
        "providers": ["XPRIZE: $11M", "MIT Solve: ~$40K/team", "Hult Prize: $1M (students)", "MIT $100K"],
        "action": "Enter MIT Solve or domain-specific competitions",
    }


def score_consulting(profile: dict, intel: dict) -> dict:
    """Consulting / Fractional CTO score (Section 3.11)."""
    founder = profile.get("founder", {})

    score = 7.0
    years = founder.get("years_experience", 0) or 0
    if years >= 10:
        score += 1.5
    if founder.get("leadership_experience"):
        score += 1.0
    if founder.get("ai_ml_expertise"):
        score += 0.5

    rates = _g(intel, "alternative_funding", "fractional_cto", default={})
    avg_rate = rates.get("average_hourly_usd", 300)

    return {
        "pathway": "Consulting / Fractional CTO",
        "score": round(max(0, min(score, 10)), 1),
        "eligible": years >= 5,
        "providers": [f"Average rate: ${avg_rate}/hr", "Monthly retainers: mid-four to low-five figures"],
        "action": "Activate if full-time search exceeds 3 months",
    }


def run_pathway_scorer(profile: dict, intel: dict) -> list[dict]:
    """Run all pathway scorers, return sorted by score descending."""
    scorers = [
        score_rbf, score_seed_vc, score_series_a, score_ai_funding,
        score_crypto_grants, score_arts_grants, score_bootstrap,
        score_cloud_credits, score_fellowships, score_competitions,
        score_consulting,
    ]
    results = [scorer(profile, intel) for scorer in scorers]
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def display_pathways(results: list[dict]):
    """Print ranked funding pathways."""
    print("FUNDING PATHWAY DECISION TREE")
    print("=" * 60)
    print()
    for i, r in enumerate(results, 1):
        eligible = "YES" if r["eligible"] else "no"
        print(f"  {i:2d}. [{r['score']:4.1f}/10] {r['pathway']:<30s} (eligible: {eligible})")
        if r["providers"]:
            for p in r["providers"]:
                print(f"       - {p}")
        print(f"       Action: {r['action']}")
        print()


# --- 2. Startup Viability Scorer ---

VIABILITY_WEIGHTS = {
    "market_timing": 0.20,
    "funding_access": 0.15,
    "solo_founder_viability": 0.10,
    "revenue_model": 0.15,
    "differentiation": 0.15,
    "runway": 0.10,
    "regulatory_moat": 0.05,
    "team_advisor": 0.10,
}


def score_viability(profile: dict, intel: dict) -> dict:
    """Startup viability composite score (0-100). Section 4."""
    startup = profile.get("startup", {})
    founder = profile.get("founder", {})
    rev = profile.get("revenue", {})
    runway = profile.get("runway", {})

    dimensions = {}

    # Market Timing (max 20)
    sector = startup.get("sector")
    winners = _g(intel, "startup_funding_landscape", "sector_winners_2026", default=[])
    if startup.get("ai_native"):
        dimensions["market_timing"] = 18
    elif sector in winners:
        dimensions["market_timing"] = 15
    elif sector:
        dimensions["market_timing"] = 8
    else:
        dimensions["market_timing"] = 5

    # Funding Access (max 15)
    if startup.get("warm_intros_available"):
        dimensions["funding_access"] = 12
    elif startup.get("incorporated"):
        dimensions["funding_access"] = 10  # accelerator eligible
    else:
        dimensions["funding_access"] = 3  # cold only

    # Solo Founder Viability (max 10)
    if founder.get("prior_exit"):
        dimensions["solo_founder_viability"] = 10
    elif founder.get("technical"):
        dimensions["solo_founder_viability"] = 8
    else:
        dimensions["solo_founder_viability"] = 4

    # Revenue Model (max 15)
    model = rev.get("model")
    model_scores = {"saas": 15, "marketplace": 12, "consulting": 8}
    dimensions["revenue_model"] = model_scores.get(model, 2)

    # Differentiation (max 15)
    if startup.get("proprietary_data"):
        dimensions["differentiation"] = 15
    elif startup.get("vertical_ai"):
        dimensions["differentiation"] = 12
    elif startup.get("ai_native"):
        dimensions["differentiation"] = 10
    else:
        dimensions["differentiation"] = 2

    # Runway (max 10)
    months = runway.get("months", 0) or 0
    if months >= 24:
        dimensions["runway"] = 10
    elif months >= 18:
        dimensions["runway"] = 8
    elif months >= 12:
        dimensions["runway"] = 5
    else:
        dimensions["runway"] = 2

    # Regulatory Moat (max 5)
    strategic = profile.get("strategic", {})
    if strategic.get("eu_ai_act_compliant"):
        dimensions["regulatory_moat"] = 5
    elif startup.get("ai_native"):
        dimensions["regulatory_moat"] = 3
    else:
        dimensions["regulatory_moat"] = 0

    # Team/Advisor (max 10)
    if founder.get("domain_expert_advisor"):
        dimensions["team_advisor"] = 10
    elif founder.get("technical") and founder.get("solo"):
        dimensions["team_advisor"] = 3
    else:
        dimensions["team_advisor"] = 5

    composite = sum(dimensions.values())
    max_possible = 100

    if composite >= 80:
        band = "STRONG — pursue aggressively"
    elif composite >= 60:
        band = "MODERATE — pursue with mitigation plan"
    elif composite >= 40:
        band = "QUESTIONABLE — consider pivoting model or team"
    else:
        band = "LOW — fundamental rethink needed"

    return {
        "composite": composite,
        "max": max_possible,
        "band": band,
        "dimensions": dimensions,
    }


def display_viability(result: dict):
    """Print startup viability report."""
    print("STARTUP VIABILITY SCORER")
    print("=" * 55)
    print()
    print(f"  COMPOSITE: {result['composite']}/{result['max']}")
    print(f"  ASSESSMENT: {result['band']}")
    print()

    max_per_dim = {
        "market_timing": 20, "funding_access": 15,
        "solo_founder_viability": 10, "revenue_model": 15,
        "differentiation": 15, "runway": 10,
        "regulatory_moat": 5, "team_advisor": 10,
    }

    print(f"  {'Dimension':<28} {'Score':>6} {'Max':>6} {'Weight':>8}")
    print(f"  {'-'*28} {'-'*6} {'-'*6} {'-'*8}")
    for dim, weight in VIABILITY_WEIGHTS.items():
        score = result["dimensions"].get(dim, 0)
        mx = max_per_dim.get(dim, 10)
        label = dim.replace("_", " ").title()
        print(f"  {label:<28} {score:>6} {mx:>6} {weight * 100:>7.0f}%")
    print()

    print("  KEY BENCHMARKS:")
    print("    AI startup failure rate:     90%")
    print("    Solo founder $1M+ revenue:   42%")
    print("    Solo founder share of exits: 52.3%")
    print("    Seed-to-Series A conversion: 36%")
    print("    YC acceptance rate:          1.5%")
    print("    Seed close time:             142 days median")
    print()


# --- 3. Differentiation Rubric ---

DIFF_WEIGHTS = {
    "proof_of_work": 0.20,
    "narrative_match": 0.15,
    "warm_path_access": 0.20,
    "vertical_depth": 0.15,
    "social_proof": 0.10,
    "ai_authenticity": 0.10,
    "dual_alignment": 0.10,
}

# Canonical metrics for proof_of_work auto-derivation
CANONICAL_METRICS = {
    "repos": 103,
    "tests": 2349,
    "words": 810000,
    "essays": 42,
    "sprints": 33,
}


def score_differentiation(profile: dict, intel: dict) -> dict:
    """Differentiation rubric: 7 dimensions, 0-10 each. Section 5."""
    startup = profile.get("startup", {})

    diff_signals = intel.get("differentiation_signals", {})

    dimensions = {}

    # Proof of Work (auto-derive from canonical metrics)
    # Strong: 103 repos, 2,349 tests, documented system → 8-10
    # Moderate: GitHub + some projects → 4-6
    # Weak: No public artifacts → 0-3
    if CANONICAL_METRICS["repos"] >= 100 and CANONICAL_METRICS["tests"] >= 2000:
        dimensions["proof_of_work"] = 9
    elif CANONICAL_METRICS["repos"] >= 20:
        dimensions["proof_of_work"] = 6
    else:
        dimensions["proof_of_work"] = 3

    # Narrative Match
    storytelling = diff_signals.get("storytelling", {})
    if storytelling.get("market_stage_narratives"):
        dimensions["narrative_match"] = 7  # stage-matched available
    else:
        dimensions["narrative_match"] = 5  # default moderate

    # Warm Path Access
    networking = diff_signals.get("networking", {})
    unrealized = networking.get("unrealized_warm_paths", 0)
    if startup.get("warm_intros_available"):
        dimensions["warm_path_access"] = 8
    elif unrealized >= 100:
        dimensions["warm_path_access"] = 5  # paths exist, unused
    else:
        dimensions["warm_path_access"] = 2  # cold only

    # Vertical Depth
    if startup.get("proprietary_data") and startup.get("vertical_ai"):
        dimensions["vertical_depth"] = 9
    elif startup.get("vertical_ai"):
        dimensions["vertical_depth"] = 7
    elif startup.get("ai_native"):
        dimensions["vertical_depth"] = 5
    else:
        dimensions["vertical_depth"] = 2

    # Social Proof
    social = diff_signals.get("social_proof", {})
    if social.get("reviews_5plus_conversion_lift"):
        # Proxy: if we have the benchmark data, assume moderate (user hasn't achieved 5+ reviews yet)
        dimensions["social_proof"] = 4
    else:
        dimensions["social_proof"] = 3

    # AI Authenticity
    ai_diff = diff_signals.get("ai_differentiation", {})
    if ai_diff.get("vertical_beats_horizontal") and startup.get("vertical_ai"):
        dimensions["ai_authenticity"] = 8
    elif startup.get("ai_native") and not startup.get("vertical_ai"):
        dimensions["ai_authenticity"] = 5
    else:
        dimensions["ai_authenticity"] = 3

    # Dual Alignment
    if startup.get("artistic_merit") and startup.get("public_benefit"):
        dimensions["dual_alignment"] = 8
    elif startup.get("public_benefit"):
        dimensions["dual_alignment"] = 6
    else:
        dimensions["dual_alignment"] = 3

    weighted = sum(dimensions[d] * DIFF_WEIGHTS[d] for d in DIFF_WEIGHTS)
    composite = round(weighted, 1)

    # Gap analysis: find weakest dimensions
    gaps = sorted(dimensions.items(), key=lambda x: x[1])[:3]

    return {
        "composite": composite,
        "dimensions": dimensions,
        "gaps": [(g[0], g[1]) for g in gaps],
    }


def display_differentiation(result: dict):
    """Print differentiation rubric report."""
    print("DIFFERENTIATION RUBRIC")
    print("=" * 55)
    print()
    print(f"  WEIGHTED COMPOSITE: {result['composite']}/10.0")
    print()

    print(f"  {'Dimension':<22} {'Score':>6} {'Weight':>8} {'Weighted':>10}")
    print(f"  {'-'*22} {'-'*6} {'-'*8} {'-'*10}")
    for dim, weight in DIFF_WEIGHTS.items():
        score = result["dimensions"].get(dim, 0)
        w = score * weight
        label = dim.replace("_", " ").title()
        print(f"  {label:<22} {score:>5}/10 {weight * 100:>7.0f}% {w:>9.1f}")
    print()

    print("  GAP ANALYSIS (weakest dimensions):")
    for dim, score in result["gaps"]:
        label = dim.replace("_", " ").title()
        print(f"    - {label}: {score}/10")
    print()

    print("  CHANNEL OPTIMIZATION:")
    print("    1. Referral:       30% success (8x cold)  → 80% of effort")
    print("    2. Direct portal:  8-12% response          → 15% of effort")
    print("    3. Indeed:         20-25% response          → 5% of effort")
    print("    4. LinkedIn Easy:  2-4% response            → AVOID as primary")
    print()


# --- 4. Blind Spots Checklist ---

def score_blindspots(profile: dict, intel: dict) -> dict:
    """Blind spots checklist with completion status. Section 11."""
    legal = profile.get("legal", {})
    health = profile.get("health", {})
    strategic = profile.get("strategic", {})

    meta = intel.get("meta_strategy", {})

    categories = {
        "Legal & Financial": [],
        "Health & Sustainability": [],
        "Strategic": [],
    }

    # Legal & Financial
    legal_items = [
        ("83(b) election filed within 30 days", legal.get("eighty_three_b_filed", False),
         "URGENT" if legal.get("eighty_three_b_deadline_approaching") else ""),
        ("Delaware franchise tax: Assumed Par Value method", legal.get("delaware_franchise_tax_method") == "assumed_par_value",
         "Can be $400K+ if using Authorized Shares method"),
        ("IP assignment agreements signed", legal.get("ip_assignment_signed", False), ""),
        ("D&O insurance ($125/month)", legal.get("d_and_o_insurance", False),
         f"${_g(meta, 'insurance', 'd_and_o_monthly_usd', default=125)}/month early is cheap"),
    ]
    categories["Legal & Financial"] = legal_items

    # Health & Sustainability
    burnout = _g(meta, "founder_burnout", "prevalence", default=0.73)
    health_items = [
        (f"Founder burnout awareness ({burnout:.0%} prevalence)", True, "Ongoing"),
        ("Structured breaks scheduled", health.get("structured_breaks", False), "Calendar non-negotiable time off"),
        ("Peer support group", health.get("peer_support_group", False), "YPO, Founder Collective, local groups"),
        ("Professional support (therapist/coach)", health.get("professional_support", False), "Before crisis, not after"),
    ]
    categories["Health & Sustainability"] = health_items

    # Strategic
    strategic_items = [
        ("Warm intro audit (200+ unrealized paths)", strategic.get("warm_intro_audit_done", False),
         "Map paths before cold outreach"),
        ("Documentation as leverage", strategic.get("documentation_as_leverage", False),
         "Public writing generates inbound deal flow (0.45 signal weight)"),
        ("Open source strategy", strategic.get("open_source_strategy", False),
         "Contributor pipeline doubles as hiring pipeline"),
        ("Academic partnerships (STTR requires)", strategic.get("academic_partnership", False),
         "Valuable for credibility + STTR funding"),
        ("Disability grants (least competitive)", strategic.get("disability_grant_eligible", False),
         "Prioritize if applicable" if strategic.get("disability_grant_eligible") else "N/A if not applicable"),
        ("Climate/ESG framing ($62.6B PE market)", strategic.get("climate_esg_framing", False),
         "Opens additional funding channels"),
        ("EU AI Act compliance as moat", strategic.get("eu_ai_act_compliant", False),
         "Compliance creates defensibility"),
    ]
    categories["Strategic"] = strategic_items

    # Compute stats
    total = 0
    completed = 0
    urgent = []
    for cat, items in categories.items():
        for label, done, note in items:
            total += 1
            if done:
                completed += 1
            if "URGENT" in str(note):
                urgent.append((cat, label, note))

    return {
        "categories": categories,
        "total": total,
        "completed": completed,
        "urgent": urgent,
    }


def display_blindspots(result: dict):
    """Print blind spots checklist."""
    print("BLIND SPOTS CHECKLIST")
    print("=" * 60)
    print()
    print(f"  Completion: {result['completed']}/{result['total']} items addressed")
    print()

    if result["urgent"]:
        print("  !! URGENT ITEMS:")
        for cat, label, note in result["urgent"]:
            print(f"     [{cat}] {label} — {note}")
        print()

    for cat, items in result["categories"].items():
        print(f"  {cat.upper()}")
        print(f"  {'-' * 40}")
        for label, done, note in items:
            check = "x" if done else " "
            line = f"    [{check}] {label}"
            if note and not done:
                line += f"  ({note})"
            print(line)
        print()


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Funding pathway scorer — executable decision frameworks from research data"
    )
    parser.add_argument("--pathway", action="store_true",
                        help="Run funding pathway decision tree")
    parser.add_argument("--viability", action="store_true",
                        help="Run startup viability scorer (0-100)")
    parser.add_argument("--differentiation", action="store_true",
                        help="Run differentiation rubric (0-10)")
    parser.add_argument("--blindspots", action="store_true",
                        help="Run blind spots checklist")
    parser.add_argument("--all", action="store_true",
                        help="Run all four reports")
    args = parser.parse_args()

    if not any([args.pathway, args.viability, args.differentiation, args.blindspots, args.all]):
        parser.print_help()
        sys.exit(1)

    profile = load_startup_profile()
    intel = load_market_intelligence()

    if args.all or args.pathway:
        results = run_pathway_scorer(profile, intel)
        display_pathways(results)

    if args.all or args.viability:
        result = score_viability(profile, intel)
        display_viability(result)

    if args.all or args.differentiation:
        result = score_differentiation(profile, intel)
        display_differentiation(result)

    if args.all or args.blindspots:
        result = score_blindspots(profile, intel)
        display_blindspots(result)


if __name__ == "__main__":
    main()
