---
id: SOP-SYS-003
title: "Multi-Agent Dispatch — Parallel Non-Competing Workstreams"
scope: system
organ: III
tier: T1
status: active
---

# Multi-Agent Dispatch

Four AI agents. Four roles. Zero competition. Claude conducts, others execute within boundaries.

## Agent Roster

| Agent | Role | Context File | Model | Strengths | Failure Mode |
|-------|------|-------------|-------|-----------|-------------|
| Claude Code | **Conductor** | CLAUDE.md + memory/ | Opus 4.6 (1M) | Architecture, judgment, memory, composition | Over-plans, under-ships |
| Gemini CLI | **Machinist** | .github/GEMINI.md | Gemini 2.5 | Batch file ops, search, fast transforms | Ignores unseen rules, commits blindly |
| Codex | **Refactorer** | CODEX.md | o3/o4-mini | Type hints, refactors, sandboxed execution | Unknown (sandbox limits) |
| OpenCode | **Scout** | .opencode.md | Configurable | Web research, contact lookup, market intel | Unknown (least tested) |

## Dispatch Protocol

### Step 1: Claude identifies parallelizable tasks
From the current work queue, Claude selects tasks that:
- Have non-overlapping file scopes
- Match an agent's strength profile
- Can be verified independently
- Cannot corrupt other workstreams

### Step 2: Claude writes dispatch prompts
Each prompt includes:
- Exact task description
- File scope (glob patterns)
- What NOT to touch
- Verification command to run after
- Output format expected

### Step 3: User runs agents in parallel terminals
```bash
# Terminal 1: Claude (already running)
claude

# Terminal 2: Gemini
gemini -p "You are operating in MACHINIST mode. [task prompt]"

# Terminal 3: Codex
codex exec "[task prompt]"

# Terminal 4: OpenCode (research only)
opencode run "[research query]"
```

### Step 4: Claude reviews all output
- `git diff` to see what Gemini/Codex changed
- Verify test results
- Ingest OpenCode research
- Reject or approve each change

### Step 5: Claude commits
Claude is the **ONLY agent that commits.** This is non-negotiable. The Gemini incident (51 changes, partial commits, dirty state) proved why.

```bash
# Claude reviews
git diff scripts/
# Claude runs tests
python -m pytest tests/ -q
# Claude commits (if approved)
git add [specific files]
git commit -m "feat: [description]"
```

## File Scope Boundaries

```
Claude ONLY:
  blocks/           ← narrative voice
  materials/*cover*  ← composition
  materials/*outreach* ← Protocol
  signals/           ← CRM judgment
  config/identity.yaml ← human truth
  .claude/           ← memory
  docs/sop--*        ← architecture

Gemini (batch ops):
  scripts/*.py       ← mechanical transforms (grep/sed scope)
  materials/resumes/**/*.html ← CSS batch updates
  pipeline/**/*.yaml ← bulk field normalization

Codex (refactors):
  scripts/*.py       ← one file at a time, code quality only
  tests/*.py         ← test improvements

OpenCode (read-only):
  (never modifies files)
  stdout → Claude ingests
```

## Anti-Patterns

1. **Never let Gemini write content.** It has no voice, no memory, no Protocol knowledge. The LinkedIn incident proved this.
2. **Never let Codex refactor across files.** One file at a time. Cross-file changes require architectural judgment.
3. **Never let OpenCode persist data directly.** It might fabricate contacts (the broken LinkedIn URL problem). Claude verifies first.
4. **Never let any agent commit.** Claude reviews everything. The dirty-repo-state incident is never repeated.
5. **Never give an agent a task that requires context it can't access.** If the task needs memory of prior decisions, it stays with Claude.

## Verification Checklist (after every parallel run)

- [ ] `git diff` reviewed for all modified files
- [ ] `python -m pytest tests/ -q` passes
- [ ] `grep -r "Anthony\|Padavano" scripts/{modified}` returns 0 (if identity decoupling)
- [ ] No files outside the agent's scope were modified
- [ ] All research output verified for accuracy (LinkedIn URLs checked)
- [ ] Changes are atomic — each agent's work can be committed or reverted independently
