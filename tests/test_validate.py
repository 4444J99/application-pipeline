"""Tests for scripts/validate.py"""

import tempfile
from pathlib import Path

import yaml

# Add scripts to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate import validate_entry


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
