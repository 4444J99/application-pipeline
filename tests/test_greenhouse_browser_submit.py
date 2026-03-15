"""Tests for scripts/greenhouse_browser_submit.py (helper functions only).

Browser automation (Playwright) is not tested here — only the data resolution
functions that prepare submissions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import greenhouse_browser_submit as gbs


def test_load_config(monkeypatch, tmp_path):
    config = {"first_name": "Test", "last_name": "User", "email": "test@test.com", "phone": "555-1234"}
    config_path = tmp_path / ".submit-config.yaml"
    config_path.write_text(yaml.dump(config))
    monkeypatch.setattr(gbs, "load_config", lambda: config)
    result = gbs.load_config()
    assert result["first_name"] == "Test"


def test_load_answers_exists(monkeypatch, tmp_path):
    answers_dir = tmp_path / ".greenhouse-answers"
    answers_dir.mkdir()
    answers = {"q1": "yes", "q2": "no"}
    (answers_dir / "test-entry.yaml").write_text(yaml.dump(answers))

    # Monkeypatch the path resolution
    def patched_load(entry_id):
        path = answers_dir / f"{entry_id}.yaml"
        if path.exists():
            return yaml.safe_load(path.read_text()) or {}
        return {}

    monkeypatch.setattr(gbs, "load_answers", patched_load)
    result = gbs.load_answers("test-entry")
    assert result == {"q1": "yes", "q2": "no"}


def test_load_answers_missing(monkeypatch, tmp_path):
    def patched_load(entry_id):
        path = tmp_path / f"{entry_id}.yaml"
        if path.exists():
            return yaml.safe_load(path.read_text()) or {}
        return {}

    monkeypatch.setattr(gbs, "load_answers", patched_load)
    result = gbs.load_answers("nonexistent")
    assert result == {}


def test_resolve_resume_batch_03_html():
    entry = {
        "submission": {
            "materials_attached": [
                "resumes/batch-03/test-entry/test-entry-resume.html",
            ]
        }
    }
    result = gbs.resolve_resume(entry)
    assert result is not None
    assert "test-entry-resume.pdf" in str(result)
    assert "batch-03" in str(result)


def test_resolve_resume_batch_03_pdf():
    entry = {
        "submission": {
            "materials_attached": [
                "resumes/batch-03/test-entry/test-entry-resume.pdf",
            ]
        }
    }
    result = gbs.resolve_resume(entry)
    assert result is not None
    assert str(result).endswith(".pdf")


def test_resolve_resume_no_batch_03():
    entry = {
        "submission": {
            "materials_attached": [
                "resumes/independent-engineer-resume.html",
            ]
        }
    }
    result = gbs.resolve_resume(entry)
    assert result is None


def test_resolve_resume_empty_materials():
    entry = {"submission": {"materials_attached": []}}
    result = gbs.resolve_resume(entry)
    assert result is None


def test_resolve_resume_no_submission():
    result = gbs.resolve_resume({})
    assert result is None


def test_resolve_cover_letter_exists(tmp_path, monkeypatch):
    variants = tmp_path / "variants"
    variants.mkdir()
    cl_path = variants / "cover-letters"
    cl_path.mkdir()
    (cl_path / "test-entry.md").write_text("Dear Team,\n\nI am applying.\n\nSincerely,\nTest")

    monkeypatch.setattr(gbs, "REPO_ROOT", tmp_path)
    entry = {"submission": {"variant_ids": {"cover_letter": "cover-letters/test-entry"}}}
    result = gbs.resolve_cover_letter(entry)
    assert "Dear Team" in result
    assert "applying" in result


def test_resolve_cover_letter_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(gbs, "REPO_ROOT", tmp_path)
    entry = {"submission": {"variant_ids": {"cover_letter": "cover-letters/nonexistent"}}}
    result = gbs.resolve_cover_letter(entry)
    assert result == ""


def test_resolve_cover_letter_no_variant():
    entry = {"submission": {"variant_ids": {}}}
    result = gbs.resolve_cover_letter(entry)
    assert result == ""


def test_resolve_cover_letter_no_submission():
    result = gbs.resolve_cover_letter({})
    assert result == ""
