"""Integration tests for pipeline_api module.

Tests that the API layer works correctly with real pipeline data.
"""

import pytest
import sys
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_api import (
    score_entry,
    advance_entry,
    draft_entry,
    compose_entry,
    validate_entry,
    ResultStatus,
)


class TestScoreAPI:
    """Test score_entry API function."""

    def test_score_entry_requires_entry_id(self):
        """Test that score_entry requires entry_id or auto_qualify."""
        result = score_entry(entry_id=None, auto_qualify=False)
        assert result.status == ResultStatus.ERROR
        assert "entry_id required" in result.error.lower()

    def test_score_entry_success_structure(self):
        """Test that successful score result has expected structure."""
        result = score_entry(entry_id="test-entry", dry_run=True)
        assert result.entry_id == "test-entry"
        assert result.status in [ResultStatus.SUCCESS, ResultStatus.DRY_RUN, ResultStatus.ERROR]
        assert result.message is not None


class TestAdvanceAPI:
    """Test advance_entry API function."""

    def test_advance_requires_entry_id(self):
        """Test that advance_entry requires entry_id."""
        result = advance_entry(entry_id=None)
        assert result.status == ResultStatus.ERROR
        assert "entry_id required" in result.error.lower()

    def test_advance_success_structure(self):
        """Test that successful advance result has expected structure."""
        result = advance_entry(entry_id="test-entry", dry_run=True)
        assert result.entry_id == "test-entry"
        assert result.status in [ResultStatus.SUCCESS, ResultStatus.DRY_RUN, ResultStatus.ERROR]
        assert result.message is not None


class TestDraftAPI:
    """Test draft_entry API function."""

    def test_draft_requires_entry_id(self):
        """Test that draft_entry requires entry_id."""
        result = draft_entry(entry_id=None)
        assert result.status == ResultStatus.ERROR
        assert "entry_id required" in result.error.lower()

    def test_draft_success_structure(self):
        """Test that successful draft result has expected structure."""
        result = draft_entry(entry_id="test-entry", dry_run=True)
        assert result.entry_id == "test-entry"
        assert result.status in [ResultStatus.SUCCESS, ResultStatus.DRY_RUN, ResultStatus.ERROR]
        assert result.message is not None


class TestComposeAPI:
    """Test compose_entry API function."""

    def test_compose_requires_entry_id(self):
        """Test that compose_entry requires entry_id."""
        result = compose_entry(entry_id=None)
        assert result.status == ResultStatus.ERROR
        assert "entry_id required" in result.error.lower()

    def test_compose_success_structure(self):
        """Test that successful compose result has expected structure."""
        result = compose_entry(entry_id="test-entry", dry_run=True)
        assert result.entry_id == "test-entry"
        assert result.status in [ResultStatus.SUCCESS, ResultStatus.DRY_RUN, ResultStatus.ERROR]
        assert result.message is not None


class TestValidateAPI:
    """Test validate_entry API function."""

    def test_validate_requires_input(self):
        """Test that validate_entry requires entry_id or entry_dict."""
        result = validate_entry()
        assert result.status == ResultStatus.ERROR
        assert "required" in result.message.lower() or result.errors

    def test_validate_success_structure(self):
        """Test that successful validation result has expected structure."""
        result = validate_entry(entry_id="test-entry")
        assert result.entry_id is not None
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_validate_dict_input(self):
        """Test validate_entry with entry dict."""
        entry_dict = {"id": "test-entry", "status": "research"}
        result = validate_entry(entry_dict=entry_dict)
        assert result.entry_id is not None
        assert isinstance(result.is_valid, bool)


class TestAPIResultTypes:
    """Test API result dataclass types."""

    def test_score_result_has_fields(self):
        """Test ScoreResult has expected fields."""
        from pipeline_api import ScoreResult
        result = ScoreResult(
            status=ResultStatus.SUCCESS,
            entry_id="test",
            old_score=7.0,
            new_score=7.5,
        )
        assert result.entry_id == "test"
        assert result.old_score == 7.0
        assert result.new_score == 7.5

    def test_advance_result_has_fields(self):
        """Test AdvanceResult has expected fields."""
        from pipeline_api import AdvanceResult
        result = AdvanceResult(
            status=ResultStatus.SUCCESS,
            entry_id="test",
            old_status="research",
            new_status="qualified",
        )
        assert result.entry_id == "test"
        assert result.old_status == "research"
        assert result.new_status == "qualified"

    def test_validation_result_initialization(self):
        """Test ValidationResult initializes errors and warnings lists."""
        from pipeline_api import ValidationResult
        result = ValidationResult(
            status=ResultStatus.SUCCESS,
            entry_id="test",
            is_valid=True,
        )
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_with_errors(self):
        """Test ValidationResult with explicit errors."""
        from pipeline_api import ValidationResult
        result = ValidationResult(
            status=ResultStatus.ERROR,
            entry_id="test",
            is_valid=False,
            errors=["Missing resume", "Invalid status"],
            warnings=["Old date"],
        )
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
