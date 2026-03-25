---
name: Log tool fixes as they happen
description: When fixing bugs or building tools, log what was fixed/built to the appropriate signal files. Don't silently fix things — the system needs to know what changed and why.
type: feedback
---

When fixing tools, building new modules, or backfilling data, log the action to the appropriate signal/tracking files. The system's diary must reflect what happened.

**Why:** The reconcile_outreach.py parser was built with bugs (contact misattribution) and backfill was done manually instead. Without logging this, the next session won't know the parser needs fixing or that 8 DMs were backfilled manually.

**How to apply:** After any tool fix, data backfill, or system change: (1) commit with descriptive message, (2) if the fix is incomplete or the tool has known bugs, note it in the commit AND in a memory/project record so it's visible next session.
