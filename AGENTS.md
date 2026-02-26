# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python CLI + content pipeline for job/grant applications.

- `scripts/`: core automation and CLI tools (`validate.py`, `compose.py`, `pipeline_status.py`, submit/enrich/scoring scripts)
- `tests/`: `pytest` coverage for script behavior and pipeline transitions (`test_<script>.py`)
- `pipeline/`: YAML application entries by state (`active/`, `deferred/`, `submitted/`, `closed/`, `drafts/`, `submissions/`)
- `blocks/`, `variants/`, `materials/`: reusable narrative blocks, generated variants, resumes/work samples
- `targets/`, `signals/`, `strategy/`: research, analytics logs, and planning docs
- `docs/`: architecture/workflow reference

## Build, Test, and Development Commands
There is no package build step; work is driven by Python scripts and YAML/Markdown assets.

- `python scripts/pipeline_status.py`: show current pipeline state and deadlines
- `python scripts/validate.py`: validate all pipeline YAML entries and schema rules
- `python scripts/compose.py --target <target-id>`: assemble a target-specific submission draft
- `python scripts/conversion_report.py`: generate conversion metrics/reporting
- `python -m pytest -q`: run the full test suite
- `python -m pytest tests/test_validate.py -q`: run a focused regression test

Use the repo-local virtualenv if present: `source .venv/bin/activate`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, `snake_case` for functions/modules, `UPPER_SNAKE_CASE` for constants.
- Keep script docstrings concise and behavior-oriented (matching existing `scripts/*.py` style).
- Prefer `pathlib.Path` for filesystem logic and explicit YAML field validation over implicit assumptions.
- YAML entry filenames must match the entry `id` (enforced by tests/validation).
- Markdown/YAML content filenames generally use lowercase kebab-case (for example, `openai-software-engineer-...yaml`).

## Testing Guidelines
- Framework: `pytest` (repository already includes integration and script-level tests).
- Add/update tests when changing validation rules, state transitions, scoring, or submit/enrich behavior.
- Name tests `tests/test_<script>.py`; keep test functions descriptive (`test_<behavior>()`).
- No formal coverage threshold is defined; prioritize regression coverage for pipeline state and YAML schema changes.

## Commit & Pull Request Guidelines
- Prefer Conventional Commit-style prefixes seen in history: `feat:`, `chore:` (imperative subject line).
- Keep commits scoped to one workflow change (script logic, pipeline data, or content batch) when possible.
- PRs should include: summary of affected directories, rationale, commands run (`validate`/`pytest`), and sample output when script behavior changes.
- Include screenshots only for UI/HTML changes (for example `materials/work-samples/interactive/`).

## Narrative Infrastructure & Identity Positions
Narratives are built using five canonical Identity Positions defined in `strategy/identity-positions.md`. Every application must align with one of these to ensure consistent storefront signal:

1. **Independent Engineer**: For AI lab roles (Anthropic, OpenAI). Focus: Large-scale infra, testing discipline, "AI-conductor" methodology.
2. **Systems Artist**: For art grants/residencies. Focus: Governance as artwork, systemic scale.
3. **Educator**: For academic roles. Focus: Teaching complex systems at scale.
4. **Creative Technologist**: For tech grants/consulting. Focus: AI orchestration, production-grade creative instruments.
5. **Community Practitioner**: For identity-specific funding. Focus: Precarity-informed systemic practice.

## Security & Configuration Tips
- Never commit secrets or local submission data (`.env`, `credentials.*`, `scripts/.submit-config.yaml`, `scripts/.*-answers/`, browser profiles).
- Treat `materials/` and submission assets as sensitive; avoid unnecessary redistribution in PR discussions.
