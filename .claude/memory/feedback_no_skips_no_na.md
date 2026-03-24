---
name: No skips, no N/A, no "no action" — water constantly flowing
description: Every index check must produce an action or a logged vacuum. "SKIP" and "N/A" are forbidden — they are vacuums disguised as decisions. Research it, plan it, log it.
type: feedback
---

Never mark an index check as SKIP, N/A, or NO ACTION. Every check must produce one of:
- **DONE** — the propagation was executed
- **VACUUM** — a gap was found, researched, and logged as a new IRF item

**Why:** The user's principle is "N/A is a vacuum." Every time something is marked as not applicable, it means there's work that should exist but doesn't. The system is water — it flows into every gap, it doesn't skip over them. Three times in this session, "N/A" items were audited and all turned out to be real work. Three times, "DEFERRED" items had fake blockers. Once, a "SKIP" on concordance turned out to need 9 IRF items, 2 milestones, and 6 named entities registered.

**How to apply:** On every 10-index propagation check:
1. For each index, ask: "What SHOULD exist here as a result of this work?"
2. If something should exist and doesn't → execute it or log it as IRF
3. If genuinely nothing could possibly exist → explain WHY in one sentence (not just "skip")
4. Never use the words SKIP, N/A, or NO ACTION in a propagation table
