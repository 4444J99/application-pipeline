# Research Pool Audit — March 19, 2026

## Finding: 902 Hidden Gems in an Unscored Pile

994 entries sat in `research_pool/` at score 0.0 — all auto-sourced by `source_jobs.py`, never evaluated.

After batch scoring:

| Score Range | Count | Meaning |
|------------|-------|---------|
| 9.0+ | 28 | Exceptional fit — should be top priority |
| 8.0-8.9 | 544 | Strong fit — active pipeline candidates |
| 7.0-7.9 | 330 | Above qualify threshold (7.0) |
| 6.0-6.9 | 82 | Below threshold but worth monitoring |
| 5.0-5.9 | 12 | Low fit |
| <5.0 | 13 | Poor fit |

**902 of 994 entries score ≥ 7.0.** These are not garbage — they're gold.

## Cross-Reference with Network

| Category | Entries | Description |
|----------|---------|-------------|
| **Warm path** (≥ 7.0 + contacts at org) | **584** | High-scoring roles at orgs where we have LinkedIn connections |
| **Cold path** (≥ 7.0, no contacts) | **302** | High-scoring but no network access yet |
| **Below threshold** (<7.0) | **108** | Market intelligence only |

## Top Discoveries

### Temporal (20 entries, 15 score 9.0)
Mason Egger + Cecil Phillip both accepted DMs. 20 open roles including Staff Developer Advocate, Staff SWE (AI SDK, Cloud, Traffic, Visibility). This is the single deepest opportunity set in the pipeline.

### Coinbase (6 entries, top 9.1)
3 contacts connected. Roles: Sr SWE Data Platform, Sr SWE Money Movement & Risk (already applied), Staff SWE Frontend.

### Anthropic (64 entries, top 8.9)
3 contacts connected. Roles span: Applied AI Engineer, FDE, Engineering Editorial Lead, UI SWE, Staff SWE Systems, Supply Chain Lead.

### OpenAI (165 entries, top 8.8)
6 contacts connected (Colin Jarvis = Global Head of FDE). 165 roles — the largest single-org opportunity set.

## Root Cause: Broken Intake Pipeline

```
source_jobs.py → dumps into research_pool/ → [NO SCORING STEP] → entries rot
```

The system ingests but never evaluates. Every `source_jobs.py` run should be followed by `score.py --include-pool` to assign scores, then `score.py --auto-qualify` to promote high-scorers to `active/`.

## What NOT To Delete

All 994 entries are observation data — the system's diary of what the market offered. Even sub-threshold entries record:
- Which companies were hiring for what roles
- ATS portal distribution (Ashby 565, Greenhouse 429)
- Role title patterns across 97 unique orgs
- Geographic distribution

**Rule: Never delete observation data. Tag, score, index — but don't destroy the record.**

## Fix: Automated Triage Step

The `source_jobs.py` → `score.py` → `auto-qualify` flow needs to be wired as a single pipeline:

1. `source_jobs.py` ingests new entries → stamps `created_at`
2. `score.py --all --include-pool` scores everything
3. Entries ≥ 7.0 at orgs with contacts → flag as `warm_lead`
4. Entries ≥ 9.0 → auto-promote to `active/qualified`
5. Entries < 5.0 → tag `low_priority` (keep, don't delete)
6. All entries get `last_scored_at` timestamp
