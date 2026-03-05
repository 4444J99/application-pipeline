#!/usr/bin/env python3
"""Tests for skills_gap.py — skills coverage analysis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from skills_gap import (
    analyze_entry,
    compute_coverage,
    extract_required_skills,
    format_analysis,
)


def _entry(entry_id="test-role", keywords=None, requirements=None):
    e = {
        "id": entry_id,
        "name": "Test Role",
        "status": "qualified",
        "fit": {"score": 8.0},
        "target": {},
        "submission": {},
    }
    if keywords:
        e["submission"]["keywords"] = keywords
    if requirements:
        e["target"]["requirements"] = requirements
    return e


class TestExtractRequiredSkills:
    def test_from_keywords(self):
        entry = _entry(keywords=["python", "kubernetes", "terraform"])
        skills = extract_required_skills(entry)
        assert "python" in skills
        assert "kubernetes" in skills

    def test_from_requirements_string(self):
        entry = _entry(requirements="Experience with React and TypeScript required")
        skills = extract_required_skills(entry)
        assert "react" in skills
        assert "typescript" in skills

    def test_from_requirements_list(self):
        entry = _entry(requirements=["golang", "docker"])
        skills = extract_required_skills(entry)
        assert "golang" in skills

    def test_filters_stop_words(self):
        entry = _entry(keywords=["the", "and", "python"])
        skills = extract_required_skills(entry)
        assert "the" not in skills
        assert "python" in skills

    def test_empty_entry(self):
        entry = _entry()
        skills = extract_required_skills(entry)
        assert isinstance(skills, list)


class TestComputeCoverage:
    def test_full_coverage(self):
        result = compute_coverage(["python", "react"], "I know python and react well")
        assert result["coverage_pct"] == 100.0
        assert len(result["missing"]) == 0

    def test_partial_coverage(self):
        result = compute_coverage(["python", "rust", "golang"], "I know python only")
        assert result["coverage_pct"] < 100
        assert "rust" in result["missing"]
        assert "golang" in result["missing"]

    def test_no_requirements(self):
        result = compute_coverage([], "anything")
        assert result["coverage_pct"] == 100.0

    def test_no_content(self):
        result = compute_coverage(["python"], "")
        assert result["coverage_pct"] == 0.0
        assert result["missing"] == ["python"]


class TestAnalyzeEntry:
    def test_basic_analysis(self):
        entry = _entry(keywords=["python", "docker"])
        result = analyze_entry(entry, block_content="python is great for scripting")
        assert result["id"] == "test-role"
        assert "coverage_pct" in result
        assert "missing" in result


class TestFormatAnalysis:
    def test_format_output(self):
        analysis = {
            "id": "test",
            "name": "Test Role",
            "score": 8.0,
            "coverage_pct": 75.0,
            "total_required": 4,
            "matched": ["python", "react", "typescript"],
            "missing": ["kubernetes"],
        }
        output = format_analysis(analysis)
        assert "test" in output
        assert "75.0%" in output
        assert "kubernetes" in output
