"""Text-match scoring signals for score.py."""

from __future__ import annotations

_TEXT_MATCH_IDF: tuple[dict[str, float], int] | None = None
_text_match_available = True


def get_text_match_idf() -> tuple[dict[str, float], int] | None:
    """Lazy-load IDF table from text_match module."""
    global _TEXT_MATCH_IDF, _text_match_available
    if not _text_match_available:
        return None
    if _TEXT_MATCH_IDF is not None:
        return _TEXT_MATCH_IDF
    try:
        from text_match import get_idf

        idf, corpus_size = get_idf()
        if idf:
            _TEXT_MATCH_IDF = (idf, corpus_size)
            return _TEXT_MATCH_IDF
    except Exception:
        _text_match_available = False
    return None


def text_match_result(entry: dict):
    """Compute text-match result for an entry, or None on failure."""
    idf_data = get_text_match_idf()
    if idf_data is None:
        return None
    idf, corpus_size = idf_data
    try:
        from text_match import analyze_entry

        entry_id = entry.get("id", "")
        return analyze_entry(entry_id, entry, idf, corpus_size)
    except Exception:
        return None


def mission_alignment_text_signal(entry: dict) -> tuple[int, str]:
    """Signal for mission alignment from text similarity."""
    result = text_match_result(entry)
    if result is None:
        return 0, "no research text available"
    score = result.mission_score
    return score, f"text similarity -> {score} (cosine={result.overall_similarity:.3f})"


def evidence_match_text_signal(entry: dict) -> tuple[int, str]:
    """Signal for evidence match from text coverage."""
    result = text_match_result(entry)
    if result is None:
        return 0, "no research text available"
    score = result.evidence_score
    return score, f"text coverage -> {score} (cosine={result.overall_similarity:.3f})"


def track_record_text_signal(entry: dict) -> tuple[int, str]:
    """Signal for track-record fit from resume/profile similarity."""
    result = text_match_result(entry)
    if result is None:
        return 0, "no research text available"
    score = result.fit_score
    return score, f"text fit -> {score} (cosine={result.overall_similarity:.3f})"


def score_description_against_corpus(description: str) -> dict[str, int]:
    """Score a job description against the living corpus fingerprint.

    Returns dimension scores derived from cosine similarity between
    the job description and the full corpus of blocks/resume/projects.
    """
    if not description or len(description.strip()) < 50:
        return {"mission_alignment": 5, "evidence_match": 4, "track_record_fit": 4}

    from corpus_fingerprint import get_fingerprint

    fp = get_fingerprint()
    similarity = fp.score_description(description)

    # Map similarity to 1-10 scores
    # Calibration: 0.00-0.03 = no overlap, 0.03-0.08 = weak, 0.08-0.15 = moderate, 0.15+ = strong
    def sim_to_score(s: float) -> int:
        if s >= 0.20:
            return 10
        if s >= 0.15:
            return 9
        if s >= 0.12:
            return 8
        if s >= 0.08:
            return 7
        if s >= 0.05:
            return 6
        if s >= 0.03:
            return 5
        if s >= 0.01:
            return 4
        return 3

    score = sim_to_score(similarity)
    return {
        "mission_alignment": score,
        "evidence_match": score,
        "track_record_fit": max(3, score - 1),
    }
