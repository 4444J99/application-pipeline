"""Tests for scripts/portfolio_analysis.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from portfolio_analysis import (
    _submitted_entries,
    query_blocks,
    query_channel,
    query_variants,
)


def _entry(
    *,
    status="submitted",
    outcome=None,
    blocks=None,
    portal="greenhouse",
    cover_letter="cover-v1",
):
    return {
        "status": status,
        "outcome": outcome,
        "target": {"portal": portal},
        "submission": {
            "blocks_used": blocks or {},
            "variant_ids": {"cover_letter": cover_letter} if cover_letter is not None else {},
        },
    }


def test_submitted_entries_filters_pipeline_states():
    entries = [_entry(status="research"), _entry(status="submitted"), _entry(status="interview")]
    filtered = _submitted_entries(entries)
    assert len(filtered) == 2
    assert all(item["status"] in {"submitted", "interview"} for item in filtered)


def test_query_blocks_calculates_acceptance_rates():
    entries = [
        _entry(outcome="accepted", blocks={"cover": "blocks/a.md"}),
        _entry(outcome="rejected", blocks={"cover": "blocks/a.md", "body": "blocks/b.md"}),
    ]

    result = query_blocks(entries)["blocks"]
    by_name = {row["block"]: row for row in result}
    assert by_name["blocks/a.md"]["accepted"] == 1
    assert by_name["blocks/a.md"]["rejected"] == 1
    assert by_name["blocks/a.md"]["rate"] == 50.0
    assert by_name["blocks/b.md"]["rate"] == 0.0


def test_query_channel_handles_missing_target_dict():
    entries = [_entry(outcome="accepted", portal="ashby"), {"status": "submitted", "outcome": "rejected", "target": None}]
    channels = query_channel(entries)["channels"]
    by_channel = {row["channel"]: row for row in channels}
    assert by_channel["ashby"]["accepted"] == 1
    assert by_channel["unknown"]["rejected"] == 1


def test_query_variants_buckets_cover_letter_types():
    entries = [
        _entry(outcome="accepted", cover_letter="my-letter-v2"),
        _entry(outcome="rejected", cover_letter="legacy-v1"),
        _entry(outcome="accepted", cover_letter=None),
    ]
    variants = query_variants(entries)["variants"]
    keys = {row["variant_type"] for row in variants}
    assert keys == {"v2_or_alchemized", "v1", "no_cover_letter"}
