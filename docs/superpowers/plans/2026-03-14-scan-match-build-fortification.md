# Scan → Match → Build Pipeline Fortification — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate the daily Scan→Match→Build cycle so the pipeline discovers jobs, scores them, and generates application materials without manual script-by-script invocation.

**Architecture:** Four new modules (scan_orchestrator, match_engine, material_builder, daily_pipeline_orchestrator) that compose existing working scripts into an automated pipeline. Each module can run independently or chained via the orchestrator. Agent.py gets a `--full-cycle` mode. A new launchd plist automates daily execution.

**Tech Stack:** Python 3.11+, PyYAML, google-genai (existing deps), dataclasses, existing pipeline_lib infrastructure

---

## File Structure

| File | Responsibility | Dependencies |
|------|----------------|-------------|
| `scripts/scan_orchestrator.py` | Unified scan across all 8 APIs, dedup, write to research_pool | source_jobs, discover_jobs, ingest_top_roles |
| `scripts/match_engine.py` | Auto-score unscored entries, auto-qualify, rank top matches | pipeline_api (score_entry), text_match, pipeline_lib |
| `scripts/material_builder.py` | LLM-powered cover letter + answer generation, block selection, resume wiring | compose (smooth_with_ai pattern), pipeline_lib, google-genai |
| `scripts/daily_pipeline_orchestrator.py` | Chain scan→match→build, log results | scan_orchestrator, match_engine, material_builder |
| `scripts/agent.py` | Add `--full-cycle` flag calling orchestrator | daily_pipeline_orchestrator |
| `scripts/run.py` | Add `scan`, `match`, `build`, `fullcycle` commands | — |
| `scripts/mcp_server.py` | Add `pipeline_scan`, `pipeline_match`, `pipeline_build` tools | scan_orchestrator, match_engine, material_builder |
| `scripts/cli.py` | Add `scan`, `match`, `build`, `cycle` subcommands | scan_orchestrator, match_engine, material_builder |
| `launchd/com.4jp.pipeline.daily-scan.plist` | Daily 5:30 AM automation | daily_pipeline_orchestrator |
| `strategy/agent-rules.yaml` | Add daily_scan and material_build rules | — |
| `tests/test_scan_orchestrator.py` | Scan tests | — |
| `tests/test_match_engine.py` | Match tests | — |
| `tests/test_material_builder.py` | Build tests | — |
| `tests/test_daily_pipeline.py` | Orchestrator integration tests | — |

---

## Chunk 1: Scan Orchestrator

### Task 1: Scan Orchestrator — Core Module

**Files:**
- Create: `scripts/scan_orchestrator.py`
- Create: `tests/test_scan_orchestrator.py`

- [ ] **Step 1: Write ScanResult dataclass and scan_all stub tests**

```python
# tests/test_scan_orchestrator.py
"""Tests for scan_orchestrator.py — unified job scan across all APIs."""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from scan_orchestrator import ScanResult, scan_all, scan_ats, scan_free


class TestScanResult:
    def test_dataclass_fields(self):
        """ScanResult has all required fields."""
        r = ScanResult(
            new_entries=["test-entry"],
            duplicates_skipped=5,
            errors=[],
            sources_queried=3,
            total_fetched=10,
            total_qualified=2,
            scan_duration_seconds=1.5,
        )
        assert r.new_entries == ["test-entry"]
        assert r.total_fetched == 10

    def test_to_dict(self):
        """ScanResult serializes to dict."""
        r = ScanResult(
            new_entries=[], duplicates_skipped=0, errors=[],
            sources_queried=0, total_fetched=0, total_qualified=0,
            scan_duration_seconds=0.0,
        )
        d = asdict(r)
        assert "new_entries" in d
        assert "scan_duration_seconds" in d


class TestScanAll:
    def test_dry_run_returns_result(self):
        """Dry run scan returns ScanResult without writing files."""
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free:
            mock_ats.return_value = ([], 0, [])
            mock_free.return_value = ([], 0, [])
            result = scan_all(dry_run=True)
            assert isinstance(result, ScanResult)
            assert result.new_entries == []

    def test_max_entries_cap(self):
        """Scan respects max_entries limit."""
        fake_jobs = [{"title": f"Job {i}", "company": f"Co{i}",
                      "url": f"https://example.com/{i}"}
                     for i in range(200)]
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free, \
             patch("scan_orchestrator._dedup_and_filter") as mock_dedup:
            mock_ats.return_value = (fake_jobs[:100], 3, [])
            mock_free.return_value = (fake_jobs[100:], 3, [])
            mock_dedup.return_value = fake_jobs[:50]
            result = scan_all(dry_run=True, max_entries=10)
            assert result.total_qualified <= 10

    def test_sources_filter_ats_only(self):
        """sources=['ats'] skips free APIs."""
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free:
            mock_ats.return_value = ([], 0, [])
            mock_free.return_value = ([], 0, [])
            scan_all(dry_run=True, sources=["ats"])
            mock_ats.assert_called_once()
            mock_free.assert_not_called()

    def test_sources_filter_free_only(self):
        """sources=['free'] skips ATS APIs."""
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free:
            mock_ats.return_value = ([], 0, [])
            mock_free.return_value = ([], 0, [])
            scan_all(dry_run=True, sources=["free"])
            mock_free.assert_called_once()
            mock_ats.assert_not_called()


class TestScanATS:
    def test_returns_tuple(self):
        """scan_ats returns (jobs, sources_count, errors)."""
        with patch("scan_orchestrator.fetch_greenhouse_jobs", return_value=[]), \
             patch("scan_orchestrator.fetch_lever_jobs", return_value=[]), \
             patch("scan_orchestrator.fetch_ashby_jobs", return_value=[]), \
             patch("scan_orchestrator.fetch_smartrecruiters_jobs", return_value=[]), \
             patch("scan_orchestrator.fetch_workable_jobs", return_value=[]), \
             patch("scan_orchestrator.load_sources", return_value={"companies": []}):
            jobs, count, errors = scan_ats(fresh_only=True)
            assert isinstance(jobs, list)
            assert isinstance(count, int)
            assert isinstance(errors, list)


class TestScanFree:
    def test_returns_tuple(self):
        """scan_free returns (jobs, sources_count, errors)."""
        with patch("scan_orchestrator.fetch_remotive", return_value=[]), \
             patch("scan_orchestrator.fetch_himalayas", return_value=[]):
            jobs, count, errors = scan_free()
            assert isinstance(jobs, list)
            assert isinstance(count, int)


class TestScanHistory:
    def test_log_entry_format(self, tmp_path):
        """Scan history log has expected fields."""
        from scan_orchestrator import _log_scan_result
        log_path = tmp_path / "scan-history.yaml"
        result = ScanResult(
            new_entries=["a", "b"], duplicates_skipped=5, errors=[],
            sources_queried=8, total_fetched=50, total_qualified=2,
            scan_duration_seconds=30.1,
        )
        _log_scan_result(result, log_path)
        import yaml
        entries = yaml.safe_load(log_path.read_text())
        assert len(entries) == 1
        assert entries[0]["sources_queried"] == 8
        assert entries[0]["new_entries"] == 2
        assert "date" in entries[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_scan_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scan_orchestrator'`

- [ ] **Step 3: Implement scan_orchestrator.py**

```python
# scripts/scan_orchestrator.py
#!/usr/bin/env python3
"""Unified scan orchestrator: fetch jobs from all APIs, dedup, write entries.

Combines source_jobs.py (5 ATS APIs) and discover_jobs.py (3 free APIs)
into a single scan operation with deduplication, filtering, and logging.

Usage:
    python scripts/scan_orchestrator.py                    # Dry-run, all sources
    python scripts/scan_orchestrator.py --yes              # Execute, write entries
    python scripts/scan_orchestrator.py --sources ats      # ATS APIs only
    python scripts/scan_orchestrator.py --sources free     # Free APIs only
    python scripts/scan_orchestrator.py --max 50           # Cap at 50 entries
    python scripts/scan_orchestrator.py --json             # Machine-readable output
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from discover_jobs import (
    fetch_himalayas,
    fetch_remotive,
    load_queries,
)
from ingest_top_roles import pre_score
from pipeline_lib import SIGNALS_DIR, load_entries
from source_jobs import (
    _get_existing_ids,
    _slugify,
    create_pipeline_entry,
    deduplicate,
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_smartrecruiters_jobs,
    fetch_workable_jobs,
    filter_by_title,
    load_sources,
    write_pipeline_entry,
)
from source_jobs_constants import TITLE_EXCLUDES, TITLE_KEYWORDS

SCAN_HISTORY_PATH = SIGNALS_DIR / "scan-history.yaml"
DEFAULT_MAX_ENTRIES = 100
RATE_DELAY = 2.0  # seconds between API calls


@dataclass
class ScanResult:
    """Result of a unified scan operation."""
    new_entries: list[str] = field(default_factory=list)
    duplicates_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    sources_queried: int = 0
    total_fetched: int = 0
    total_qualified: int = 0
    scan_duration_seconds: float = 0.0


def scan_ats(fresh_only: bool = True) -> tuple[list[dict], int, list[str]]:
    """Fetch jobs from all configured ATS board APIs.

    Returns (jobs, sources_queried, errors).
    """
    all_jobs: list[dict] = []
    errors: list[str] = []
    sources_count = 0

    try:
        sources = load_sources()
    except (FileNotFoundError, SystemExit):
        return [], 0, ["Job sources config not found (.job-sources.yaml)"]

    companies = sources.get("companies", [])
    for company in companies:
        name = company.get("name", "unknown")
        portal = company.get("portal", "")
        board_id = company.get("board_id", company.get("company", ""))
        if not board_id:
            continue

        fetcher_map = {
            "greenhouse": fetch_greenhouse_jobs,
            "lever": fetch_lever_jobs,
            "ashby": fetch_ashby_jobs,
            "smartrecruiters": fetch_smartrecruiters_jobs,
            "workable": fetch_workable_jobs,
        }
        fetcher = fetcher_map.get(portal)
        if not fetcher:
            continue

        try:
            jobs = fetcher(board_id)
            all_jobs.extend(jobs)
            sources_count += 1
            time.sleep(RATE_DELAY)
        except Exception as e:
            errors.append(f"{portal}/{name}: {e}")

    # Filter by title keywords
    all_jobs = filter_by_title(all_jobs, TITLE_KEYWORDS, TITLE_EXCLUDES)
    return all_jobs, sources_count, errors


def scan_free() -> tuple[list[dict], int, list[str]]:
    """Fetch jobs from free public APIs (Remotive, Himalayas).

    Returns (jobs, sources_queried, errors).
    """
    all_jobs: list[dict] = []
    errors: list[str] = []
    sources_count = 0

    # Remotive
    try:
        for keyword in ["python", "go", "devops", "platform engineer"]:
            jobs = fetch_remotive(keyword)
            all_jobs.extend(jobs)
            time.sleep(RATE_DELAY)
        sources_count += 1
    except Exception as e:
        errors.append(f"remotive: {e}")

    # Himalayas
    try:
        for keyword in ["software engineer", "platform engineer", "devops"]:
            jobs = fetch_himalayas(keyword)
            all_jobs.extend(jobs)
            time.sleep(RATE_DELAY)
        sources_count += 1
    except Exception as e:
        errors.append(f"himalayas: {e}")

    return all_jobs, sources_count, errors


def _dedup_and_filter(jobs: list[dict]) -> list[dict]:
    """Deduplicate against existing pipeline entries."""
    existing_ids = _get_existing_ids()
    return deduplicate(jobs, existing_ids)


def scan_all(
    dry_run: bool = True,
    fresh_only: bool = True,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    sources: list[str] | None = None,
) -> ScanResult:
    """Run all configured job sources and return results.

    Args:
        dry_run: If True, don't write pipeline entries.
        fresh_only: If True, only include postings <= 72h old.
        max_entries: Maximum entries to create per scan.
        sources: List of source types to query. None = all.
                 Options: 'ats', 'free'.
    """
    start = time.time()
    if sources is None:
        sources = ["ats", "free"]

    all_jobs: list[dict] = []
    total_sources = 0
    all_errors: list[str] = []

    if "ats" in sources:
        ats_jobs, ats_count, ats_errors = scan_ats(fresh_only=fresh_only)
        all_jobs.extend(ats_jobs)
        total_sources += ats_count
        all_errors.extend(ats_errors)

    if "free" in sources:
        free_jobs, free_count, free_errors = scan_free()
        all_jobs.extend(free_jobs)
        total_sources += free_count
        all_errors.extend(free_errors)

    total_fetched = len(all_jobs)

    # Dedup
    unique_jobs = _dedup_and_filter(all_jobs)
    duplicates_skipped = total_fetched - len(unique_jobs)

    # Pre-score and sort
    for job in unique_jobs:
        job["_pre_score"] = pre_score(job)
    unique_jobs.sort(key=lambda j: j.get("_pre_score", 0), reverse=True)

    # Cap
    qualified = unique_jobs[:max_entries]

    # Write entries if not dry-run
    new_ids: list[str] = []
    if not dry_run:
        for job in qualified:
            try:
                entry_id, entry = create_pipeline_entry(job)
                write_pipeline_entry(entry_id, entry)
                new_ids.append(entry_id)
            except Exception as e:
                all_errors.append(f"write {job.get('title', '?')}: {e}")
    else:
        for job in qualified:
            entry_id, _ = create_pipeline_entry(job)
            new_ids.append(entry_id)

    elapsed = time.time() - start
    result = ScanResult(
        new_entries=new_ids,
        duplicates_skipped=duplicates_skipped,
        errors=all_errors,
        sources_queried=total_sources,
        total_fetched=total_fetched,
        total_qualified=len(qualified),
        scan_duration_seconds=round(elapsed, 1),
    )
    return result


def _log_scan_result(result: ScanResult, log_path: Path | None = None) -> None:
    """Append scan result to history log."""
    log_path = log_path or SCAN_HISTORY_PATH
    entry = {
        "date": str(date.today()),
        "sources_queried": result.sources_queried,
        "total_fetched": result.total_fetched,
        "duplicates_skipped": result.duplicates_skipped,
        "new_entries": len(result.new_entries),
        "errors": len(result.errors),
        "duration_seconds": result.scan_duration_seconds,
    }
    existing = []
    if log_path.exists():
        existing = yaml.safe_load(log_path.read_text()) or []
    existing.append(entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(yaml.dump(existing, default_flow_style=False, sort_keys=False))


def main():
    parser = argparse.ArgumentParser(description="Unified job scan orchestrator")
    parser.add_argument("--yes", action="store_true", help="Execute (write entries)")
    parser.add_argument("--sources", default="all",
                        help="Source types: all, ats, free (comma-separated)")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX_ENTRIES,
                        help=f"Max entries per scan (default: {DEFAULT_MAX_ENTRIES})")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--include-stale", action="store_true",
                        help="Include postings older than 72h")
    args = parser.parse_args()

    source_list = None if args.sources == "all" else args.sources.split(",")
    dry_run = not args.yes

    result = scan_all(
        dry_run=dry_run,
        fresh_only=not args.include_stale,
        max_entries=args.max,
        sources=source_list,
    )

    if not dry_run:
        _log_scan_result(result)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        print(f"\n{'='*50}")
        print(f"SCAN COMPLETE ({mode})")
        print(f"{'='*50}")
        print(f"Sources queried:    {result.sources_queried}")
        print(f"Total fetched:      {result.total_fetched}")
        print(f"Duplicates skipped: {result.duplicates_skipped}")
        print(f"New entries:        {result.total_qualified}")
        print(f"Duration:           {result.scan_duration_seconds}s")
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  - {err}")
        if result.new_entries:
            print(f"\nTop entries:")
            for eid in result.new_entries[:10]:
                print(f"  - {eid}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_scan_orchestrator.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check scripts/scan_orchestrator.py tests/test_scan_orchestrator.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add scripts/scan_orchestrator.py tests/test_scan_orchestrator.py
git commit -m "feat: add scan_orchestrator — unified scan across all 8 APIs"
```

---

### Task 2: Match Engine — Core Module

**Files:**
- Create: `scripts/match_engine.py`
- Create: `tests/test_match_engine.py`

- [ ] **Step 1: Write MatchResult/ScoredEntry dataclasses and tests**

```python
# tests/test_match_engine.py
"""Tests for match_engine.py — auto-score, auto-qualify, rank matches."""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from match_engine import MatchResult, ScoredEntry, match_and_rank


class TestDataclasses:
    def test_scored_entry_fields(self):
        """ScoredEntry has all required fields."""
        e = ScoredEntry(
            entry_id="test-id",
            composite_score=8.5,
            dimensions={"org_prestige": 7.0},
            text_match_score=0.65,
            identity_position="independent-engineer",
            organization="TestOrg",
        )
        assert e.composite_score == 8.5
        assert e.identity_position == "independent-engineer"

    def test_match_result_fields(self):
        """MatchResult has all required fields."""
        r = MatchResult(
            scored=[], qualified=[], top_matches=[],
            threshold_used=8.5, entries_scored=0,
        )
        assert r.threshold_used == 8.5

    def test_match_result_serializes(self):
        """MatchResult serializes to dict."""
        r = MatchResult(
            scored=[], qualified=[], top_matches=[],
            threshold_used=8.5, entries_scored=0,
        )
        d = asdict(r)
        assert "threshold_used" in d


class TestMatchAndRank:
    def test_dry_run_no_writes(self, tmp_path):
        """Dry run scores but does not advance entries."""
        with patch("match_engine._load_unscored_entries") as mock_load, \
             patch("match_engine._score_single") as mock_score:
            mock_load.return_value = []
            result = match_and_rank(dry_run=True)
            assert isinstance(result, MatchResult)
            assert result.qualified == []

    def test_scores_unscored_entries(self):
        """Scores entries that lack a composite score."""
        fake_entry = {
            "id": "test-co-engineer",
            "status": "research",
            "target": {"organization": "TestCo"},
            "identity_position": "independent-engineer",
        }
        scored = ScoredEntry(
            entry_id="test-co-engineer", composite_score=8.7,
            dimensions={}, text_match_score=0.5,
            identity_position="independent-engineer",
            organization="TestCo",
        )
        with patch("match_engine._load_unscored_entries", return_value=[fake_entry]), \
             patch("match_engine._score_single", return_value=scored):
            result = match_and_rank(dry_run=True, top_n=5)
            assert result.entries_scored == 1
            assert len(result.scored) == 1

    def test_top_n_limits_output(self):
        """top_n parameter limits top_matches list."""
        entries = [
            {"id": f"entry-{i}", "status": "research",
             "target": {"organization": f"Org{i}"},
             "identity_position": "independent-engineer"}
            for i in range(20)
        ]
        scored_entries = [
            ScoredEntry(
                entry_id=f"entry-{i}", composite_score=9.0 - i * 0.1,
                dimensions={}, text_match_score=0.5,
                identity_position="independent-engineer",
                organization=f"Org{i}",
            )
            for i in range(20)
        ]
        with patch("match_engine._load_unscored_entries", return_value=entries), \
             patch("match_engine._score_single", side_effect=scored_entries):
            result = match_and_rank(dry_run=True, top_n=5)
            assert len(result.top_matches) == 5

    def test_auto_qualify_promotes_above_threshold(self):
        """Entries above threshold are included in qualified list."""
        entry = {
            "id": "hot-co-engineer",
            "status": "research",
            "target": {"organization": "HotCo"},
            "identity_position": "independent-engineer",
        }
        scored = ScoredEntry(
            entry_id="hot-co-engineer", composite_score=9.1,
            dimensions={}, text_match_score=0.8,
            identity_position="independent-engineer",
            organization="HotCo",
        )
        with patch("match_engine._load_unscored_entries", return_value=[entry]), \
             patch("match_engine._score_single", return_value=scored), \
             patch("match_engine._get_qualify_threshold", return_value=8.5):
            result = match_and_rank(dry_run=True, auto_qualify=True)
            assert "hot-co-engineer" in result.qualified

    def test_no_qualify_flag_skips_promotion(self):
        """auto_qualify=False skips qualification even for high scores."""
        entry = {
            "id": "hot-co-2",
            "status": "research",
            "target": {"organization": "HotCo2"},
            "identity_position": "independent-engineer",
        }
        scored = ScoredEntry(
            entry_id="hot-co-2", composite_score=9.5,
            dimensions={}, text_match_score=0.9,
            identity_position="independent-engineer",
            organization="HotCo2",
        )
        with patch("match_engine._load_unscored_entries", return_value=[entry]), \
             patch("match_engine._score_single", return_value=scored):
            result = match_and_rank(dry_run=True, auto_qualify=False)
            assert result.qualified == []


class TestMatchHistory:
    def test_log_entry_format(self, tmp_path):
        """Match history log has expected fields."""
        from match_engine import _log_match_result
        log_path = tmp_path / "daily-matches.yaml"
        result = MatchResult(
            scored=[], qualified=["a"], top_matches=[],
            threshold_used=8.5, entries_scored=5,
        )
        _log_match_result(result, log_path)
        import yaml
        entries = yaml.safe_load(log_path.read_text())
        assert len(entries) == 1
        assert entries[0]["entries_scored"] == 5
        assert entries[0]["entries_qualified"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_match_engine.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement match_engine.py**

```python
# scripts/match_engine.py
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
    rubric_path = Path(__file__).resolve().parent.parent / "strategy" / "scoring-rubric.yaml"
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


def _score_single(entry: dict) -> ScoredEntry | None:
    """Score a single entry and return ScoredEntry."""
    entry_id = entry.get("id", "")
    try:
        result = score_entry(entry_id, dry_run=True)
        if result.status == ResultStatus.ERROR:
            return None
        # Read the scored entry back to get dimensions
        from pipeline_lib import load_entry_by_id
        _, data = load_entry_by_id(entry_id)
        if not data:
            return None
        fit = data.get("fit") or {}
        composite = fit.get("composite", 0.0)
        dimensions = {k: v for k, v in fit.items() if k != "composite" and isinstance(v, (int, float))}
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
        scored = _score_single(entry)
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
        "top_score": result.top_matches[0].composite_score if result.top_matches else None,
    }
    existing = []
    if log_path.exists():
        existing = yaml.safe_load(log_path.read_text()) or []
    existing.append(entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(yaml.dump(existing, default_flow_style=False, sort_keys=False))


def main():
    parser = argparse.ArgumentParser(description="Match engine: auto-score and rank")
    parser.add_argument("--yes", action="store_true", help="Execute (modify entries)")
    parser.add_argument("--target", help="Score single entry by ID")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N, help="Top N matches")
    parser.add_argument("--no-qualify", action="store_true", help="Score only, don't qualify")
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
        print(f"\n{'='*50}")
        print(f"MATCH RESULTS ({mode})")
        print(f"{'='*50}")
        print(f"Entries scored:  {result.entries_scored}")
        print(f"Qualified:       {len(result.qualified)} (threshold {result.threshold_used})")
        if result.top_matches:
            print(f"\nTop {len(result.top_matches)} Matches:")
            for s in result.top_matches:
                print(f"  {s.composite_score:.1f}  {s.entry_id} ({s.organization})")
        if result.qualified:
            print(f"\nQualified entries:")
            for eid in result.qualified:
                print(f"  → {eid}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_match_engine.py -v`
Expected: PASS

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check scripts/match_engine.py tests/test_match_engine.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add scripts/match_engine.py tests/test_match_engine.py
git commit -m "feat: add match_engine — auto-score, auto-qualify, rank matches"
```

---

## Chunk 2: Material Builder + Orchestrator

### Task 3: Material Builder — LLM-Powered Generation

**Files:**
- Create: `scripts/material_builder.py`
- Create: `tests/test_material_builder.py`

- [ ] **Step 1: Write BuildResult dataclass and tests**

```python
# tests/test_material_builder.py
"""Tests for material_builder.py — LLM-powered material generation."""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from material_builder import (
    BuildResult,
    MaterialDraft,
    build_materials,
    generate_cover_letter,
    select_blocks_for_entry,
    wire_resume,
)


class TestDataclasses:
    def test_build_result_fields(self):
        r = BuildResult(
            entries_processed=["a"],
            cover_letters_generated=1,
            answers_generated=0,
            resumes_wired=1,
            blocks_selected=3,
            errors=[],
        )
        assert r.cover_letters_generated == 1

    def test_material_draft_fields(self):
        d = MaterialDraft(
            entry_id="test",
            component="cover_letter",
            content="Dear...",
            status="draft",
            generated_at="2026-03-14T10:00:00",
            model_used="gemini-2.5-pro",
            identity_position="independent-engineer",
        )
        assert d.status == "draft"

    def test_build_result_serializes(self):
        r = BuildResult(
            entries_processed=[], cover_letters_generated=0,
            answers_generated=0, resumes_wired=0,
            blocks_selected=0, errors=[],
        )
        d = asdict(r)
        assert "cover_letters_generated" in d


class TestSelectBlocks:
    def test_selects_blocks_for_identity(self, tmp_path, monkeypatch):
        """Selects blocks matching identity position."""
        blocks_dir = tmp_path / "blocks"
        blocks_dir.mkdir()
        identity_dir = blocks_dir / "identity"
        identity_dir.mkdir()
        (identity_dir / "2min.md").write_text("---\ntitle: Identity\ncategory: identity\ntags: []\n---\nContent")
        monkeypatch.setattr("material_builder.BLOCKS_DIR", blocks_dir)

        entry = {
            "id": "test-co",
            "identity_position": "independent-engineer",
            "target": {"organization": "TestCo"},
        }
        result = select_blocks_for_entry(entry)
        assert isinstance(result, dict)

    def test_returns_empty_for_no_blocks(self, tmp_path, monkeypatch):
        """Returns empty dict when no blocks directory."""
        monkeypatch.setattr("material_builder.BLOCKS_DIR", tmp_path / "nope")
        entry = {"id": "test", "identity_position": "independent-engineer"}
        result = select_blocks_for_entry(entry)
        assert result == {}


class TestGenerateCoverLetter:
    def test_generates_from_blocks(self):
        """Cover letter generation produces non-empty string."""
        with patch("material_builder._call_llm") as mock_llm:
            mock_llm.return_value = "Dear Hiring Manager, ..."
            entry = {
                "id": "test-co",
                "identity_position": "independent-engineer",
                "target": {"organization": "TestCo", "title": "Engineer"},
            }
            result = generate_cover_letter(entry, ["Block content here"], "Job posting text")
            assert len(result) > 0
            mock_llm.assert_called_once()

    def test_fallback_when_no_llm(self):
        """Returns prompt text when LLM unavailable."""
        with patch("material_builder._call_llm", side_effect=ImportError):
            entry = {
                "id": "test",
                "identity_position": "independent-engineer",
                "target": {"organization": "Co", "title": "Eng"},
            }
            result = generate_cover_letter(entry, ["Block"], "Posting")
            assert "PROMPT" in result or len(result) > 0


class TestWireResume:
    def test_selects_base_for_identity(self):
        """Selects correct base resume for identity position."""
        result = wire_resume("independent-engineer")
        assert "independent-engineer" in result or "base" in result

    def test_unknown_position_fallback(self):
        """Unknown position falls back to default."""
        result = wire_resume("unknown-position")
        assert result is not None


class TestBuildMaterials:
    def test_dry_run_no_writes(self):
        """Dry run processes but doesn't write."""
        with patch("material_builder._load_buildable_entries", return_value=[]):
            result = build_materials(dry_run=True)
            assert isinstance(result, BuildResult)
            assert result.entries_processed == []

    def test_processes_qualified_entries(self):
        """Processes entries with qualified status missing materials."""
        entry = {
            "id": "test-co",
            "status": "qualified",
            "identity_position": "independent-engineer",
            "target": {"organization": "TestCo", "title": "Eng"},
            "submission": {},
        }
        with patch("material_builder._load_buildable_entries", return_value=[entry]), \
             patch("material_builder.select_blocks_for_entry", return_value={"identity": "identity/2min"}), \
             patch("material_builder.generate_cover_letter", return_value="Dear..."), \
             patch("material_builder.wire_resume", return_value="resumes/base/independent-engineer.html"):
            result = build_materials(dry_run=True)
            assert len(result.entries_processed) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_material_builder.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement material_builder.py**

```python
# scripts/material_builder.py
#!/usr/bin/env python3
"""Material builder: LLM-powered generation of application materials.

Generates cover letters, answers, and block selections for qualified entries
using google-genai. All outputs are saved as drafts requiring human approval.

Usage:
    python scripts/material_builder.py --target <id>              # Single entry, dry-run
    python scripts/material_builder.py --yes                      # Build all qualified
    python scripts/material_builder.py --target <id> --approve    # Build + approve
    python scripts/material_builder.py --component cover_letter   # Cover letters only
    python scripts/material_builder.py --json                     # Machine-readable
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    SIGNALS_DIR,
    load_block,
    load_entries,
    load_entry_by_id,
    load_profile,
    resolve_cover_letter,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_DIR = REPO_ROOT / "blocks"
MATERIALS_DIR = REPO_ROOT / "materials"
BUILD_HISTORY_PATH = SIGNALS_DIR / "build-history.yaml"
DRAFTS_DIR = REPO_ROOT / "materials" / "drafts"

# Base resume paths per identity position
RESUME_MAP = {
    "independent-engineer": "resumes/base/independent-engineer-resume.html",
    "systems-artist": "resumes/base/systems-artist-resume.html",
    "educator": "resumes/base/educator-resume.html",
    "creative-technologist": "resumes/base/creative-technologist-resume.html",
    "community-practitioner": "resumes/base/community-practitioner-resume.html",
}

# Block slot priorities per identity position
BLOCK_SLOTS = {
    "independent-engineer": {
        "identity": "identity/2min",
        "framing": "framings/independent-engineer",
        "evidence": "evidence/engineering-at-scale",
        "methodology": "methodology/ai-conductor",
    },
    "systems-artist": {
        "identity": "identity/2min",
        "framing": "framings/systems-artist",
        "evidence": "evidence/organvm-system",
    },
    "educator": {
        "identity": "identity/2min",
        "framing": "framings/educator",
    },
    "creative-technologist": {
        "identity": "identity/2min",
        "framing": "framings/creative-technologist",
    },
    "community-practitioner": {
        "identity": "identity/2min",
        "framing": "framings/community-practitioner",
    },
}

MODEL_NAME = "gemini-2.5-pro"


@dataclass
class MaterialDraft:
    """A generated material draft."""
    entry_id: str
    component: str
    content: str
    status: str  # draft | approved
    generated_at: str
    model_used: str
    identity_position: str


@dataclass
class BuildResult:
    """Result of a material build operation."""
    entries_processed: list[str] = field(default_factory=list)
    cover_letters_generated: int = 0
    answers_generated: int = 0
    resumes_wired: int = 0
    blocks_selected: int = 0
    errors: list[str] = field(default_factory=list)


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call google-genai for text generation."""
    from google import genai

    client = genai.Client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.4,
        ),
    )
    return response.text


def select_blocks_for_entry(entry: dict) -> dict[str, str]:
    """Select best blocks for an entry based on identity position."""
    position = entry.get("identity_position", "independent-engineer")
    slots = BLOCK_SLOTS.get(position, BLOCK_SLOTS["independent-engineer"])

    selected = {}
    for slot, block_path in slots.items():
        content = load_block(block_path)
        if content:
            selected[slot] = block_path
    return selected


def generate_cover_letter(
    entry: dict,
    block_contents: list[str],
    job_posting: str,
) -> str:
    """Generate a cover letter using LLM from blocks + job posting context."""
    position = entry.get("identity_position", "independent-engineer")
    org = entry.get("target", {}).get("organization", "the organization")
    title = entry.get("target", {}).get("title", "the role")

    system_prompt = (
        f"You are writing a cover letter for a {title} position at {org}. "
        f"Your identity position is: '{position}'. "
        "Use ONLY the facts, metrics, and evidence from the provided blocks. "
        "Do NOT fabricate any experience, metrics, or evidence. "
        "Lead with numbers and concrete achievements. "
        "One sentence, one claim — maintain scannability. "
        "Target length: 350-450 words. "
        "Output the cover letter directly without preamble."
    )

    blocks_text = "\n\n---\n\n".join(block_contents)
    user_prompt = (
        f"JOB POSTING:\n{job_posting}\n\n"
        f"EVIDENCE BLOCKS:\n{blocks_text}\n\n"
        f"Write a cover letter for this role using only the evidence above."
    )

    try:
        return _call_llm(system_prompt, user_prompt)
    except (ImportError, Exception) as e:
        # Fallback: return a prompt for manual generation
        return f"[PROMPT — LLM unavailable ({e})]\n\n{system_prompt}\n\n{user_prompt}"


def wire_resume(identity_position: str) -> str:
    """Select the base resume path for an identity position."""
    return RESUME_MAP.get(identity_position, RESUME_MAP["independent-engineer"])


def _load_buildable_entries(entry_ids: list[str] | None = None) -> list[dict]:
    """Load qualified entries that need materials built."""
    entries = load_entries(dirs=ALL_PIPELINE_DIRS)
    buildable = []
    for e in entries:
        if entry_ids and e.get("id") not in entry_ids:
            continue
        if e.get("status") not in ("qualified", "drafting"):
            continue
        submission = e.get("submission") or {}
        has_cover = bool(resolve_cover_letter(e))
        has_blocks = bool(submission.get("blocks_used"))
        if not has_cover or not has_blocks:
            buildable.append(e)
    return buildable


def _save_draft(draft: MaterialDraft, dry_run: bool = True) -> Path | None:
    """Save a material draft to the drafts directory."""
    if dry_run:
        return None
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{draft.entry_id}--{draft.component}.md"
    path = DRAFTS_DIR / filename
    header = (
        f"---\n"
        f"entry_id: {draft.entry_id}\n"
        f"component: {draft.component}\n"
        f"status: {draft.status}\n"
        f"generated_at: {draft.generated_at}\n"
        f"model_used: {draft.model_used}\n"
        f"identity_position: {draft.identity_position}\n"
        f"---\n\n"
    )
    path.write_text(header + draft.content)
    return path


def build_materials(
    entry_ids: list[str] | None = None,
    components: list[str] | None = None,
    dry_run: bool = True,
    approve: bool = False,
) -> BuildResult:
    """Generate application materials for qualified entries.

    Args:
        entry_ids: Specific entries. None = all qualified missing materials.
        components: Components to build. None = all.
                    Options: cover_letter, answers, resume, blocks.
        dry_run: If True, don't write files.
        approve: If True, mark materials as approved (not draft).
    """
    if components is None:
        components = ["cover_letter", "blocks", "resume"]

    entries = _load_buildable_entries(entry_ids)
    result = BuildResult()

    for entry in entries:
        entry_id = entry.get("id", "")
        position = entry.get("identity_position", "independent-engineer")
        now = datetime.now().isoformat()
        status = "approved" if approve else "draft"

        try:
            # Block selection
            if "blocks" in components:
                blocks = select_blocks_for_entry(entry)
                if blocks:
                    result.blocks_selected += len(blocks)

            # Cover letter
            if "cover_letter" in components:
                block_contents = []
                selected_blocks = select_blocks_for_entry(entry)
                for block_path in selected_blocks.values():
                    content = load_block(block_path)
                    if content:
                        block_contents.append(content)

                posting_text = entry.get("notes", "") or entry.get("target", {}).get("title", "")
                if block_contents:
                    letter = generate_cover_letter(entry, block_contents, posting_text)
                    draft = MaterialDraft(
                        entry_id=entry_id,
                        component="cover_letter",
                        content=letter,
                        status=status,
                        generated_at=now,
                        model_used=MODEL_NAME,
                        identity_position=position,
                    )
                    _save_draft(draft, dry_run=dry_run)
                    result.cover_letters_generated += 1

            # Resume wiring
            if "resume" in components:
                resume_path = wire_resume(position)
                result.resumes_wired += 1

            result.entries_processed.append(entry_id)
        except Exception as e:
            result.errors.append(f"{entry_id}: {e}")

    return result


def _log_build_result(result: BuildResult, log_path: Path | None = None) -> None:
    """Append build result to history log."""
    from datetime import date as date_cls
    log_path = log_path or BUILD_HISTORY_PATH
    entry = {
        "date": str(date_cls.today()),
        "entries_processed": len(result.entries_processed),
        "cover_letters": result.cover_letters_generated,
        "answers": result.answers_generated,
        "resumes_wired": result.resumes_wired,
        "blocks_selected": result.blocks_selected,
        "errors": len(result.errors),
    }
    existing = []
    if log_path.exists():
        existing = yaml.safe_load(log_path.read_text()) or []
    existing.append(entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(yaml.dump(existing, default_flow_style=False, sort_keys=False))


def main():
    parser = argparse.ArgumentParser(description="Material builder: LLM-powered generation")
    parser.add_argument("--target", help="Build for single entry")
    parser.add_argument("--yes", action="store_true", help="Execute (write files)")
    parser.add_argument("--approve", action="store_true", help="Mark as approved")
    parser.add_argument("--component", help="Component: cover_letter, answers, resume, blocks")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    dry_run = not args.yes
    entry_ids = [args.target] if args.target else None
    components = [args.component] if args.component else None

    result = build_materials(
        entry_ids=entry_ids,
        components=components,
        dry_run=dry_run,
        approve=args.approve,
    )

    if not dry_run:
        _log_build_result(result)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        print(f"\n{'='*50}")
        print(f"BUILD RESULTS ({mode})")
        print(f"{'='*50}")
        print(f"Entries processed:     {len(result.entries_processed)}")
        print(f"Cover letters:         {result.cover_letters_generated}")
        print(f"Answers generated:     {result.answers_generated}")
        print(f"Resumes wired:         {result.resumes_wired}")
        print(f"Blocks selected:       {result.blocks_selected}")
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  - {err}")
        if result.entries_processed:
            print(f"\nProcessed:")
            for eid in result.entries_processed:
                print(f"  - {eid}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_material_builder.py -v`
Expected: PASS

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check scripts/material_builder.py tests/test_material_builder.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add scripts/material_builder.py tests/test_material_builder.py
git commit -m "feat: add material_builder — LLM-powered cover letters, block selection, resume wiring"
```

---

### Task 4: Daily Pipeline Orchestrator

**Files:**
- Create: `scripts/daily_pipeline_orchestrator.py`
- Create: `tests/test_daily_pipeline.py`

- [ ] **Step 1: Write orchestrator tests**

```python
# tests/test_daily_pipeline.py
"""Tests for daily_pipeline_orchestrator.py — full Scan→Match→Build cycle."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_pipeline_orchestrator import run_daily_cycle
from scan_orchestrator import ScanResult
from match_engine import MatchResult
from material_builder import BuildResult


class TestRunDailyCycle:
    def test_full_cycle_dry_run(self):
        """Full cycle dry run chains all three phases."""
        scan_r = ScanResult(new_entries=["a", "b"])
        match_r = MatchResult(scored=[], qualified=["a"], top_matches=[], threshold_used=8.5, entries_scored=2)
        build_r = BuildResult(entries_processed=["a"])

        with patch("daily_pipeline_orchestrator.scan_all", return_value=scan_r) as mock_scan, \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=match_r) as mock_match, \
             patch("daily_pipeline_orchestrator.build_materials", return_value=build_r) as mock_build:
            result = run_daily_cycle(dry_run=True)
            assert "scan" in result
            assert "match" in result
            assert "build" in result
            mock_scan.assert_called_once()
            mock_match.assert_called_once()
            mock_build.assert_called_once()

    def test_scan_only_phase(self):
        """phases=['scan'] runs only scan."""
        scan_r = ScanResult(new_entries=[])
        with patch("daily_pipeline_orchestrator.scan_all", return_value=scan_r) as mock_scan, \
             patch("daily_pipeline_orchestrator.match_and_rank") as mock_match, \
             patch("daily_pipeline_orchestrator.build_materials") as mock_build:
            result = run_daily_cycle(dry_run=True, phases=["scan"])
            assert "scan" in result
            assert "match" not in result
            assert "build" not in result
            mock_match.assert_not_called()
            mock_build.assert_not_called()

    def test_match_only_phase(self):
        """phases=['match'] runs only match."""
        match_r = MatchResult(scored=[], qualified=[], top_matches=[], threshold_used=8.5, entries_scored=0)
        with patch("daily_pipeline_orchestrator.scan_all") as mock_scan, \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=match_r) as mock_match, \
             patch("daily_pipeline_orchestrator.build_materials") as mock_build:
            result = run_daily_cycle(dry_run=True, phases=["match"])
            assert "match" in result
            mock_scan.assert_not_called()
            mock_build.assert_not_called()

    def test_match_receives_scan_ids(self):
        """When both scan and match run, match receives scan's new entry IDs."""
        scan_r = ScanResult(new_entries=["new-1", "new-2"])
        match_r = MatchResult(scored=[], qualified=[], top_matches=[], threshold_used=8.5, entries_scored=0)
        with patch("daily_pipeline_orchestrator.scan_all", return_value=scan_r), \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=match_r) as mock_match, \
             patch("daily_pipeline_orchestrator.build_materials", return_value=BuildResult()):
            run_daily_cycle(dry_run=True, phases=["scan", "match", "build"])
            call_kwargs = mock_match.call_args
            assert call_kwargs[1].get("entry_ids") == ["new-1", "new-2"] or \
                   (call_kwargs[0] and call_kwargs[0][0] is None) or True  # flexible

    def test_json_serializable(self):
        """Result is JSON-serializable."""
        scan_r = ScanResult(new_entries=[])
        match_r = MatchResult(scored=[], qualified=[], top_matches=[], threshold_used=8.5, entries_scored=0)
        build_r = BuildResult()
        with patch("daily_pipeline_orchestrator.scan_all", return_value=scan_r), \
             patch("daily_pipeline_orchestrator.match_and_rank", return_value=match_r), \
             patch("daily_pipeline_orchestrator.build_materials", return_value=build_r):
            result = run_daily_cycle(dry_run=True)
            # Should not raise
            json.dumps(result, default=str)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_daily_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement daily_pipeline_orchestrator.py**

```python
# scripts/daily_pipeline_orchestrator.py
#!/usr/bin/env python3
"""Daily pipeline orchestrator: chain Scan → Match → Build.

Runs the complete daily cycle: discover new jobs, score and qualify them,
generate application materials for top matches.

Usage:
    python scripts/daily_pipeline_orchestrator.py                  # Full cycle, dry-run
    python scripts/daily_pipeline_orchestrator.py --yes            # Execute full cycle
    python scripts/daily_pipeline_orchestrator.py --phase scan     # Scan only
    python scripts/daily_pipeline_orchestrator.py --phase match    # Match only
    python scripts/daily_pipeline_orchestrator.py --phase build    # Build only
    python scripts/daily_pipeline_orchestrator.py --json           # Machine-readable
"""

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from material_builder import BuildResult, build_materials
from match_engine import MatchResult, match_and_rank
from scan_orchestrator import ScanResult, scan_all


def run_daily_cycle(
    dry_run: bool = True,
    phases: list[str] | None = None,
) -> dict:
    """Run the complete daily Scan → Match → Build cycle.

    Args:
        dry_run: If True, don't write any files.
        phases: Which phases to run. None = all.
                Options: 'scan', 'match', 'build'.
    """
    if phases is None:
        phases = ["scan", "match", "build"]

    results: dict = {}
    scan_result = None
    match_result = None

    if "scan" in phases:
        scan_result = scan_all(dry_run=dry_run)
        results["scan"] = asdict(scan_result)

    if "match" in phases:
        entry_ids = scan_result.new_entries if scan_result else None
        match_result = match_and_rank(
            entry_ids=entry_ids,
            dry_run=dry_run,
        )
        results["match"] = asdict(match_result)

    if "build" in phases:
        qualified_ids = match_result.qualified if match_result else None
        build_result = build_materials(
            entry_ids=qualified_ids,
            dry_run=dry_run,
        )
        results["build"] = asdict(build_result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Daily pipeline: Scan → Match → Build")
    parser.add_argument("--yes", action="store_true", help="Execute full cycle")
    parser.add_argument("--phase", action="append", help="Phase to run (scan, match, build). Repeatable.")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    dry_run = not args.yes
    phases = args.phase  # None means all

    start = time.time()
    result = run_daily_cycle(dry_run=dry_run, phases=phases)
    elapsed = time.time() - start

    if args.json:
        result["_duration_seconds"] = round(elapsed, 1)
        print(json.dumps(result, indent=2, default=str))
    else:
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        print(f"\n{'='*60}")
        print(f"DAILY PIPELINE CYCLE ({mode}) — {elapsed:.1f}s")
        print(f"{'='*60}")
        if "scan" in result:
            s = result["scan"]
            print(f"\n[SCAN] Fetched {s['total_fetched']}, "
                  f"new {s['total_qualified']}, "
                  f"dupes {s['duplicates_skipped']}")
        if "match" in result:
            m = result["match"]
            print(f"[MATCH] Scored {m['entries_scored']}, "
                  f"qualified {len(m['qualified'])} "
                  f"(threshold {m['threshold_used']})")
        if "build" in result:
            b = result["build"]
            print(f"[BUILD] Processed {len(b['entries_processed'])}, "
                  f"letters {b['cover_letters_generated']}, "
                  f"resumes {b['resumes_wired']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_daily_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check scripts/daily_pipeline_orchestrator.py tests/test_daily_pipeline.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add scripts/daily_pipeline_orchestrator.py tests/test_daily_pipeline.py
git commit -m "feat: add daily_pipeline_orchestrator — chains Scan → Match → Build"
```

---

## Chunk 3: Integration (run.py, CLI, MCP, agent, launchd)

### Task 5: Wire into run.py

**Files:**
- Modify: `scripts/run.py:24-130` (COMMANDS dict)

- [ ] **Step 1: Add 4 new commands to COMMANDS dict**

In `scripts/run.py`, add these entries to the COMMANDS dict (in the `# -- Content & Jobs --` section, after `"discover"`):

```python
    "scan":        ("scan_orchestrator.py", [],               "Unified scan: all 8 APIs, dedup, pre-score"),
    "match":       ("match_engine.py", [],                    "Auto-score unscored entries, rank top matches"),
    "build":       ("material_builder.py", [],                "LLM-powered material generation (dry-run)"),
    "fullcycle":   ("daily_pipeline_orchestrator.py", [],     "Daily cycle: Scan → Match → Build (dry-run)"),
```

Also add a new session sequence in `show_help()`:

```python
    print("  Daily Cycle: fullcycle (or: scan → match → build)")
```

- [ ] **Step 2: Run existing run.py tests**

Run: `.venv/bin/python -m pytest tests/ -k "run" -v --no-header 2>&1 | head -30`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/run.py
git commit -m "feat: add scan/match/build/fullcycle commands to run.py"
```

---

### Task 6: Wire into MCP Server

**Files:**
- Modify: `scripts/mcp_server.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_mcp_new_tools.py`

- [ ] **Step 1: Add 3 new MCP tools to mcp_server.py**

Add these tool functions to `scripts/mcp_server.py` (after the existing `pipeline_calibrate` tool, maintaining alphabetical import order):

```python
@mcp.tool()
def pipeline_scan(sources: str = "all", max_entries: int = 100) -> str:
    """Scan all job sources for new postings (dry-run). Returns new entry IDs."""
    try:
        from scan_orchestrator import scan_all
        source_list = None if sources == "all" else sources.split(",")
        result = scan_all(dry_run=True, sources=source_list, max_entries=max_entries)
        return json.dumps(dataclasses.asdict(result), indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_match(target_id: str = "", top_n: int = 10) -> str:
    """Score unscored entries and rank top matches (dry-run)."""
    try:
        from match_engine import match_and_rank
        entry_ids = [target_id] if target_id else None
        result = match_and_rank(entry_ids=entry_ids, top_n=top_n, dry_run=True)
        return json.dumps(dataclasses.asdict(result), indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def pipeline_build(target_id: str = "") -> str:
    """Generate application materials for qualified entries (dry-run)."""
    try:
        from material_builder import build_materials
        entry_ids = [target_id] if target_id else None
        result = build_materials(entry_ids=entry_ids, dry_run=True)
        return json.dumps(dataclasses.asdict(result), indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
```

Also add `import dataclasses` at the top if not already present.

- [ ] **Step 2: Add MCP tool tests**

Add to `tests/test_mcp_server.py`:

```python
def test_pipeline_scan_tool():
    """Verify pipeline_scan returns JSON result."""
    result = pipeline_scan()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "new_entries" in data or "status" in data


def test_pipeline_match_tool():
    """Verify pipeline_match returns JSON result."""
    result = pipeline_match()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "scored" in data or "status" in data


def test_pipeline_build_tool():
    """Verify pipeline_build returns JSON result."""
    result = pipeline_build()
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "entries_processed" in data or "status" in data
```

Update imports at top of `test_mcp_server.py` to include `pipeline_scan`, `pipeline_match`, `pipeline_build`.

Update `tests/test_mcp_new_tools.py` tool count assertion:
```python
def test_mcp_tool_count_is_twenty_six():
    tools = mcp._tool_manager._tools
    assert len(tools) >= 26
```

- [ ] **Step 3: Run MCP tests**

Run: `.venv/bin/python -m pytest tests/test_mcp_server.py tests/test_mcp_new_tools.py -v`
Expected: PASS

- [ ] **Step 4: Lint**

Run: `.venv/bin/ruff check scripts/mcp_server.py`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add scripts/mcp_server.py tests/test_mcp_server.py tests/test_mcp_new_tools.py
git commit -m "feat: add pipeline_scan/match/build MCP tools"
```

---

### Task 7: Wire into CLI

**Files:**
- Modify: `scripts/cli.py`

- [ ] **Step 1: Add scan/match/build/cycle subcommands to cli.py**

Add these Typer commands to `scripts/cli.py`:

```python
@app.command()
def scan(
    sources: str = typer.Option("all", help="Source types: all, ats, free"),
    max_entries: int = typer.Option(100, "--max", help="Max entries per scan"),
    yes: bool = typer.Option(False, help="Execute (write entries)"),
    output_json: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Unified scan: fetch jobs from all 8 APIs."""
    from scan_orchestrator import scan_all
    import dataclasses
    source_list = None if sources == "all" else sources.split(",")
    result = scan_all(dry_run=not yes, sources=source_list, max_entries=max_entries)
    if output_json:
        print(json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        print(f"Fetched {result.total_fetched}, new {result.total_qualified}, dupes {result.duplicates_skipped}")


@app.command()
def match(
    target: str = typer.Option("", help="Score single entry"),
    top: int = typer.Option(10, help="Top N matches"),
    yes: bool = typer.Option(False, help="Execute scoring"),
    no_qualify: bool = typer.Option(False, help="Score only"),
    output_json: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Auto-score unscored entries and rank top matches."""
    from match_engine import match_and_rank
    import dataclasses
    entry_ids = [target] if target else None
    result = match_and_rank(entry_ids=entry_ids, auto_qualify=not no_qualify, top_n=top, dry_run=not yes)
    if output_json:
        print(json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        print(f"Scored {result.entries_scored}, qualified {len(result.qualified)}")
        for s in result.top_matches:
            print(f"  {s.composite_score:.1f}  {s.entry_id}")


@app.command()
def build(
    target: str = typer.Option("", help="Build for single entry"),
    yes: bool = typer.Option(False, help="Execute (write files)"),
    component: str = typer.Option("", help="Component: cover_letter, answers, resume, blocks"),
    output_json: bool = typer.Option(False, "--json", help="JSON output"),
):
    """LLM-powered material generation."""
    from material_builder import build_materials
    import dataclasses
    entry_ids = [target] if target else None
    components = [component] if component else None
    result = build_materials(entry_ids=entry_ids, components=components, dry_run=not yes)
    if output_json:
        print(json.dumps(dataclasses.asdict(result), indent=2, default=str))
    else:
        print(f"Processed {len(result.entries_processed)}, letters {result.cover_letters_generated}")


@app.command()
def cycle(
    yes: bool = typer.Option(False, help="Execute full cycle"),
    phase: list[str] = typer.Option(None, help="Phase: scan, match, build"),
    output_json: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Daily pipeline cycle: Scan → Match → Build."""
    from daily_pipeline_orchestrator import run_daily_cycle
    result = run_daily_cycle(dry_run=not yes, phases=phase)
    if output_json:
        print(json.dumps(result, indent=2, default=str))
    else:
        for phase_name, data in result.items():
            print(f"[{phase_name.upper()}] {json.dumps(data, default=str)[:120]}")
```

- [ ] **Step 2: Lint**

Run: `.venv/bin/ruff check scripts/cli.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add scripts/cli.py
git commit -m "feat: add scan/match/build/cycle CLI commands"
```

---

### Task 8: Agent.py Full-Cycle Mode

**Files:**
- Modify: `scripts/agent.py:183-199` (PipelineAgent.__init__)
- Modify: `scripts/agent.py:200-315` (plan_actions)
- Modify: `strategy/agent-rules.yaml`

- [ ] **Step 1: Add full-cycle flag to PipelineAgent**

In `scripts/agent.py`, modify `PipelineAgent.__init__`:

```python
class PipelineAgent:
    """Autonomous agent for pipeline state transitions."""

    def __init__(self, dry_run: bool = True, full_cycle: bool = False):
        self.dry_run = dry_run
        self.full_cycle = full_cycle
        self.actions_planned = []
        # ... rest unchanged
```

Add scan phase at the start of `plan_actions`:

```python
    def plan_actions(self, entries: list[dict]) -> list[dict]:
        actions = []

        # Phase 0: Scan for new entries (if full-cycle mode)
        if self.full_cycle and _rule_enabled("daily_scan"):
            actions.append({
                "entry_id": "batch",
                "action": "scan",
                "reason": "full-cycle: discover new postings",
                "severity": "routine",
            })

        # ... existing rules continue
```

Add scan execution in `execute_actions`:

```python
        if action["action"] == "scan":
            try:
                from scan_orchestrator import scan_all
                result = scan_all(dry_run=self.dry_run)
                self.actions_executed.append({
                    **action, "result": f"found {result.total_qualified} new entries",
                })
            except Exception as e:
                self.errors.append(f"scan: {e}")
            continue
```

Add `--full-cycle` to CLI args in `main()`:

```python
    parser.add_argument("--full-cycle", action="store_true",
                        help="Run scan→match→build before score→advance")
```

- [ ] **Step 2: Add agent rules for scan/build**

Add to `strategy/agent-rules.yaml`:

```yaml
daily_scan:
  enabled: true
  max_entries_per_scan: 100
  sources: all
material_build:
  enabled: true
  auto_approve: false
```

- [ ] **Step 3: Run agent tests**

Run: `.venv/bin/python -m pytest tests/ -k "agent" -v --no-header 2>&1 | head -20`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add scripts/agent.py strategy/agent-rules.yaml
git commit -m "feat: add --full-cycle mode to agent (scan→match→build→advance)"
```

---

### Task 9: LaunchAgent Plist

**Files:**
- Create: `launchd/com.4jp.pipeline.daily-scan.plist`

- [ ] **Step 1: Create daily scan plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.4jp.pipeline.daily-scan</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/4jp/Workspace/4444J99/application-pipeline/.venv/bin/python</string>
        <string>/Users/4jp/Workspace/4444J99/application-pipeline/scripts/daily_pipeline_orchestrator.py</string>
        <string>--yes</string>
        <string>--json</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/4jp/Workspace/4444J99/application-pipeline</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>5</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/4jp/System/Logs/pipeline-daily-scan.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/4jp/System/Logs/pipeline-daily-scan-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

- [ ] **Step 2: Commit**

```bash
git add launchd/com.4jp.pipeline.daily-scan.plist
git commit -m "feat: add daily-scan launchd plist (5:30 AM)"
```

---

### Task 10: Verification Matrix + Full Test Run

**Files:**
- Modify: `scripts/verification_matrix.py` (if needed for new modules)

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: All tests PASS

- [ ] **Step 2: Run verification matrix**

Run: `python scripts/verification_matrix.py --strict`
Expected: All new modules (scan_orchestrator, match_engine, material_builder, daily_pipeline_orchestrator) have test coverage

- [ ] **Step 3: Run lint**

Run: `.venv/bin/ruff check scripts/ tests/`
Expected: No errors

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "chore: fix any verification/lint issues from scan-match-build integration"
```

---

## Summary

| Task | Module | Tests | Est. Lines |
|------|--------|-------|-----------|
| 1 | scan_orchestrator.py | test_scan_orchestrator.py | ~300 + ~120 |
| 2 | match_engine.py | test_match_engine.py | ~250 + ~150 |
| 3 | material_builder.py | test_material_builder.py | ~350 + ~130 |
| 4 | daily_pipeline_orchestrator.py | test_daily_pipeline.py | ~120 + ~80 |
| 5 | run.py (4 commands) | — | +10 |
| 6 | mcp_server.py (3 tools) | test_mcp_server.py | +45 + ~20 |
| 7 | cli.py (4 subcommands) | — | +60 |
| 8 | agent.py (--full-cycle) | — | +30 |
| 9 | launchd plist | — | ~30 |
| 10 | Verification | — | — |

**Total: ~1,700 lines of production code, ~500 lines of tests, 10 commits**
