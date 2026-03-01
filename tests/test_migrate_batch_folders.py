"""Tests for scripts/migrate_batch_folders.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import migrate_batch_folders as mbf

# --- TestFindResumeFiles ---


def test_find_resume_files_empty_dir(tmp_path):
    """No files in directory → empty list."""
    batch_dir = tmp_path / "batch-01"
    batch_dir.mkdir()
    result = mbf.find_resume_files(batch_dir)
    assert result == []


def test_find_resume_files_finds_html(tmp_path):
    """HTML resume file is detected."""
    batch_dir = tmp_path / "batch-01"
    batch_dir.mkdir()
    (batch_dir / "acme-swe-resume.html").write_text("<html/>")
    result = mbf.find_resume_files(batch_dir)
    assert len(result) == 1
    entry_id, files = result[0]
    assert entry_id == "acme-swe"


def test_find_resume_files_finds_pdf(tmp_path):
    """PDF resume file is detected."""
    batch_dir = tmp_path / "batch-01"
    batch_dir.mkdir()
    (batch_dir / "acme-swe-resume.pdf").write_bytes(b"%PDF-1.4")
    result = mbf.find_resume_files(batch_dir)
    assert len(result) == 1
    entry_id, files = result[0]
    assert entry_id == "acme-swe"


def test_find_resume_files_groups_by_entry_id(tmp_path):
    """HTML and PDF for same entry_id → one group with both files."""
    batch_dir = tmp_path / "batch-01"
    batch_dir.mkdir()
    (batch_dir / "acme-swe-resume.html").write_text("<html/>")
    (batch_dir / "acme-swe-resume.pdf").write_bytes(b"%PDF")
    result = mbf.find_resume_files(batch_dir)
    assert len(result) == 1
    entry_id, files = result[0]
    assert entry_id == "acme-swe"
    assert len(files) == 2


def test_find_resume_files_skips_non_resume(tmp_path):
    """Non-resume HTML files are skipped."""
    batch_dir = tmp_path / "batch-01"
    batch_dir.mkdir()
    (batch_dir / "cover-letter.html").write_text("<html/>")
    (batch_dir / "notes.txt").write_text("some notes")
    result = mbf.find_resume_files(batch_dir)
    assert result == []


def test_find_resume_files_skips_subdirectory_files(tmp_path):
    """Files already inside subdirectories are ignored (not flat)."""
    batch_dir = tmp_path / "batch-01"
    batch_dir.mkdir()
    # Create file inside a subdirectory
    subdir = batch_dir / "acme-swe"
    subdir.mkdir()
    (subdir / "acme-swe-resume.html").write_text("<html/>")
    # find_resume_files only iterates top-level (not rglob)
    result = mbf.find_resume_files(batch_dir)
    assert result == []


def test_find_resume_files_multiple_entries(tmp_path):
    """Multiple distinct entry IDs → multiple groups."""
    batch_dir = tmp_path / "batch-01"
    batch_dir.mkdir()
    (batch_dir / "acme-swe-resume.html").write_text("<html/>")
    (batch_dir / "beta-pm-resume.html").write_text("<html/>")
    result = mbf.find_resume_files(batch_dir)
    assert len(result) == 2
    ids = [entry_id for entry_id, _ in result]
    assert "acme-swe" in ids
    assert "beta-pm" in ids


# --- TestFindCoverLetter ---


def test_find_cover_letter_found(tmp_path, monkeypatch):
    """Returns path when alchemized cover letter exists."""
    cl_dir = tmp_path / "cover-letters"
    cl_dir.mkdir(parents=True)
    cl_file = cl_dir / "acme-swe-alchemized.md"
    cl_file.write_text("# Cover Letter\nBody text here.")
    monkeypatch.setattr(mbf, "VARIANTS_DIR", tmp_path)
    result = mbf.find_cover_letter("acme-swe")
    assert result is not None
    assert result == cl_file


def test_find_cover_letter_none_when_missing(tmp_path, monkeypatch):
    """Returns None when cover letter doesn't exist."""
    monkeypatch.setattr(mbf, "VARIANTS_DIR", tmp_path)
    result = mbf.find_cover_letter("nonexistent-entry")
    assert result is None


# --- TestFindAnswers ---


def test_find_answers_found(tmp_path, monkeypatch):
    """Returns path when answers file exists."""
    answers_dir = tmp_path / ".greenhouse-answers"
    answers_dir.mkdir()
    answers_file = answers_dir / "acme-swe.yaml"
    answers_file.write_text("question: answer\n")
    monkeypatch.setattr(mbf, "ANSWERS_DIR", answers_dir)
    result = mbf.find_answers("acme-swe")
    assert result is not None
    assert result == answers_file


def test_find_answers_none_when_missing(tmp_path, monkeypatch):
    """Returns None when answers file doesn't exist."""
    answers_dir = tmp_path / ".greenhouse-answers"
    answers_dir.mkdir()
    monkeypatch.setattr(mbf, "ANSWERS_DIR", answers_dir)
    result = mbf.find_answers("nonexistent-entry")
    assert result is None


# --- TestUpdatePipelineYamls ---


def test_update_pipeline_yamls_replaces_reference(tmp_path, monkeypatch):
    """Old ref is replaced with new ref in YAML content."""
    pipeline_dir = tmp_path / "active"
    pipeline_dir.mkdir()
    yaml_file = pipeline_dir / "acme-swe.yaml"
    yaml_file.write_text("materials_attached:\n  resume: resumes/batch-01/acme-swe-resume.pdf\n")
    monkeypatch.setattr(mbf, "PIPELINE_DIRS", [pipeline_dir])
    monkeypatch.setattr(mbf, "REPO_ROOT", tmp_path)

    count = mbf.update_pipeline_yamls(
        "resumes/batch-01/acme-swe-resume.pdf",
        "resumes/batch-01/acme-swe/acme-swe-resume.pdf",
        execute=True,
    )
    assert count == 1
    content = yaml_file.read_text()
    assert "resumes/batch-01/acme-swe/acme-swe-resume.pdf" in content
    assert "resumes/batch-01/acme-swe-resume.pdf" not in content


def test_update_pipeline_yamls_no_match_returns_zero(tmp_path, monkeypatch):
    """No matching reference → returns 0."""
    pipeline_dir = tmp_path / "active"
    pipeline_dir.mkdir()
    yaml_file = pipeline_dir / "acme-swe.yaml"
    yaml_file.write_text("materials_attached:\n  resume: some/other/path.pdf\n")
    monkeypatch.setattr(mbf, "PIPELINE_DIRS", [pipeline_dir])
    monkeypatch.setattr(mbf, "REPO_ROOT", tmp_path)

    count = mbf.update_pipeline_yamls(
        "resumes/batch-01/acme-swe-resume.pdf",
        "resumes/batch-01/acme-swe/acme-swe-resume.pdf",
        execute=True,
    )
    assert count == 0


def test_update_pipeline_yamls_dry_run_no_write(tmp_path, monkeypatch):
    """execute=False → file content unchanged."""
    pipeline_dir = tmp_path / "active"
    pipeline_dir.mkdir()
    yaml_file = pipeline_dir / "acme-swe.yaml"
    original_content = "materials_attached:\n  resume: resumes/batch-01/acme-swe-resume.pdf\n"
    yaml_file.write_text(original_content)
    monkeypatch.setattr(mbf, "PIPELINE_DIRS", [pipeline_dir])
    monkeypatch.setattr(mbf, "REPO_ROOT", tmp_path)

    count = mbf.update_pipeline_yamls(
        "resumes/batch-01/acme-swe-resume.pdf",
        "resumes/batch-01/acme-swe/acme-swe-resume.pdf",
        execute=False,
    )
    assert count == 1  # Reports the would-be match
    assert yaml_file.read_text() == original_content  # File unchanged


def test_update_pipeline_yamls_skips_underscore_files(tmp_path, monkeypatch):
    """Files starting with _ are skipped."""
    pipeline_dir = tmp_path / "active"
    pipeline_dir.mkdir()
    schema_file = pipeline_dir / "_schema.yaml"
    schema_file.write_text("resume: resumes/batch-01/acme-swe-resume.pdf\n")
    monkeypatch.setattr(mbf, "PIPELINE_DIRS", [pipeline_dir])
    monkeypatch.setattr(mbf, "REPO_ROOT", tmp_path)

    count = mbf.update_pipeline_yamls(
        "resumes/batch-01/acme-swe-resume.pdf",
        "new-path",
        execute=True,
    )
    assert count == 0
