"""Tests for batch hypothesis mode in scripts/feedback_capture.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from feedback_capture import (
    VALID_CATEGORIES,
    _is_high_prestige,
    infer_hypothesis,
    load_hypotheses,
)

# ---------------------------------------------------------------------------
# _is_high_prestige
# ---------------------------------------------------------------------------


def test_is_high_prestige_known_org():
    """Known prestige organization returns True."""
    entry = {"target": {"organization": "Anthropic"}}
    assert _is_high_prestige(entry) is True


def test_is_high_prestige_unknown_org():
    """Unknown organization returns False."""
    entry = {"target": {"organization": "Unknown Startup XYZ"}}
    assert _is_high_prestige(entry) is False


def test_is_high_prestige_missing_target():
    """Entry without target returns False."""
    entry = {}
    assert _is_high_prestige(entry) is False


def test_is_high_prestige_empty_org():
    """Empty organization string returns False."""
    entry = {"target": {"organization": ""}}
    assert _is_high_prestige(entry) is False


# ---------------------------------------------------------------------------
# infer_hypothesis
# ---------------------------------------------------------------------------


def test_infer_tier1_cold_app():
    """Tier 1 prestige + no follow-up → timing category."""
    entry = {
        "id": "anthropic-test",
        "target": {"organization": "Anthropic"},
        "tags": [],
        "submission": {"variant_ids": {"cover_letter": "cl-v1"}, "portal_fields": {"q1": "a1"}},
        "follow_up": {},
    }
    cat, hyp = infer_hypothesis(entry)
    assert cat == "timing"
    assert "referral" in hyp.lower() or "cold app" in hyp.lower()


def test_infer_tier1_with_followup():
    """Tier 1 prestige + has follow-up → falls through to next rule."""
    entry = {
        "id": "anthropic-followed",
        "target": {"organization": "Anthropic"},
        "tags": [],
        "submission": {"variant_ids": {}, "portal_fields": {}},
        "follow_up": {"linkedin_connect": "2026-02-15"},
    }
    cat, hyp = infer_hypothesis(entry)
    # Should NOT be timing since follow-up exists
    assert cat != "timing"


def test_infer_auto_sourced():
    """Auto-sourced entry → auto_rejection category."""
    entry = {
        "id": "auto-test",
        "target": {"organization": "Small Corp"},
        "tags": ["auto-sourced"],
        "submission": {"variant_ids": {"cover_letter": "cl-v1"}, "portal_fields": {"q1": "a1"}},
        "follow_up": {},
    }
    cat, hyp = infer_hypothesis(entry)
    assert cat == "auto_rejection"
    assert "auto-sourced" in hyp.lower() or "keyword" in hyp.lower()


def test_infer_no_cover_letter():
    """No cover letter → cover_letter category."""
    entry = {
        "id": "no-cl",
        "target": {"organization": "Medium Corp"},
        "tags": [],
        "submission": {"variant_ids": {}, "portal_fields": {"q1": "a1"}},
        "follow_up": {},
    }
    cat, hyp = infer_hypothesis(entry)
    assert cat == "cover_letter"


def test_infer_no_portal_fields():
    """No custom answers → resume_screen category."""
    entry = {
        "id": "no-answers",
        "target": {"organization": "Medium Corp"},
        "tags": [],
        "submission": {"variant_ids": {"cover_letter": "cl-v1"}, "portal_fields": {}},
        "follow_up": {},
    }
    cat, hyp = infer_hypothesis(entry)
    assert cat == "resume_screen"


def test_infer_default_fallback():
    """Complete application → role_fit default."""
    entry = {
        "id": "complete-app",
        "target": {"organization": "Medium Corp"},
        "tags": [],
        "submission": {"variant_ids": {"cover_letter": "cl-v1"}, "portal_fields": {"q1": "a1"}},
        "follow_up": {},
    }
    cat, hyp = infer_hypothesis(entry)
    assert cat == "role_fit"
    assert "awaiting signal" in hyp.lower()


def test_infer_returns_valid_category():
    """All inference paths return a valid category."""
    test_entries = [
        {"id": "t1", "target": {"organization": "Anthropic"}, "tags": [], "submission": {}, "follow_up": {}},
        {"id": "t2", "target": {"organization": "X"}, "tags": ["auto-sourced"], "submission": {}, "follow_up": {}},
        {"id": "t3", "target": {"organization": "X"}, "tags": [], "submission": {"variant_ids": {}}, "follow_up": {}},
        {"id": "t4", "target": {}, "tags": [], "submission": {}, "follow_up": {}},
    ]
    for entry in test_entries:
        cat, hyp = infer_hypothesis(entry)
        assert cat in VALID_CATEGORIES, f"Invalid category '{cat}' for entry {entry['id']}"
        assert isinstance(hyp, str) and len(hyp) > 0


# ---------------------------------------------------------------------------
# load_hypotheses (existing functionality)
# ---------------------------------------------------------------------------


def test_load_hypotheses_returns_list():
    """load_hypotheses always returns a list."""
    result = load_hypotheses()
    assert isinstance(result, list)
