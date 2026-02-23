# Daily Workflow

## Daily Standup (Start Here)

The standup is the daily entry point. Run it every session before doing anything else.

```bash
# Full standup with default 3-hour budget
python scripts/standup.py

# Adjust time budget
python scripts/standup.py --hours 5

# Single section
python scripts/standup.py --section health
python scripts/standup.py --section stale
python scripts/standup.py --section plan

# Mark an entry as reviewed after working on it
python scripts/standup.py --touch pen-america

# Log session metrics to signals/standup-log.yaml
python scripts/standup.py --log
```

The standup produces 7 sections:

1. **Pipeline Health** — Counts, velocity, days since last submission
2. **Staleness Alerts** — Expired, at-risk, stagnant entries
3. **Today's Work Plan** — Deadline-driven + score-sorted within time budget
4. **Outreach Suggestions** — Per-target checklists based on status
5. **Best Practices** — Context-sensitive reminders
6. **Pipeline Replenishment** — Alerts when actionable count is low
7. **Session Log** — Optional daily record to signals/standup-log.yaml

### Staleness Rules

- **EXPIRED**: Deadline passed + not yet submitted. Action: archive or withdraw.
- **AT-RISK**: Hard deadline ≤3 days away + still in research/qualified. Action: stage immediately or withdraw.
- **STAGNANT**: No `last_touched` update in >7 days + actionable status. Action: review or touch.

### Outreach Tracking

Each pipeline entry can have an `outreach` list tracking actions taken:

```yaml
outreach:
  - type: warm_contact
    contact: "Jane Doe"
    channel: email
    date: "2026-03-01"
    note: "Intro email about Creative Capital application"
    status: done
```

Cross-cutting networking (not tied to a single target) goes in `signals/outreach-log.yaml`.

## Adding a New Target

1. **Research** — Create a file in `targets/{track}/` with organization info, eligibility, deadlines, fit assessment
2. **Create pipeline entry** — Add `pipeline/active/{target-id}.yaml` with status `research`
3. **Qualify** — Verify eligibility, check benefits cliff, assess fit score. Update status to `qualified`
4. **Draft** — Select blocks from `blocks/`, choose identity position, compose materials. Update status to `drafting`
5. **Stage** — Finalize materials, create variants in `variants/`. Update status to `staged`
6. **Submit** — Submit via portal, record date. Move file to `pipeline/submitted/`. Update status to `submitted`

## Composing a Submission

```bash
# See available blocks
ls blocks/identity/ blocks/projects/ blocks/methodology/

# Compose for a specific target
python scripts/compose.py --target creative-capital-2027

# The script reads the pipeline YAML's submission.blocks_used
# and assembles them into a single document
```

### Block Selection Guide

| Application asks for... | Use block... | Depth |
|-------------------------|-------------|-------|
| "Brief artist statement" | `identity/60s.md` or `identity/2min.md` | 100-300 words |
| "Artist statement" | `identity/2min.md` or `identity/5min.md` | 300-800 words |
| "Detailed project description" | `projects/organvm-system.md` | Full |
| "Methodology" | `methodology/ai-conductor.md` | Adapt to length |
| "What makes you different" | `evidence/differentiators.md` | Bullet list |

### Identity Position Selection

| Target type | Default position | Rationale |
|-------------|-----------------|-----------|
| Art grants, residencies | `systems-artist` | The system IS the artwork |
| Education grants | `educator` | 11 years, 2,000+ students |
| Tech grants, tech roles | `creative-technologist` | Production-grade AI orchestration |
| LGBTQ+/identity funding | `community-practitioner` | Lived experience of precarity |

## Weekly Pipeline Review

```bash
# Check current state
python scripts/pipeline_status.py

# See what's due this week
python scripts/pipeline_status.py --upcoming 7

# Validate all entries
python scripts/validate.py
```

## After Receiving a Response

1. Update the pipeline YAML's `conversion` section
2. Record `response_type`, `time_to_response_days`, `feedback`
3. Move file to `pipeline/closed/` if final outcome
4. Update `signals/conversion-log.yaml`
5. Run `python scripts/conversion_report.py` periodically to spot patterns

## Updating Metrics

When system metrics change (new repos, new essays, etc.):

1. Update `organvm-corpvs-testamentvm/docs/applications/00-covenant-ark.md` first
2. Update `blocks/evidence/metrics-snapshot.md`
3. Propagate to any identity blocks that cite specific numbers
