"""Direct tests for scripts/score_human_dimensions.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import corpus_fingerprint
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


# ---------------------------------------------------------------------------
# Tests for corpus-driven scoring in auto-sourced branch
# ---------------------------------------------------------------------------

_BLOCK_CONTENT = """\
---
title: Systems Engineering
tags: [python, ai, systems]
---

We build agentic workflows and AI orchestration systems using Python and Rust.
The pipeline automates multi-step reasoning with structured output and LLM tooling.
Creative technologists design governance systems that scale across distributed teams.
"""


def _setup_corpus_tmp(tmp_path: Path, monkeypatch) -> None:
    """Write a test block file and point corpus_fingerprint at tmp_path."""
    blocks = tmp_path / "blocks"
    blocks.mkdir()
    (blocks / "identity.md").write_text(_BLOCK_CONTENT, encoding="utf-8")
    monkeypatch.setattr(corpus_fingerprint, "BLOCKS_DIR", blocks)
    corpus_fingerprint._cached_fingerprint = None


def test_auto_sourced_with_description_uses_corpus(tmp_path, monkeypatch):
    """Auto-sourced entry with a long description should use corpus scoring, not title matching."""
    _setup_corpus_tmp(tmp_path, monkeypatch)

    # Track calls to estimate_role_fit_from_title to confirm it is NOT called
    title_calls = []
    original_title_fn = score_human_dimensions.estimate_role_fit_from_title

    def tracking_title_fn(entry):
        title_calls.append(entry)
        return original_title_fn(entry)

    monkeypatch.setattr(score_human_dimensions, "estimate_role_fit_from_title", tracking_title_fn)

    entry = {
        "name": "Pastry Chef",  # deliberately wrong title to confirm corpus path is used
        "tags": ["auto-sourced"],
        "target": {
            "description": (
                "We are hiring an AI systems engineer to build agentic workflows "
                "and LLM orchestration pipelines using Python. You will design governance "
                "frameworks for distributed teams and automate structured reasoning at scale. "
                "Creative technologists who understand multi-step AI tooling are highly valued."
            )
        },
        "submission": {"blocks_used": {}},
    }

    result = score_human_dimensions.compute_human_dimensions(entry)

    assert set(result.keys()) == {"mission_alignment", "evidence_match", "track_record_fit"}
    # Title matching was NOT invoked — corpus path was taken
    assert len(title_calls) == 0


def test_auto_sourced_without_description_falls_back_to_title(monkeypatch):
    """Auto-sourced entry with empty description should use estimate_role_fit_from_title."""
    title_calls = []
    original_title_fn = score_human_dimensions.estimate_role_fit_from_title

    def tracking_title_fn(entry):
        title_calls.append(entry)
        return original_title_fn(entry)

    monkeypatch.setattr(score_human_dimensions, "estimate_role_fit_from_title", tracking_title_fn)

    entry = {
        "name": "Software Engineer, Agent SDK",
        "tags": ["auto-sourced"],
        "target": {"description": ""},
        "submission": {"blocks_used": {}},
    }

    result = score_human_dimensions.compute_human_dimensions(entry)

    assert set(result.keys()) == {"mission_alignment", "evidence_match", "track_record_fit"}
    # Title matching WAS invoked
    assert len(title_calls) == 1
