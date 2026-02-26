# GEMINI.md

This file provides foundational instructional context for Gemini CLI interactions in the `application-pipeline` repository.

## Project Overview
A career application infrastructure that treats the job and grant search as a structured **conversion pipeline**. It implements a **"Cathedral → Storefront"** philosophy: preserving deep, immersive systemic work (Cathedral) while providing high-signal, scannable entry points (Storefront) for reviewers.

### Core Architecture
- **Pipeline State Machine**: Applications move through `research → qualified → drafting → staged → submitted → acknowledged → interview → outcome`.
- **Modular Content**:
  - `blocks/`: Atomic, reusable narrative units with tiered depth (60s, 2min, 5min, cathedral).
  - `variants/`: A/B tracked versions of materials (cover letters, project descriptions).
  - `targets/profiles/`: Target-specific data including pre-written statements and work samples.
- **Eight-Organ System Integration**: All metrics and evidence derive from the canonical `organvm-corpvs-testamentvm` corpus (Theoria, Poiesis, Ergon, Taxis, Logos, Koinonia, Kerygma, Meta).

## Key Workflows & Commands

### 1. Daily Management
- **Daily Standup**: `python scripts/standup.py` (Must run at start of every session).
- **Status Check**: `python scripts/pipeline_status.py` (High-level dashboard).
- **Triage Stale Entries**: `python scripts/standup.py --triage`.

### 2. Submission Generation
- **Drafting from Profiles**: `python scripts/draft.py --target <id>` (Assembles portal-ready drafts).
- **Composing from Blocks**: `python scripts/compose.py --target <id> --snapshot` (Snapshots final documents).
- **Alchemy Suite**: `python scripts/alchemize.py --target <id>` (End-to-end Greenhouse orchestrator: intake → research → map → synthesize).

### 3. Pipeline Advancement
- **Scoring**: `python scripts/score.py --target <id>` (8-dimension weighted rubric).
- **Advancement**: `python scripts/advance.py --to <status> --id <id>` (Enforces forward transitions).
- **Enrichment**: `python scripts/enrich.py --all --yes` (Wires resumes, blocks, and variants).

### 4. Validation & Submission
- **Validation**: `python scripts/validate.py` (Ensures YAML integrity and valid status transitions).
- **Submission Recording**: `python scripts/submit.py --target <id> --record` (Generates checklist and logs submission).

## Development & Content Conventions

### Identity Framing
Always apply one of the five canonical **Identity Positions** defined in `strategy/identity-positions.md`:
1. **Systems Artist**: For art grants/residencies ("Governance IS the artwork").
2. **Educator**: For academic/education fellowships (Teaching as practice).
3. **Creative Technologist**: For tech grants/consulting (Production-grade orchestration).
4. **Community Practitioner**: For identity/precarity-specific funding (Lived experience of precarity).
5. **Independent Engineer**: For AI lab/infra roles (Scale, testing, CI/CD).

### Content Rules (Storefront Playbook)
- **Lead with Numbers**: "103 repositories," "2,349 tests," "810K+ words."
- **One Sentence, One Claim**: Maintain scannability for 60-second reviews.
- **Preemptive Framing**: Address gaps (e.g., lack of awards) as deliberate trajectory.

### Technical Integrity
- **YAML Schema**: Strictly follow `pipeline/_schema.yaml`.
- **Status Transitions**: Follow the graph in `CLAUDE.md`. Transitions must be forward-only unless moving to `deferred`.
- **Deadline Prioritization**: 
  - Remind user when a deadline is within **14 days**.
  - Heavily prioritize/flag as urgent when within **7 days**.

## Dependencies
- **Python 3.11+** (scripts use `pyyaml`).
- **Source of Truth**: Always sync metrics from `organvm-corpvs-testamentvm/docs/applications/00-covenant-ark.md`.
