---
name: Session Arc 2026-03-31
description: CLAUDE.md compression from 43.7k to 27.6k chars — eliminated performance warning, preserved all behavioral rules
type: project
---

CLAUDE.md compressed from 43,749 → 27,580 chars (37% reduction, 12.4k headroom below 40k threshold).

**Why:** Claude Code loads the full CLAUDE.md into every conversation's context window. At 43.7k chars it exceeded the 40k performance threshold, degrading response quality and wasting ~11k tokens per conversation before any work began.

**How to apply:** The compression taxonomy is reusable — separate behavioral rules (not derivable from code) from reference material (derivable from code). Reference material compresses into tables or gets deleted. Behavioral rules stay untouched.

**What changed:**
- Commands + Quick Commands + CLI vs Raw Scripts → single unified 3-column table (saved ~7,700 chars)
- Script Dependency Graph → import relationship table + 9 non-obvious script notes (saved ~5,300 chars)
- Architecture, Config Files, Makefile, Conventions, Module Architecture → tighter formatting (saved ~3,100 chars)
- Completion Summaries folded into Conventions as a bullet
- `daily_batch.py` deprecation notice removed (months stale)

**What preserved (unchanged):**
All behavioral rules, all identity content (9 positions, 3 pillars, state machine), all academic context (SGO, IRA, thesis), Pipeline Philosophy, Canonical Application Flow, Resume Workflow, Key ID Mapping, Greenhouse Integration, CI & Linting, Dependencies, Testing Patterns, Automation.

**Verification:** 134/135 tests pass (1 pre-existing rubric validation failure unrelated to changes). No cross-reference breakage. Plan archived at `.claude/plans/2026-03-31-claude-md-compression.md`.
