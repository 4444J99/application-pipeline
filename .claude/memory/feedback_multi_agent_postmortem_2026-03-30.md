---
name: Multi-agent dispatch post-mortem — first parallel run 2026-03-30
description: Three agents ran in parallel. Codex 9/10, Gemini 7/10, OpenCode 6/10. Lessons for tighter handoff trust and less drift.
type: feedback
---

## What Happened

First parallel dispatch: Codex (type hints), Gemini (identity decoupling), OpenCode (funder research). All three completed. None corrupted each other's work. Claude reviewed and approved.

## Agent-by-Agent

### Codex (9/10) — near-perfect
- Read CODEX.md first, understood scope
- Introduced TypeAlias (smart — added value beyond the prompt)
- Isolated pre-existing test failure from its own changes
- Ran targeted test subset to prove its work was clean
- **Trust earned:** Can increase scope next time (2-3 files, small refactors)

### Gemini (7/10) — did the work, introduced a defect
- Read GEMINI.md, followed guardrails (no commit, no blocks/)
- Replaced names in 7 files, used short_name vs full_name intelligently
- BUT: broke a docstring in network_graph.py during edit (unterminated triple-quote)
- Self-repaired after test failure revealed it
- Ran full test suite (3,266 tests) — caused timeout on 16GB RAM
- Scope-wandered when given the unrelated Zettelkasten prompt — searched for files in the wrong repo for 8+ tool calls
- **Trust issue:** Edits can introduce syntax errors. Need post-edit compile check in the prompt.

### OpenCode (6/10) — adequate but shallow
- Found real funders with real amounts
- Used free model (minimax-m2.5-free) — insufficient depth
- Listed stated missions, not actual funded portfolios (violated "revealed preferences > stated mission" principle)
- Several entries were vague ("Varies by cohort")
- **Trust issue:** Research quality depends on model quality. Free tier insufficient for this work.

## Lessons for Next Time

### 1. PROMPT PRECISION prevents drift
**Problem:** Gemini's prompt said "replace all hardcoded 'Anthony James Padavano'" but several files had "Anthony Padavano" (short form). Gemini had to discover this on its own, costing 4+ extra search steps.
**Fix:** Pre-compute the exact search terms. Instead of "replace hardcoded names," say: "Search for both 'Anthony James Padavano' AND 'Anthony Padavano'. Replace the first with `load_identity()['person']['full_name']` and the second with `load_identity()['person']['short_name']`."

### 2. COMPILE CHECK must be in the prompt
**Problem:** Gemini introduced a syntax error and only discovered it when tests failed.
**Fix:** Add to every Gemini prompt: "After EACH file edit, run `python -c 'import py_compile; py_compile.compile(\"scripts/FILENAME.py\", doraise=True)'`. Fix any errors before moving to the next file."

### 3. TEST SCOPE must be constrained
**Problem:** Gemini ran the full 3,266-test suite, which timed out on 16GB RAM.
**Fix:** Specify exact test files in the prompt: "Run ONLY `python -m pytest tests/test_network_graph.py tests/test_pipeline_lib.py -q`. Do NOT run the full suite."

### 4. BONUS PROMPTS cause scope creep
**Problem:** After completing the task, Gemini received an unrelated prompt about Zettelkasten architecture and spent 8+ tool calls searching for files that don't exist in this repo.
**Fix:** End every dispatch with: "When done, report results and stop. Do not respond to additional prompts outside this task scope."

### 5. MODEL SELECTION matters for Scouts
**Problem:** OpenCode used minimax-m2.5-free, producing surface-level research.
**Fix:** Specify model in the prompt: `opencode run --model claude-sonnet "..."` or configure OpenCode to use a stronger default model for research tasks.

### 6. VERIFICATION SPEC must be explicit
**Problem:** Each agent verified differently — Codex ran targeted tests, Gemini ran everything, OpenCode didn't verify at all.
**Fix:** Every dispatch prompt ends with an explicit verification block:
```
VERIFY:
1. python -c 'import py_compile; py_compile.compile("scripts/FILE.py", doraise=True)'
2. python -m pytest tests/test_FILE.py -q
3. grep -c "Anthony" scripts/FILE.py  # should be 0
REPORT: files changed, test results, grep counts
```

### 7. FILE MANIFEST in the prompt prevents extra searching
**Problem:** Gemini searched 6 of the 11 listed files and found 0 matches in most, because the hardcoded strings were already removed by tailor_resume.py's earlier fix. Wasted cycles.
**Fix:** Pre-scan and include only files that ACTUALLY have matches: "The following files contain hardcoded names (verified by grep): [list]. Only modify these files."

## Template for Next Dispatch

```
ROLE: [MACHINIST/REFACTORER/SCOUT]
TASK: [one sentence]
FILES: [exact list, pre-verified to contain the target]
SEARCH: [exact strings to find]
REPLACE: [exact replacement expressions]
VERIFY AFTER EACH FILE:
  python -c 'import py_compile; py_compile.compile("scripts/FILE.py", doraise=True)'
VERIFY AFTER ALL FILES:
  source .venv/bin/activate && python -m pytest tests/[SPECIFIC_TEST].py -q
  grep -c "[SEARCH_TERM]" scripts/{modified files}  # should be 0
REPORT: files changed, compile results, test results, grep counts
DO NOT: commit, modify files outside the list, respond to unrelated prompts, run the full test suite
```

## How to apply
When dispatching agents, spend 2 minutes writing a precise prompt using the template above. The 2 minutes of prompt precision saves 10+ minutes of agent drift, self-repair, and scope wandering. The prompt IS the governance.
