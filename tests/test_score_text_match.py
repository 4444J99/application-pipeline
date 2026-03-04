"""Tests for scripts/score_text_match.py."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_text_match
from score_text_match import (
    evidence_match_text_signal,
    get_text_match_idf,
    mission_alignment_text_signal,
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
