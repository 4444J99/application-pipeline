"""Tests for scripts/funding_metrics.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from funding_metrics import CANONICAL_METRICS, build_canonical_metrics


def test_build_canonical_metrics_has_expected_keys():
    metrics = build_canonical_metrics()
    assert set(metrics.keys()) == {"repos", "tests", "words", "essays", "sprints"}


def test_canonical_metrics_values_are_positive():
    assert CANONICAL_METRICS["repos"] > 0
    assert CANONICAL_METRICS["tests"] > 0
    assert CANONICAL_METRICS["words"] > 0
    assert CANONICAL_METRICS["essays"] >= 0
    assert CANONICAL_METRICS["sprints"] >= 0

