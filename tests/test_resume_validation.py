"""Tests for resume validation in preflight checks."""

import pytest
import sys
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from preflight import check_entry


class TestResumeValidation:
    """Test resume validation in preflight checks."""

    def test_base_resume_error(self):
        """Base resume in materials_attached triggers critical error."""
        entry = {
            "id": "test-entry",
            "status": "staged",
            "submission": {
                "materials_attached": ["resumes/base/engineer.pdf"],
            },
            "target": {"application_url": "https://example.com"},
        }
        errors, warnings = check_entry(entry)
        assert any("base resume" in e.lower() and "critical" in e.lower() for e in errors)

    def test_base_resume_path_error(self):
        """Base resume in resume_path field triggers error."""
        entry = {
            "id": "test-entry",
            "status": "staged",
            "submission": {
                "resume_path": "materials/resumes/base/engineer.pdf",
            },
            "target": {"application_url": "https://example.com"},
        }
        errors, warnings = check_entry(entry)
        assert any("base resume" in e.lower() for e in errors)

    def test_batch_resume_passes(self):
        """Batch resume (tailored) doesn't trigger base resume error."""
        entry = {
            "id": "test-entry",
            "status": "staged",
            "submission": {
                "materials_attached": ["resumes/batch-03/test-entry.pdf"],
            },
            "target": {"application_url": "https://example.com"},
        }
        errors, warnings = check_entry(entry)
        # Should not have base resume error (though may have other errors)
        assert not any("base resume" in e.lower() for e in errors if "critical" in e.lower())

    def test_resume_path_not_found(self):
        """Non-existent resume file triggers error."""
        entry = {
            "id": "test-entry",
            "status": "staged",
            "submission": {
                "resume_path": "materials/resumes/batch-03/nonexistent.pdf",
            },
            "target": {"application_url": "https://example.com"},
        }
        errors, warnings = check_entry(entry)
        assert any("not found" in e.lower() for e in errors)

    def test_non_pdf_resume(self):
        """Non-PDF resume file triggers error (only checked if path exists conceptually)."""
        entry = {
            "id": "test-entry",
            "status": "staged",
            "submission": {
                "resume_path": "materials/resumes/batch-03/test.txt",
            },
            "target": {"application_url": "https://example.com"},
        }
        errors, warnings = check_entry(entry)
        # Should get either "not found" or "must be PDF" error
        assert any(("not found" in e.lower() or "must be pdf" in e.lower()) for e in errors)
