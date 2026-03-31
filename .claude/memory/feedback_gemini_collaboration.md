---
name: Gemini CLI collaboration — when to use, when to avoid
description: Gemini CLI tested 2026-03-26. Net negative for this repo. No access to persistent memory means it violates rules it can't see. Use only for isolated stateless tasks.
type: feedback
---

Gemini CLI was tested for application pipeline work on 2026-03-26. Assessment: net negative for this specific repo.

**What Gemini did well:**
- Logged batch 1 submissions (contacts, outreach, entry status updates)
- Found correct files and understood YAML structure
- Researched contacts and roles for batch 2
- Ran pipeline scripts (alchemize, tailor_resume, build_resumes, apply.py)

**What Gemini broke:**
- Didn't use .venv (import errors, tried installing globally)
- Cover letters had metadata garbage headers
- Put batch doc in wrong directory
- Made 51 file changes but only committed a fraction — dirty repo state
- Inflated metrics (127 repos instead of canonical 113, 766K instead of 739K)
- Resume layouts went columnar (violating vertical stacked rule)
- Couldn't write heredocs (every cat <<'EOF' failed)

**Why:** Gemini doesn't share context with Claude. Feedback rules, the Protocol, the three-pillar model, the outreach rules, the creation-first philosophy, the identity reframe — Gemini saw none of it. It operated on repo files alone.

**How to apply:**
- Use Gemini for isolated, stateless tasks (batch file operations, data transforms, one-shot scripts)
- NEVER use for materials production, outreach composition, or anything requiring session history
- When Claude hits context limits, start a new Claude session (persistent memory carries over), don't switch to Gemini
- If Gemini was used, audit ALL changes before committing — check metrics, layout, identity, file paths

**2026-03-30 update — LinkedIn Content Engine incident:**
Gemini was given the LinkedIn posting task across 3 sessions. Results:
- Session 1: Infinite planning loop (repeated "Wait, I'll do read_file" ~50 times), crashed via `_recoverFromLoop`
- Sessions 2-3: Built a template-concatenation engine (linkedin_composer.py) that pastes block text with hardcoded subheadings. Zero compositional intelligence.
- Ignored strategy/linkedin-content/ entirely (existing Testament discipline, 3 prior posts, revision patterns). Only reviewed after being explicitly asked "did you review this directory?"
- Generated 5 LinkedIn "posts" that were raw block text with headers stapled on — not LinkedIn-ready
- Committed directly to main with `git add .` without reviewing staged files
- Repeated the exact same session identically across 3 invocations (no memory = no learning)
- Makefile target used interactive `read -p` (bad for automation)

This confirms the core assessment: Gemini is net negative for any task requiring system awareness, style discipline, or compositional judgment. The no-persistent-memory limitation is disqualifying for this repo's complexity.
