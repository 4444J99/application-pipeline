# Massive Source Pool Expansion + 3-Per-Company Cap Enforcement

## Context

The sourcing pool is too small (43 companies) and too concentrated (top 3 = 38% of entries). The user requires:
1. **150+ companies** in `.job-sources.yaml` across Greenhouse, Ashby, and Lever ATS platforms
2. **Hard cap of 3 active+submitted entries per company** — enforced at promotion, advance, and submission time

## Phase 1: Shared Cap Infrastructure (`pipeline_lib.py`)

Add to `scripts/pipeline_lib.py`:

```python
COMPANY_CAP = 3  # Max active+submitted entries per organization

def company_entry_counts(entries: list[dict], actionable_only: bool = True) -> dict[str, int]:
    """Count entries per organization. If actionable_only, only count active+submitted statuses."""
    counts: dict[str, int] = {}
    for entry in entries:
        org = (entry.get("target") or {}).get("organization", "Unknown")
        if actionable_only:
            status = entry.get("status", "")
            # Count research_pool entries too since they can be promoted
            if status in ("closed", "expired", "withdrawn"):
                continue
        counts[org] = counts.get(org, 0) + 1
    return counts

def check_company_cap(org: str, entries: list[dict], cap: int = COMPANY_CAP) -> tuple[bool, int]:
    """Check if an organization is under the cap. Returns (allowed, current_count)."""
    count = 0
    for entry in entries:
        entry_org = (entry.get("target") or {}).get("organization", "")
        entry_status = entry.get("status", "")
        if entry_org == org and entry_status not in ("closed", "expired", "withdrawn", "rejected"):
            count += 1
    return count < cap, count
```

**Files:** `scripts/pipeline_lib.py` — ~25 new lines

## Phase 2: Cap Enforcement Points

### 2a — `ingest_top_roles.py` promote loop (~line 300)

Before writing a promoted entry to `pipeline/active/`, check the cap:

```python
from pipeline_lib import check_company_cap, COMPANY_CAP, load_entries, ALL_PIPELINE_DIRS

all_entries = load_entries(ALL_PIPELINE_DIRS)
# In the promote loop:
allowed, current = check_company_cap(org_name, all_entries)
if not allowed:
    print(f"  SKIP {entry_id}: {org_name} at cap ({current}/{COMPANY_CAP})")
    continue
```

**Files:** `scripts/ingest_top_roles.py` — ~10 lines added to promote loop

### 2b — `advance.py` candidate filtering (~line 225)

When advancing entries to `staged` or `submitted`, check the cap:

```python
from pipeline_lib import check_company_cap, COMPANY_CAP

# After existing filters in run_advance():
if target_status in ("staged", "submitted"):
    org = (entry.get("target") or {}).get("organization", "")
    allowed, current = check_company_cap(org, all_entries)
    if not allowed:
        skipped.append(f"{entry_id} — {org} at cap ({current}/{COMPANY_CAP})")
        continue
```

**Files:** `scripts/advance.py` — ~8 lines added

### 2c — `hygiene.py` company focus section (~line 488)

Replace hardcoded `DEFAULT_FOCUS_LIMIT = 3` with shared constant:

```python
from pipeline_lib import COMPANY_CAP
# Replace DEFAULT_FOCUS_LIMIT with COMPANY_CAP
```

**Files:** `scripts/hygiene.py` — ~3 lines changed

## Phase 3: Expand `.job-sources.yaml` to 150+ Companies

**Current state:** 25 Greenhouse + 18 Ashby + 0 Lever = 43 total. Several companies already tried and commented out with reasons (no public API, HTML-only board, acquired). Lever section is empty ("all migrated to Greenhouse or Ashby").

**Approach:** Two-pass strategy:
1. **Compile candidate list** of ~200 companies across Greenhouse + Ashby (skip Lever — confirmed dead)
2. **Verification script** (`scripts/verify_sources.py`) — hits each API endpoint with a HEAD/GET request, reports which slugs return valid JSON. Run once, add working slugs, comment out failures with reason.

### Verification script (`scripts/verify_sources.py`, NEW, ~60 lines)

```python
# For each candidate slug:
#   Greenhouse: GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs → 200 = valid
#   Ashby: POST https://api.ashbyhq.com/posting-api/job-board/{slug} → 200 = valid
# Output: YAML-ready list of working slugs + failure report
```

This is run once during implementation to validate candidates before adding them. Not a recurring pipeline script.

### Greenhouse candidates (~80 new slugs to test)

Current: 25 → Target: ~85 (after verification filtering)

**AI/ML:** huggingface, mistralai, databricks, anyscale, weightsandbiases, labelbox, snorkelai, allenai, adeptai, inflectionai, midjourney, jasperai, writesonic, copyai, lightningai, modallabs, replicate, stability, deepmind, cohereai

**Infrastructure/Platform:** cockroachlabs, timescaledb, singlestore, apollographql, hasura, prismaio, aiabornedata, fivetran, prefectio, dagsterio, mabornedata, mux, imgix, fastly

**Developer Tools:** postman, gitpod, circleci, buildkite, sentryio, zabornedindustries, codeium, tabnine, gitpod

**Growth-Stage Tech:** plaid, brex, mercury, rippling, gusto, lattice, deel, remotehq, oysterhr, justworks

**Fintech/Infra:** coinbase, robinhood, affirm, marqeta, lithic, unit, moov, moderntreasury, column, svb

**Enterprise AI:** palantir, c3ai, dataminr, relativity, h2oai, datarobot

**Media/Content AI:** spotify, soundcloud, shutterstock, getty, adoberesearch

**Healthcare/Govtech:** veradigm, palantir, anduril

**Note:** Many of these will 404 — the verification script will filter. Expect ~50-60% hit rate based on existing commented-out failures.

### Ashby candidates (~50 new slugs to test)

Current: 18 → Target: ~50 (after verification filtering)

**AI/ML:** stabilityai, glean, sierraai, harveyai, cognitionlabs, magicdev, poolsideai, pikalabs, lumaai, mistral, cerebras, fireworksai, groq, deno, valtown (re-test — some may have migrated to Ashby since last check)

**Infrastructure:** clerk, convex, turso, upstash, axiom, tinybird, motherduck, clickhouse, duckdblabs, qdrant, weaviate, pinecone, chroma

**Developer Tools:** calcom, twenty, hoppscotch, pieces, zed

**Growth-Stage:** mercury, ashby (meta!), liveblocks, inngest, trigger, unkey

### Display name mapping (`source_jobs.py`)

Add entries to `COMPANY_DISPLAY_NAMES` for each verified slug. Only add verified working slugs.

**Files:** `scripts/source_jobs.py` `COMPANY_DISPLAY_NAMES` dict — entries for all verified slugs

### Prestige updates (`score.py`)

Add notable new companies to `HIGH_PRESTIGE` dict with appropriate tier scores:

- Tier 10: DeepMind
- Tier 9: Databricks, Plaid, Coinbase, Palantir
- Tier 8: Hugging Face, Mistral, Weights & Biases, Robinhood, Affirm, Anduril
- Tier 7: Brex, Mercury, Rippling, Prefect, Dagster, Sentry (if verified)
- Tier 6: Airbyte, Fivetran, Postman, Gusto, Lattice, Deel

**Files:** `scripts/score.py` `HIGH_PRESTIGE` dict — entries for verified notable companies

## Phase 4: Tests

### `tests/test_company_cap.py` (~50 lines)

- Test `company_entry_counts()`: correct counting, excludes closed/expired
- Test `check_company_cap()`: returns (True, n) when under cap, (False, 3) when at cap
- Test cap enforcement in promote context: mock entries, verify skip when at cap
- Test edge cases: missing organization field, empty entries list

### Extensions to existing tests

- `tests/test_ingest_top_roles.py` — add test for cap-skip behavior in promote loop
- `tests/test_advance.py` — if exists, add test for cap-skip at staged/submitted transition

**Files:** `tests/test_company_cap.py` (NEW, ~50 lines)

## Phase 5: Wire into `run.py`

Add a `sourcecap` command to show company concentration:

```python
"sourcecap": ("pipeline_lib.py", [], "Show company entry counts vs cap")
```

Or better: add `--cap-report` flag to an existing script. The `hygiene.py` company focus section already reports this — just ensure it uses the shared constant.

## Files Modified (Summary)

| File | Change |
|------|--------|
| `scripts/pipeline_lib.py` | +~25 lines (COMPANY_CAP, company_entry_counts, check_company_cap) |
| `scripts/ingest_top_roles.py` | +~10 lines (cap check in promote loop) |
| `scripts/advance.py` | +~8 lines (cap check at staged/submitted) |
| `scripts/hygiene.py` | ~3 lines (use shared COMPANY_CAP) |
| `scripts/verify_sources.py` | NEW (~60 lines, one-time verification utility) |
| `scripts/.job-sources.yaml` | +~100-130 new company entries (Greenhouse + Ashby, post-verification) |
| `scripts/source_jobs.py` | Display name entries for all verified slugs |
| `scripts/score.py` | HIGH_PRESTIGE entries for verified notable companies |
| `tests/test_company_cap.py` | NEW (~50 lines) |

## What We Do NOT Change

- No changes to scoring formula or dimension weights
- No changes to existing pipeline entry YAMLs
- No changes to enrichment, compose, or submission scripts
- No changes to freshness, backfill, or profile generation (just completed)
- No changes to feedback_capture or hypothesis logic

## Verification

```bash
source .venv/bin/activate

# Lint
ruff check scripts/ tests/

# Tests
python -m pytest tests/ -v

# Validate pipeline YAML
python scripts/validate.py

# Verify candidate slugs (one-time)
python scripts/verify_sources.py                   # Tests all candidate slugs, outputs working list

# Source expansion
python scripts/source_jobs.py --fetch --dry-run   # Should show jobs from 150+ companies

# Cap enforcement smoke test
python scripts/run.py topjobs                      # Fetch + promote respecting cap

# Company concentration check
python scripts/run.py hygiene                      # Company focus section

# Full pipeline integrity
python scripts/run.py preflight
```

## Execution Order

1. Phase 1: Shared cap utilities in `pipeline_lib.py`
2. Phase 2a-c: Cap enforcement in ingest, advance, hygiene
3. Phase 3a: Write `verify_sources.py` + compile candidate slug list
4. Phase 3b: Run verification, filter to working slugs
5. Phase 3c: Add verified slugs to `.job-sources.yaml` + display names + prestige
6. Phase 4: Tests
7. Full verification pass (lint, tests, validate, dry-run fetch)

**Note:** There are also uncommitted changes from the previous session (20 rolled-back entries, 5 new promotions, cleaned hypotheses) that should be committed before starting this work.
