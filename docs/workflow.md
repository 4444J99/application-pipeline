# Daily Workflow

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
