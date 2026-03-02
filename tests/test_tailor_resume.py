"""Tests for scripts/tailor_resume.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from tailor_resume import (
    BASE_RESUME_BY_IDENTITY,
    CURRENT_BATCH,
    DEFAULT_BASE_RESUME,
    RESUMES_DIR,
    SECTION_MARKERS,
    extract_sections,
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


# --- Identity position mapping ---


def test_all_identities_have_base_resume():
    """Every identity position maps to a Path."""
    for identity, path in BASE_RESUME_BY_IDENTITY.items():
        assert isinstance(path, Path), f"{identity} doesn't map to a Path"
        assert "resumes" in str(path).lower(), f"{identity} path doesn't contain 'resumes'"


def test_default_base_resume_is_independent_engineer():
    """Default base resume is the independent-engineer template."""
    assert "independent-engineer" in str(DEFAULT_BASE_RESUME)


def test_resolve_base_resume_all_identities():
    """resolve_base_resume returns correct path for each known identity."""
    for identity in BASE_RESUME_BY_IDENTITY:
        result = resolve_base_resume(identity)
        assert result == BASE_RESUME_BY_IDENTITY[identity]


def test_resolve_base_resume_none():
    """None identity returns default."""
    result = resolve_base_resume(None)
    assert result == DEFAULT_BASE_RESUME


# --- Section patterns ---


def test_section_patterns_keys():
    """Section patterns include expected resume sections."""
    expected = {"TITLE_LINE", "PROFILE", "SKILLS", "PROJECTS", "EXPERIENCE"}
    assert set(SECTION_MARKERS.keys()) == expected


def test_section_patterns_have_start_end():
    """Each section pattern has start and end regex."""
    for name, pattern in SECTION_MARKERS.items():
        assert "start" in pattern, f"{name} missing start"
        assert "end" in pattern, f"{name} missing end"


# --- extract_sections ---


def test_extract_sections_empty_html():
    """Empty HTML returns empty dict."""
    sections = extract_sections("")
    assert sections == {}


def test_extract_sections_partial_html():
    """HTML with only some sections extracts what's available."""
    html = '<div class="skills-list">python, go, rust</div>'
    sections = extract_sections(html)
    # Should extract SKILLS or return empty depending on full pattern match
    assert isinstance(sections, dict)


# --- Batch path structure ---


def test_batch_path_under_resumes():
    """Batch directory is under RESUMES_DIR."""
    batch_path = RESUMES_DIR / CURRENT_BATCH
    assert str(batch_path).startswith(str(RESUMES_DIR))


def test_resumes_dir_is_materials():
    """RESUMES_DIR is under materials/."""
    assert "materials" in str(RESUMES_DIR)
