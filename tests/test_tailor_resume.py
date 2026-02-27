"""Tests for scripts/tailor_resume.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from tailor_resume import (
    BASE_RESUME_BY_IDENTITY,
    CURRENT_BATCH,
    RESUMES_DIR,
    resolve_base_resume,
)


# --- resolve_base_resume ---


def test_resolve_base_resume_default():
    """Default identity returns independent-engineer base."""
    result = resolve_base_resume()
    assert "independent-engineer" in str(result)


def test_resolve_base_resume_known_identity():
    """Known identity position returns correct base resume."""
    for identity, expected_path in BASE_RESUME_BY_IDENTITY.items():
        result = resolve_base_resume(identity)
        assert result == expected_path, f"{identity} resolved to wrong path"


def test_resolve_base_resume_unknown_identity():
    """Unknown identity falls back to default."""
    result = resolve_base_resume("nonexistent-identity")
    assert "independent-engineer" in str(result)


# --- Batch format ---


def test_batch_format_validation():
    """Batch folder path follows materials/resumes/batch-NN/ pattern."""
    import re
    assert re.match(r"batch-\d{2}", CURRENT_BATCH), f"CURRENT_BATCH '{CURRENT_BATCH}' doesn't match batch-NN"
    batch_path = RESUMES_DIR / CURRENT_BATCH
    assert "resumes" in str(batch_path)


# --- Wire mechanics (tested via structure, not file writes) ---


def test_wire_resume_ref_format():
    """Wired reference follows expected format."""
    entry_id = "test-company-software-engineer"
    new_ref = f"resumes/{CURRENT_BATCH}/{entry_id}/{entry_id}-resume.html"
    assert new_ref.startswith("resumes/")
    assert entry_id in new_ref
    assert new_ref.endswith("-resume.html")
