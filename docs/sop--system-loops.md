---
id: SOP-SYS-001
title: "System Loops — Every Action Is a Cycle"
scope: system
organ: III
tier: T1
status: active
---

# System Loops

Nothing is a single shot. Every action is a cycle triggered at intervals. This document defines every loop in the system, its cadence, its SOP, and its trigger mechanism. If a loop doesn't have an SOP, it's ungoverned — and ungoverned loops produce ungoverned output.

> "How any one thing is done = how every thing is done."
> — SOP-INST-001

---

## Architecture

```
TRIGGER (interval/event) → SOP (process) → ACTION (execution) → OUTPUT (artifact)
      ↑                                                              |
      └──────────── FEEDBACK (output informs next cycle) ────────────┘
```

Every loop has:
1. **Trigger** — what initiates the cycle (time interval, event, human command)
2. **SOP** — the standardized process governing execution
3. **Input** — what the loop consumes (data, state, prior output)
4. **Output** — what the loop produces (artifact, state change, signal)
5. **Feedback** — how the output feeds the next iteration

---

## LOOP 1: DISCOVER
**What:** Find opportunities across all three pillars
**Cadence:** Daily (jobs), Weekly (grants), Continuous (consulting)
**Trigger:** LaunchAgent `daily-scan` + `daily-intake-triage` + manual
**SOP:** SOP-DIS-001

### Process
1. **Source** — Ingest from ATS APIs (Greenhouse, Lever, Ashby), grant calendars, consulting signals
2. **Score** — Run 9-dimension rubric against each opportunity (configurable per track)
3. **Filter** — Apply thresholds (min 7.0 score, network_proximity >= 5 preferred)
4. **Qualify** — Promote research → qualified entries that pass the gate
5. **Flush** — Archive stale research entries (72h for jobs, configurable)

### Feedback Loop
Scoring accuracy improves from outcome data (LOOP 8). Rejected entries inform rubric recalibration (quarterly via `recalibrate.py`). The 1,510:9 research-to-actionable ratio is the system's selectivity metric — tracked in daily snapshots.

### CLI
```bash
python scripts/run.py topjobs        # Source + score
python scripts/run.py qualify        # Promote qualified
python scripts/run.py hygiene        # Flush stale
```

---

## LOOP 2: RESEARCH
**What:** Deep-research an opportunity before committing to apply
**Cadence:** Per-entry (triggered when entry reaches "qualified")
**Trigger:** Entry status transition qualified → drafting
**SOP:** SOP-RES-001

### Process
1. **Funder/Employer intelligence** — Who are they? What do they value? Recent news, funding, culture signals
2. **Contact research** — 3 FRESH contacts per role, verified LinkedIn URLs, role-aligned (NEVER recycle contacted people)
3. **Funder-fit gate** — Does this opportunity actually match? (Creative Capital deferred because CC funds sensory art, not infrastructure. This gate saved wasted effort.)
4. **Competitive landscape** — Who else applies to this? What's the signal density?
5. **Text match** — TF-IDF comparison of job posting keywords against block/profile content

### Feedback Loop
Contact research quality feeds the network graph (LOOP 6). Funder-fit gate results feed the scoring rubric (if a class of opportunities consistently fails the gate, adjust the rubric to score them lower upfront).

### CLI
```bash
python scripts/run.py contacts <id>  # Research contacts
python scripts/run.py textmatch <id> # Keyword match
python scripts/run.py orgdetail <org> # Org intelligence
```

---

## LOOP 3: BUILD
**What:** Produce application materials (resume, cover letter, portal answers)
**Cadence:** Per-entry (triggered when entry reaches "drafting" or "staged")
**Trigger:** `apply.py --target <id>` or campaign execution
**SOP:** SOP-BLD-001 (incorporates SOP-INST-001 Forced Revision Protocol)

### Process
1. **Select identity** — Load mask from identity_positions based on entry's fit.identity_position
2. **Tailor resume** — Generate prompt → AI revision → integrate → validate sentence completeness → build PDF
3. **Draft cover letter** — Raw material (Phase 2) → forced compression (Phase 3) → verification (Phase 4) → citrinitas (Phase 5)
4. **Generate portal answers** — Auto-fill standard fields from identity.yaml, leave unknown fields blank for human review
5. **Quality gates** — Sentence completeness, page fill (95-98%), link liveness, no "Independent Engineer", metrics match canonical, overlap check (CL vs resume < 3 shared 4-word phrases)
6. **Build PDFs** — Chrome headless, --no-pdf-header-footer, absolute file:// URLs, verify 1 page

### Feedback Loop
Quality gate failures feed the validator (new patterns added to sentence completeness regex). Truncation incidents feed the tailoring prompt (hard rule #5: never truncate). Material quality feeds block-outcome correlation (LOOP 8) — which blocks correlate with positive outcomes.

### CLI
```bash
python scripts/run.py apply <id>     # Full pipeline
python scripts/run.py tailor <id>    # Resume only
python scripts/run.py review <id>    # Quality audit
```

---

## LOOP 4: SUBMIT
**What:** Submit application through portal + send outreach
**Cadence:** Per-entry (triggered when materials pass all gates)
**Trigger:** Human-gated (SOP-INST-001 Phase 6)
**SOP:** SOP-SUB-001

### Process
1. **Pre-flight** — Verify all materials exist, all quality gates pass, portal URL is live
2. **Submit** — Open portal, paste answers, upload resume + cover letter
3. **Record** — Update entry status to "submitted", log submission date
4. **Outreach** — Send 3 connect requests to FRESH contacts (NEVER recycle)
5. **Log** — Record outreach actions in contacts.yaml + outreach-log.yaml + network.yaml

### Feedback Loop
Submission data feeds daily snapshots (LOOP 7). Portal friction scores feed the market intelligence JSON. ATS-specific learnings feed the submission guide.

### CLI
```bash
python scripts/run.py submit <id>    # Pre-flight + checklist
python scripts/run.py record <id>    # Record submission
python scripts/run.py logdm <contact> # Log outreach
```

---

## LOOP 5: FOLLOW UP
**What:** Pursue submitted applications through timed outreach protocol
**Cadence:** Daily check, actions triggered by protocol timing
**Trigger:** LaunchAgent `daily-deferred` + `python scripts/run.py followup`
**SOP:** SOP-FOL-001

### Process
1. **Scan** — Check all submitted entries for follow-up windows (Day 1-3: connect, Day 7-10: DM, Day 14-21: final)
2. **Generate DMs** — Protocol-validated messages (7 articles: hook planting, continuity, ratio decay, terminal question, inhabitation, bare resource, thread parity)
3. **Send** — Deliver DM via LinkedIn (human-gated)
4. **Log** — Record interaction in all 3 signal files
5. **Escalate** — If Day 21+ with no response, flag for triage

### Feedback Loop
Response rates feed the outreach protocol tuning. DM content that gets responses → extract patterns into the protocol. DM content that gets silence → identify anti-patterns. The 20% DM response rate is the system's engagement metric.

### CLI
```bash
python scripts/run.py followup       # Today's actions
python scripts/run.py dm <contact>   # Compose DM
python scripts/run.py logdm <contact> # Log action
```

---

## LOOP 6: CULTIVATE (Network)
**What:** Build and deepen the relationship network
**Cadence:** Continuous (every interaction is cultivation)
**Trigger:** Connection acceptance, DM response, event, referral
**SOP:** SOP-CUL-001

### Process
1. **Monitor** — Check for connection acceptances, DM responses, profile views
2. **Respond** — Context-aware response using Protocol articles
3. **Deepen** — Move from dormant → weak → moderate → strong (tie strength)
4. **Map** — Update network graph with new edges, hop-decay scoring (Granovetter weak ties)
5. **Sync** — Reverse-sync graph → contacts.yaml via `network_graph.py --sync-contacts`

### Feedback Loop
Network density feeds scoring (network_proximity dimension). Strong ties produce referrals (8x hire rate). Dormant-to-weak conversions are the system's relationship velocity metric. 153 dormant ties = 153 opportunities for one meaningful exchange.

### CLI
```bash
python scripts/run.py network        # Dashboard
python scripts/run.py cultivate      # Candidates for deepening
python scripts/run.py warmintro      # Referral path audit
```

---

## LOOP 7: OBSERVE (Analytics + Snapshots)
**What:** Measure system health and track trends
**Cadence:** Daily (snapshots), Weekly (briefs), Quarterly (recalibration)
**Trigger:** LaunchAgent `daily-monitor` + `weekly-briefing`
**SOP:** SOP-OBS-001

### Process
1. **Snapshot** — Pipeline counts, score distributions, stage distribution, velocity
2. **Trend** — 7d/30d/90d deltas, linear regression slopes, inflection detection
3. **Alert** — Stale entries (>14d untouched), dead links, blank required fields
4. **Brief** — Weekly executive summary with recommended actions
5. **Diagnose** — System diagnostic scorecard across 9 quality dimensions

### Feedback Loop
Snapshot data feeds trend analysis. Trends feed the weekly brief. Brief feeds prioritization decisions. Diagnostic scores feed the IRA (inter-rater agreement) facility — multiple AI models rate the system independently, consensus scores drive improvement.

### CLI
```bash
python scripts/run.py morning        # Daily digest
python scripts/run.py snapshot       # Save daily snapshot
python scripts/run.py weeklybrief    # Weekly summary
python scripts/run.py diagnose       # System scorecard
```

---

## LOOP 8: LEARN (Outcomes + Recalibration)
**What:** Extract lessons from outcomes to improve all prior loops
**Cadence:** Per-outcome (triggered by response/rejection/interview), Quarterly (rubric recalibration)
**Trigger:** `check_outcomes.py` + `recalibrate.py`
**SOP:** SOP-LRN-001

### Process
1. **Record outcome** — accepted, rejected, withdrawn, expired + reason if known
2. **Hypothesis validation** — Compare predicted outcome (from `feedback_capture.py`) against actual
3. **Block-outcome correlation** — Which narrative blocks correlate with acceptance vs rejection
4. **Dimension analysis** — Which scoring dimensions predicted correctly, which didn't
5. **Recalibrate** — Quarterly rubric weight adjustment proposal based on outcome patterns
6. **Publish** — Outcome learnings become content (LOOP 9)

### Feedback Loop
Outcome data feeds scoring accuracy (LOOP 1). Block correlations feed material selection (LOOP 3). Dimension accuracy feeds rubric weights. Rejection patterns feed hypothesis generation. **This is the loop that makes every other loop smarter.**

### CLI
```bash
python scripts/run.py outcomes       # Check for responses
python scripts/run.py rejections     # Rejection analysis
python scripts/run.py blockoutcomes  # Block correlation
python scripts/run.py recalibrate    # Weight adjustment
python scripts/run.py hypothesis <id> # Record prediction
```

---

## LOOP 9: PUBLISH (Content Engine)
**What:** Transform pipeline data into public-facing content
**Cadence:** Daily (micro-content), 2x/week (Testament posts), Weekly (articles)
**Trigger:** Application completion, outcome received, system milestone
**SOP:** SOP-PUB-001

### Process
1. **Harvest** — Extract content themes from recent applications, outcomes, system changes
2. **Select mask** — Narrator (Q1), Strategist (Q2), Architect (Q3), Integrator (Q4)
3. **Draft** — Raw material in scratch/ (SOP-INST-001 Phase 2)
4. **Revise** — Forced compression into format constraints (Phase 3)
5. **Audit** — Testament audit engine (13 articles, 6/8 minimum to publish)
6. **Publish** — LinkedIn, Dev.to, Hashnode, YouTube
7. **Measure** — Engagement metrics feed content strategy

### Feedback Loop
Engagement data feeds mask selection (which quadrant responds to which voice). High-performing content themes feed more content in that vein. The content attracts inbound leads (employers, institutions, users) that feed back into the pipeline. **The pipeline markets itself through its own operation.**

### CLI
```bash
python scripts/run.py linkedin       # List Testament posts
python scripts/run.py linkedinaudit  # Audit all posts
python scripts/run.py linkedinnext   # Suggest next topic
```

---

## LOOP 10: GOVERN (Meta-Loop)
**What:** Ensure all loops are running, healthy, and improving
**Cadence:** Weekly (standup review), Monthly (SOP review), Quarterly (system audit)
**Trigger:** Weekly rhythm (Monday morning), LaunchAgent health checks
**SOP:** SOP-GOV-001

### Process
1. **Loop health check** — Is every loop running at its cadence? Which are stale?
2. **SOP compliance** — Are outputs meeting SOP standards? (e.g., are cover letters going through forced revision?)
3. **Feedback integrity** — Are feedback loops actually connected? (e.g., is outcome data actually reaching the scoring rubric?)
4. **Standards audit** — 5-level hierarchical validation (standards.py)
5. **Evolve** — Update SOPs based on what the system learned

### Feedback Loop
This is the meta-loop. It governs the governance. When a loop breaks (e.g., follow-ups go 30 days overdue), this loop detects it and triggers remediation. When a SOP is inadequate (e.g., one-pass cover letters), this loop upgrades the SOP.

### CLI
```bash
python scripts/run.py standup        # Daily dashboard
python scripts/run.py verifyall      # Full verification
python scripts/run.py standards      # Hierarchical audit
python scripts/run.py diagnose       # System scorecard
```

---

## SOP Registry

| ID | Title | Loop | Location | Status |
|----|-------|------|----------|--------|
| SOP-INST-001 | Forced Revision Protocol | 3, 9 | aerarium/sops/grant-application-process.md | ACTIVE |
| SOP-SYS-001 | System Loops (this document) | ALL | docs/sop--system-loops.md | ACTIVE |
| SOP-DIS-001 | Discovery & Scoring | 1 | docs/sop--discovery.md | DRAFT |
| SOP-RES-001 | Research & Intelligence | 2 | docs/sop--research.md | DRAFT |
| SOP-BLD-001 | Material Production | 3 | docs/sop--build.md | DRAFT |
| SOP-SUB-001 | Submission & Outreach | 4 | docs/sop--submit.md | DRAFT |
| SOP-FOL-001 | Follow-Up Protocol | 5 | docs/sop--follow-up.md | DRAFT |
| SOP-CUL-001 | Network Cultivation | 6 | docs/sop--cultivate.md | DRAFT |
| SOP-OBS-001 | Observation & Analytics | 7 | docs/sop--observe.md | DRAFT |
| SOP-LRN-001 | Outcome Learning | 8 | docs/sop--learn.md | DRAFT |
| SOP-PUB-001 | Content Publication | 9 | docs/sop--publish.md | DRAFT |
| SOP-GOV-001 | Meta-Governance | 10 | docs/sop--govern.md | DRAFT |
| SOP-IRA-001 | Inter-Rater Agreement | 7, 10 | docs/sop--diagnostic-inter-rater-agreement.md | ACTIVE |

---

## Interval Triggers (LaunchAgent → Loop Mapping)

| LaunchAgent | Cadence | Loop(s) |
|-------------|---------|---------|
| daily-scan | Daily 6:15 AM | LOOP 1 (Discover) |
| daily-intake-triage | Daily 6:15 AM | LOOP 1 (Discover) |
| daily-deferred | Daily 6:00 AM | LOOP 5 (Follow Up) |
| daily-monitor | Daily 6:30 AM | LOOP 7 (Observe) |
| daily-health | Daily 6:30 AM | LOOP 7 (Observe) |
| agent-daily | Daily 7:00 AM | LOOP 10 (Govern) |
| calendar-refresh | Daily 6:45 AM | LOOP 7 (Observe) |
| weekly-backup | Sunday 2:00 AM | LOOP 7 (Observe) |
| weekly-briefing | Sunday 7:00 PM | LOOP 7 (Observe) |

### Missing Triggers (need LaunchAgents)
| Need | Cadence | Loop |
|------|---------|------|
| follow-up-check | Daily 8:00 AM | LOOP 5 — scan for DM windows |
| content-harvest | Daily 9:00 PM | LOOP 9 — extract content themes from today's work |
| network-sync | Weekly Monday 6:00 AM | LOOP 6 — sync graph, detect acceptances |
| outcome-check | Daily 10:00 AM | LOOP 8 — check for responses |
| sop-compliance | Weekly Monday 7:00 AM | LOOP 10 — are all loops healthy? |

---

## Principle

A process without a loop is a one-time event — it produces output but never improves. A loop without an SOP is an automated repetition — it runs but doesn't govern itself. A loop WITH an SOP is an institution — it runs, governs itself, and gets better with each cycle.

The system is 10 loops. Each loop has an SOP. Each SOP enforces a standard. Each standard produces measurable output. Each output feeds back into the next cycle. That is the engine. That is what we sell.
