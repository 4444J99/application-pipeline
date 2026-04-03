---
name: Session Handoff Protocol
description: Every session close must produce a handoff file that makes the next Claude instance functionally equivalent to the current one. The avalanche (task chain) is separate from the handoff (context cascade).
type: feedback
---

Every session that produces non-trivial work MUST write a handoff file before closing.

**Why:** Claude instances don't share conversation memory. The next instance starts cold — it has CLAUDE.md, memory files, and repo state, but NOT the decisions, user emotional state, hanging context, or strategic frame from the prior session. Without a handoff, the next instance rebuilds context from scratch, losing momentum and misreading intent.

**How to apply:**

Write `.claude/plans/{date}-session-handoff-{session-id}.md` containing:

1. **What Happened** — 2-3 sentences. What was the session about.
2. **User State** — emotional/strategic frame. What energy the user is bringing. What they corrected. What frame the next session must carry.
3. **Decisions Made** — numbered list. What was decided, not just what was done.
4. **Artifacts Created** — table: path, status (committed/uncommitted/draft).
5. **Hanging Actions** — table: action, owner, blocking?, due date.
6. **What the Next Session Must Know** — numbered list. The 5-7 things that, if the next Claude doesn't know them, will cause it to waste time or misread intent.

The handoff is NOT a summary. It's a **context injection** — the minimum document that transforms a cold Claude into a warm one.

The handoff is NOT the avalanche. The avalanche is a task chain (what to DO next). The handoff is a state transfer (what to KNOW next). They are siblings, not the same thing.
