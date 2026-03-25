---
name: IRA raters — break evidence for small models, never send full CLAUDE.md to Haiku
description: When running multi-model IRA ratings, break evidence into chunks for smaller models. Haiku cannot hold the full CLAUDE.md + scripts context. Use Sonnet minimum for all raters, or split evidence into targeted sections per dimension.
type: feedback
---

When running subagent-based IRA ratings, smaller models (Haiku) fail on context length when given the full CLAUDE.md + script sampling task. The CLAUDE.md alone is ~700 lines.

**Why:** Session 2026-03-25 — Haiku rater failed with "Prompt is too long." The other 3 raters (Opus, Sonnet x2) succeeded. The Haiku failure meant Architecture and Documentation each got only 1 rating instead of 2, weakening the IRA consensus.

**How to apply:**
1. Never send full CLAUDE.md to Haiku. Either use Sonnet minimum for all raters, or extract only the relevant CLAUDE.md sections per dimension.
2. If using Haiku, break the task into smaller pieces: read CLAUDE.md in one call, sample scripts in separate calls, then synthesize.
3. Better: use 4 Sonnet raters with different persona prompts. The model tier diversity (Opus/Sonnet/Haiku) is less valuable than actually getting ratings from all raters.
4. Alternative: pre-extract evidence into a summary file, then send the summary to all raters regardless of model size.
