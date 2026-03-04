"""Tests for scripts/outcome_risk.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from outcome_risk import _bucket_score, predict_success_probability, train_model


def test_bucket_score_thresholds():
    assert _bucket_score(8.5) == "high"
    assert _bucket_score(7.0) == "medium"
    assert _bucket_score(5.0) == "low"
    assert _bucket_score(None) == "unknown"


def test_predict_requires_min_training_samples():
    rows = [({"track": "job"}, 1), ({"track": "job"}, 0)]
    model = train_model(rows)
    prediction = predict_success_probability({"track": "job"}, model)
    assert prediction["available"] is False
    assert "insufficient" in prediction["reason"]


def test_predict_with_sufficient_samples():
    rows = []
    for _ in range(12):
        rows.append((
            {
                "track": "job",
                "identity_position": "independent-engineer",
                "portal": "greenhouse",
                "effort_level": "standard",
                "score_band": "high",
                "has_cover_letter": "yes",
                "has_portal_fields": "yes",
                "reviewed": "yes",
            },
            1,
        ))
    for _ in range(12):
        rows.append((
            {
                "track": "job",
                "identity_position": "independent-engineer",
                "portal": "greenhouse",
                "effort_level": "standard",
                "score_band": "low",
                "has_cover_letter": "no",
                "has_portal_fields": "no",
                "reviewed": "no",
            },
            0,
        ))

    model = train_model(rows)

    good_entry = {
        "track": "job",
        "fit": {"identity_position": "independent-engineer", "score": 8.6},
        "target": {"portal": "greenhouse"},
        "submission": {"effort_level": "standard", "variant_ids": {"cover_letter": "x"}},
        "portal_fields": {"fields": [{"name": "q"}]},
        "status_meta": {"reviewed_by": "tester"},
    }
    bad_entry = {
        "track": "job",
        "fit": {"identity_position": "independent-engineer", "score": 4.2},
        "target": {"portal": "greenhouse"},
        "submission": {"effort_level": "standard", "variant_ids": {}},
        "portal_fields": {"fields": []},
        "status_meta": {},
    }

    good = predict_success_probability(good_entry, model)
    bad = predict_success_probability(bad_entry, model)

    assert good["available"] is True
    assert bad["available"] is True
    assert good["success_probability"] > bad["success_probability"]
    assert 0.0 <= good["risk"] <= 1.0
    assert 0.0 <= bad["risk"] <= 1.0
