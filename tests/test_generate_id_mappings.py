"""Tests for scripts/generate_id_mappings.py helper logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_id_mappings import _best_match, _print_diff, _similarity, _tokens


def test_tokens_strips_noise_and_numbers():
    assert _tokens("Acme-Platform-2026!!") == {"acme", "platform"}


def test_similarity_rewards_token_overlap():
    similar = _similarity("acme-platform-engine", "acme-platform-core")
    dissimilar = _similarity("acme-platform-engine", "museum-curation-program")
    assert similar > dissimilar


def test_best_match_rejects_ambiguous_candidates():
    match, score = _best_match(
        "acme-engine",
        ["acme-engine-core", "acme-engine-app"],
        threshold=0.2,
    )
    assert match is None
    assert score >= 0.2


def test_print_diff_returns_failure_when_maps_differ(capsys):
    exit_code = _print_diff(
        "PROFILE_ID_MAP",
        generated={"a": "x", "c": "z"},
        existing={"a": "x", "b": "y"},
    )
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "MISSING: b -> y" in output
    assert "EXTRA:   c -> z" in output
