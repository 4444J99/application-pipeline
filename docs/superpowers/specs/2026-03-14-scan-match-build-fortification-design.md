# Scan → Match → Build Pipeline Fortification

## Problem

The application pipeline has 127 modules but only ~40% serve the core cycle:
**Scan → Match → Build → Apply → Follow up.**

The three foundational phases (Scan, Match, Build) exist as independent CLI scripts
with no orchestration, no automation, and no feedback between them:

- **Scan**: 3 scripts, 8 API integrations — never automated, agent.py never calls them
- **Match**: TF-IDF keyword matching + 9-dim rubric — always manual trigger
- **Build**: Block assembly + 1 LLM call (compose --smooth) — generates prompts for humans, not materials

The agent (`agent.py`) only scores and advances existing entries. It never discovers
new ones or generates materials. The daily cycle requires manually running 5+ scripts
in sequence.

## Solution

A unified daily pipeline orchestrator that runs the complete Scan→Match→Build cycle,
with each phase as an independent module that also integrates into the agent.

### Architecture

```
daily_pipeline_orchestrator.py
├── Phase 1: scan_orchestrator.py
│   ├── source_jobs.py (5 ATS APIs: Greenhouse, Lever, Ashby, SmartRecruiters, Workable)
│   ├── discover_jobs.py (3 free APIs: Remotive, Himalayas, TheMuse)
│   └── ingest_top_roles.py (pre-scoring, identity match)
├── Phase 2: match_engine.py
│   ├── text_match.py (TF-IDF corpus matching)
│   ├── score.py (9-dimension rubric)
│   └── auto-qualify (threshold from external calibration)
└── Phase 3: material_builder.py
    ├── Block selection (identity position → best blocks)
    ├── Cover letter generation (google-genai)
    ├── Answer generation (google-genai)
    └── Resume wiring (tailor_resume.py)
```

### Data Flow

```
[8 APIs] → scan_orchestrator → research_pool/*.yaml (new entries)
                                        ↓
                               match_engine → scored + qualified entries
                                        ↓
                              material_builder → draft materials (review gate)
                                        ↓
                               agent.py → advance to staged
```

## Phase 1: Scan Orchestrator

**File:** `scripts/scan_orchestrator.py`

### Responsibilities

1. Call all configured job sources in sequence with rate limiting
2. Deduplicate results across sources AND against existing pipeline entries
3. Apply location filter (US-accessible only), freshness filter (72h default)
4. Write qualifying entries to `pipeline/research_pool/`
5. Log scan statistics to `signals/scan-history.yaml`
6. Return list of new entry IDs

### Interface

```python
def scan_all(
    dry_run: bool = True,
    fresh_only: bool = True,
    max_entries: int = 100,
    sources: list[str] | None = None,  # None = all sources
) -> ScanResult:
    """Run all configured job sources and return results."""

@dataclass
class ScanResult:
    new_entries: list[str]       # IDs of newly created entries
    duplicates_skipped: int
    errors: list[str]
    sources_queried: int
    total_fetched: int
    total_qualified: int
    scan_duration_seconds: float
```

### Implementation Details

- Reuses existing functions: `fetch_greenhouse_jobs()`, `fetch_lever_jobs()`,
  `fetch_ashby_jobs()` from `source_jobs.py`; API adapters from `discover_jobs.py`;
  `pre_score()` from `ingest_top_roles.py`
- Dedup key: `(organization, title, portal_url)` — same as existing `deduplicate()`
- Rate limiting: 2s between API calls (existing `DEFAULT_RATE_DELAY`)
- Max 100 entries per scan (configurable) to prevent research_pool flooding
- Scan history log format:
  ```yaml
  - date: "2026-03-14"
    sources_queried: 8
    total_fetched: 247
    duplicates_skipped: 189
    new_entries: 12
    top_score: 8.7
    duration_seconds: 45.2
  ```

### CLI

```bash
python scripts/scan_orchestrator.py                    # Dry-run, all sources
python scripts/scan_orchestrator.py --yes              # Execute, write entries
python scripts/scan_orchestrator.py --sources ats      # ATS APIs only
python scripts/scan_orchestrator.py --sources free     # Free APIs only
python scripts/scan_orchestrator.py --max 50           # Cap at 50 entries
python scripts/scan_orchestrator.py --json             # Machine-readable output
```

## Phase 2: Match Engine

**File:** `scripts/match_engine.py`

### Responsibilities

1. Score all unscored research entries (auto-trigger, not manual)
2. Run TF-IDF corpus matching for `evidence_match` dimension
3. Auto-qualify entries above calibrated threshold
4. Rank and surface top N daily matches
5. Save daily match results to `signals/daily-matches.yaml`

### Interface

```python
def match_and_rank(
    entry_ids: list[str] | None = None,  # None = all unscored
    auto_qualify: bool = True,
    top_n: int = 10,
    dry_run: bool = True,
) -> MatchResult:
    """Score, rank, and optionally qualify entries."""

@dataclass
class MatchResult:
    scored: list[ScoredEntry]      # All scored entries with dimensions
    qualified: list[str]           # IDs promoted to qualified
    top_matches: list[ScoredEntry] # Top N by composite score
    threshold_used: float          # Auto-qualify threshold (from calibration)

@dataclass
class ScoredEntry:
    entry_id: str
    composite_score: float
    dimensions: dict[str, float]
    text_match_score: float
    identity_position: str
    organization: str
```

### Implementation Details

- Calls `score.py`'s scoring logic directly (imports `compute_score()`)
- Calls `text_match.py`'s `compute_similarity()` for evidence_match
- Auto-qualify threshold loaded from `scoring-rubric.yaml` (calibrated by external_validator)
- Company cap enforcement: max 1 entry per org (existing `check_company_cap()`)
- Daily matches log format:
  ```yaml
  - date: "2026-03-14"
    threshold: 8.5
    entries_scored: 12
    entries_qualified: 3
    top_match:
      id: "anthropic-devex-engineer"
      score: 9.2
  ```

### CLI

```bash
python scripts/match_engine.py                         # Score all unscored, dry-run
python scripts/match_engine.py --yes                   # Execute scoring + qualify
python scripts/match_engine.py --target <id>           # Score single entry
python scripts/match_engine.py --top 20                # Show top 20
python scripts/match_engine.py --no-qualify            # Score only, don't promote
python scripts/match_engine.py --json                  # Machine-readable output
```

## Phase 3: Material Builder

**File:** `scripts/material_builder.py`

### Responsibilities

1. For each qualified entry with incomplete materials:
   a. Select best blocks based on identity position + text match gaps
   b. Generate a cover letter using LLM (google-genai)
   c. Generate answers for custom portal questions using LLM
   d. Wire appropriate base resume for identity position
2. Save all LLM outputs as drafts requiring human approval
3. Log build actions to `signals/build-history.yaml`

### Interface

```python
def build_materials(
    entry_ids: list[str] | None = None,  # None = all qualified missing materials
    components: list[str] | None = None, # None = all; options: cover_letter, answers, resume, blocks
    dry_run: bool = True,
    approve: bool = False,               # True = mark as final, False = draft
) -> BuildResult:
    """Generate application materials for qualified entries."""

@dataclass
class BuildResult:
    entries_processed: list[str]
    cover_letters_generated: int
    answers_generated: int
    resumes_wired: int
    blocks_selected: int
    llm_tokens_used: int
    errors: list[str]

@dataclass
class MaterialDraft:
    entry_id: str
    component: str          # cover_letter, answers, resume, blocks
    content: str
    status: str             # draft | approved
    generated_at: str       # ISO datetime
    model_used: str         # gemini-2.5-pro
    identity_position: str
```

### Cover Letter Generation

Uses google-genai (already a dependency, working in `compose.py --smooth`):

```python
def generate_cover_letter(entry: dict, blocks: list[str], job_posting: str) -> str:
    """Generate a cover letter from blocks + job posting context."""
    # System prompt enforces:
    # - Identity position framing
    # - Storefront rules (lead with numbers, one sentence one claim)
    # - No fabricated metrics (only use what's in blocks)
    # - 400-word target length
    # Uses: entry's identity_position, selected blocks content,
    #        job posting text (from entry's posting_url cache or notes)
```

### Answer Generation

Upgrades `answer_questions.py` from prompt-generation to actual generation:

```python
def generate_answers(entry: dict, questions: list[dict], context: str) -> dict:
    """Generate answers for custom portal questions using LLM."""
    # For each question:
    # - Use cover letter + blocks as context
    # - Respect character/word limits from portal
    # - Match identity position voice
    # Returns: {question_key: answer_text}
```

### Block Selection

```python
def select_blocks(entry: dict, match_result: ScoredEntry) -> dict[str, str]:
    """Select best blocks for an entry based on identity position and gap analysis."""
    # 1. Get identity position from entry
    # 2. Get text_match gaps (keywords in job posting not covered by corpus)
    # 3. Score each block by relevance to gaps
    # 4. Return {slot: block_path} mapping for submission.blocks_used
```

### Safety Rails

- **Review gate**: All LLM outputs saved with `status: draft` by default
- **No hallucination**: System prompts explicitly forbid fabricating metrics
- **Token tracking**: Every LLM call logs model + token count
- **Fallback**: If google-genai unavailable, falls back to prompt generation (existing behavior)
- **Dry-run default**: `--yes` required to write any files

### CLI

```bash
python scripts/material_builder.py --target <id>              # Single entry, dry-run
python scripts/material_builder.py --yes                      # Build all qualified
python scripts/material_builder.py --target <id> --approve    # Build + approve
python scripts/material_builder.py --component cover_letter   # Cover letters only
python scripts/material_builder.py --component answers        # Answers only
python scripts/material_builder.py --json                     # Machine-readable
```

## Integration: Daily Pipeline Orchestrator

**File:** `scripts/daily_pipeline_orchestrator.py`

Chains the three phases:

```python
def run_daily_cycle(
    dry_run: bool = True,
    phases: list[str] | None = None,  # None = all; options: scan, match, build
) -> dict:
    """Run the complete daily Scan → Match → Build cycle."""
    results = {}

    if "scan" in phases:
        scan_result = scan_all(dry_run=dry_run)
        results["scan"] = scan_result

    if "match" in phases:
        entry_ids = scan_result.new_entries if scan_result else None
        match_result = match_and_rank(entry_ids=entry_ids, dry_run=dry_run)
        results["match"] = match_result

    if "build" in phases:
        qualified_ids = match_result.qualified if match_result else None
        build_result = build_materials(entry_ids=qualified_ids, dry_run=dry_run)
        results["build"] = build_result

    return results
```

### CLI

```bash
python scripts/daily_pipeline_orchestrator.py                  # Full cycle, dry-run
python scripts/daily_pipeline_orchestrator.py --yes            # Execute full cycle
python scripts/daily_pipeline_orchestrator.py --phase scan     # Scan only
python scripts/daily_pipeline_orchestrator.py --phase match    # Match only
python scripts/daily_pipeline_orchestrator.py --phase build    # Build only
python scripts/daily_pipeline_orchestrator.py --json           # Machine-readable
```

## Agent.py Enhancement

Add a `--full-cycle` flag to `agent.py` that runs the orchestrator before the
existing score→advance loop:

```python
# In PipelineAgent.plan_actions():
# NEW Phase 0: Scan for new entries
if self.full_cycle and _rule_enabled("daily_scan"):
    scan_result = scan_all(dry_run=self.dry_run)
    # ... log scan results

# Existing phases continue as before
```

New agent rule in `strategy/agent-rules.yaml`:
```yaml
daily_scan:
  enabled: true
  max_entries_per_scan: 100
  sources: all  # or: ats, free
material_build:
  enabled: true
  auto_approve: false  # require human review
```

## Automation

**New LaunchAgent:** `launchd/com.4jp.pipeline.daily-scan.plist`
- Schedule: Daily 5:30 AM (before existing 6:00 AM deferred check)
- Command: `python scripts/daily_pipeline_orchestrator.py --yes --json`
- Logs to: `/Users/4jp/System/Logs/pipeline-daily-scan.log`

**Modified LaunchAgent:** `com.4jp.pipeline.agent-biweekly.plist`
- Add `--full-cycle` flag to existing agent invocation

## CLI / MCP / run.py Integration

| Layer | Command | Maps To |
|-------|---------|---------|
| `run.py` | `scan` | `scan_orchestrator.py` (dry-run) |
| `run.py` | `match` | `match_engine.py` (dry-run) |
| `run.py` | `build` | `material_builder.py` (dry-run) |
| `run.py` | `fullcycle` | `daily_pipeline_orchestrator.py` (dry-run) |
| `cli.py` | `pipeline scan` | With `--yes`, `--sources`, `--max` flags |
| `cli.py` | `pipeline match` | With `--yes`, `--target`, `--top` flags |
| `cli.py` | `pipeline build` | With `--yes`, `--target`, `--component` flags |
| `cli.py` | `pipeline cycle` | With `--yes`, `--phase` flags |
| `mcp_server.py` | `pipeline_scan` | JSON result from scan_all() |
| `mcp_server.py` | `pipeline_match` | JSON result from match_and_rank() |
| `mcp_server.py` | `pipeline_build` | JSON result from build_materials() |

## Files

| File | Action | Lines (est.) |
|------|--------|-------------|
| `scripts/scan_orchestrator.py` | CREATE | ~300 |
| `scripts/match_engine.py` | CREATE | ~350 |
| `scripts/material_builder.py` | CREATE | ~450 |
| `scripts/daily_pipeline_orchestrator.py` | CREATE | ~200 |
| `scripts/agent.py` | MODIFY | +40 |
| `scripts/run.py` | MODIFY | +4 |
| `scripts/cli.py` | MODIFY | +60 |
| `scripts/mcp_server.py` | MODIFY | +45 |
| `launchd/com.4jp.pipeline.daily-scan.plist` | CREATE | ~30 |
| `strategy/agent-rules.yaml` | MODIFY | +8 |
| `tests/test_scan_orchestrator.py` | CREATE | ~250 |
| `tests/test_match_engine.py` | CREATE | ~250 |
| `tests/test_material_builder.py` | CREATE | ~300 |
| `tests/test_daily_pipeline.py` | CREATE | ~150 |

**Total:** 4 new modules, 5 modified files, 4 new test files, 1 new plist

## Dependencies

- **Existing**: PyYAML, google-genai (already in pyproject.toml)
- **No new dependencies**

## Verification

```bash
# After implementation:
python scripts/scan_orchestrator.py                    # Scan dry-run
python scripts/match_engine.py                         # Match dry-run
python scripts/material_builder.py --target <id>       # Build dry-run
python scripts/daily_pipeline_orchestrator.py           # Full cycle dry-run

# Tests:
.venv/bin/python -m pytest tests/test_scan_orchestrator.py tests/test_match_engine.py tests/test_material_builder.py tests/test_daily_pipeline.py -v

# Integration:
python scripts/verification_matrix.py --strict
.venv/bin/ruff check scripts/ tests/
```
