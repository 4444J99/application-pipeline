"""Direct tests for scripts/score_human_dimensions.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_human_dimensions


def test_estimate_role_fit_from_title_tier_match():
    dims = score_human_dimensions.estimate_role_fit_from_title(
        {"name": "Software Engineer, Agent SDK"},
    )
    assert dims["mission_alignment"] >= 7
    assert dims["evidence_match"] >= 6


def test_ma_position_profile_match_primary():
    score, reason = score_human_dimensions._ma_position_profile_match(
        {"fit": {"identity_position": "systems-artist"}},
        {"primary_position": "systems-artist", "secondary_position": "educator"},
    )
    assert score == 4
    assert "primary_position" in reason


def test_compute_human_dimensions_auto_sourced_path():
    result = score_human_dimensions.compute_human_dimensions(
        {
            "name": "Software Engineer, Agent SDK",
            "tags": ["auto-sourced"],
            "submission": {"blocks_used": {}},
        }
    )
    assert set(result.keys()) == {
        "mission_alignment",
        "evidence_match",
        "track_record_fit",
    }


def test_tr_differentiators_coverage_with_profile():
    score, reason = score_human_dimensions._tr_differentiators_coverage(
        {},
        {"evidence_highlights": ["a", "b", "c"]},
    )
    assert score == 1
    assert ">= 3" in reason
