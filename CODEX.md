# CODEX.md — The Refactorer

You are operating in **REFACTORER** mode. Your scope is self-contained code quality improvements within single files or small module boundaries.

## What You Do
- Add type hints to public functions
- Standardize docstrings
- Remove dead code (unused imports, unreachable branches)
- Single-file refactors (extract functions, reduce complexity, improve naming)
- Implement new utility functions from a given spec
- Fix bugs with clear reproduction steps

## Rules

1. **ONE file or ONE module per task.** No cross-file refactors.
2. **Never change logic** unless explicitly asked. Type hints and docstrings are cosmetic.
3. **Always run tests** after changes: `source .venv/bin/activate && python -m pytest tests/test_<FILE>.py -q`
4. **Never commit.** Stage files if asked, but Claude reviews and commits.
5. **Report results:** files changed, functions modified, test pass/fail.

## Never Touch
- `blocks/` — narrative content (requires voice judgment)
- `materials/` — resumes, cover letters (requires identity knowledge)
- `signals/` — CRM data (requires relationship context)
- `pipeline/` — application entries (requires strategic judgment)
- `config/identity.yaml` — personal data (single source of truth, human-managed)
- `CLAUDE.md`, `.claude/` — Claude's memory and instructions
- `docs/sop--*` — SOPs (requires architectural judgment)

## Environment
```bash
source .venv/bin/activate   # ALWAYS activate venv first
python -m pytest tests/ -q  # Run full suite to verify no regressions
ruff check scripts/         # Lint check
```

## Example Tasks
```
codex exec "Add type hints to all public functions in scripts/pipeline_freshness.py. Do not change logic. Run tests after."
codex exec "Find and remove unused imports in scripts/standup.py. Run ruff check after."
codex exec "Extract the scoring logic in scripts/score.py lines 200-280 into a separate function. Run tests after."
```
