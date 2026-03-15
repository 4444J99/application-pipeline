#!/usr/bin/env python3
"""Match engine: auto-score unscored entries, auto-qualify, rank top matches.

Automatically scores all unscored research entries using the 9-dimension
rubric, optionally qualifies entries above threshold, and surfaces the
top N daily matches.

Usage:
    python scripts/match_engine.py                         # Score all unscored, dry-run
    python scripts/match_engine.py --yes                   # Execute scoring + qualify
    python scripts/match_engine.py --target <id>           # Score single entry
    python scripts/match_engine.py --top 20                # Show top 20
    python scripts/match_engine.py --no-qualify            # Score only, don't promote
    python scripts/match_engine.py --json                  # Machine-readable output
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_api import ResultStatus, score_entry
from pipeline_lib import (
    ALL_PIPELINE_DIRS_WITH_POOL,
    SIGNALS_DIR,
    load_entries,
    load_entry_by_id,
)

MATCH_HISTORY_PATH = SIGNALS_DIR / "daily-matches.yaml"
DEFAULT_TOP_N = 10


@dataclass
class ScoredEntry:
    """A scored pipeline entry."""

    entry_id: str
    composite_score: float
    dimensions: dict[str, float]
    text_match_score: float
    identity_position: str
    organization: str


@dataclass
class MatchResult:
    """Result of a match-and-rank operation."""

    scored: list[ScoredEntry] = field(default_factory=list)
    qualified: list[str] = field(default_factory=list)
    top_matches: list[ScoredEntry] = field(default_factory=list)
    threshold_used: float = 8.5
    entries_scored: int = 0


def _get_qualify_threshold() -> float:
    """Load auto-qualify threshold from scoring rubric."""
    rubric_path = (
        Path(__file__).resolve().parent.parent / "strategy" / "scoring-rubric.yaml"
    )
    try:
        data = yaml.safe_load(rubric_path.read_text()) or {}
        return float(data.get("thresholds", {}).get("auto_qualify_min", 8.5))
    except Exception:
        return 8.5


def _load_unscored_entries(entry_ids: list[str] | None = None) -> list[dict]:
    """Load entries that need scoring."""
    entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
    unscored = []
    for e in entries:
        if entry_ids and e.get("id") not in entry_ids:
            continue
        if e.get("status") not in ("research", "qualified"):
            continue
        fit = e.get("fit")
        if isinstance(fit, dict) and fit.get("composite") is not None:
            if entry_ids is None:
                continue  # already scored, skip unless explicit
        unscored.append(e)
    return unscored


def _score_single(entry: dict, dry_run: bool = True) -> ScoredEntry | None:
    """Score a single entry and return ScoredEntry.

    When dry_run=False, the score is written to the entry YAML.
    """
    entry_id = entry.get("id", "")
    try:
        result = score_entry(entry_id, dry_run=dry_run)
        if result.status == ResultStatus.ERROR:
            return None

        # Use the score from the result directly when available
        composite = result.new_score or 0.0

        # Read entry for dimension details and metadata
        _, data = load_entry_by_id(entry_id)
        if not data:
            return None
        fit = data.get("fit") or {}
        # If score was written (non-dry-run), composite is in the file
        if not composite:
            composite = fit.get("composite", 0.0)
        dimensions = {
            k: v
            for k, v in fit.items()
            if k != "composite" and isinstance(v, (int, float))
        }
        return ScoredEntry(
            entry_id=entry_id,
            composite_score=float(composite) if composite else 0.0,
            dimensions=dimensions,
            text_match_score=float(dimensions.get("evidence_match", 0.0)),
            identity_position=data.get("identity_position", "unknown"),
            organization=data.get("target", {}).get("organization", "unknown"),
        )
    except Exception:
        return None


def match_and_rank(
    entry_ids: list[str] | None = None,
    auto_qualify: bool = True,
    top_n: int = DEFAULT_TOP_N,
    dry_run: bool = True,
) -> MatchResult:
    """Score, rank, and optionally qualify entries.

    Args:
        entry_ids: Specific entries to score. None = all unscored.
        auto_qualify: If True, promote entries above threshold.
        top_n: Number of top matches to surface.
        dry_run: If True, don't modify entry files.
    """
    threshold = _get_qualify_threshold()
    entries = _load_unscored_entries(entry_ids)
    scored_list: list[ScoredEntry] = []
    qualified_ids: list[str] = []

    for entry in entries:
        scored = _score_single(entry, dry_run=dry_run)
        if scored:
            scored_list.append(scored)

    # Sort by score descending
    scored_list.sort(key=lambda s: s.composite_score, reverse=True)

    # Auto-qualify
    if auto_qualify:
        for s in scored_list:
            if s.composite_score >= threshold:
                qualified_ids.append(s.entry_id)
                if not dry_run:
                    try:
                        from pipeline_api import advance_entry

                        advance_entry(s.entry_id, to_status="qualified", dry_run=False)
                    except Exception:
                        pass

    top_matches = scored_list[:top_n]

    return MatchResult(
        scored=scored_list,
        qualified=qualified_ids,
        top_matches=top_matches,
        threshold_used=threshold,
        entries_scored=len(scored_list),
    )


def _log_match_result(result: MatchResult, log_path: Path | None = None) -> None:
    """Append match result to history log."""
    log_path = log_path or MATCH_HISTORY_PATH
    entry = {
        "date": str(date.today()),
        "entries_scored": result.entries_scored,
        "entries_qualified": len(result.qualified),
        "threshold": result.threshold_used,
        "top_score": result.top_matches[0].composite_score
        if result.top_matches
        else None,
    }
    existing = []
    if log_path.exists():
        existing = yaml.safe_load(log_path.read_text()) or []
    existing.append(entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        yaml.dump(existing, default_flow_style=False, sort_keys=False)
    )


def main():
    parser = argparse.ArgumentParser(description="Match engine: auto-score and rank")
    parser.add_argument("--yes", action="store_true", help="Execute (modify entries)")
    parser.add_argument("--target", help="Score single entry by ID")
    parser.add_argument(
        "--top", type=int, default=DEFAULT_TOP_N, help="Top N matches"
    )
    parser.add_argument(
        "--no-qualify", action="store_true", help="Score only, don't qualify"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    dry_run = not args.yes
    entry_ids = [args.target] if args.target else None

    result = match_and_rank(
        entry_ids=entry_ids,
        auto_qualify=not args.no_qualify,
        top_n=args.top,
        dry_run=dry_run,
    )

    if not dry_run:
        _log_match_result(result)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        print(f"\n{'=' * 50}")
        print(f"MATCH RESULTS ({mode})")
        print(f"{'=' * 50}")
        print(f"Entries scored:  {result.entries_scored}")
        print(
            f"Qualified:       {len(result.qualified)} (threshold {result.threshold_used})"
        )
        if result.top_matches:
            print(f"\nTop {len(result.top_matches)} Matches:")
            for s in result.top_matches:
                print(f"  {s.composite_score:.1f}  {s.entry_id} ({s.organization})")
        if result.qualified:
            print("\nQualified entries:")
            for eid in result.qualified:
                print(f"  → {eid}")


if __name__ == "__main__":
    main()
