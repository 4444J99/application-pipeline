# Weekly Plan: 2026-03-30 (Week 14)

## Context

New week. The pipeline has been building infrastructure for 3 weeks — 10-loop architecture, Atomic Clock SOPs, identity decoupling, multi-agent governance. But the **automation layer is dead**: every LaunchAgent plist points to `/opt/anaconda3/bin/python` (doesn't exist), and `launchd_manager.py` looks in `launchd/` instead of `.config/launchd/`. The engine was built but never started.

Meanwhile: Creative Capital ($50K grant, systems-artist fit 9/10) deadline is **Wednesday April 2, 3 PM ET** — 3 days away. It's `staged` status with materials ~80% ready. This is the only hard deadline this week.

The morning digest shows: 72 total entries, 5 actionable, 24 submitted, 30 overdue follow-ups, campaign viability 56/100 (QUESTIONABLE). One stale job submission auto-expired (Supabase).

**This week's mission:** Fix the engines, submit Creative Capital, and establish the weekly rhythm so the system runs itself.

---

## Stream 1: ENGINE HEALTH (P0 — Monday morning unlock)

Everything downstream depends on this. Three root causes, one fix sequence.

### Root Cause 1: Wrong Python path in all 9 plists
- **File:** `.config/launchd/com.4jp.pipeline.*.plist` (9 files)
- **Bug:** Line 9: `<string>/opt/anaconda3/bin/python</string>`
- **Fix:** Change to `/Users/4jp/Workspace/4444J99/application-pipeline/.venv/bin/python`

### Root Cause 2: `launchd_manager.py` wrong directory
- **File:** `scripts/launchd_manager.py:19`
- **Bug:** `LAUNCHD_DIR = REPO_ROOT / "launchd"`
- **Fix:** `LAUNCHD_DIR = REPO_ROOT / ".config" / "launchd"`

### Root Cause 3: Reinstall + kickstart
- Run: `python scripts/launchd_manager.py --install --kickstart`
- Verify: `python scripts/launchd_manager.py --status`

### Root Cause 4: system-metrics.json syntax error
- **File:** `~/Workspace/meta-organvm/organvm-corpvs-testamentvm/system-metrics.json`
- **Bug:** "Expecting property name enclosed in double quotes: line 3 column 1"
- **Fix:** Find and fix the JSON syntax error (trailing comma or comment)

### Execution
- **Agent:** Codex — mechanical find-replace across 10 files
- **Verification:** `python scripts/launchd_manager.py --status` shows all 9 agents loaded

---

## Stream 2: CREATIVE CAPITAL SPRINT (P0 — deadline Wed April 2)

### Current State
- Status: `staged` | Fit: 9/10 profile, 7.0 pipeline | Deadline: April 2, 3 PM ET
- Materials exist: cover letter, resume, profile (all in `batch-03/`)
- `materials_ready: null` — not yet validated
- Missing: 6 short portal answers, Medicaid benefits cliff consultation (advisory, not blocking)
- `network_proximity: 1` — weakest dimension, need 3 fresh contacts

### Monday (today)
- Research Creative Capital portal: what fields, what format, what length limits
- Run `python scripts/apply.py --target creative-capital-2027 --dry-run` to preview package
- Identify the 6 short answer questions and draft initial responses
- Research 3 Creative Capital contacts (past grantees, program staff, alumni network)

### Tuesday (April 1)
- Finalize short answers using blocks: `identity/5min`, `projects/organvm-system`, `methodology/governance-as-art`
- Run `python scripts/apply.py --target creative-capital-2027` — full pipeline
- Quality gates: overlap check, sentence completeness, page fill, metrics match
- Build PDFs, create application directory
- Send outreach to 3 fresh Creative Capital contacts

### Wednesday (April 2, before 3 PM ET)
- Final review of all materials
- Submit through portal by 2:00 PM ET (1hr buffer)
- Record: `python scripts/advance.py --to submitted --id creative-capital-2027`
- Log submission in all 3 signal files

### Critical Files
- `pipeline/active/creative-capital-2027.yaml`
- `materials/resumes/batch-03/creative-capital-2027/`
- `materials/variants/` (cover letter variants)
- `materials/targets/profiles/creative-capital.json`

---

## Stream 3: WEEKLY RHYTHM (Atomic Clock)

With engines fixed, establish the weekly cadence:

| Day | Stream | Primary Work |
|-----|--------|-------------|
| **Mon** (today) | DISCOVER + ENGINE | Fix plists, morning catch-up, score/qualify new entries |
| **Tue** | GRANTS | Creative Capital finalization (all-day sprint) |
| **Wed AM** | SUBMIT | Creative Capital submission before 3 PM ET |
| **Wed PM** | CULTIVATE | CRM dashboard, 5 dormant tie reactivations |
| **Thu** | BUILD | LOOP 9 expansion: `content_harvest.py`, LinkedIn publish pipeline |
| **Fri** | HYGIENE | Research pool pruning, signal rotation, verification matrix |
| **Sat/Sun** | REST | Weekly backup, weekly brief, diagnose |

---

## Stream 4: FOLLOW-UP TRIAGE (P1 — 30 overdue actions)

30 overdue follow-up actions across 24 submitted entries. Process in batches:

### Monday: Categorize
- Run `.venv/bin/python scripts/run.py followup` with the venv
- Sort 30 actions into: still-actionable vs expired vs withdrawn
- Any entry >30 days with no response → move to `check_outcomes.py` for resolution

### Wednesday PM: Execute
- Send reactivation DMs for the top 10 still-actionable follow-ups
- Log each via `python scripts/log_dm.py`
- Target: reduce overdue from 30 to <15

### Friday: Clean up
- Run `python scripts/check_outcomes.py` for all submitted >21 days
- Expire truly dead entries
- Update conversion log

---

## Stream 5: IDENTITY WIRING (P2 — Thursday)

`config/identity.yaml` exists and `pipeline_lib.load_identity()` works, but the two most critical scripts don't use it:

- `scripts/apply.py` — hardcoded personal references
- `scripts/dm_composer.py` — hardcoded personal references

### Scope
- Find all hardcoded name/email/identity references in these 2 files
- Replace with `load_identity()` calls
- Run tests to verify: `pytest tests/test_apply.py tests/test_dm_composer.py -v`

### Files
- `scripts/apply.py`
- `scripts/dm_composer.py`
- `config/identity.yaml`
- `scripts/pipeline_lib.py` (where `load_identity()` lives)

---

## Stream 6: LOOP 9 EXPANSION (P2 — Thursday/Friday)

LOOP 9 (PUBLISH) is at 2% of system capacity (3 scripts, 1,096 lines). This week's target: meaningful step toward 5%.

### Thursday: Build `content_harvest.py`
- Scan recent applications, outcomes, system milestones
- Extract content themes for LinkedIn/blog posts
- Output: `strategy/linkedin-content/harvest-YYYY-MM-DD.yaml`

### Thursday: Extend `linkedin_composer.py`
- Add `--publish` mode: stage post for clipboard, record publish date
- Post #004 (AI Conductor) is ready (scores 7/8 on Testament audit)
- Target: publish post #004 this week

### Friday: Create LOOP 9 LaunchAgent
- `com.4jp.pipeline.content-harvest.plist` — daily 9 PM trigger
- Wire into `launchd_manager.py`

---

## Multi-Agent Distribution

| Agent | Day | Work | Type |
|-------|-----|------|------|
| **Claude** | Mon-Wed | Morning digest, Creative Capital composition, follow-up DMs | Judgment |
| **Codex** | Mon | Fix 9 plist Python paths + launchd_manager.py | Mechanical |
| **Codex** | Thu | `content_harvest.py`, identity decoupling | Mechanical |
| **Gemini** | Tue | Creative Capital portal research, PDF validation | Stateless research |
| **OpenCode** | Wed | Dormant tie research, follow-up status checks | Research |

Per multi-agent post-mortem (memory): prompt precision prevents drift, compile check in every edit prompt, constrain test scope, pre-scan file manifests.

---

## Verification

### Engine Health (Monday)
```bash
python scripts/launchd_manager.py --status          # All 9 agents loaded
.venv/bin/python scripts/run.py morning              # Digest runs clean
.venv/bin/python scripts/run.py standup              # Dashboard renders
```

### Creative Capital (Wednesday)
```bash
python scripts/apply.py --target creative-capital-2027 --dry-run  # Package complete
python scripts/recruiter_filter.py --target creative-capital-2027  # Materials pass
# Portal submission before 2 PM ET
python scripts/advance.py --to submitted --id creative-capital-2027
```

### Weekly Health (Friday)
```bash
python scripts/verify_all.py --quick                 # Verification matrix passes
python scripts/validate.py --check-id-maps --check-rubric
python scripts/snapshot.py --save                    # Weekly snapshot
python scripts/diagnose.py                           # System scorecard
```

### End of Week
- LaunchAgents: 9/9 loaded and running
- Creative Capital: submitted
- Overdue follow-ups: <15 (from 30)
- LOOP 9: 5 scripts (from 3)
- Identity wiring: apply.py + dm_composer.py using `load_identity()`
