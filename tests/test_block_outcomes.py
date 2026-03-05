#!/usr/bin/env python3
"""Tests for block_outcomes.py — block-outcome correlation analysis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from block_outcomes import (
    classify_blocks,
    compute_block_cross_tabs,
    format_block_report,
)


def _entry(entry_id, blocks=None, outcome=None, position="independent-engineer", portal="greenhouse"):
    return {
        "id": entry_id,
        "status": "submitted" if outcome is None else "outcome",
        "outcome": outcome,
        "fit": {"identity_position": position},
        "target": {"portal": portal},
        "submission": {"blocks_used": blocks or {}},
    }


class TestComputeBlockCrossTabs:
    def test_basic_cross_tab(self):
        entries = [
            _entry("a", blocks={"intro": "identity/2min"}, outcome="accepted"),
            _entry("b", blocks={"intro": "identity/2min"}, outcome="rejected"),
        ]
        tabs = compute_block_cross_tabs(entries)
        assert "identity/2min" in tabs
        assert tabs["identity/2min"]["accepted"] == 1
        assert tabs["identity/2min"]["rejected"] == 1
        assert tabs["identity/2min"]["used"] == 2

    def test_empty_entries(self):
        tabs = compute_block_cross_tabs([])
        assert tabs == {}

    def test_pending_counted(self):
        entries = [_entry("a", blocks={"intro": "identity/2min"}, outcome=None)]
        tabs = compute_block_cross_tabs(entries)
        assert tabs["identity/2min"]["pending"] == 1

    def test_position_tracking(self):
        entries = [
            _entry("a", blocks={"intro": "bio/short"}, outcome="accepted", position="systems-artist"),
        ]
        tabs = compute_block_cross_tabs(entries)
        assert tabs["bio/short"]["position"]["systems-artist"] == 1

    def test_multiple_blocks(self):
        entries = [
            _entry("a", blocks={"intro": "bio/short", "body": "projects/organvm"}, outcome="accepted"),
        ]
        tabs = compute_block_cross_tabs(entries)
        assert "bio/short" in tabs
        assert "projects/organvm" in tabs


class TestClassifyBlocks:
    def test_golden_classification(self):
        tabs = {
            "good-block": {"used": 8, "accepted": 6, "rejected": 2, "pending": 0,
                          "position": {}, "portal": {}},
        }
        classified = classify_blocks(tabs)
        assert len(classified["golden"]) == 1
        assert classified["golden"][0]["block"] == "good-block"

    def test_toxic_classification(self):
        tabs = {
            "bad-block": {"used": 8, "accepted": 0, "rejected": 8, "pending": 0,
                         "position": {}, "portal": {}},
        }
        classified = classify_blocks(tabs)
        assert len(classified["toxic"]) == 1

    def test_neutral_insufficient_data(self):
        tabs = {
            "new-block": {"used": 1, "accepted": 1, "rejected": 0, "pending": 0,
                         "position": {}, "portal": {}},
        }
        classified = classify_blocks(tabs)
        assert len(classified["neutral"]) == 1
        assert "insufficient data" in classified["neutral"][0]["reason"]

    def test_empty_tabs(self):
        classified = classify_blocks({})
        assert classified == {"golden": [], "neutral": [], "toxic": []}


class TestFormatReport:
    def test_format_with_data(self):
        classified = {
            "golden": [{"block": "bio/short", "accept_rate": 0.75, "used": 4}],
            "toxic": [],
            "neutral": [{"block": "intro/long", "used": 1, "reason": "insufficient data"}],
        }
        output = format_block_report(classified)
        assert "GOLDEN" in output
        assert "bio/short" in output
        assert "TOXIC" in output

    def test_format_empty(self):
        classified = {"golden": [], "toxic": [], "neutral": []}
        output = format_block_report(classified)
        assert "none yet" in output
