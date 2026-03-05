#!/usr/bin/env python3
"""TF-IDF cosine similarity engine for objective text-based scoring.

Computes similarity between job posting text and candidate content (blocks,
resumes, profiles) using pure stdlib Python. No sklearn, no numpy.

Three content slices per entry:
- "mission": identity + framing blocks + artist statements
- "evidence": evidence + methodology + project blocks
- "fit": resume HTML→text + profile highlights

Usage:
    python scripts/text_match.py --build-corpus
    python scripts/text_match.py --target <id>
    python scripts/text_match.py --target <id> --gaps
    python scripts/text_match.py --all
    python scripts/text_match.py --all --gaps --json
"""

import argparse
import html as html_lib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    SIGNALS_DIR,
    load_block,
    load_block_index,
    load_entries,
    load_entry_by_id,
    load_profile,
)

# --- Constants ---

WORK_DIR = Path(__file__).resolve().parent / ".alchemize-work"

CORPUS_CACHE_PATH = SIGNALS_DIR / "text-match-corpus.yaml"

MIN_DF = 2          # terms in only 1 doc are noise
MAX_DF_RATIO = 0.80  # terms in >80% of docs are too generic

# English stopwords + domain stopwords (copied from distill_keywords.py, not imported)
STOPWORDS = {
    # Standard English
    "a", "an", "the", "and", "or", "but", "not", "is", "are", "was", "were",
    "am", "be", "been", "being", "do", "does", "did", "have", "has", "had",
    "will", "would", "shall", "should", "can", "could", "may", "must", "might",
    "to", "of", "in", "on", "at", "by", "for", "with", "from", "up", "out",
    "if", "then", "so", "no", "as", "it", "its", "he", "she", "we", "they",
    "me", "him", "her", "us", "them", "my", "his", "our", "your", "their",
    "this", "that", "these", "those", "what", "which", "who", "whom", "how",
    "when", "where", "why", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "any", "such", "than", "too", "very", "just",
    "also", "now", "here", "there", "about", "above", "below", "between",
    "through", "during", "before", "after", "into", "over", "under", "again",
    "further", "once", "own", "same", "only", "still", "even", "back",
    # Domain-specific (application/job posting language)
    "apply", "application", "team", "company", "role", "position", "candidate",
    "experience", "work", "working", "opportunity", "responsibilities", "requirements",
    "qualifications", "join", "looking", "ideal", "strong", "ability",
    "skills", "years", "including", "across", "within", "help", "build", "make",
    "well", "new", "use", "using", "used", "like", "need",
    "ensure", "create", "support", "provide", "develop", "include", "based",
    "related", "relevant", "preferred", "required", "plus", "bonus", "etc",
}


# --- Dataclasses ---

@dataclass
class GapTerm:
    """A term present in the posting but weak/absent in candidate content."""
    term: str
    posting_tfidf: float
    candidate_tfidf: float
    gap_magnitude: float
    suggested_blocks: list[str] = field(default_factory=list)


@dataclass
class TextMatchResult:
    """Result of text matching analysis for a single entry."""
    entry_id: str
    overall_similarity: float
    mission_score: int
    evidence_score: int
    fit_score: int
    gap_terms: list[GapTerm] = field(default_factory=list)
    per_block_similarity: dict[str, float] = field(default_factory=dict)
    posting_word_count: int = 0
    candidate_word_count: int = 0
    corpus_size: int = 0


# --- Core Math Functions (pure, no side effects) ---

def normalize_text(text: str) -> str:
    """Strip HTML/markdown, lowercase, preserve hyphens in technical terms."""
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = html_lib.unescape(text)
    # Strip remaining numeric entities
    text = re.sub(r"&#?\w+;", " ", text)
    # Strip markdown headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Strip markdown bold/italic
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Strip markdown links [text](url)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Lowercase
    text = text.lower()
    # Replace non-word chars except hyphens with space
    text = re.sub(r"[^\w\s-]", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    """Split normalized text into filtered unigram tokens."""
    words = normalize_text(text).split()
    return [
        w for w in words
        if w not in STOPWORDS
        and len(w) > 2
        and not w.isdigit()
    ]


def compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency: count/total for each token."""
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def compute_idf(corpus_tokens: list[list[str]]) -> dict[str, float]:
    """Compute IDF from a corpus, filtering by MIN_DF and MAX_DF_RATIO.

    Returns log(N/df) for each qualifying term.
    """
    if not corpus_tokens:
        return {}
    n = len(corpus_tokens)
    max_df = int(n * MAX_DF_RATIO)

    # Document frequency: number of docs containing each term
    df: dict[str, int] = Counter()
    for doc_tokens in corpus_tokens:
        unique_terms = set(doc_tokens)
        for term in unique_terms:
            df[term] += 1

    idf = {}
    for term, freq in df.items():
        if freq < MIN_DF:
            continue
        if freq > max_df:
            continue
        idf[term] = math.log(n / freq)

    return idf


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Compute sparse TF-IDF vector (only terms present in IDF table)."""
    tf = compute_tf(tokens)
    return {
        term: tf_val * idf[term]
        for term, tf_val in tf.items()
        if term in idf
    }


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    if not vec_a or not vec_b:
        return 0.0

    # Dot product (only shared keys)
    shared_keys = set(vec_a) & set(vec_b)
    if not shared_keys:
        return 0.0

    dot = sum(vec_a[k] * vec_b[k] for k in shared_keys)

    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    return dot / (mag_a * mag_b)


# --- Text Processing Helpers ---

def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from block content."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text


def _html_to_text(html_text: str) -> str:
    """Convert HTML to plain text by stripping tags and decoding entities."""
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


# --- Corpus Builder ---

def load_research_text(entry_id: str) -> str | None:
    """Load research.md for an entry, stripping the Custom Questions section."""
    research_path = WORK_DIR / entry_id / "research.md"
    if not research_path.exists():
        return None
    text = research_path.read_text(encoding="utf-8", errors="replace")
    # Strip ## Custom Questions section (not relevant for similarity)
    cq_idx = text.find("## Custom Questions")
    if cq_idx != -1:
        text = text[:cq_idx]
    return text.strip() or None


def build_corpus() -> tuple[dict[str, float], list[list[str]], int]:
    """Build IDF table from all research.md files.

    Returns (idf_table, per_doc_tokens, corpus_size).
    """
    corpus_tokens = []
    if not WORK_DIR.exists():
        return {}, [], 0

    for entry_dir in sorted(WORK_DIR.iterdir()):
        if not entry_dir.is_dir():
            continue
        text = load_research_text(entry_dir.name)
        if text:
            tokens = tokenize(text)
            if tokens:
                corpus_tokens.append(tokens)

    idf = compute_idf(corpus_tokens)
    return idf, corpus_tokens, len(corpus_tokens)


def save_corpus_cache(idf: dict[str, float], corpus_size: int) -> None:
    """Save IDF table to YAML cache."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    cache_data = {
        "generated": datetime.now().isoformat(),
        "corpus_size": corpus_size,
        "term_count": len(idf),
        "idf": {k: round(v, 6) for k, v in sorted(idf.items())},
    }
    CORPUS_CACHE_PATH.write_text(
        yaml.dump(cache_data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def load_corpus_cache() -> tuple[dict[str, float], int] | None:
    """Load cached IDF table if fresh (< 7 days old)."""
    if not CORPUS_CACHE_PATH.exists():
        return None

    from datetime import datetime
    try:
        data = yaml.safe_load(CORPUS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict) or "idf" not in data:
        return None

    generated = data.get("generated", "")
    if generated:
        try:
            gen_dt = datetime.fromisoformat(generated)
            age_days = (datetime.now() - gen_dt).days
            if age_days > 7:
                return None
        except (ValueError, TypeError):
            return None

    return data["idf"], data.get("corpus_size", 0)


def get_idf(force_rebuild: bool = False) -> tuple[dict[str, float], int]:
    """Get IDF table, using cache if fresh.

    Returns (idf_table, corpus_size).
    """
    if not force_rebuild:
        cached = load_corpus_cache()
        if cached is not None:
            return cached

    idf, _, corpus_size = build_corpus()
    if idf:
        save_corpus_cache(idf, corpus_size)
    return idf, corpus_size


# --- Content Assembly ---

# Block path prefixes that map to each content type
_MISSION_PREFIXES = ("identity/", "framings/")
_EVIDENCE_PREFIXES = ("evidence/", "methodology/", "projects/")
_FIT_PREFIXES = ()  # fit uses resumes + profile, not blocks


def assemble_candidate_content(entry: dict, content_type: str) -> str:
    """Build text from blocks, profiles, and resumes for a content type.

    content_type: "mission", "evidence", or "fit"
    """
    parts = []
    entry_id = entry.get("id", "")
    submission = entry.get("submission", {}) or {}
    blocks_used = submission.get("blocks_used", {}) or {}

    if content_type == "mission":
        # Identity + framing blocks
        for key, block_path in blocks_used.items():
            if not block_path:
                continue
            bp = str(block_path)
            if any(bp.startswith(p) for p in _MISSION_PREFIXES):
                content = load_block(bp)
                if content:
                    parts.append(_strip_frontmatter(content))

        # Artist statements from profile
        profile = load_profile(entry_id)
        if profile:
            for stmt_key in ("artist_statement_long", "artist_statement_medium", "artist_statement_short"):
                stmt = profile.get(stmt_key, "")
                if stmt:
                    parts.append(stmt)

    elif content_type == "evidence":
        # Evidence + methodology + project blocks
        for key, block_path in blocks_used.items():
            if not block_path:
                continue
            bp = str(block_path)
            if any(bp.startswith(p) for p in _EVIDENCE_PREFIXES):
                content = load_block(bp)
                if content:
                    parts.append(_strip_frontmatter(content))

    elif content_type == "fit":
        # Resume HTML → text
        materials = submission.get("materials_attached", []) or []
        for mat in materials:
            mat_str = str(mat)
            if "resume" in mat_str.lower() and mat_str.endswith(".html"):
                resume_path = Path(__file__).resolve().parent.parent / "materials" / mat_str.removeprefix("materials/")
                if not resume_path.exists():
                    # Try relative from repo root
                    resume_path = Path(__file__).resolve().parent.parent / mat_str
                if resume_path.exists():
                    html_text = resume_path.read_text(encoding="utf-8", errors="replace")
                    parts.append(_html_to_text(html_text))

        # Profile highlights
        profile = load_profile(entry_id)
        if profile:
            highlights = profile.get("evidence_highlights", [])
            if highlights:
                parts.append(" ".join(str(h) for h in highlights))
            work_samples = profile.get("work_samples", [])
            if work_samples:
                for ws in work_samples:
                    if isinstance(ws, dict):
                        desc = ws.get("description", "")
                        if desc:
                            parts.append(desc)

    return " ".join(parts)


def _similarity_to_score(similarity: float) -> int:
    """Map cosine similarity [0,1] to signal score [0,2].

    Coarse 3-tier mapping: TF-IDF without semantics is imprecise, so we only
    distinguish "no match", "some match", "good match".
    """
    if similarity < 0.05:
        return 0
    elif similarity < 0.15:
        return 1
    else:
        return 2


# --- Gap Analysis ---

def _compute_gaps(
    posting_vec: dict[str, float],
    content_vec: dict[str, float],
    idf: dict[str, float],
    top_n: int = 15,
) -> list[GapTerm]:
    """Find terms with high posting weight but low/zero candidate weight."""
    gaps = []
    for term, posting_weight in posting_vec.items():
        candidate_weight = content_vec.get(term, 0.0)
        gap_mag = posting_weight - candidate_weight
        # Gap must be > 50% of posting weight to be meaningful
        if gap_mag > posting_weight * 0.5:
            gaps.append(GapTerm(
                term=term,
                posting_tfidf=round(posting_weight, 4),
                candidate_tfidf=round(candidate_weight, 4),
                gap_magnitude=round(gap_mag, 4),
            ))

    gaps.sort(key=lambda g: g.gap_magnitude, reverse=True)
    return gaps[:top_n]


def _find_blocks_for_term(term: str, tag_index: dict[str, list[str]]) -> list[str]:
    """Find blocks that match a gap term via tag index, capped at 3."""
    # Direct tag match
    if term in tag_index:
        return tag_index[term][:3]

    # Partial match: term is substring of tag or vice versa
    matches = []
    for tag, blocks in tag_index.items():
        if term in tag or tag in term:
            matches.extend(blocks)
            if len(matches) >= 3:
                break
    return list(dict.fromkeys(matches))[:3]  # dedupe, preserve order


# --- Entry Analysis ---

def analyze_entry(
    entry_id: str,
    entry: dict,
    idf: dict[str, float],
    corpus_size: int,
) -> TextMatchResult | None:
    """Run full text match analysis for a single entry.

    Returns TextMatchResult or None if no research text available.
    """
    posting_text = load_research_text(entry_id)
    if not posting_text:
        return None

    posting_tokens = tokenize(posting_text)
    if not posting_tokens:
        return None

    posting_vec = tfidf_vector(posting_tokens, idf)
    if not posting_vec:
        return None

    # Compute similarity for each content slice
    content_types = ["mission", "evidence", "fit"]
    similarities = {}
    content_vecs = {}

    for ct in content_types:
        content_text = assemble_candidate_content(entry, ct)
        if content_text.strip():
            ct_tokens = tokenize(content_text)
            ct_vec = tfidf_vector(ct_tokens, idf)
            sim = cosine_similarity(posting_vec, ct_vec)
            similarities[ct] = sim
            content_vecs[ct] = ct_vec
        else:
            similarities[ct] = 0.0
            content_vecs[ct] = {}

    # Overall: average of non-zero slices, or combined
    all_content = " ".join(
        assemble_candidate_content(entry, ct) for ct in content_types
    )
    all_tokens = tokenize(all_content)
    all_vec = tfidf_vector(all_tokens, idf)
    overall_sim = cosine_similarity(posting_vec, all_vec)

    # Per-block similarity
    per_block = {}
    submission = entry.get("submission", {}) or {}
    blocks_used = submission.get("blocks_used", {}) or {}
    for key, block_path in blocks_used.items():
        if not block_path:
            continue
        content = load_block(str(block_path))
        if content:
            b_tokens = tokenize(_strip_frontmatter(content))
            b_vec = tfidf_vector(b_tokens, idf)
            b_sim = cosine_similarity(posting_vec, b_vec)
            per_block[str(block_path)] = round(b_sim, 4)

    # Gap analysis (against combined content)
    tag_index = {}
    try:
        idx = load_block_index()
        tag_index = idx.get("tag_index", {})
    except Exception as e:
        print(f"  Warning: Could not load block index for gap analysis: {e}")

    gaps = _compute_gaps(posting_vec, all_vec, idf)
    for gap in gaps:
        gap.suggested_blocks = _find_blocks_for_term(gap.term, tag_index)

    return TextMatchResult(
        entry_id=entry_id,
        overall_similarity=round(overall_sim, 4),
        mission_score=_similarity_to_score(similarities["mission"]),
        evidence_score=_similarity_to_score(similarities["evidence"]),
        fit_score=_similarity_to_score(similarities["fit"]),
        gap_terms=gaps,
        per_block_similarity=per_block,
        posting_word_count=len(posting_tokens),
        candidate_word_count=len(all_tokens),
        corpus_size=corpus_size,
    )


# --- CLI ---

def _format_result(result: TextMatchResult, show_gaps: bool = False, show_blocks: bool = False) -> str:
    """Format a TextMatchResult for CLI output."""
    lines = [
        f"\n  {result.entry_id}",
        f"    overall similarity: {result.overall_similarity:.4f}",
        f"    mission:  {result.mission_score}/2 (cosine used for signal)",
        f"    evidence: {result.evidence_score}/2",
        f"    fit:      {result.fit_score}/2",
        f"    posting tokens: {result.posting_word_count}  candidate tokens: {result.candidate_word_count}",
    ]

    if show_blocks and result.per_block_similarity:
        lines.append("    per-block similarity:")
        sorted_blocks = sorted(result.per_block_similarity.items(), key=lambda x: x[1], reverse=True)
        for bp, sim in sorted_blocks:
            lines.append(f"      {sim:.4f}  {bp}")

    if show_gaps and result.gap_terms:
        lines.append("    gap terms (high in posting, low in candidate):")
        for gap in result.gap_terms:
            suggestions = f"  -> {', '.join(gap.suggested_blocks)}" if gap.suggested_blocks else ""
            lines.append(
                f"      {gap.term:<25s} posting={gap.posting_tfidf:.4f}  "
                f"candidate={gap.candidate_tfidf:.4f}  gap={gap.gap_magnitude:.4f}{suggestions}"
            )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="TF-IDF text match analysis")
    parser.add_argument("--build-corpus", action="store_true", help="Build/rebuild IDF corpus cache")
    parser.add_argument("--target", type=str, help="Analyze a single entry by ID")
    parser.add_argument("--all", action="store_true", help="Analyze all entries with research text")
    parser.add_argument("--gaps", action="store_true", help="Show gap analysis")
    parser.add_argument("--blocks", action="store_true", help="Show per-block similarity")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--top", type=int, default=0, help="Show only top N results by similarity")
    args = parser.parse_args()

    if args.build_corpus:
        print("Building TF-IDF corpus from research files...")
        idf, _, corpus_size = build_corpus()
        if idf:
            save_corpus_cache(idf, corpus_size)
            print(f"  corpus: {corpus_size} documents, {len(idf)} terms")
            print(f"  cached to: {CORPUS_CACHE_PATH}")
        else:
            print("  no research files found in .alchemize-work/")
        return

    if not args.target and not args.all:
        parser.print_help()
        sys.exit(1)

    idf, corpus_size = get_idf()
    if not idf:
        print("No corpus available. Run --build-corpus first.")
        sys.exit(1)

    results = []

    if args.target:
        filepath, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Entry not found: {args.target}", file=sys.stderr)
            sys.exit(1)
        result = analyze_entry(args.target, entry, idf, corpus_size)
        if result:
            results.append(result)
        else:
            print(f"No research text for {args.target}")
            sys.exit(0)

    elif args.all:
        entries = load_entries()
        for entry in entries:
            eid = entry.get("id", "")
            if not eid:
                continue
            result = analyze_entry(eid, entry, idf, corpus_size)
            if result:
                results.append(result)

    if args.top > 0:
        results.sort(key=lambda r: r.overall_similarity, reverse=True)
        results = results[:args.top]

    if args.json:
        output = []
        for r in results:
            d = asdict(r)
            # Convert GapTerm dataclasses to dicts (already done by asdict)
            output.append(d)
        print(json.dumps(output, indent=2))
    else:
        print(f"Text Match Analysis (corpus: {corpus_size} docs, {len(idf)} terms)")
        print("=" * 60)
        for r in results:
            print(_format_result(r, show_gaps=args.gaps, show_blocks=args.blocks))
        if not results:
            print("  No entries with research text found.")


if __name__ == "__main__":
    main()
