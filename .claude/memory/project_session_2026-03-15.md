---
name: Session 2026-03-15 — Pipeline Activation & Corpus Scoring
description: Major session: freshness gate, scoring recalibration, corpus fingerprint, browser submission, test coverage to 139/139, evaluation-to-growth analysis
type: project
---

## What Was Built (2026-03-15)

### Infrastructure
- **72h freshness gate** — `flush_stale_active_jobs()` in `pipeline_freshness.py`. Runs automatically before standup/morning/campaign. Job entries >72h moved to research_pool.
- **Location filter** — `_is_acceptable_location()` in `score.py`. Only remote or NYC-metro job entries qualify. User priority: remote first, NYC-metro second.
- **Scoring threshold recalibration** — `scoring-rubric.yaml` auto_qualify_min 9.0→7.0. Mathematically derived: 9.0 was impossible with network_proximity at 0.20 weight.
- **Living corpus fingerprint** — `corpus_fingerprint.py`. Reads ALL 126 blocks + 5 base resumes → 3,708 unique terms → TF-IDF vector. Auto-rebuilds every 24h. No hardcoded skills.
- **Corpus-driven scoring** — `score_description_against_corpus()` in `score_text_match.py`. Job descriptions matched against corpus fingerprint. Replaces title-pattern matching as primary scorer.
- **Description fetching** — `source_jobs.py` now fetches full job descriptions from Greenhouse/Lever/Ashby APIs. Stored as `target.description` in entry YAML.
- **Browser submission** — `greenhouse_browser_submit.py`. Playwright fills Greenhouse forms, uploads resume/cover letter. Pauses for reCAPTCHA (human-in-loop).
- **Org cap fix** — `check_company_cap()` now only counts active-pursuit statuses, not research_pool.
- **Title scoring fix** — disqualifiers (marketing, android, hardware, etc.) checked before positive matches.

### Test Coverage
- **139/139 modules covered** (was 134/139)
- New test files: test_classify_position (168 tests), test_derive_positions (43), test_refresh_from_ecosystem (80), test_enrich_prestige (14), test_greenhouse_browser_submit (13), test_corpus_fingerprint (7), test_score_text_match (4)
- 508+ tests passing across all modified/new files

### Application Submitted
- **Anduril Lead Technical Writer, Intelligence Systems** — confirmed via browser automation. Tailored resume (Documentation Engineer framing), cover letter, all fields filled.

### Known Issues
- Description fetching is slow (100ms per job × hundreds of filtered jobs). Needs batch/async optimization.
- `sim_to_score()` thresholds calibrated from limited data — need tuning after first corpus-scored batch.
- agentic-titan test count discrepancy: blocks say 1,095, resumes say 1,276.
- Follow-up protocol has 0 logged actions across 25 submissions.

### Evaluation-to-Growth Finding
0% conversion from 25 cold submissions. The pipeline optimizes application quality but the strategy (cold apply to posted jobs) doesn't work. Structural shift needed toward relationship-first workflow.

**How to apply:** Next session should (1) optimize description fetching speed, (2) source + score a corpus-driven batch, (3) begin follow-up actions on the 8 live submitted entries.
