#!/usr/bin/env python3
"""Living corpus fingerprint — TF-IDF vector built from all blocks, resumes, and project content.

The blocks directory IS the corpus. As blocks are added, modified, or removed,
the fingerprint automatically reflects the full scope of work on next rebuild.

Usage:
    from corpus_fingerprint import get_fingerprint
    fp = get_fingerprint()
    similarity = fp.score_description("job description text here")
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import REPO_ROOT  # noqa: E402
from text_match import (  # noqa: E402
    compute_idf,
    compute_tf,
    cosine_similarity,
    tfidf_vector,
    tokenize,
)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

BLOCKS_DIR = REPO_ROOT / "blocks"
RESUME_BASE_DIR = REPO_ROOT / "materials" / "resumes" / "base"

# ---------------------------------------------------------------------------
# Cache settings
# ---------------------------------------------------------------------------

CACHE_MAX_AGE: int = 86400  # 24 hours in seconds

_cached_fingerprint: CorpusFingerprint | None = None


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class CorpusFingerprint:
    """TF-IDF fingerprint of the full candidate corpus."""

    tfidf_vector: dict[str, float]
    terms: set[str]
    term_count: int
    source_file_count: int
    built_at: float  # time.time() timestamp

    def score_description(self, description: str) -> float:
        """Compute cosine similarity between this fingerprint and a job description.

        Builds a two-document IDF from corpus tokens + description tokens so that
        IDF values are meaningful for this specific comparison.

        Returns:
            float in [0.0, 1.0]; 0.0 if description is empty or no overlap.
        """
        if not description or not description.strip():
            return 0.0

        desc_tokens = tokenize(description)
        if not desc_tokens:
            return 0.0

        # Reconstruct corpus token list from the stored TF-IDF vector keys.
        # We treat each unique term in the corpus as a pseudo-document so that
        # IDF is computed across two documents: corpus and description.
        corpus_tokens = list(self.tfidf_vector.keys())
        if not corpus_tokens:
            return 0.0

        # Build IDF from the two documents (corpus terms, description terms)
        idf = compute_idf([corpus_tokens, desc_tokens])

        # If no shared IDF terms, fall back to raw TF cosine (rare edge case)
        if not idf:
            corpus_tf = {t: 1.0 / len(corpus_tokens) for t in corpus_tokens}
            desc_tf = compute_tf(desc_tokens)
            return cosine_similarity(corpus_tf, desc_tf)

        corpus_vec = tfidf_vector(corpus_tokens, idf)
        desc_vec = tfidf_vector(desc_tokens, idf)

        return cosine_similarity(corpus_vec, desc_vec)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from block content."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text


def _html_to_text(html_text: str) -> str:
    """Convert HTML to plain text by stripping tags and decoding entities."""
    import html as html_lib

    # Remove <style> blocks
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html_text, flags=re.DOTALL | re.IGNORECASE)
    # Remove <script> blocks
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode entities
    text = html_lib.unescape(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Corpus readers
# ---------------------------------------------------------------------------


def _read_all_blocks(blocks_dir: Path | None = None) -> str:
    """Read and concatenate all .md files in blocks/, stripping YAML frontmatter.

    Skips files whose name starts with '_' and README.md (case-insensitive).
    Descends recursively into subdirectories.

    Returns:
        Single concatenated string of all block content.
    """
    root = Path(blocks_dir) if blocks_dir is not None else BLOCKS_DIR
    parts: list[str] = []

    if not root.exists():
        return ""

    for md_file in sorted(root.rglob("*.md")):
        name = md_file.name
        # Skip underscore-prefixed files and README
        if name.startswith("_") or name.lower() == "readme.md":
            continue
        try:
            raw = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        content = _strip_frontmatter(raw)
        if content:
            parts.append(content)

    return "\n\n".join(parts)


def _read_all_resumes(resume_dir: Path | None = None) -> str:
    """Read base resume HTML files and convert to plain text.

    Returns:
        Single concatenated string of all resume text.
    """
    root = Path(resume_dir) if resume_dir is not None else RESUME_BASE_DIR
    parts: list[str] = []

    if not root.exists():
        return ""

    for html_file in sorted(root.glob("*.html")):
        try:
            raw = html_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        text = _html_to_text(raw)
        if text:
            parts.append(text)

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Fingerprint builder
# ---------------------------------------------------------------------------


def build_corpus_fingerprint(
    blocks_dir: Path | None = None,
    resume_dir: Path | None = None,
) -> CorpusFingerprint:
    """Build the full TF-IDF fingerprint from all blocks and base resumes.

    The fingerprint represents "everything this person has done and can do."
    No skills are hardcoded — the blocks directory IS the corpus.

    Args:
        blocks_dir: Override path to blocks directory (for testing).
        resume_dir: Override path to base resumes directory (for testing).

    Returns:
        A populated CorpusFingerprint.
    """
    block_text = _read_all_blocks(blocks_dir)
    resume_text = _read_all_resumes(resume_dir)

    # Count source files
    source_count = 0
    b_root = Path(blocks_dir) if blocks_dir is not None else BLOCKS_DIR
    if b_root.exists():
        source_count += sum(
            1 for f in b_root.rglob("*.md")
            if not f.name.startswith("_") and f.name.lower() != "readme.md"
        )
    r_root = Path(resume_dir) if resume_dir is not None else RESUME_BASE_DIR
    if r_root.exists():
        source_count += sum(1 for f in r_root.glob("*.html"))

    # Combine all corpus text
    combined = "\n\n".join(filter(None, [block_text, resume_text]))
    corpus_tokens = tokenize(combined)

    if not corpus_tokens:
        return CorpusFingerprint(
            tfidf_vector={},
            terms=set(),
            term_count=0,
            source_file_count=source_count,
            built_at=time.time(),
        )

    # Build TF-IDF: treat full corpus as a single document.
    # IDF with a single document is degenerate (all terms appear in 1/1 docs),
    # so we use raw TF as the vector and record terms for later two-doc IDF.
    tf = compute_tf(corpus_tokens)
    unique_terms = set(corpus_tokens)

    return CorpusFingerprint(
        tfidf_vector=tf,
        terms=unique_terms,
        term_count=len(unique_terms),
        source_file_count=source_count,
        built_at=time.time(),
    )


# ---------------------------------------------------------------------------
# Cached accessor
# ---------------------------------------------------------------------------


def get_fingerprint() -> CorpusFingerprint:
    """Module-level cached access to the corpus fingerprint.

    Returns a cached fingerprint if it was built within CACHE_MAX_AGE seconds;
    otherwise rebuilds from disk.
    """
    global _cached_fingerprint

    now = time.time()
    if _cached_fingerprint is not None and (now - _cached_fingerprint.built_at) < CACHE_MAX_AGE:
        return _cached_fingerprint

    _cached_fingerprint = build_corpus_fingerprint()
    return _cached_fingerprint


# ---------------------------------------------------------------------------
# CLI (informational)
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Corpus fingerprint builder")
    parser.add_argument("--describe", action="store_true", help="Print fingerprint stats")
    parser.add_argument("--score", type=str, metavar="TEXT", help="Score a description against the fingerprint")
    args = parser.parse_args()

    fp = get_fingerprint()

    if args.describe or not args.score:
        print("Corpus fingerprint")
        print(f"  source files: {fp.source_file_count}")
        print(f"  unique terms: {fp.term_count}")
        print(f"  built at:     {fp.built_at:.0f}")

    if args.score:
        sim = fp.score_description(args.score)
        print(f"  similarity:   {sim:.4f}")


if __name__ == "__main__":
    main()
