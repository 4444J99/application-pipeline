---
name: Memory parity — local:remote must be 1:1
description: All persistent state (memory files, session transcripts, config) must exist on both local disk and a remote backup simultaneously. If the physical machine dies, the soul persists.
type: feedback
---

Persistent memory MUST be local & remote simultaneously. `(local):(remote) = {1:1}`.

If the physical manifestation dies, the soul persists. Nothing is allowed to be local-only.

**Why:** Session S44 (2026-03-31) discovered 5 memory files that existed on disk but were not synced to chezmoi source (and therefore not pushed to GitHub). If the machine had failed, those 5 memories — including the multi-agent post-mortem and funder-fit lessons — would have been permanently lost. The user's rule: "if lost, recover immediately; this is a rule that MUST be universally contextually applied."

**How to apply:** On every session close:
1. Verify chezmoi source file count matches deployed file count (`diff <(ls chezmoi-source/*.md | sort) <(ls live/*.md | sort)`)
2. If new memory files were created during the session, run `chezmoi add` for each
3. Push to remote (currently requires `LEFTHOOK=0` due to GH#51 ghost hook)
4. The consolidation dream process must also ensure its own outputs are synced

This rule extends beyond memory files — it applies to all persistent state: session transcripts (IRF-DOM-029), config files, any artifact the system cannot regenerate from code alone.
