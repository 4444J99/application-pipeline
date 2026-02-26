"""Tests for scripts/validate.py"""

import tempfile
from pathlib import Path

import yaml

# Add scripts to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate import validate_entry, _reachable_statuses, VALID_TRANSITIONS, VALID_DEFERRAL_REASONS


def _write_yaml(tmp_dir: Path, filename: str, data: dict) -> Path:
    """Write a YAML file and return its path."""
    filepath = tmp_dir / filename
    with open(filepath, "w") as f:
        yaml.dump(data, f)
    return filepath


def test_valid_entry_passes():
    """A well-formed entry should produce no errors."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_missing_required_field():
    """An entry missing a required field should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            # missing track and status
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("Missing required field: track" in e for e in errors)
        assert any("Missing required field: status" in e for e in errors)


def test_invalid_track():
    """An entry with an invalid track should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "invalid_track",
            "status": "qualified",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("Invalid track" in e for e in errors)


def test_invalid_status():
    """An entry with an invalid status should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "bogus",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("Invalid status" in e for e in errors)


def test_id_filename_mismatch():
    """An entry whose id doesn't match the filename should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "wrong-id",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("does not match filename" in e for e in errors)


def test_fit_score_out_of_range():
    """A fit score outside 1-10 should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "fit": {"score": 15},
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("out of range" in e for e in errors)


def test_invalid_outcome():
    """An invalid outcome value should produce an error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "outcome",
            "outcome": "maybe",
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("Invalid outcome" in e for e in errors)


def test_all_valid_tracks():
    """All valid track values should pass validation."""
    valid_tracks = [
        "grant", "residency", "job", "fellowship",
        "writing", "emergency", "prize", "program", "consulting",
    ]
    for track in valid_tracks:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data = {
                "id": "test-entry",
                "name": "Test Entry",
                "track": track,
                "status": "qualified",
                "outcome": None,
            }
            filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
            errors = validate_entry(filepath)
            assert errors == [], f"Track '{track}' should be valid, got: {errors}"


# --- Status transition validation tests ---


def test_reachable_from_research():
    """All statuses should be reachable from research."""
    reachable = _reachable_statuses("research")
    assert "qualified" in reachable
    assert "submitted" in reachable
    assert "outcome" in reachable


def test_reachable_from_outcome():
    """No statuses should be reachable from outcome (terminal)."""
    reachable = _reachable_statuses("outcome")
    assert reachable == set()


def test_valid_transitions_keys():
    """Every status in VALID_TRANSITIONS should map to valid statuses."""
    all_statuses = set(VALID_TRANSITIONS.keys()) | {"withdrawn"}
    for status, targets in VALID_TRANSITIONS.items():
        for target in targets:
            assert target in all_statuses, (
                f"Transition target '{target}' from '{status}' is not a valid status"
            )


def test_transition_consistent_timeline():
    """An entry whose status matches its timeline should pass."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "timeline": {
                "researched": "2026-01-01",
                "qualified": "2026-01-15",
                "materials_ready": None,
                "submitted": None,
                "acknowledged": None,
                "interview": None,
                "outcome_date": None,
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_transition_inconsistent_timeline():
    """An entry whose status can't be reached from its timeline should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "research",
            "outcome": None,
            "timeline": {
                "researched": "2026-01-01",
                "qualified": "2026-01-15",
                "materials_ready": None,
                "submitted": "2026-02-01",
                "acknowledged": None,
                "interview": None,
                "outcome_date": None,
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("not reachable" in e for e in errors)


# --- Recommendations validation ---


def test_valid_recommendations():
    """An entry with valid recommendations should pass."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "recommendations": [
                {"name": "Jane Doe", "status": "asked", "relationship": "advisor"},
            ],
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_recommendation_status():
    """An entry with invalid recommendation status should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "recommendations": [
                {"name": "Jane Doe", "status": "maybe"},
            ],
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("recommendations[0].status" in e for e in errors)


# --- Portal fields validation ---


def test_valid_portal_fields():
    """An entry with valid portal_fields should pass."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "portal_fields": {
                "platform": "submittable",
                "fields": [
                    {"name": "Artist Statement", "format": "textarea", "char_limit": 2000},
                ],
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_portal_field_format():
    """An entry with invalid portal field format should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "portal_fields": {
                "platform": "submittable",
                "fields": [
                    {"name": "Test", "format": "hologram"},
                ],
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("portal_fields.fields[0].format" in e for e in errors)


# --- Withdrawal reason validation ---


def test_valid_withdrawal_reason():
    """An entry with valid withdrawal_reason should pass."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "outcome",
            "outcome": "withdrawn",
            "withdrawal_reason": {
                "reason": "missed_deadline",
                "detail": "Deadline passed",
                "date": "2026-02-01",
                "reopen": False,
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_withdrawal_reason():
    """An entry with invalid withdrawal reason should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "outcome",
            "outcome": "withdrawn",
            "withdrawal_reason": {
                "reason": "aliens",
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("withdrawal_reason.reason" in e for e in errors)


# --- Deferred status validation ---


def test_deferred_status_valid():
    """An entry with status=deferred should pass validation."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "deferred",
            "outcome": None,
            "deferral": {
                "reason": "portal_paused",
                "resume_date": "2026-06-01",
                "note": "Portal paused until June.",
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


def test_deferred_without_deferral_field_warns():
    """A deferred entry without deferral field should produce a warning."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "deferred",
            "outcome": None,
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("no 'deferral' field present" in e for e in errors)


def test_invalid_deferral_reason():
    """An entry with an invalid deferral reason should error."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "deferred",
            "outcome": None,
            "deferral": {
                "reason": "bored",
            },
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert any("deferral.reason" in e for e in errors)


def test_valid_deferral_reasons():
    """All valid deferral reasons should pass."""
    for reason in VALID_DEFERRAL_REASONS:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data = {
                "id": "test-entry",
                "name": "Test Entry",
                "track": "grant",
                "status": "deferred",
                "outcome": None,
                "deferral": {"reason": reason},
            }
            filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
            errors = validate_entry(filepath)
            assert not any("deferral.reason" in e for e in errors), (
                f"Reason '{reason}' should be valid, got: {errors}"
            )


# --- Fixed deadline type validation ---


def test_fixed_deadline_type_valid():
    """An entry with deadline.type=fixed should pass validation."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data = {
            "id": "test-entry",
            "name": "Test Entry",
            "track": "grant",
            "status": "qualified",
            "outcome": None,
            "deadline": {"date": "2026-03-16", "type": "fixed"},
        }
        filepath = _write_yaml(tmp_path, "test-entry.yaml", data)
        errors = validate_entry(filepath)
        assert errors == [], f"Expected no errors, got: {errors}"


# --- Deferred reachability ---


def test_deferred_reachable_from_research():
    """deferred should be reachable from research via qualified/drafting/staged."""
    reachable = _reachable_statuses("research")
    assert "deferred" in reachable
