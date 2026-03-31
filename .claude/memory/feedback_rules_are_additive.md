---
name: Rules are ADDITIVE — new rules amend, never overwrite
description: Hard-won lesson from 2026-03-26. When new rules were written, old rules (550-700 word count, base-not-output) were forgotten. Rules must accumulate, never replace. The unified rules file must contain ALL rules, not just the latest.
type: feedback
---

New rules AMEND existing rules. They never replace them. Every rule ever established remains in force unless explicitly revoked by the user.

**Why:** On 2026-03-26, new feedback rules about identity (ORGANVM), format parity, and project diversity were written. In the process, the original rules from 2026-03-20 were forgotten: cover letter word count (550-700), dual output via build_cover_letters.py, fix bases not outputs. The result: cover letters came out at 300-385 words (half a page), and output files were patched directly instead of fixing base templates. Three sessions of work were wasted fixing what should never have broken.

**How to apply:**
1. Before writing ANY new feedback rule, read ALL existing feedback_*.md files first
2. The unified rules file (`feedback_resume_cover_letter_quality_2026-03-26.md`) must contain ORIGINAL + AMENDMENTS sections
3. When a new rule is added, explicitly state which existing rules it EXTENDS, not which it replaces
4. The Materials Protocol formalization (`materials_validator.py`) is the code-level enforcement — if a rule isn't in the validator, it will be forgotten again
5. If two rules conflict, flag it as a VACUUM and ask the user to resolve — never silently choose one over the other
