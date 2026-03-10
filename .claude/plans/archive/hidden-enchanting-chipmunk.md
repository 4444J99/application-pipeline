# Plan: Skill-Based Job Discovery System

## Context

Current `source_jobs.py` is **company-locked** — polls ~172 specific ATS boards (Greenhouse/Ashby) and filters by title. This creates a closed loop: same companies, same engineering roles, no discovery of creative technologist, educator, museum, or community roles. The user has 5 identity positions but is only surfacing `independent-engineer` jobs.

**Goal:** Add a new discovery script that searches free job APIs by **skills and role types** across all 5 identity positions, surfacing opportunities the company-locked system can't find.

## New Files

| File | Purpose |
|------|---------|
| `scripts/discover_jobs.py` | Main discovery script (~350-400 lines) |
| `scripts/.discovery-queries.yaml` | Config: search queries per identity position + API params |
| `tests/test_discover_jobs.py` | Unit tests |

## Modified Files

| File | Change |
|------|---------|
| `scripts/run.py` | Add `discover` to COMMANDS + PARAM_COMMANDS |
| `.gitignore` | Add `scripts/.discovery-queries.yaml` and `scripts/.discovery-stats.yaml` |

## API Sources (all free, no auth for primary 3)

| API | Auth | Keyword Search | Why |
|-----|------|---------------|-----|
| **Remotive** | None | Yes (`search=` param) | Best keyword search, clean API, remote-focused |
| **Himalayas** | None | Yes (via endpoint filters) | No-auth, broad, posting dates |
| **The Muse** | None | Category-based | Quality companies, good for creative/tech |
| **Adzuna** | Free key | Yes (`what=` param) | Broadest market (deferred until key registered) |

## Search Query Sets Per Identity Position

Each position gets its own title keywords that map to the role types it should surface:

**independent-engineer:** `developer experience`, `developer tools`, `platform engineer`, `developer advocate`, `ai engineer`, `cli engineer`, `infrastructure engineer`, `devops`, `backend engineer`

**systems-artist:** `artist in residence`, `new media`, `museum technology`, `digital art`, `creative technologist`, `gallery`, `interactive installation`, `art and technology`

**educator:** `curriculum developer`, `instructional designer`, `education engineer`, `technical instructor`, `learning engineer`, `edtech`, `course developer`

**creative-technologist:** `creative technologist`, `creative developer`, `creative engineer`, `interactive developer`, `experience engineer`, `innovation lab`, `technical artist`, `creative coder`, `r&d engineer`

**community-practitioner:** `community manager`, `program coordinator`, `social impact`, `nonprofit technology`, `civic tech`, `community engagement`, `dei program`

## Architecture

```
discover_jobs.py
  ├── load_queries()              # Read .discovery-queries.yaml
  ├── fetch_remotive(search, category)   # Remotive API adapter
  ├── fetch_himalayas(keywords)          # Himalayas API adapter
  ├── fetch_themuse(category)            # The Muse API adapter
  ├── normalize_job(raw, source_api)     # Normalize to source_jobs.py dict shape
  ├── discover_for_position(pos, cfg)    # Run all queries for one position
  ├── cross_position_dedup(results)      # Keep highest-scored per company+title
  ├── create_discovery_entry(job, pos)   # Wrap source_jobs.create_pipeline_entry
  ├── display_results(results)           # Formatted output with scores + URLs
  └── main()                             # CLI: --position, --yes, --limit, --apis, --min-score
```

**Reuses from existing scripts:**
- `source_jobs.py`: `create_pipeline_entry()`, `deduplicate()`, `_get_existing_ids()`, `classify_location()`, `filter_by_freshness()`, `_slugify()`
- `pipeline_lib.py`: `http_request_with_retry()`, `load_entries()`, path constants
- `ingest_top_roles.py`: `pre_score()` for job-track scoring

## CLI Interface

```bash
python scripts/discover_jobs.py                              # All positions, dry-run
python scripts/discover_jobs.py --position creative-technologist  # Single position
python scripts/discover_jobs.py --yes                        # Create entries in research_pool/
python scripts/discover_jobs.py --limit 20 --min-score 6.0   # Filters
python scripts/discover_jobs.py --apis remotive,himalayas     # Select APIs

# Via run.py:
python scripts/run.py discover                       # All positions, dry-run
python scripts/run.py discover creative-technologist # Single position
```

## Key Design Decisions

1. **New script, not extending source_jobs.py** — Different data access pattern (keyword search vs company board polling). Both import shared infrastructure.
2. **Config-driven queries** — `.discovery-queries.yaml` so queries can be tuned without code changes.
3. **Identity position auto-assigned** from which query set found the job.
4. **3-layer dedup** — within run, across positions, against full pipeline (including research_pool + closed).
5. **Fail-soft per API** — if Remotive times out, Himalayas and Muse results still returned. Critical for unreliable hotspot.
6. **2-second rate delay** between requests. ~30-50 requests per full run = ~60-100 seconds total.
7. **Start with 3 no-auth APIs** (Remotive, Himalayas, The Muse). Adzuna added later when user registers free key.

## Implementation Sequence

1. Create `.discovery-queries.yaml` config
2. Create `discover_jobs.py` with API adapters (Remotive first, then Himalayas, then The Muse)
3. Wire discovery orchestrator + dedup + pre-scoring + entry creation
4. Add CLI + run.py integration
5. Add `.gitignore` entries
6. Write tests
7. Run full test suite to verify no regressions

## Verification

1. `python scripts/discover_jobs.py --dry-run` — shows discovered jobs with scores and URLs
2. `python scripts/discover_jobs.py --position creative-technologist` — surfaces non-engineering roles
3. `python scripts/run.py discover` — quick command works
4. `source .venv/bin/activate && python -m pytest tests/ -q` — all tests pass
5. `ruff check scripts/ tests/` — lint clean
