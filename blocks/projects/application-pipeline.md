---
title: "Application Pipeline — Career Infrastructure CLI"
category: projects
tags: [python, testing, automation, cli, yaml, state-machine, ci-cd, developer-tools, analytics, ats]
identity_positions: [independent-engineer, creative-technologist]
tracks: [job]
related_projects: [organvm-system, agentic-titan, recursive-engine]
tier: full
---

# Project: Application Pipeline — Career Infrastructure CLI

## One-Line

37-script Python CLI suite managing career applications as a structured conversion pipeline: YAML state machine, 8-dimension scoring rubric, Greenhouse/Lever/Ashby ATS integrations, and 700+ tests.

## Short (60s)

A production-grade personal career management system: 37 scripts sharing a common library (`pipeline_lib.py`), a 9-status YAML state machine with forward-only enforcement, an 8-dimension weighted scoring rubric with dual weight sets (creative vs. job tracks), and native API integrations for Greenhouse, Lever, and Ashby portals using stdlib urllib. Tested with 700+ pytest cases operating on real pipeline data — no mocking, no test doubles. This is not a demo. It is operational infrastructure managing 100+ active applications across five tracks (job, grant, residency, prize, writing).

## Full

**What it is:** A personal career management system implemented as production-grade Python infrastructure — the same kind of internal tooling a platform team might build for a recruiting operation, but designed, tested, and maintained by a single practitioner.

**Architecture:**

- **State machine:** 9-status pipeline (`research → qualified → drafting → staged → submitted → acknowledged → interview → outcome`, plus `deferred`) with forward-only progression enforced by `advance.py` and schema validation
- **Scoring rubric:** 8-dimension weighted model (`mission_alignment`, `evidence_match`, `track_record_fit`, `financial_alignment`, `effort_to_value`, `strategic_value`, `deadline_feasibility`, `portal_friction`) with separate weight sets for creative vs. job tracks — auto-computed from YAML fields, no gut-feel input
- **Content composition model:** Three-tier block library (60s/2min/5min/cathedral) referenced by path in pipeline YAML, with fallback chain to profile JSON content and legacy submission scripts
- **ATS integrations:** Native API integrations for Greenhouse, Lever, and Ashby portals using stdlib `urllib` only — no external HTTP dependencies. Scrapes portal fields, auto-populates answers, handles multipart form submission.
- **Campaign orchestrator:** Deadline-aware batch execution — `campaign.py` computes urgency tiers across a configurable day window and drives `enrich → advance → preflight → submit` as a pipeline
- **Analytics layer:** Conversion funnel analytics by track/position/channel, A/B variant tracking, outcome hypothesis capture (`feedback_capture.py`), stale-submission alerts, and follow-up scheduling
- **Enrichment automation:** Auto-wires resume variants, block references, cover letter variants, and portal fields based on entry metadata and identity-position rules

**Engineering signals:**

- 37 scripts with shared foundation in `pipeline_lib.py` — no copy-paste, single source for path constants, entry loading, YAML manipulation utilities
- 700+ tests (pytest) operating on real pipeline data — actual YAML files, actual block directories, actual profiles — no mocking framework
- YAML schema validation on all pipeline entries via `validate.py`; schema defined in `_schema.yaml`
- CI via GitHub Actions: ruff lint, schema validation, pytest on Ubuntu / Python 3.12
- No external runtime dependencies beyond PyYAML — ATS submitters use only stdlib urllib

**Why it matters for an engineering role:** This project demonstrates the same discipline applied throughout the ORGANVM system — test coverage on real data, state machine design with validation, modular architecture with shared library, validation-first development — applied to a domain with real stakes and real time pressure. The pipeline codebase is public and linked from the resume; test counts and script architecture are verifiable.

## Links

- GitHub: https://github.com/4444j99/application-pipeline
- Resume project entry: "Application Pipeline — CLI Tooling Suite"
