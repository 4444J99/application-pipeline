"""Tests for scripts/ingest_top_roles.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ingest_top_roles import (
    FRESHNESS_MODIFIERS,
    freshness_tier,
    identity_match,
    pre_score,
)

# --- TestFreshnessTier ---


def test_freshness_tier_no_date():
    """None posting date → ('unknown', None)."""
    tier, age = freshness_tier(None)
    assert tier == "unknown"
    assert age is None


def test_freshness_tier_today():
    """Age 0 → 'urgent'."""
    today = date.today().isoformat()
    tier, age = freshness_tier(today)
    assert tier == "urgent"
    assert age == 0


def test_freshness_tier_day_1():
    """Age 1 → 'urgent'."""
    d = (date.today() - timedelta(days=1)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "urgent"


def test_freshness_tier_day_2():
    """Age 2 → 'urgent' (boundary)."""
    d = (date.today() - timedelta(days=2)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "urgent"


def test_freshness_tier_day_3():
    """Age 3 → 'fresh'."""
    d = (date.today() - timedelta(days=3)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "fresh"


def test_freshness_tier_day_7():
    """Age 7 → 'fresh' (boundary)."""
    d = (date.today() - timedelta(days=7)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "fresh"


def test_freshness_tier_day_8():
    """Age 8 → 'standard'."""
    d = (date.today() - timedelta(days=8)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "standard"


def test_freshness_tier_day_14():
    """Age 14 → 'standard' (boundary)."""
    d = (date.today() - timedelta(days=14)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "standard"


def test_freshness_tier_day_15():
    """Age 15 → 'aging'."""
    d = (date.today() - timedelta(days=15)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "aging"


def test_freshness_tier_day_21():
    """Age 21 → 'aging' (boundary)."""
    d = (date.today() - timedelta(days=21)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "aging"


def test_freshness_tier_day_22():
    """Age 22 → 'stale'."""
    d = (date.today() - timedelta(days=22)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "stale"


def test_freshness_tier_day_30():
    """Age 30 → 'stale' (boundary)."""
    d = (date.today() - timedelta(days=30)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "stale"


def test_freshness_tier_day_31():
    """Age 31 → 'ghost'."""
    d = (date.today() - timedelta(days=31)).isoformat()
    tier, _ = freshness_tier(d)
    assert tier == "ghost"


def test_freshness_tier_invalid_date():
    """Invalid date string → ('unknown', None)."""
    tier, age = freshness_tier("not-a-date")
    assert tier == "unknown"
    assert age is None


def test_freshness_tier_empty_string():
    """Empty string → ('unknown', None)."""
    tier, age = freshness_tier("")
    assert tier == "unknown"
    assert age is None


def test_freshness_tier_age_returned_correctly():
    """Age in days is accurate."""
    d = (date.today() - timedelta(days=5)).isoformat()
    tier, age = freshness_tier(d)
    assert age == 5


# --- TestPreScore ---


def test_pre_score_returns_float_in_range():
    """pre_score returns a float between 0.0 and 10.0."""
    job = {"title": "Software Engineer", "company_display": "SomeCompany", "portal": "greenhouse"}
    score = pre_score(job)
    assert isinstance(score, float)
    assert 0.0 <= score <= 10.0


def test_pre_score_urgent_beats_ghost():
    """Urgent posting scores higher than ghost posting for same role/company."""
    today = date.today().isoformat()
    ghost_date = (date.today() - timedelta(days=45)).isoformat()
    job_base = {"title": "Software Engineer", "company_display": "Acme", "portal": "greenhouse"}
    urgent = pre_score({**job_base, "posting_date": today})
    ghost = pre_score({**job_base, "posting_date": ghost_date})
    assert urgent > ghost


def test_pre_score_score_capped_at_ten():
    """Score cannot exceed 10.0."""
    job = {
        "title": "developer experience",
        "company_display": "Anthropic",
        "portal": "ashby",
        "posting_date": date.today().isoformat(),
    }
    score = pre_score(job)
    assert score <= 10.0


def test_pre_score_score_floor_at_zero():
    """Score cannot go below 0.0."""
    job = {
        "title": "irrelevant role",
        "company_display": "UnknownCorp",
        "portal": "unknown_portal",
        "posting_date": (date.today() - timedelta(days=60)).isoformat(),
    }
    score = pre_score(job)
    assert score >= 0.0


def test_pre_score_no_posting_date_uses_unknown_modifier():
    """Missing posting date uses 0.0 modifier (unknown tier)."""
    job = {"title": "Software Engineer", "company_display": "Acme", "portal": "greenhouse"}
    score = pre_score(job)
    assert isinstance(score, float)
    assert 0.0 <= score <= 10.0


# --- TestIdentityMatch ---


def test_identity_match_devrel():
    """'developer relations' title matches identity."""
    job = {"title": "Developer Relations Engineer"}
    assert identity_match(job) is True


def test_identity_match_devex():
    """'devex' in title matches identity."""
    job = {"title": "DevEx Platform Lead"}
    assert identity_match(job) is True


def test_identity_match_devtools():
    """'developer tools' matches."""
    job = {"title": "Senior Developer Tools Engineer"}
    assert identity_match(job) is True


def test_identity_match_agentic():
    """'agentic' matches."""
    job = {"title": "Agentic Systems Engineer"}
    assert identity_match(job) is True


def test_identity_match_cli():
    """'cli' matches."""
    job = {"title": "CLI Framework Developer"}
    assert identity_match(job) is True


def test_identity_match_unrelated():
    """Unrelated title does not match."""
    job = {"title": "Staff Accountant"}
    assert identity_match(job) is False


def test_identity_match_case_insensitive():
    """Matching is case-insensitive."""
    job = {"title": "DEVELOPER EXPERIENCE LEAD"}
    assert identity_match(job) is True


def test_identity_match_empty_title():
    """Empty title does not match."""
    job = {"title": ""}
    assert identity_match(job) is False


def test_identity_match_no_title_key():
    """Missing title key does not match (defaults to empty string)."""
    job = {}
    assert identity_match(job) is False


# --- FRESHNESS_MODIFIERS coverage ---


def test_freshness_modifiers_has_all_tiers():
    """FRESHNESS_MODIFIERS covers all expected tier names."""
    for tier_name in ("urgent", "fresh", "standard", "aging", "stale", "ghost", "unknown"):
        assert tier_name in FRESHNESS_MODIFIERS


def test_freshness_modifiers_urgent_highest():
    """Urgent has the highest modifier."""
    assert FRESHNESS_MODIFIERS["urgent"] == max(FRESHNESS_MODIFIERS.values())


def test_freshness_modifiers_ghost_lowest():
    """Ghost has the most negative modifier."""
    assert FRESHNESS_MODIFIERS["ghost"] == min(FRESHNESS_MODIFIERS.values())
