# Plan: Compress CLAUDE.md Below 40k Threshold

## Context

The project CLAUDE.md at `application-pipeline/CLAUDE.md` is 43,749 chars — 3,749 over the 40k performance threshold. Claude Code loads this file into every conversation's context window, so oversized CLAUDE.md directly degrades response quality and wastes tokens. The file has grown into a full reference manual; the compression restores it to a strategic guidance document.

**Target:** ~29,000 chars (~11k headroom for future growth)

## Diagnosis

Three sections account for **47% of the file** (20,435 chars) and are almost entirely derivable from the code:

| Section | Chars | % | Problem |
|---------|-------|---|---------|
| Script Dependency Graph | 8,079 | 18.5% | Prose descriptions of 25+ scripts; duplicates Commands section |
| Commands | 7,534 | 17.2% | Verbose code blocks with inline comments |
| Quick Commands | 4,822 | 11.0% | Table that overlaps almost completely with Commands |

No content duplication exists with ancestor CLAUDE.md files (`~/CLAUDE.md`, `~/Workspace/CLAUDE.md`, `~/Workspace/4444J99/CLAUDE.md`).

## Strategy: Compress Reference Material, Preserve All Behavioral Rules

### Sections to preserve UNCHANGED
- What This Is, Three-Pillar Model, Canonical Application Flow, Pipeline Philosophy
- Pipeline State Machine, Identity Positions, Content Composition Model
- Resume Workflow, Key ID Mapping, Greenhouse Integration
- Academic & Institutional Context, Relationship to Corpus
- CI & Linting, Dependencies, Testing Patterns, Automation (LaunchAgent)

These contain behavioral rules, identity content, or pipeline constraints that cannot be derived from the code.

---

## Step 1: Merge Commands + Quick Commands → single "Commands" section

**Files:** `CLAUDE.md` lines 215–407

Replace both sections with a unified section:

1. **Intro paragraph** (3 lines): explain three interfaces (`run.py`, `pipeline` CLI, MCP), link to `--help`
2. **Categorized compact table** with columns: `| Command | Script | Key Flags |`
   - Group by workflow: Daily, Pipeline, Composition, ATS, Analytics, Triage, Calendar, Relationships, Validation, Diagnostics, Network, Infrastructure, Tests
   - Each row: quick command alias + script name + 1-2 most important flags
   - ~55 rows at ~80 chars avg = ~4,400 chars
3. **Parameterized commands** line (preserved from line 393)
4. **Session sequences** block (preserved from lines 395–407, ~600 chars)

Also fold "CLI vs Raw Scripts" (lines 442–451) into the intro paragraph.
Also fold "Completion Summaries" (lines 209–214) into Conventions as a bullet.

**Expected savings:** ~7,300 chars (12,356 → ~5,050)

---

## Step 2: Restructure Script Dependency Graph → import table + brief notes

**Files:** `CLAUDE.md` lines 134–174

Replace 41 lines of prose with two compact parts:

**Part A — Import relationship table (~1,200 chars):**
One statement that `pipeline_lib.py` is the shared foundation (every script imports it), then a table of the 12 cross-script import relationships:

| Script | Imports From |
|--------|-------------|
| `campaign.py` | `enrich.py` |
| `alchemize.py` | `greenhouse_submit.py` |
| `hygiene.py` | `source_jobs.py` |
| `submit.py` | `check_metrics.py` |
| `interview_prep.py` | `org_intelligence.py`, `skills_gap.py` |
| `recalibrate.py` | `score.py` |
| `diagnose.py` | `launchd_manager.py` |
| `generate_ratings.py` | `diagnose.py` |
| `standards.py` | `diagnose.py`, `diagnose_ira.py`, `audit_system.py` |
| `external_validator.py` | `pipeline_market.py` |
| `score_network.py` | `network_graph.py` |
| `protocol_validator.py`, `dm_composer.py` | `protocol_types.py` |

**Part B — Non-obvious scripts (~1,500 chars):**
One-sentence notes ONLY for scripts whose behavior is non-obvious and not covered in the Commands table:
- `pipeline_lib.py` — shared foundation: `load_entries()`, `load_profile()`, `load_block()`, path constants, ID maps
- `protocol_validator.py` — validates against 7 formal articles (P-I through P-VII)
- `reconcile_outreach.py` — LinkedIn DM parsing (anchors on "Open the options list" line)
- `network_graph.py` — BFS/DFS path-finding, Granovetter weak-ties hop-decay scoring
- `recruiter_filter.py` — canonical metrics single source of truth; `--fix` propagates to base resumes
- `diagnose_ira.py` — ICC, Cohen's kappa, Fleiss kappa; `partition_dimensions()` separates objective/subjective
- `feedback_capture.py` — writes hypotheses to `signals/hypotheses.yaml`
- `log_dm.py` — single-command DM logging across all 3 signal files
- `standards.py` — 5-level oversight, triad regulators, ≥2/3 quorum; wired into `apply.py` as Level 1 gate

Remove the duplicate `apply.py` entry (line 171 — already fully described in Canonical Application Flow).
Remove the duplicate `standards.py` entry (line 173 — duplicate of line 162).

**Expected savings:** ~5,280 chars (8,079 → ~2,800)

---

## Step 3: Compress secondary sections

### Architecture (lines 62–91) → save ~1,000 chars
- Keep top-level directory listing, compress sub-descriptions
- Remove block frontmatter field lists, profile counts, obvious subdirectory names (`cvs/`, `headshots/`)
- Remove "33 files" memory count

### Configuration Files (lines 408–423) → save ~680 chars
- Shorten descriptions to `<purpose> (loaded by <script>)` format
- Remove scoring-rubric dimensional breakdown (already in Three-Pillar Model)

### Makefile (lines 452–476) → save ~550 chars
- Convert to compact table: `| Target | Purpose |`
- Combine ecosystem/feedback targets into summary lines

### Conventions (lines 506–519) → save ~280 chars
- Remove `daily_batch.py` deprecation notice (months old)
- Add Completion Summaries bullet (folded from its own section)

### Module Architecture (lines 176–189) → save ~200 chars
- Keep table, remove explanatory paragraph at line 189

---

## Projected Result

| Section | Before | After | Saved |
|---------|--------|-------|-------|
| Commands + Quick Commands + CLI | 12,755 | 5,050 | **7,705** |
| Script Dependency Graph | 8,079 | 2,800 | **5,279** |
| Architecture | 2,641 | 1,600 | **1,041** |
| Config Files | 1,678 | 1,000 | **678** |
| Makefile | 1,253 | 700 | **553** |
| Conventions + Completion Summaries | 1,545 | 1,150 | **395** |
| Module Architecture | 1,126 | 926 | **200** |
| **Total savings** | | | **~15,850** |
| **Projected final size** | 43,749 | **~27,900** | |

~12,100 chars of headroom below 40k threshold.

## What NOT to do
- Do NOT create separate reference docs (Minimal Root philosophy)
- Do NOT remove behavioral rules (rules are ADDITIVE)
- Do NOT compress Identity Positions, Academic Context, or Pipeline Philosophy
- Do NOT use HTML comments or collapsed sections (raw text is processed)

## Implementation Order
1. Merge Commands + Quick Commands (biggest win, cleanest edit)
2. Restructure Script Dependency Graph
3. Compress secondary sections (Architecture, Config, Makefile, Conventions, Module Architecture)
4. Fold Completion Summaries into Conventions; fold CLI vs Raw Scripts into Commands intro

## Verification
1. `wc -c CLAUDE.md` — confirm under 35k chars
2. Read compressed file end-to-end to verify no behavioral rules lost
3. `grep -r "CLAUDE.md" docs/ scripts/` — confirm no broken cross-references
4. `make test-fast` — smoke test (pipeline_lib, validate, run, cli tests)
5. Start a new Claude Code conversation in the repo — verify warning is gone
