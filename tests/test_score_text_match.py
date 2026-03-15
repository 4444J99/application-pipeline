"""Tests for scripts/score_text_match.py."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import corpus_fingerprint
import score_text_match
from score_text_match import (
    evidence_match_text_signal,
    get_text_match_idf,
    mission_alignment_text_signal,
    score_description_against_corpus,
    track_record_text_signal,
)


def test_get_text_match_idf_short_circuits_when_disabled(monkeypatch):
    monkeypatch.setattr(score_text_match, "_text_match_available", False)
    monkeypatch.setattr(score_text_match, "_TEXT_MATCH_IDF", None)
    assert get_text_match_idf() is None


def test_text_signals_return_fallback_when_no_result(monkeypatch):
    monkeypatch.setattr(score_text_match, "text_match_result", lambda entry: None)
    score, reason = mission_alignment_text_signal({"id": "x"})
    assert score == 0
    assert "no research text available" in reason


def test_text_signals_use_result_scores(monkeypatch):
    fake = SimpleNamespace(
        mission_score=2,
        evidence_score=1,
        fit_score=3,
        overall_similarity=0.456,
    )
    monkeypatch.setattr(score_text_match, "text_match_result", lambda entry: fake)

    ma_score, ma_reason = mission_alignment_text_signal({"id": "x"})
    em_score, em_reason = evidence_match_text_signal({"id": "x"})
    tr_score, tr_reason = track_record_text_signal({"id": "x"})

    assert ma_score == 2 and "cosine=0.456" in ma_reason
    assert em_score == 1 and "cosine=0.456" in em_reason
    assert tr_score == 3 and "cosine=0.456" in tr_reason


# ---------------------------------------------------------------------------
# Tests for score_description_against_corpus
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


def test_score_description_against_corpus_high_match(tmp_path, monkeypatch):
    """Description with terms matching the corpus scores >= 7."""
    _setup_corpus_tmp(tmp_path, monkeypatch)

    description = (
        "We are looking for an AI systems engineer to build agentic workflows "
        "and LLM orchestration pipelines using Python. You will design governance "
        "frameworks for distributed teams and automate structured reasoning at scale. "
        "Creative technologists who understand multi-step AI tooling are highly valued."
    )
    result = score_description_against_corpus(description)

    assert result["mission_alignment"] >= 7
    assert result["evidence_match"] >= 7
    assert result["track_record_fit"] >= 6


def test_score_description_against_corpus_low_match(tmp_path, monkeypatch):
    """Unrelated description scores <= 4 for mission_alignment."""
    _setup_corpus_tmp(tmp_path, monkeypatch)

    description = (
        "We are hiring a chef to prepare artisanal bread and pastries in our downtown bakery. "
        "Experience with sourdough fermentation and wood-fired ovens is required. "
        "Must be comfortable working early mornings and managing flour inventory. "
        "Knowledge of French patisserie techniques is a strong plus for this role."
    )
    result = score_description_against_corpus(description)

    assert result["mission_alignment"] <= 4
    assert result["evidence_match"] <= 4


def test_score_description_against_corpus_empty():
    """Empty string returns neutral defaults without touching corpus."""
    result = score_description_against_corpus("")
    assert result == {"mission_alignment": 5, "evidence_match": 5, "track_record_fit": 4}


def test_score_description_against_corpus_too_short():
    """Very short description (< 50 chars) returns neutral defaults."""
    result = score_description_against_corpus("Engineer wanted.")
    assert result == {"mission_alignment": 5, "evidence_match": 5, "track_record_fit": 4}
