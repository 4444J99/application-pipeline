"""Tests for scripts/recruiter_filter.py — pre-submission recruiter/hiring-manager filter."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from recruiter_filter import (
    CANONICAL,
    RED_FLAGS,
    STALE_METRICS,
    auto_fix_stale_metrics,
    check_entry,
    check_file,
)


@pytest.fixture
def tmp_file(tmp_path):
    """Create a temporary file with given content."""
    def _make(content, name="test.html"):
        f = tmp_path / name
        f.write_text(content)
        return f
    return _make


# --- Canonical metrics ---


class TestCanonical:
    def test_canonical_has_required_keys(self):
        required = ["repos", "orgs", "words", "tests_system", "cicd", "dependency_edges",
                     "courses", "students", "agentic_tests", "recursive_tests"]
        for key in required:
            assert key in CANONICAL, f"Missing canonical key: {key}"

    def test_canonical_repos_is_current(self):
        assert CANONICAL["repos"] == 113

    def test_canonical_words_is_current(self):
        assert CANONICAL["words"] == "739K"

    def test_canonical_cicd_is_current(self):
        assert CANONICAL["cicd"] == 104


# --- Stale metric detection ---


class TestStaleMetrics:
    def test_detects_old_repo_count(self, tmp_file):
        f = tmp_file("Built a 103-repository system across 8 orgs")
        findings = check_file(f)
        errors = [x for x in findings if x["severity"] == "error"]
        assert any("103" in e["message"] for e in errors)

    def test_detects_old_word_count(self, tmp_file):
        f = tmp_file("Authored 386K words of documentation")
        findings = check_file(f)
        errors = [x for x in findings if x["severity"] == "error"]
        assert any("386K" in e["message"] or "739K" in e["message"] for e in errors)

    def test_detects_old_cicd_count(self, tmp_file):
        f = tmp_file("Maintained 94 CI/CD pipelines across the system")
        findings = check_file(f)
        errors = [x for x in findings if x["severity"] == "error"]
        assert any("94" in e["message"] or "104" in e["message"] for e in errors)

    def test_detects_old_test_count(self, tmp_file):
        f = tmp_file("Framework with 1,276 tests and 85% coverage")
        findings = check_file(f)
        errors = [x for x in findings if x["severity"] == "error"]
        assert any("1,276" in e["message"] or "1,095" in e["message"] for e in errors)

    def test_detects_old_edge_count(self, tmp_file):
        f = tmp_file("31 dependency edges with zero violations")
        findings = check_file(f)
        errors = [x for x in findings if x["severity"] == "error"]
        assert any("31" in e["message"] or "50" in e["message"] for e in errors)

    def test_passes_current_metrics(self, tmp_file):
        f = tmp_file("Built a 113-repository system with 739K words, 104 CI/CD pipelines, 2,349 tests, 50 dependency edges")
        findings = check_file(f)
        errors = [x for x in findings if x["severity"] == "error"]
        assert len(errors) == 0

    def test_stale_patterns_have_severity(self):
        for pattern, should_be, severity in STALE_METRICS:
            assert severity in ("error", "warning"), f"Invalid severity for pattern '{pattern}'"


# --- Red flag detection ---


class TestRedFlags:
    def test_detects_independent_self_employed(self, tmp_file):
        f = tmp_file("Independent · Self-employed · Jan 2020 - Present")
        findings = check_file(f)
        warnings = [x for x in findings if x["check"] == "red_flag"]
        assert len(warnings) >= 1

    def test_detects_open_to_work(self, tmp_file):
        f = tmp_file("I am open to opportunities in software engineering")
        findings = check_file(f)
        warnings = [x for x in findings if x["check"] == "red_flag"]
        assert any("Open to" in w["message"] or "opportunities" in w["message"] for w in warnings)

    def test_detects_responsible_for(self, tmp_file):
        f = tmp_file("Responsible for maintaining the CI/CD pipeline")
        findings = check_file(f)
        warnings = [x for x in findings if x["check"] == "red_flag"]
        assert any("Responsible for" in w["message"] for w in warnings)

    def test_passes_clean_content(self, tmp_file):
        f = tmp_file("Architected a multi-tenant orchestration system governing 113 repositories.")
        findings = check_file(f)
        red_flags = [x for x in findings if x["check"] == "red_flag"]
        assert len(red_flags) == 0

    def test_red_flags_have_messages(self):
        for pattern, message in RED_FLAGS:
            assert len(message) > 10, f"Red flag pattern '{pattern}' has empty message"


# --- Format checks ---


class TestFormatChecks:
    def test_detects_long_cover_letter(self, tmp_file):
        long_text = "word " * 600
        f = tmp_file(long_text, name="test-cover-letter.md")
        findings = check_file(f)
        warnings = [x for x in findings if x["check"] == "not_too_long_cl"]
        assert len(warnings) == 1

    def test_passes_short_cover_letter(self, tmp_file):
        short_text = "word " * 300
        f = tmp_file(short_text, name="test-cover-letter.md")
        findings = check_file(f)
        warnings = [x for x in findings if x["check"] == "not_too_long_cl"]
        assert len(warnings) == 0

    def test_detects_html_in_cover_letter(self, tmp_file):
        f = tmp_file("<p>This is HTML content</p>", name="cover-letter.md")
        findings = check_file(f)
        warnings = [x for x in findings if x["check"] == "plain_text_cl"]
        assert len(warnings) == 1


# --- Auto-fix ---


class TestAutoFix:
    def test_auto_fix_replaces_stale_metrics(self, tmp_path, monkeypatch):
        import recruiter_filter
        monkeypatch.setattr(recruiter_filter, "REPO_ROOT", tmp_path)

        base_dir = tmp_path / "materials" / "resumes" / "base"
        base_dir.mkdir(parents=True)
        resume = base_dir / "test-resume.html"
        resume.write_text("103-repository system with 94 CI/CD pipelines and 386K words")

        fixed = auto_fix_stale_metrics(dry_run=False)
        assert fixed == 1

        content = resume.read_text()
        assert "113" in content
        assert "104" in content
        assert "739K" in content

    def test_auto_fix_dry_run_does_not_modify(self, tmp_path, monkeypatch):
        import recruiter_filter
        monkeypatch.setattr(recruiter_filter, "REPO_ROOT", tmp_path)

        base_dir = tmp_path / "materials" / "resumes" / "base"
        base_dir.mkdir(parents=True)
        resume = base_dir / "test-resume.html"
        resume.write_text("103-repository system")

        auto_fix_stale_metrics(dry_run=True)
        assert "103" in resume.read_text()  # Not changed

    def test_auto_fix_skips_clean_files(self, tmp_path, monkeypatch):
        import recruiter_filter
        monkeypatch.setattr(recruiter_filter, "REPO_ROOT", tmp_path)

        base_dir = tmp_path / "materials" / "resumes" / "base"
        base_dir.mkdir(parents=True)
        resume = base_dir / "clean-resume.html"
        resume.write_text("113-repository system with 104 CI/CD pipelines")

        fixed = auto_fix_stale_metrics(dry_run=False)
        assert fixed == 0


# --- Entry-level checks ---


class TestEntryChecks:
    def test_missing_cover_letter_is_error(self, tmp_path, monkeypatch):
        import recruiter_filter
        monkeypatch.setattr(recruiter_filter, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(recruiter_filter, "ALL_PIPELINE_DIRS", [])

        # Create batch-03 resume but no cover letter
        batch = tmp_path / "materials" / "resumes" / "batch-03" / "test-entry"
        batch.mkdir(parents=True)
        (batch / "test-entry-resume.html").write_text("Clean resume content with 113 repos")

        findings = check_entry("test-entry")
        errors = [x for x in findings if x["check"] == "cover_letter_exists"]
        assert len(errors) == 1

    def test_missing_tailored_resume_is_error(self, tmp_path, monkeypatch):
        import recruiter_filter
        monkeypatch.setattr(recruiter_filter, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(recruiter_filter, "ALL_PIPELINE_DIRS", [])

        # Create cover letter but no batch-03 resume
        cl_dir = tmp_path / "variants" / "cover-letters"
        cl_dir.mkdir(parents=True)
        (cl_dir / "test-entry.md").write_text("Dear Team,\n\nFinancial transactions are state machines.")

        findings = check_entry("test-entry")
        errors = [x for x in findings if x["check"] == "resume_tailored"]
        assert len(errors) == 1

    def test_complete_entry_passes(self, tmp_path, monkeypatch):
        import recruiter_filter
        monkeypatch.setattr(recruiter_filter, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(recruiter_filter, "ALL_PIPELINE_DIRS", [])

        # Create both cover letter and resume
        cl_dir = tmp_path / "variants" / "cover-letters"
        cl_dir.mkdir(parents=True)
        (cl_dir / "test-entry.md").write_text("Dear Team,\n\nFinancial transactions are state machines. 113 repos.")

        batch = tmp_path / "materials" / "resumes" / "batch-03" / "test-entry"
        batch.mkdir(parents=True)
        (batch / "test-entry-resume.html").write_text("113-repo system with 739K words and 104 CI/CD")

        findings = check_entry("test-entry")
        errors = [x for x in findings if x["severity"] == "error"]
        assert len(errors) == 0

    def test_generic_opener_detected(self, tmp_path, monkeypatch):
        import recruiter_filter
        monkeypatch.setattr(recruiter_filter, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(recruiter_filter, "ALL_PIPELINE_DIRS", [])

        cl_dir = tmp_path / "variants" / "cover-letters"
        cl_dir.mkdir(parents=True)
        (cl_dir / "test-entry.md").write_text("Dear Team,\n\nI am writing to express my interest in the role.")

        batch = tmp_path / "materials" / "resumes" / "batch-03" / "test-entry"
        batch.mkdir(parents=True)
        (batch / "test.html").write_text("clean")

        findings = check_entry("test-entry")
        warnings = [x for x in findings if x["check"] == "generic_opener"]
        assert len(warnings) == 1
