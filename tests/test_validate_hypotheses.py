"""Tests for scripts/validate_hypotheses.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_hypotheses import accuracy_stats, build_outcome_map, validate


def test_build_outcome_map_supports_entry_id_and_id_fields():
    log = [
        {"entry_id": "entry-1", "outcome": "accepted"},
        {"id": "entry-2", "outcome": "rejected"},
    ]
    assert build_outcome_map(log) == {"entry-1": "accepted", "entry-2": "rejected"}


def test_validate_marks_correct_incorrect_and_unresolved():
    hypotheses = [
        {"hypothesis_id": "h1", "entry_id": "entry-1", "hypothesis": "good fit", "predicted_outcome": "accepted"},
        {"hypothesis_id": "h2", "entry_id": "entry-2", "hypothesis": "weak fit", "predicted_outcome": "accepted"},
        {"hypothesis_id": "h3", "entry_id": "entry-3", "hypothesis": "unknown", "predicted_outcome": "rejected"},
    ]
    outcomes = {"entry-1": "accepted", "entry-2": "rejected"}
    results = validate(hypotheses, outcomes)
    by_id = {row["hypothesis_id"]: row for row in results}
    assert by_id["h1"]["validated"] is True
    assert by_id["h2"]["validated"] is False
    assert by_id["h3"]["validated"] is None


def test_accuracy_stats_computes_percentage_from_resolved_items():
    results = [
        {"validated": True},
        {"validated": False},
        {"validated": None},
    ]
    stats = accuracy_stats(results)
    assert stats == {
        "total": 3,
        "resolved": 2,
        "correct": 1,
        "incorrect": 1,
        "accuracy": 50.0,
        "unresolved": 1,
    }
