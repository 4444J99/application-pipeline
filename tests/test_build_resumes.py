"""Tests for scripts/build_resumes.py"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_resumes import (
    check_page_count,
    find_chrome,
    run_check,
    run_list,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_synthetic_pdf(pages: int) -> bytes:
    """Construct minimal PDF bytes with N /Type /Page objects (not /Pages)."""
    # Each page object has '/Type /Page' (singular)
    # The pages dict has '/Type /Pages' (plural) — should NOT be counted
    lines = [b"% synthetic PDF\n", b"/Type /Pages\n"]
    for _ in range(pages):
        lines.append(b"/Type /Page\n")
    return b"".join(lines)


# --- TestCheckPageCount ---


def test_check_page_count_one_page(tmp_path):
    """PDF with 1 /Type /Page marker → count 1."""
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(_make_synthetic_pdf(1))
    assert check_page_count(pdf) == 1


def test_check_page_count_two_pages(tmp_path):
    """PDF with 2 /Type /Page markers → count 2."""
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(_make_synthetic_pdf(2))
    assert check_page_count(pdf) == 2


def test_check_page_count_excludes_pages_dict(tmp_path):
    """'/Type /Pages' (plural) is NOT counted as a page."""
    pdf = tmp_path / "resume.pdf"
    # Only /Type /Pages — no singular /Type /Page
    pdf.write_bytes(b"/Type /Pages\n")
    assert check_page_count(pdf) == 0


def test_check_page_count_zero_pages(tmp_path):
    """PDF with no page markers → count 0."""
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"% empty pdf\n")
    assert check_page_count(pdf) == 0


# --- TestFindChrome ---


def test_find_chrome_none_when_no_chrome(monkeypatch, tmp_path):
    """All CHROME_PATHS missing and 'which' fails → returns None."""
    import subprocess

    import build_resumes as br

    # Patch CHROME_PATHS to non-existent paths
    monkeypatch.setattr(br, "CHROME_PATHS", ["/nonexistent/chrome"])

    # Patch subprocess.run for 'which google-chrome' to return failure
    original_run = subprocess.run

    def mock_run(cmd, *args, **kwargs):
        if cmd == ["which", "google-chrome"]:
            class FakeResult:
                returncode = 1
                stdout = ""
            return FakeResult()
        return original_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)
    result = find_chrome()
    assert result is None


def test_find_chrome_returns_first_found(monkeypatch, tmp_path):
    """Returns first CHROME_PATH that exists on disk."""
    import build_resumes as br

    fake_chrome = tmp_path / "google-chrome"
    fake_chrome.write_text("#!/usr/bin/env bash\necho chrome\n")
    fake_chrome.chmod(0o755)

    monkeypatch.setattr(br, "CHROME_PATHS", ["/nonexistent/chrome", str(fake_chrome)])
    result = find_chrome()
    assert result == str(fake_chrome)


# --- TestRunCheck ---


def test_run_check_no_html_files(tmp_path, monkeypatch, capsys):
    """No HTML resume files → prints message and returns 1."""
    import build_resumes as br
    monkeypatch.setattr(br, "RESUMES_DIR", tmp_path)
    result = run_check()
    out = capsys.readouterr().out
    assert "No resume HTML files found" in out
    assert result == 1


def test_run_check_missing_pdf_reported(tmp_path, monkeypatch, capsys):
    """HTML file without PDF → 'MISSING' in output."""
    import build_resumes as br
    monkeypatch.setattr(br, "RESUMES_DIR", tmp_path)
    html = tmp_path / "acme-resume.html"
    html.write_text("<html><body>Resume</body></html>")
    result = run_check()
    out = capsys.readouterr().out
    assert "MISSING" in out
    assert result == 1


def test_run_check_stale_pdf_reported(tmp_path, monkeypatch, capsys):
    """PDF older than HTML → 'STALE' in output."""
    import build_resumes as br
    monkeypatch.setattr(br, "RESUMES_DIR", tmp_path)
    html = tmp_path / "acme-resume.html"
    html.write_text("<html><body>Resume</body></html>")
    pdf = tmp_path / "acme-resume.pdf"
    pdf.write_bytes(_make_synthetic_pdf(1))

    # Make PDF appear older than HTML
    old_time = time.time() - 100
    import os
    os.utime(str(pdf), (old_time, old_time))

    result = run_check()
    out = capsys.readouterr().out
    assert "STALE" in out
    assert result == 1


def test_run_check_all_up_to_date(tmp_path, monkeypatch, capsys):
    """HTML+PDF with PDF newer or same mtime → OK."""
    import build_resumes as br
    monkeypatch.setattr(br, "RESUMES_DIR", tmp_path)
    html = tmp_path / "acme-resume.html"
    html.write_text("<html><body>Resume</body></html>")
    pdf = tmp_path / "acme-resume.pdf"
    pdf.write_bytes(_make_synthetic_pdf(1))

    # Make PDF newer than HTML
    new_time = time.time() + 10
    import os
    os.utime(str(pdf), (new_time, new_time))

    result = run_check()
    out = capsys.readouterr().out
    assert "OK" in out
    assert result == 0


def test_run_check_strict_page_count_fail(tmp_path, monkeypatch, capsys):
    """strict=True with 2-page PDF → returns 1."""
    import build_resumes as br
    monkeypatch.setattr(br, "RESUMES_DIR", tmp_path)
    html = tmp_path / "acme-resume.html"
    html.write_text("<html><body>Resume</body></html>")
    pdf = tmp_path / "acme-resume.pdf"
    pdf.write_bytes(_make_synthetic_pdf(2))

    # Make PDF newer than HTML
    new_time = time.time() + 10
    import os
    os.utime(str(pdf), (new_time, new_time))

    result = run_check(strict=True)
    assert result == 1


# --- TestRunList ---


def test_run_list_no_files_message(tmp_path, monkeypatch, capsys):
    """No HTML files → prints 'No resume HTML files found.'"""
    import build_resumes as br
    monkeypatch.setattr(br, "RESUMES_DIR", tmp_path)
    run_list()
    out = capsys.readouterr().out
    assert "No resume HTML files found" in out


def test_run_list_lists_html_files(tmp_path, monkeypatch, capsys):
    """HTML files are listed."""
    import build_resumes as br
    monkeypatch.setattr(br, "RESUMES_DIR", tmp_path)
    html = tmp_path / "acme-resume.html"
    html.write_text("<html><body>Resume</body></html>")
    run_list()
    out = capsys.readouterr().out
    assert "acme-resume.html" in out


def test_run_list_shows_pdf_status(tmp_path, monkeypatch, capsys):
    """PDF status is shown per file."""
    import build_resumes as br
    monkeypatch.setattr(br, "RESUMES_DIR", tmp_path)
    html = tmp_path / "acme-resume.html"
    html.write_text("<html><body>Resume</body></html>")
    # No PDF
    run_list()
    out = capsys.readouterr().out
    assert "NO PDF" in out

    # Now add a PDF
    pdf = tmp_path / "acme-resume.pdf"
    pdf.write_bytes(_make_synthetic_pdf(1))
    run_list()
    out = capsys.readouterr().out
    assert "PDF exists" in out
