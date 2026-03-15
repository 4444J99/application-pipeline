"""Tests for scripts/corpus_fingerprint.py."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import corpus_fingerprint as cf

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_block(directory: Path, filename: str, body: str, frontmatter: str = "") -> None:
    """Write a block .md file, optionally with YAML frontmatter."""
    if frontmatter:
        content = f"---\n{frontmatter}\n---\n\n{body}"
    else:
        content = body
    (directory / filename).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_build_fingerprint_reads_all_blocks(tmp_path):
    """Both block files contribute terms to the fingerprint."""
    blocks_dir = tmp_path / "blocks"
    blocks_dir.mkdir()

    _write_block(blocks_dir, "alpha.md", "Python TypeScript pipeline orchestration systems")
    _write_block(blocks_dir, "beta.md", "React CI/CD deployment infrastructure engineering")

    fp = cf.build_corpus_fingerprint(blocks_dir=blocks_dir)

    assert fp.term_count > 0
    # Terms from both files should appear
    assert "python" in fp.terms
    assert "react" in fp.terms


def test_fingerprint_skips_readme_and_underscore(tmp_path):
    """README.md and _schema.md are excluded from the corpus."""
    blocks_dir = tmp_path / "blocks"
    blocks_dir.mkdir()

    # These should be included
    _write_block(blocks_dir, "real-block.md", "functional systems programming orchestration")
    # These should be excluded
    _write_block(blocks_dir, "README.md", "uniquereadmetermxyz should not appear")
    _write_block(blocks_dir, "_schema.md", "uniqueschematermxyz should not appear")

    fp = cf.build_corpus_fingerprint(blocks_dir=blocks_dir)

    assert "uniquereadmetermxyz" not in fp.terms
    assert "uniqueschematermxyz" not in fp.terms
    # The real block term should be present
    assert "orchestration" in fp.terms or fp.term_count > 0


def test_score_description_high_for_matching(tmp_path):
    """Description closely matching corpus content returns similarity > 0.10."""
    blocks_dir = tmp_path / "blocks"
    blocks_dir.mkdir()

    _write_block(
        blocks_dir,
        "tech.md",
        (
            "Python TypeScript React CI/CD pipeline infrastructure engineering "
            "systems orchestration deployment automation testing distributed"
        ),
    )

    fp = cf.build_corpus_fingerprint(blocks_dir=blocks_dir)

    description = (
        "We are looking for a Python TypeScript engineer with React experience. "
        "Strong CI/CD, pipeline, and infrastructure skills required. "
        "Experience with distributed systems and deployment automation preferred."
    )
    similarity = fp.score_description(description)
    assert similarity > 0.10, f"Expected similarity > 0.10, got {similarity:.4f}"


def test_score_description_low_for_unrelated(tmp_path):
    """Description about an unrelated domain returns similarity < 0.05."""
    blocks_dir = tmp_path / "blocks"
    blocks_dir.mkdir()

    _write_block(
        blocks_dir,
        "python.md",
        (
            "Python backend systems engineering orchestration pipeline testing "
            "distributed infrastructure automation deployment cloud"
        ),
    )

    fp = cf.build_corpus_fingerprint(blocks_dir=blocks_dir)

    description = (
        "iOS Swift UIKit CoreData Objective-C Xcode Instruments "
        "App Store TestFlight SwiftUI Combine ARKit SceneKit "
        "mobile app development iPhone iPad watchOS"
    )
    similarity = fp.score_description(description)
    assert similarity < 0.05, f"Expected similarity < 0.05, got {similarity:.4f}"


def test_score_description_empty_returns_zero(tmp_path):
    """Empty or whitespace-only description returns exactly 0.0."""
    blocks_dir = tmp_path / "blocks"
    blocks_dir.mkdir()
    _write_block(blocks_dir, "block.md", "Python engineering systems")

    fp = cf.build_corpus_fingerprint(blocks_dir=blocks_dir)

    assert fp.score_description("") == 0.0
    assert fp.score_description("   ") == 0.0


def test_get_fingerprint_caches(tmp_path, monkeypatch):
    """Calling get_fingerprint() twice returns the same cached object."""
    # Reset module-level cache
    monkeypatch.setattr(cf, "_cached_fingerprint", None)
    monkeypatch.setattr(cf, "BLOCKS_DIR", tmp_path / "blocks")
    monkeypatch.setattr(cf, "RESUME_BASE_DIR", tmp_path / "resumes")
    (tmp_path / "blocks").mkdir()
    _write_block(tmp_path / "blocks", "a.md", "Python engineering systems")

    first = cf.get_fingerprint()
    second = cf.get_fingerprint()

    assert first is second, "Expected same cached object on second call"
    assert first.built_at == second.built_at


def test_get_fingerprint_rebuilds_when_stale(tmp_path, monkeypatch):
    """get_fingerprint() rebuilds the fingerprint when the cache is older than CACHE_MAX_AGE."""
    # Reset module-level cache
    monkeypatch.setattr(cf, "_cached_fingerprint", None)
    monkeypatch.setattr(cf, "BLOCKS_DIR", tmp_path / "blocks")
    monkeypatch.setattr(cf, "RESUME_BASE_DIR", tmp_path / "resumes")
    (tmp_path / "blocks").mkdir()
    _write_block(tmp_path / "blocks", "a.md", "Python engineering systems")

    # Build a fresh fingerprint, then backdate its timestamp
    first = cf.get_fingerprint()
    stale_time = time.time() - cf.CACHE_MAX_AGE - 1
    monkeypatch.setattr(cf, "_cached_fingerprint", cf.CorpusFingerprint(
        tfidf_vector=first.tfidf_vector,
        terms=first.terms,
        term_count=first.term_count,
        source_file_count=first.source_file_count,
        built_at=stale_time,
    ))

    second = cf.get_fingerprint()

    assert second.built_at > stale_time, "Expected fingerprint to be rebuilt with a newer timestamp"
    assert second is not cf._cached_fingerprint or second.built_at != stale_time
