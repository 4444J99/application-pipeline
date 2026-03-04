"""Funding scorer metric helpers."""

from __future__ import annotations

from check_metrics import load_source_metrics


def build_canonical_metrics() -> dict[str, int]:
    """Build canonical metric snapshot used for proof-of-work scoring."""
    source = load_source_metrics()
    return {
        "repos": source["total_repos"],
        "tests": source["automated_tests"],
        "words": source["total_words_k"] * 1000,
        "essays": source["published_essays"],
        "sprints": source["named_sprints"],
    }


CANONICAL_METRICS = build_canonical_metrics()

