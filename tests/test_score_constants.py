"""Tests for scripts/score_constants.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from score_constants import HIGH_PRESTIGE, ROLE_FIT_TIERS


def test_high_prestige_contains_reference_orgs():
    assert "Creative Capital" in HIGH_PRESTIGE
    assert HIGH_PRESTIGE["Creative Capital"] >= 8


def test_role_fit_tiers_have_required_shape():
    assert len(ROLE_FIT_TIERS) >= 3
    for tier in ROLE_FIT_TIERS:
        assert "name" in tier
        assert "title_patterns" in tier
        assert isinstance(tier["title_patterns"], list)
        assert "mission_alignment" in tier
        assert "evidence_match" in tier
        assert "track_record_fit" in tier


def test_high_prestige_values_all_in_range():
    for org, value in HIGH_PRESTIGE.items():
        assert 1 <= value <= 10, f"{org} prestige {value} out of range [1, 10]"


def test_role_fit_tiers_numeric_fields_in_range():
    for tier in ROLE_FIT_TIERS:
        for field in ("mission_alignment", "evidence_match", "track_record_fit"):
            val = tier[field]
            assert 1 <= val <= 10, f"{tier['name']}.{field}={val} out of range [1, 10]"

