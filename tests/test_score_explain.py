"""Direct tests for scripts/score_explain.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_explain


def _dims():
    return {
        "mission_alignment": 7,
        "evidence_match": 7,
        "track_record_fit": 6,
        "network_proximity": 5,
        "strategic_value": 8,
        "financial_alignment": 7,
        "effort_to_value": 6,
        "deadline_feasibility": 9,
        "portal_friction": 8,
    }


def _weights(_track):
    return {
        "mission_alignment": 0.25,
        "evidence_match": 0.20,
        "track_record_fit": 0.15,
        "network_proximity": 0.12,
        "strategic_value": 0.10,
        "financial_alignment": 0.08,
        "effort_to_value": 0.05,
        "deadline_feasibility": 0.03,
        "portal_friction": 0.02,
    }


def _dim_reason(_entry, explain=False):
    if explain:
        return 7, "ok"
    return 7


def test_rubric_desc_known_dimension():
    desc = score_explain._rubric_desc("mission_alignment", 9)
    assert "exemplifies" in desc


def test_explain_entry_includes_composite_line():
    output = score_explain.explain_entry(
        {"id": "test-id", "track": "grant", "fit": {"score": 7.4}},
        [],
        get_weights=_weights,
        compute_dimensions=lambda _entry, _all: _dims(),
        compute_composite=lambda _dims, _track: 7.4,
        compute_human_dimensions=lambda _entry, _all, explain=False: (
            {
                "mission_alignment": 7,
                "evidence_match": 7,
                "track_record_fit": 6,
            },
            {
                "mission_alignment": "m",
                "evidence_match": "e",
                "track_record_fit": "t",
            },
        ) if explain else {},
        score_network_proximity=lambda _entry, _all: 5,
        score_financial_alignment=_dim_reason,
        score_effort_to_value=_dim_reason,
        score_strategic_value=_dim_reason,
        score_deadline_feasibility=_dim_reason,
        score_portal_friction=_dim_reason,
        dimension_order=list(_dims().keys()),
    )
    assert "SIGNAL-BASED DIMENSIONS:" in output
    assert "COMPOSITE:" in output


def test_review_compressed_no_entries(capsys):
    score_explain.review_compressed([], lo=6.5, hi=7.5)
    captured = capsys.readouterr()
    assert "No entries in the 6.5-7.5 composite band need review." in captured.out
