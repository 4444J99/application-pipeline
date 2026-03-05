# Handoff Protocol

Single-operator dependency mitigation. What another person needs to operate the pipeline.

## System Overview

This is a career application pipeline managing ~1,700 entries across grants, jobs, fellowships, and residencies. It is Python CLI tooling with YAML data files, designed for a single operator.

## Critical Daily Operations

| Task | Command | When |
|------|---------|------|
| Check pipeline status | `python scripts/run.py standup` | Morning |
| Review follow-ups | `python scripts/run.py followup` | Morning |
| Check for responses | `python scripts/run.py outcomes` | Morning |
| Campaign deadlines | `python scripts/run.py campaign` | After standup |

## Data Locations

| Path | Contents | Backup? |
|------|----------|---------|
| `pipeline/active/` | Actionable entries (max ~10) | Yes |
| `pipeline/submitted/` | Entries sent to targets | Yes |
| `pipeline/closed/` | Terminal outcomes (accepted/rejected) | Yes |
| `pipeline/research_pool/` | Auto-sourced research entries (~700) | Yes |
| `signals/` | Audit trails, logs, analytics | Yes |
| `strategy/` | Scoring rubric, market intelligence, config | Yes |
| `blocks/` | Modular narrative content | Yes |
| `materials/resumes/` | Resume templates and target-tailored PDFs | Yes |

## Automation Schedule

6 LaunchAgents run on macOS (check status: `python scripts/launchd_manager.py --status`):

| Agent | Schedule | Purpose |
|-------|----------|---------|
| daily-deferred | 6:00 AM | Check deferred entries for re-activation |
| daily-monitor | 6:30 AM | Backup verification + signal freshness |
| calendar-refresh | 6:45 AM | Export deadlines to iCal |
| agent-biweekly | Mon/Thu 7:00 AM | Autonomous pipeline operations |
| weekly-backup | Sun 2:00 AM | Pipeline backup (tar.gz) |
| weekly-briefing | Sun 7:00 PM | Executive summary generation |

## Key Concepts

- **Identity Positions**: 5 framings that determine how to present work (see `strategy/identity-positions.md`)
- **Scoring Rubric**: 9 dimensions, weighted by track type (see `strategy/scoring-rubric.yaml`)
- **Precision Mode**: Max 1-2 applications/week, minimum score 9.0 to apply
- **Blocks**: Modular content at 4 depth tiers (60s / 2min / 5min / cathedral)

## If the Operator Is Unavailable

1. **Urgent deadlines** (<7 days): Run `python scripts/run.py campaign` to see what's due
2. **Submissions in progress**: Check `pipeline/active/` for entries with status `staged`
3. **Don't submit anything new** — precision mode means only the operator can make judgment calls on fit
4. **Backups**: Weekly tar.gz in repo root or `backups/` directory. Restore: extract and replace `pipeline/`

## Environment Setup

```bash
cd ~/Workspace/4444J99/application-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v  # verify everything works
```

Requires Python 3.11+, GEMINI_API_KEY for AI features (optional).

## Credential Files

See `docs/secrets-management.md` for all credential locations and rotation.
