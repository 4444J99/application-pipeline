"""Tests for the hypothesis -> outcome -> adjustment loop.

Covers:
- validate_hypotheses.py: category-aware validation, accuracy_by_category,
  classify_patterns, generate_full_report
- outcome_learner.py: validate_hypotheses_with_weights, CATEGORY_DIMENSION_MAP
"""

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import validate_hypotheses as vh_mod
from pipeline_lib import DIMENSION_ORDER
from validate_hypotheses import (
    CATEGORY_CONFIRMS_ON,
    CATEGORY_DISPROVES_ON,
    NON_TERMINAL_OUTCOMES,
    accuracy_by_category,
    accuracy_stats,
    build_outcome_detail_map,
    build_outcome_map,
    classify_patterns,
    generate_full_report,
    validate,
)

# ---------------------------------------------------------------------------
# build_outcome_map
# ---------------------------------------------------------------------------

def test_build_outcome_map_supports_entry_id_and_id_fields():
    log = [
        {"entry_id": "entry-1", "outcome": "accepted"},
        {"id": "entry-2", "outcome": "rejected"},
    ]
    assert build_outcome_map(log) == {"entry-1": "accepted", "entry-2": "rejected"}


def test_build_outcome_map_skips_null_outcome():
    log = [{"entry_id": "entry-1", "outcome": None}]
    assert build_outcome_map(log) == {}


def test_build_outcome_map_skips_missing_id():
    log = [{"outcome": "rejected"}]
    assert build_outcome_map(log) == {}


# ---------------------------------------------------------------------------
# build_outcome_detail_map
# ---------------------------------------------------------------------------

def test_build_outcome_detail_map_captures_all_fields():
    log = [
        {
            "id": "e1",
            "outcome": "rejected",
            "outcome_stage": "resume_screen",
            "feedback": "Not enough experience",
            "time_to_response_days": 3,
        }
    ]
    details = build_outcome_detail_map(log)
    assert "e1" in details
    assert details["e1"]["outcome"] == "rejected"
    assert details["e1"]["outcome_stage"] == "resume_screen"
    assert details["e1"]["feedback"] == "Not enough experience"
    assert details["e1"]["time_to_response_days"] == 3


def test_build_outcome_detail_map_handles_null_fields():
    log = [{"id": "e1", "outcome": None}]
    details = build_outcome_detail_map(log)
    assert details["e1"]["outcome"] is None


# ---------------------------------------------------------------------------
# validate: category-aware correctness
# ---------------------------------------------------------------------------

def test_validate_category_timing_rejected_is_correct():
    """A 'timing' hypothesis confirmed when entry is rejected."""
    hypotheses = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "Role filled externally"}
    ]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is True
    assert results[0]["category"] == "timing"


def test_validate_category_timing_expired_is_correct():
    """A 'timing' hypothesis confirmed when entry expires."""
    hypotheses = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "Headcount frozen"}
    ]
    outcomes = {"e1": "expired"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is True


def test_validate_category_timing_accepted_is_incorrect():
    """A 'timing' hypothesis disproved when entry is accepted."""
    hypotheses = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "Bad timing"}
    ]
    outcomes = {"e1": "accepted"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is False


def test_validate_category_timing_interview_is_incorrect():
    """A 'timing' hypothesis disproved when entry reaches interview."""
    hypotheses = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "Role closed"}
    ]
    outcomes = {"e1": "interview"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is False


def test_validate_category_auto_rejection_confirmed():
    hypotheses = [
        {"entry_id": "e1", "category": "auto_rejection", "hypothesis": "ATS filter"}
    ]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is True


def test_validate_category_resume_screen_confirmed():
    hypotheses = [
        {"entry_id": "e1", "category": "resume_screen", "hypothesis": "No custom answers"}
    ]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is True


def test_validate_acknowledged_is_unresolved():
    """Acknowledged is non-terminal -- hypothesis stays unresolved."""
    hypotheses = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "Cold app"}
    ]
    outcomes = {"e1": "acknowledged"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is None


def test_validate_no_outcome_is_unresolved():
    hypotheses = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "Cold app"}
    ]
    outcomes = {}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is None


def test_validate_legacy_predicted_outcome_exact_match():
    """Legacy mode: predicted_outcome field enables exact matching."""
    hypotheses = [
        {"entry_id": "e1", "predicted_outcome": "rejected", "hypothesis": "Weak fit"}
    ]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is True


def test_validate_legacy_predicted_outcome_mismatch():
    hypotheses = [
        {"entry_id": "e1", "predicted_outcome": "accepted", "hypothesis": "Strong fit"}
    ]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is False


def test_validate_cover_letter_category():
    hypotheses = [
        {"entry_id": "e1", "category": "cover_letter", "hypothesis": "No cover letter"}
    ]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is True


def test_validate_role_fit_withdrawn_is_correct():
    """Role fit mismatch confirmed by voluntary withdrawal."""
    hypotheses = [
        {"entry_id": "e1", "category": "role_fit", "hypothesis": "Overqualified"}
    ]
    outcomes = {"e1": "withdrawn"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is True


def test_validate_preserves_entry_metadata():
    """Result carries through entry_id, category, hypothesis, actual."""
    hypotheses = [
        {
            "entry_id": "test-id",
            "category": "credential_gap",
            "hypothesis": "Missing CS degree",
            "hypothesis_id": "hyp-42",
        }
    ]
    outcomes = {"test-id": "rejected"}
    results = validate(hypotheses, outcomes)
    r = results[0]
    assert r["entry_id"] == "test-id"
    assert r["category"] == "credential_gap"
    assert r["hypothesis"] == "Missing CS degree"
    assert r["hypothesis_id"] == "hyp-42"
    assert r["actual"] == "rejected"


# ---------------------------------------------------------------------------
# Correctness rule coverage: confirm every category has confirmation rules
# ---------------------------------------------------------------------------

def test_all_categories_have_confirmation_rules():
    """Every category in CATEGORY_CONFIRMS_ON should have at least one confirming outcome."""
    for cat, outcomes in CATEGORY_CONFIRMS_ON.items():
        assert len(outcomes) > 0, f"Category {cat} has no confirming outcomes"


def test_all_categories_have_disproval_rules():
    """Every category in CATEGORY_DISPROVES_ON should have at least one disproving outcome."""
    for cat, outcomes in CATEGORY_DISPROVES_ON.items():
        assert len(outcomes) > 0, f"Category {cat} has no disproving outcomes"


def test_non_terminal_outcomes_are_none_and_acknowledged():
    assert None in NON_TERMINAL_OUTCOMES
    assert "acknowledged" in NON_TERMINAL_OUTCOMES


# ---------------------------------------------------------------------------
# accuracy_stats
# ---------------------------------------------------------------------------

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


def test_accuracy_stats_empty_results():
    stats = accuracy_stats([])
    assert stats["total"] == 0
    assert stats["resolved"] == 0
    assert stats["accuracy"] == 0.0


def test_accuracy_stats_all_unresolved():
    results = [{"validated": None}, {"validated": None}]
    stats = accuracy_stats(results)
    assert stats["resolved"] == 0
    assert stats["accuracy"] == 0.0
    assert stats["unresolved"] == 2


def test_accuracy_stats_all_correct():
    results = [{"validated": True}, {"validated": True}]
    stats = accuracy_stats(results)
    assert stats["accuracy"] == 100.0
    assert stats["correct"] == 2
    assert stats["incorrect"] == 0


# ---------------------------------------------------------------------------
# accuracy_by_category
# ---------------------------------------------------------------------------

def test_accuracy_by_category_groups_correctly():
    results = [
        {"category": "timing", "validated": True},
        {"category": "timing", "validated": False},
        {"category": "timing", "validated": None},
        {"category": "auto_rejection", "validated": True},
        {"category": "auto_rejection", "validated": True},
    ]
    cat_stats = accuracy_by_category(results)

    assert "timing" in cat_stats
    assert cat_stats["timing"]["total"] == 3
    assert cat_stats["timing"]["resolved"] == 2
    assert cat_stats["timing"]["correct"] == 1
    assert cat_stats["timing"]["accuracy"] == 50.0

    assert "auto_rejection" in cat_stats
    assert cat_stats["auto_rejection"]["total"] == 2
    assert cat_stats["auto_rejection"]["resolved"] == 2
    assert cat_stats["auto_rejection"]["correct"] == 2
    assert cat_stats["auto_rejection"]["accuracy"] == 100.0


def test_accuracy_by_category_validated_pattern():
    """Category with >50% accuracy -> validated_pattern."""
    results = [
        {"category": "timing", "validated": True},
        {"category": "timing", "validated": True},
        {"category": "timing", "validated": False},
    ]
    cat_stats = accuracy_by_category(results)
    assert cat_stats["timing"]["pattern"] == "validated_pattern"


def test_accuracy_by_category_invalid_assumption():
    """Category with <30% accuracy -> invalid_assumption."""
    results = [
        {"category": "cover_letter", "validated": False},
        {"category": "cover_letter", "validated": False},
        {"category": "cover_letter", "validated": False},
        {"category": "cover_letter", "validated": True},
    ]
    cat_stats = accuracy_by_category(results)
    assert cat_stats["cover_letter"]["accuracy"] == 25.0
    assert cat_stats["cover_letter"]["pattern"] == "invalid_assumption"


def test_accuracy_by_category_inconclusive():
    """Category with 30-50% accuracy -> inconclusive."""
    results = [
        {"category": "role_fit", "validated": True},
        {"category": "role_fit", "validated": False},
        {"category": "role_fit", "validated": False},
    ]
    cat_stats = accuracy_by_category(results)
    # 33.3% -> inconclusive
    assert cat_stats["role_fit"]["pattern"] == "inconclusive"


def test_accuracy_by_category_no_data():
    """Category with no resolved entries -> no_data."""
    results = [
        {"category": "ie_framing", "validated": None},
    ]
    cat_stats = accuracy_by_category(results)
    assert cat_stats["ie_framing"]["pattern"] == "no_data"


def test_accuracy_by_category_empty():
    cat_stats = accuracy_by_category([])
    assert cat_stats == {}


def test_accuracy_by_category_defaults_missing_category_to_other():
    results = [{"validated": True}]
    cat_stats = accuracy_by_category(results)
    assert "other" in cat_stats


# ---------------------------------------------------------------------------
# classify_patterns
# ---------------------------------------------------------------------------

def test_classify_patterns_sorts_into_buckets():
    cat_stats = {
        "timing": {"pattern": "validated_pattern"},
        "cover_letter": {"pattern": "invalid_assumption"},
        "role_fit": {"pattern": "inconclusive"},
        "ie_framing": {"pattern": "no_data"},
    }
    patterns = classify_patterns(cat_stats)
    assert patterns["validated"] == ["timing"]
    assert patterns["invalid"] == ["cover_letter"]
    assert patterns["inconclusive"] == ["role_fit"]
    assert patterns["no_data"] == ["ie_framing"]


def test_classify_patterns_empty():
    patterns = classify_patterns({})
    assert patterns == {
        "validated": [],
        "invalid": [],
        "inconclusive": [],
        "no_data": [],
    }


def test_classify_patterns_multiple_validated():
    cat_stats = {
        "timing": {"pattern": "validated_pattern"},
        "auto_rejection": {"pattern": "validated_pattern"},
    }
    patterns = classify_patterns(cat_stats)
    assert sorted(patterns["validated"]) == ["auto_rejection", "timing"]


# ---------------------------------------------------------------------------
# generate_full_report
# ---------------------------------------------------------------------------

def test_generate_full_report_structure():
    results = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "Cold app",
         "predicted": None, "actual": "rejected", "validated": True},
        {"entry_id": "e2", "category": "timing", "hypothesis": "Bad timing",
         "predicted": None, "actual": None, "validated": None},
    ]
    report = generate_full_report(results)

    assert "summary" in report
    assert report["summary"]["total"] == 2
    assert report["summary"]["resolved"] == 1
    assert report["summary"]["correct"] == 1

    assert "category_accuracy" in report
    assert "timing" in report["category_accuracy"]

    assert "patterns" in report
    assert isinstance(report["patterns"]["validated"], list)

    assert "resolved" in report
    assert len(report["resolved"]) == 1
    assert report["resolved"][0]["correct"] is True

    assert "unresolved" in report
    assert len(report["unresolved"]) == 1


def test_generate_full_report_serializable_as_json():
    """Full report should be JSON-serializable for --json output."""
    results = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "test",
         "predicted": None, "actual": "rejected", "validated": True},
    ]
    report = generate_full_report(results)
    serialized = json.dumps(report)
    assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# load_hypotheses / load_conversion_log file handling
# ---------------------------------------------------------------------------

def test_load_hypotheses_supports_dict_shape(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()
    (signals / "hypotheses.yaml").write_text(
        "hypotheses:\n  - hypothesis: test\n    category: timing\n"
    )
    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)
    data = vh_mod.load_hypotheses()
    assert isinstance(data, list)
    assert data[0]["hypothesis"] == "test"


def test_load_hypotheses_supports_list_shape(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()
    (signals / "hypotheses.yaml").write_text(
        "- hypothesis: test\n  category: timing\n"
    )
    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)
    data = vh_mod.load_hypotheses()
    assert isinstance(data, list)
    assert len(data) == 1


def test_load_hypotheses_returns_empty_on_missing_file(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()
    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)
    assert vh_mod.load_hypotheses() == []


def test_load_conversion_log_supports_dict_shape(tmp_path, monkeypatch):
    signals = tmp_path / "signals"
    signals.mkdir()
    (signals / "conversion-log.yaml").write_text(
        "entries:\n  - id: e1\n    outcome: accepted\n"
    )
    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)
    data = vh_mod.load_conversion_log()
    assert isinstance(data, list)
    assert data[0]["id"] == "e1"


# ---------------------------------------------------------------------------
# Integration: validate_hypotheses_with_weights (outcome_learner)
# ---------------------------------------------------------------------------

def test_validate_hypotheses_with_weights_no_hypotheses(tmp_path, monkeypatch):
    """Returns empty results when no hypotheses exist."""
    from outcome_learner import validate_hypotheses_with_weights

    signals = tmp_path / "signals"
    signals.mkdir()
    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)

    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    result = validate_hypotheses_with_weights(base_weights)

    assert "No hypotheses found" in result["report"]
    assert result["adjustments"] == {}
    assert result["yaml_snippet"] == ""


def test_validate_hypotheses_with_weights_generates_increase(tmp_path, monkeypatch):
    """Validated timing pattern -> recommends increasing deadline_feasibility."""
    from outcome_learner import CATEGORY_DIMENSION_MAP, validate_hypotheses_with_weights

    signals = tmp_path / "signals"
    signals.mkdir()

    # Create hypotheses: 3 timing hypotheses, all confirmed by rejection
    hypotheses_data = {
        "hypotheses": [
            {"entry_id": f"e{i}", "category": "timing", "hypothesis": "Cold app"}
            for i in range(3)
        ]
    }
    (signals / "hypotheses.yaml").write_text(yaml.dump(hypotheses_data))

    # Create conversion log with all rejected
    log_data = {
        "entries": [
            {"id": f"e{i}", "outcome": "rejected"} for i in range(3)
        ]
    }
    (signals / "conversion-log.yaml").write_text(yaml.dump(log_data))

    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)

    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    result = validate_hypotheses_with_weights(base_weights)

    # Timing maps to deadline_feasibility
    assert "deadline_feasibility" in CATEGORY_DIMENSION_MAP["timing"]

    # Should recommend increase for deadline_feasibility
    assert "deadline_feasibility" in result["adjustments"]
    assert result["adjustments"]["deadline_feasibility"]["direction"] == "increase"

    # YAML snippet should contain the recommendation
    assert "deadline_feasibility" in result["yaml_snippet"]
    assert "increase" in result["yaml_snippet"]

    # Category accuracy should show timing as validated
    assert result["category_accuracy"]["timing"]["pattern"] == "validated_pattern"
    assert "timing" in result["patterns"]["validated"]


def test_validate_hypotheses_with_weights_generates_decrease(tmp_path, monkeypatch):
    """Invalid cover_letter pattern -> recommends decreasing related dimensions."""
    from outcome_learner import CATEGORY_DIMENSION_MAP, validate_hypotheses_with_weights

    signals = tmp_path / "signals"
    signals.mkdir()

    # Create hypotheses: cover_letter predictions that are wrong (entry accepted despite concern)
    hypotheses_data = {
        "hypotheses": [
            {"entry_id": f"e{i}", "category": "cover_letter", "hypothesis": "No cover letter"}
            for i in range(4)
        ]
    }
    (signals / "hypotheses.yaml").write_text(yaml.dump(hypotheses_data))

    # All accepted -> cover_letter hypothesis was wrong
    log_data = {
        "entries": [
            {"id": f"e{i}", "outcome": "accepted"} for i in range(4)
        ]
    }
    (signals / "conversion-log.yaml").write_text(yaml.dump(log_data))

    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)

    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    result = validate_hypotheses_with_weights(base_weights)

    # cover_letter maps to mission_alignment and evidence_match
    assert "mission_alignment" in CATEGORY_DIMENSION_MAP["cover_letter"]

    # Should have invalid pattern for cover_letter (0% accuracy)
    assert result["category_accuracy"]["cover_letter"]["accuracy"] == 0.0
    assert result["category_accuracy"]["cover_letter"]["pattern"] == "invalid_assumption"
    assert "cover_letter" in result["patterns"]["invalid"]

    # Should recommend decrease for mapped dimensions
    mapped_dims = CATEGORY_DIMENSION_MAP["cover_letter"]
    for dim in mapped_dims:
        assert dim in result["adjustments"]
        assert result["adjustments"][dim]["direction"] == "decrease"


def test_validate_hypotheses_with_weights_increase_overrides_decrease(tmp_path, monkeypatch):
    """When a dimension has both validated and invalid signals, increase wins."""
    from outcome_learner import validate_hypotheses_with_weights

    signals = tmp_path / "signals"
    signals.mkdir()

    # resume_screen (maps to evidence_match, track_record_fit) - all correct -> validated
    # cover_letter (maps to mission_alignment, evidence_match) - all wrong -> invalid
    # evidence_match appears in both: validated should win
    hypotheses_data = {
        "hypotheses": [
            {"entry_id": f"rs{i}", "category": "resume_screen", "hypothesis": "Screen fail"}
            for i in range(3)
        ] + [
            {"entry_id": f"cl{i}", "category": "cover_letter", "hypothesis": "No CL"}
            for i in range(4)
        ]
    }
    (signals / "hypotheses.yaml").write_text(yaml.dump(hypotheses_data))

    log_data = {
        "entries": [
            {"id": f"rs{i}", "outcome": "rejected"} for i in range(3)
        ] + [
            {"id": f"cl{i}", "outcome": "accepted"} for i in range(4)
        ]
    }
    (signals / "conversion-log.yaml").write_text(yaml.dump(log_data))

    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)

    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    result = validate_hypotheses_with_weights(base_weights)

    # evidence_match: resume_screen (validated) and cover_letter (invalid) both map here
    # increase should win over decrease
    assert result["adjustments"]["evidence_match"]["direction"] == "increase"


def test_validate_hypotheses_with_weights_yaml_snippet_format(tmp_path, monkeypatch):
    """YAML snippet should be parseable YAML."""
    from outcome_learner import validate_hypotheses_with_weights

    signals = tmp_path / "signals"
    signals.mkdir()

    hypotheses_data = {
        "hypotheses": [
            {"entry_id": "e1", "category": "timing", "hypothesis": "Cold app"},
            {"entry_id": "e2", "category": "timing", "hypothesis": "Cold app"},
        ]
    }
    (signals / "hypotheses.yaml").write_text(yaml.dump(hypotheses_data))

    log_data = {
        "entries": [
            {"id": "e1", "outcome": "rejected"},
            {"id": "e2", "outcome": "rejected"},
        ]
    }
    (signals / "conversion-log.yaml").write_text(yaml.dump(log_data))

    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)

    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    result = validate_hypotheses_with_weights(base_weights)

    # Filter out comment lines for YAML parsing
    yaml_content = "\n".join(
        line for line in result["yaml_snippet"].split("\n")
        if not line.strip().startswith("#")
    )
    parsed = yaml.safe_load(yaml_content)
    assert parsed is not None
    assert "hypothesis_weight_adjustments" in parsed


def test_validate_hypotheses_with_weights_mixed_resolved_unresolved(tmp_path, monkeypatch):
    """Some resolved, some unresolved -- only resolved count toward accuracy."""
    from outcome_learner import validate_hypotheses_with_weights

    signals = tmp_path / "signals"
    signals.mkdir()

    hypotheses_data = {
        "hypotheses": [
            {"entry_id": "e1", "category": "timing", "hypothesis": "Cold app"},
            {"entry_id": "e2", "category": "timing", "hypothesis": "Cold app"},
            {"entry_id": "e3", "category": "timing", "hypothesis": "Cold app"},
        ]
    }
    (signals / "hypotheses.yaml").write_text(yaml.dump(hypotheses_data))

    # e1 rejected (correct), e2 no outcome, e3 acknowledged (non-terminal)
    log_data = {
        "entries": [
            {"id": "e1", "outcome": "rejected"},
            {"id": "e3", "outcome": "acknowledged"},
        ]
    }
    (signals / "conversion-log.yaml").write_text(yaml.dump(log_data))

    monkeypatch.setattr(vh_mod, "SIGNALS_DIR", signals)

    base_weights = {dim: 1.0 / len(DIMENSION_ORDER) for dim in DIMENSION_ORDER}
    result = validate_hypotheses_with_weights(base_weights)

    # Only 1 resolved out of 3
    assert result["category_accuracy"]["timing"]["total"] == 3
    assert result["category_accuracy"]["timing"]["resolved"] == 1
    assert result["category_accuracy"]["timing"]["correct"] == 1


# ---------------------------------------------------------------------------
# CATEGORY_DIMENSION_MAP completeness
# ---------------------------------------------------------------------------

def test_category_dimension_map_covers_feedback_capture_categories():
    """All valid categories from feedback_capture should have dimension mappings."""
    from feedback_capture import VALID_CATEGORIES
    from outcome_learner import CATEGORY_DIMENSION_MAP

    # 'other' is a catch-all without a mapping, which is fine
    for cat in VALID_CATEGORIES:
        if cat != "other":
            assert cat in CATEGORY_DIMENSION_MAP, (
                f"Category '{cat}' from feedback_capture has no dimension mapping in outcome_learner"
            )


def test_category_dimension_map_dimensions_are_valid():
    """All dimensions referenced in the map must exist in DIMENSION_ORDER."""
    from outcome_learner import CATEGORY_DIMENSION_MAP

    for cat, dims in CATEGORY_DIMENSION_MAP.items():
        for dim in dims:
            assert dim in DIMENSION_ORDER, (
                f"CATEGORY_DIMENSION_MAP['{cat}'] references invalid dimension '{dim}'"
            )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_validate_unknown_category_defaults_to_other():
    """Hypothesis with unrecognized category uses 'other' rules."""
    hypotheses = [
        {"entry_id": "e1", "category": "totally_new", "hypothesis": "Test"}
    ]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    # "totally_new" not in CATEGORY_CONFIRMS_ON -> falls through to
    # CATEGORY_CONFIRMS_ON.get("totally_new", set()) which is empty,
    # then CATEGORY_DISPROVES_ON.get("totally_new", set()) which is empty
    # -> None (unresolved because we can't determine correctness)
    assert results[0]["validated"] is None


def test_validate_handles_missing_hypothesis_field():
    """Hypothesis without 'hypothesis' text still validates."""
    hypotheses = [{"entry_id": "e1", "category": "timing"}]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    assert results[0]["validated"] is True
    assert results[0]["hypothesis"] == ""


def test_validate_multiple_hypotheses_same_entry():
    """Multiple hypotheses for the same entry are each independently validated."""
    hypotheses = [
        {"entry_id": "e1", "category": "timing", "hypothesis": "Bad timing"},
        {"entry_id": "e1", "category": "resume_screen", "hypothesis": "Bad resume"},
    ]
    outcomes = {"e1": "rejected"}
    results = validate(hypotheses, outcomes)
    assert len(results) == 2
    assert results[0]["validated"] is True  # timing -> rejected is correct
    assert results[1]["validated"] is True  # resume_screen -> rejected is correct


def test_validate_with_real_hypothesis_structure():
    """Validate against the actual data structure from signals/hypotheses.yaml."""
    # This mirrors the real file format
    hypotheses = [
        {
            "entry_id": "anthropic-se-claude-code",
            "date": "2026-03-02",
            "outcome": None,
            "category": "timing",
            "hypothesis": "Tier 1 cold app; referral pathway not established",
        },
        {
            "entry_id": "awesome-foundation",
            "date": "2026-03-02",
            "outcome": None,
            "category": "cover_letter",
            "hypothesis": "No tailored cover letter submitted",
        },
    ]
    outcomes = {
        "anthropic-se-claude-code": "rejected",
        "awesome-foundation": "accepted",
    }
    results = validate(hypotheses, outcomes)

    # timing + rejected = correct
    assert results[0]["validated"] is True
    assert results[0]["category"] == "timing"

    # cover_letter + accepted = incorrect (entry succeeded despite concern)
    assert results[1]["validated"] is False
    assert results[1]["category"] == "cover_letter"
