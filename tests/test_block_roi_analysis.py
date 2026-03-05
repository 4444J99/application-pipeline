"""Tests for scripts/block_roi_analysis.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from block_roi_analysis import calculate_roi, gather_block_outcomes


def test_gather_block_outcomes_counts_by_status_and_outcome():
    entries = [
        {
            "status": "submitted",
            "outcome": "accepted",
            "submission": {"blocks_used": {"cover": "blocks/a.md", "body": "blocks/b.md"}},
        },
        {
            "status": "interview",
            "submission": {"blocks_used": {"cover": "blocks/a.md"}},
        },
        {
            "status": "acknowledged",
            "outcome": "rejected",
            "submission": {"blocks_used": {"cover": "blocks/a.md"}},
        },
        {
            "status": "research",
            "outcome": "accepted",
            "submission": {"blocks_used": {"cover": "blocks/ignored.md"}},
        },
    ]

    result = gather_block_outcomes(entries)
    assert result["blocks/a.md"] == {
        "submitted": 3,
        "accepted": 1,
        "rejected": 1,
        "interview": 1,
        "pending": 0,
    }
    assert result["blocks/b.md"]["submitted"] == 1
    assert "blocks/ignored.md" not in result


def test_calculate_roi_sorts_by_acceptance_then_volume():
    block_data = {
        "blocks/high-rate.md": {"submitted": 2, "accepted": 2, "rejected": 0, "interview": 0, "pending": 0},
        "blocks/lower-rate.md": {"submitted": 5, "accepted": 2, "rejected": 2, "interview": 1, "pending": 0},
    }

    results = calculate_roi(block_data)
    assert results[0]["block"] == "blocks/high-rate.md"
    assert results[0]["acceptance_rate"] == 100.0
    assert results[1]["acceptance_rate"] == 40.0
