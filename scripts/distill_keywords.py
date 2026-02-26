#!/usr/bin/env python3
"""Extract and rank keywords from external sources (job postings, funding descriptions).

Reads scraped research files from alchemize work directories and pipeline YAML
entries, extracts recurring keywords, and optionally writes them back to pipeline
YAML and aggregate signals.

Usage:
    python scripts/distill_keywords.py                    # Analyze all with research files
    python scripts/distill_keywords.py --target <id>      # Single entry
    python scripts/distill_keywords.py --write --yes      # Write keywords to pipeline YAMLs
    python scripts/distill_keywords.py --signals          # Write aggregate to signals/
    python scripts/distill_keywords.py --match-tags       # Show which keywords match block tags
"""

import argparse
import re
import string
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS_WITH_POOL,
    BLOCKS_DIR,
    REPO_ROOT,
    SIGNALS_DIR,
    load_block_index,
    load_entries,
    load_entry_by_id,
)

WORK_DIR = Path(__file__).resolve().parent / ".alchemize-work"

# Domain-specific stopwords to filter out generic application language
DOMAIN_STOPWORDS = {
    "apply", "application", "team", "company", "role", "position", "candidate",
    "experience", "work", "working", "opportunity", "responsibilities", "requirements",
    "qualifications", "about", "join", "looking", "ideal", "strong", "ability",
    "skills", "years", "including", "across", "within", "help", "build", "make",
    "well", "also", "new", "will", "use", "using", "used", "like", "need",
    "ensure", "create", "support", "provide", "develop", "include", "based",
    "related", "relevant", "preferred", "required", "plus", "bonus", "etc",
    "e.g", "i.e", "the", "and", "our", "you", "your", "this", "that", "with",
    "for", "are", "have", "has", "been", "being", "from", "they", "their",
    "can", "more", "other", "than", "into", "over", "such", "what", "how",
    "who", "which", "when", "where", "while", "would", "should", "could",
    "may", "must", "shall", "not", "but", "all", "each", "every", "both",
    "few", "some", "any", "most", "own", "same", "here", "there", "these",
    "those", "just", "very", "only", "still", "even", "back", "its",
}


def normalize_text(text: str) -> str:
    """Lowercase, strip HTML tags, and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&\w+;", " ", text)
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_keywords(text: str, top_n: int = 20) -> list[tuple[str, int]]:
    """Extract top keywords from text using unigram and bigram frequency.

    Returns list of (keyword, count) sorted by count descending.
    """
    normalized = normalize_text(text)
    words = normalized.split()

    # Filter stopwords and short words
    filtered = [
        w for w in words
        if w not in DOMAIN_STOPWORDS
        and len(w) > 2
        and not w.isdigit()
        and w not in string.punctuation
    ]

    # Unigrams
    unigrams = Counter(filtered)

    # Bigrams
    bigrams = Counter()
    for i in range(len(filtered) - 1):
        bg = f"{filtered[i]}-{filtered[i+1]}"
        bigrams[bg] += 1

    # Combine: bigrams with count >= 2 get priority
    combined = Counter()
    for bg, count in bigrams.items():
        if count >= 2:
            combined[bg] = count
    for ug, count in unigrams.items():
        if ug not in combined:
            combined[ug] = count

    return combined.most_common(top_n)


def load_research_text(entry_id: str) -> str | None:
    """Load research.md from alchemize work directory for an entry."""
    research_path = WORK_DIR / entry_id / "research.md"
    if research_path.exists():
        return research_path.read_text()
    return None


def analyze_entry(entry_id: str, entry: dict) -> list[tuple[str, int]] | None:
    """Extract keywords for a single pipeline entry.

    Tries research.md first, then falls back to entry name/framing text.
    Returns None if insufficient text to analyze.
    """
    text = load_research_text(entry_id)
    if not text:
        # Fall back to available entry metadata
        parts = []
        parts.append(entry.get("name", ""))
        fit = entry.get("fit", {})
        if isinstance(fit, dict):
            parts.append(fit.get("framing", ""))
        notes = entry.get("notes", "")
        if notes:
            parts.append(notes)
        text = " ".join(parts)

    if not text or len(text.split()) < 10:
        return None

    return extract_keywords(text)


def write_keywords_to_entry(entry_id: str, keywords: list[str]) -> bool:
    """Write extracted_keywords to a pipeline entry's fit section.

    Returns True if the file was modified.
    """
    path, entry = load_entry_by_id(entry_id)
    if not path or not entry:
        return False

    content = path.read_text()

    # Check if extracted_keywords already exists
    if "extracted_keywords:" in content:
        # Replace existing
        pattern = r"(\s+extracted_keywords:).*?(?=\n\s+\w|\nfit:|\n[a-z]|\Z)"
        kw_yaml = yaml.dump(keywords, default_flow_style=True).strip()
        replacement = f"\\1 {kw_yaml}"
        new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
        if new_content == content:
            return False
        path.write_text(new_content)
        return True

    # Insert after identity_position or framing in the fit section
    for anchor in ("identity_position:", "framing:", "score:"):
        idx = content.find(anchor)
        if idx != -1:
            # Find end of this line
            eol = content.find("\n", idx)
            if eol != -1:
                kw_yaml = yaml.dump(keywords, default_flow_style=True).strip()
                indent = "    "
                insertion = f"\n{indent}extracted_keywords: {kw_yaml}"
                new_content = content[:eol] + insertion + content[eol:]
                path.write_text(new_content)
                return True

    return False


def write_signals(all_keywords: dict[str, list[tuple[str, int]]], track_entries: dict[str, list[str]]):
    """Write aggregate keyword signals to signals/keyword-signals.yaml."""
    # Aggregate across all entries
    global_counter = Counter()
    track_counters: dict[str, Counter] = {}

    for entry_id, keywords in all_keywords.items():
        for kw, count in keywords:
            global_counter[kw] += 1  # Count entries containing this keyword

        # Track by application track
        for track, ids in track_entries.items():
            if entry_id in ids:
                if track not in track_counters:
                    track_counters[track] = Counter()
                for kw, _ in keywords:
                    track_counters[track][kw] += 1

    total = len(all_keywords)

    top_keywords = []
    for kw, count in global_counter.most_common(50):
        top_keywords.append({
            "keyword": kw,
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0,
        })

    by_track = {}
    for track, counter in sorted(track_counters.items()):
        by_track[track] = {"top": [kw for kw, _ in counter.most_common(10)]}

    from datetime import date

    signals = {
        "generated": str(date.today()),
        "total_postings_analyzed": total,
        "top_keywords": top_keywords,
        "by_track": by_track,
    }

    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SIGNALS_DIR / "keyword-signals.yaml"
    header = "# Auto-generated by distill_keywords.py — do not edit manually\n"
    output_path.write_text(
        header + yaml.dump(signals, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )
    print(f"Wrote {output_path.relative_to(REPO_ROOT)}: {total} entries, {len(top_keywords)} keywords")


def match_tags_report(all_keywords: dict[str, list[tuple[str, int]]]):
    """Cross-reference extracted keywords against block index tags."""
    block_index = load_block_index()
    tag_index = block_index.get("tag_index", {})

    if not tag_index:
        print("No block index found. Run: python scripts/build_block_index.py")
        return

    for entry_id, keywords in sorted(all_keywords.items()):
        kw_list = [kw for kw, _ in keywords]
        matched = {}
        unmatched = []

        for kw in kw_list:
            if kw in tag_index:
                matched[kw] = tag_index[kw]
            else:
                unmatched.append(kw)

        print(f"\n{entry_id}:")
        print(f"  Extracted: {kw_list[:15]}")
        if matched:
            print("  Matched tags:")
            for tag, blocks in matched.items():
                block_str = ", ".join(blocks[:3])
                if len(blocks) > 3:
                    block_str += f" (+{len(blocks)-3} more)"
                print(f"    {tag} -> [{block_str}]")
        if unmatched:
            print(f"  Unmatched: {unmatched[:10]}")


def main():
    parser = argparse.ArgumentParser(description="Distill keywords from external sources")
    parser.add_argument("--target", help="Single entry ID to analyze")
    parser.add_argument("--write", action="store_true", help="Write keywords to pipeline YAMLs")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    parser.add_argument("--signals", action="store_true", help="Write aggregate signals")
    parser.add_argument("--match-tags", action="store_true", help="Show block tag matches")
    args = parser.parse_args()

    # Load entries
    if args.target:
        path, entry = load_entry_by_id(args.target)
        if not entry:
            print(f"Entry not found: {args.target}")
            sys.exit(1)
        entries = [(args.target, entry)]
    else:
        all_entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
        entries = [(e.get("id", "unknown"), e) for e in all_entries]

    # Analyze
    all_keywords: dict[str, list[tuple[str, int]]] = {}
    track_entries: dict[str, list[str]] = {}

    for entry_id, entry in entries:
        keywords = analyze_entry(entry_id, entry)
        if keywords:
            all_keywords[entry_id] = keywords

            track = entry.get("track", "unknown")
            track_entries.setdefault(track, [])
            track_entries[track].append(entry_id)

    if not all_keywords:
        print("No entries with sufficient text to analyze.")
        sys.exit(0)

    # Default: print summary
    if not args.write and not args.signals and not args.match_tags:
        print(f"Analyzed {len(all_keywords)} entries:\n")
        for entry_id, keywords in sorted(all_keywords.items()):
            kw_display = ", ".join(f"{kw}({c})" for kw, c in keywords[:10])
            print(f"  {entry_id}: {kw_display}")
        return

    # --match-tags
    if args.match_tags:
        match_tags_report(all_keywords)
        return

    # --write
    if args.write:
        if not args.yes:
            print(f"Would write keywords to {len(all_keywords)} pipeline entries.")
            print("Run with --yes to confirm.")
            return
        written = 0
        for entry_id, keywords in all_keywords.items():
            kw_list = [kw for kw, _ in keywords[:15]]
            if write_keywords_to_entry(entry_id, kw_list):
                written += 1
                print(f"  Wrote keywords to {entry_id}")
        print(f"\nUpdated {written}/{len(all_keywords)} entries.")

    # --signals
    if args.signals:
        write_signals(all_keywords, track_entries)


if __name__ == "__main__":
    main()
