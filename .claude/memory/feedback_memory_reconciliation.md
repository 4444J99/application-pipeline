---
name: Memory triggers reconciliation, not recitation
description: When memory is loaded, verify every claim against current state before presenting. Memory is a hypothesis, not a fact. Render reality first.
type: feedback
---

Memory is a point-in-time snapshot. Presenting it to the user without verification is worse than not having it — it creates false confidence in stale state.

**Why:** Session S45 opened with a status overview that presented 11-day-old LinkedIn items as "hanging" without checking whether any had been completed, files had changed, or the landscape had shifted. The user correctly flagged this as a failure mode.

**How to apply:**
1. When memory claims "X is not done" — verify X is still not done (check files, git log, current state)
2. When memory claims "file exists at path" — read the file, confirm it's there and hasn't changed
3. When memory claims a count or metric — recompute it
4. Present the DELTA between memory-state and current-state, not the memory itself
5. Memory is a search index for what to verify, not a source of truth to recite
6. The sequence is: load memory → identify claims → verify each against reality → present reconciled state
