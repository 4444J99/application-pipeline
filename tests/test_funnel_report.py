"""Tests for scripts/funnel_report.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from funnel_report import (
    TARGETS,
    FUNNEL_STAGES,
    get_stage_index,
    _get_dimension_value,
)


# --- TARGETS ---


def test_targets_all_positive():
    """All conversion targets should be positive."""
    for key, val in TARGETS.items():
        assert val > 0, f"Target {key} is non-positive"


def test_targets_all_less_than_one():
    """All conversion targets should be rates (0-1)."""
    for key, val in TARGETS.items():
        assert 0 < val <= 1.0, f"Target {key} = {val} not in (0, 1]"


def test_targets_required_keys():
    """Should have all required target keys."""
    required = {"apply_to_phone", "phone_to_onsite", "onsite_to_offer",
                "full_funnel_cold", "full_funnel_followup"}
    assert required.issubset(set(TARGETS.keys()))


# --- FUNNEL_STAGES ---


def test_funnel_stages_count():
    """Should have 9 stages (including deferred)."""
    assert len(FUNNEL_STAGES) == 9


def test_funnel_stages_ordered():
    """Stages should match pipeline status order."""
    from pipeline_lib import STATUS_ORDER
    assert FUNNEL_STAGES == STATUS_ORDER


# --- get_stage_index ---


def test_stage_index_research():
    """Research should be index 0."""
    assert get_stage_index("research") == 0


def test_stage_index_outcome():
    """Outcome should be last index."""
    assert get_stage_index("outcome") == len(FUNNEL_STAGES) - 1


def test_stage_index_unknown():
    """Unknown status should return -1."""
    assert get_stage_index("nonexistent") == -1


def test_stage_index_submitted():
    """Submitted should be index 5 (after deferred)."""
    assert get_stage_index("submitted") == 5


# --- _get_dimension_value ---


def _make_entry(
    track="job",
    portal="greenhouse",
    position="independent-engineer",
    channel=None,
    cover_letter_present=None,
    follow_up_count=None,
    variant_cover_letter=None,
):
    """Build a minimal entry for dimension value tests."""
    entry = {
        "track": track,
        "target": {"portal": portal},
        "fit": {"identity_position": position},
        "conversion": {},
        "submission": {"variant_ids": {}},
    }
    if channel:
        entry["conversion"]["channel"] = channel
    if cover_letter_present is not None:
        entry["conversion"]["cover_letter_present"] = cover_letter_present
    if follow_up_count is not None:
        entry["conversion"]["follow_up_count"] = follow_up_count
    if variant_cover_letter:
        entry["submission"]["variant_ids"]["cover_letter"] = variant_cover_letter
    return entry


def test_dimension_channel():
    """Should return channel from conversion."""
    entry = _make_entry(channel="referral")
    assert _get_dimension_value(entry, "channel") == "referral"


def test_dimension_channel_default():
    """Should return 'unknown' when no channel."""
    entry = _make_entry()
    assert _get_dimension_value(entry, "channel") == "unknown"


def test_dimension_position():
    """Should return identity_position from fit."""
    entry = _make_entry(position="educator")
    assert _get_dimension_value(entry, "position") == "educator"


def test_dimension_portal():
    """Should return portal from target."""
    entry = _make_entry(portal="ashby")
    assert _get_dimension_value(entry, "portal") == "ashby"


def test_dimension_track():
    """Should return track."""
    entry = _make_entry(track="grant")
    assert _get_dimension_value(entry, "track") == "grant"


def test_dimension_cover_letter_true():
    """Should return 'with_cover_letter' when present."""
    entry = _make_entry(cover_letter_present=True)
    assert _get_dimension_value(entry, "cover_letter") == "with_cover_letter"


def test_dimension_cover_letter_false():
    """Should return 'no_cover_letter' when absent."""
    entry = _make_entry(cover_letter_present=False)
    assert _get_dimension_value(entry, "cover_letter") == "no_cover_letter"


def test_dimension_cover_letter_inferred():
    """Should infer cover letter from variant_ids."""
    entry = _make_entry(variant_cover_letter="cover-letters/test-v1")
    assert _get_dimension_value(entry, "cover_letter") == "with_cover_letter"


def test_dimension_follow_up_zero():
    """Should return 'no_followup' for 0 count."""
    entry = _make_entry(follow_up_count=0)
    assert _get_dimension_value(entry, "follow_up") == "no_followup"


def test_dimension_follow_up_one():
    """Should return '1_followup' for count 1."""
    entry = _make_entry(follow_up_count=1)
    assert _get_dimension_value(entry, "follow_up") == "1_followup"


def test_dimension_follow_up_many():
    """Should return 'N+_followups' for count > 1."""
    entry = _make_entry(follow_up_count=3)
    assert _get_dimension_value(entry, "follow_up") == "3+_followups"


def test_dimension_unknown():
    """Unknown dimension should return 'unknown'."""
    entry = _make_entry()
    assert _get_dimension_value(entry, "nonexistent") == "unknown"
