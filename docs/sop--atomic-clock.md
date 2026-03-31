---
id: SOP-SYS-004
title: "The Atomic Clock — Natural Sequencing of All Forces"
scope: system
organ: III
tier: T0
status: active
---

# The Atomic Clock

Every action in this system is a collision on an eternal propelling clock. The BPM is the weekly rhythm. The click track is the daily sequence. The atoms are the scripts. The bonds are the imports. The timeline emerges from the physics — not from a plan imposed on the physics.

---

## THE FOUR LAYERS

### Layer 0: ATOMS (36 scripts — no internal dependencies)

Pure primitives. Each one does exactly one thing. No coupling. These are the quarks.

```
build_block_index     build_cover_letters   build_resumes
check_metrics         classify_position     cli
derive_positions      diagnose_ira          launchd_manager
market_intel          pipeline_api          protocol_types
run                   source_jobs_constants yaml_mutation
... (36 total)
```

**Clock position:** These fire independently. Any time. Any order. No sequencing required.

### Layer 1: MOLECULES (5 scripts — depend only on atoms)

First bonds. Two atoms combine to produce a function that neither could alone.

```
pipeline_entry_state + pipeline_market  →  pipeline_freshness
pipeline_market                         →  pipeline_lib
check_metrics                           →  funding_metrics
score_constants                         →  enrich_prestige
protocol_types                          →  protocol_validator
```

**Clock position:** Must fire after their atoms. But can fire in parallel with each other.

### Layer 2: COMPOUNDS (91 scripts — depend on molecules)

The workhorses. Every compound depends on pipeline_lib (the central molecule). These are the 10 loops' moving parts.

```
pipeline_lib → score, standup, validate, advance, followup,
               dm_composer, network_graph, crm, tailor_resume,
               apply, submit, diagnose, snapshot, ...
               (91 total)
```

**Clock position:** Must fire after pipeline_lib loads. Within this layer, sequencing is determined by the LOOP they belong to, not by dependency.

### Layer 3: ORGANISMS (29 scripts — deep dependency chains)

Multi-bond structures. Each organism orchestrates multiple compounds.

```
campaign        ← score + enrich + pipeline_lib
alchemize       ← greenhouse_submit + enrich + yaml_mutation + pipeline_lib
browser_submit  ← ashby_submit + submit + greenhouse_submit + ats_base + pipeline_lib
weekly_brief    ← submission_audit + velocity_report + check_outcomes + warm_intro_audit + pipeline_lib
scan_orchestrator ← discover_jobs + ingest_top_roles + source_jobs + pipeline_lib
daily_pipeline_orchestrator ← apply_engine + match_engine + scan_orchestrator + outreach_engine + material_builder
```

**Clock position:** These are the heartbeats — the weekly/daily triggers that fire cascades through the layers below.

---

## THE CLICK TRACK (daily BPM)

```
BEAT 1  ──── 06:00 ──── LAYER 3 ORGANISMS fire (LaunchAgents)
  │                      scan_orchestrator → discover_jobs → source_jobs → score
  │                      daily_pipeline_orchestrator → all sub-engines
  │
BEAT 2  ──── 07:00 ──── LAYER 2 COMPOUNDS report (morning digest)
  │                      morning → standup → campaign → followup → check_outcomes
  │
BEAT 3  ──── 08:00 ──── LAYER 2 COMPOUNDS act (follow-up loop)
  │                      followup → dm_composer → protocol_validator → log_dm
  │                      crm → network_graph → cultivate → warm_intro_audit
  │
BEAT 4  ──── 09:30 ──── LAYER 3 ORGANISMS build (per weekly rhythm)
  │                      Mon: score → enrich → tailor_resume → apply → submit
  │                      Tue: research_contacts → org_intelligence → draft
  │                      Wed: crm → cultivate → prepare_submission
  │
BEAT 5  ──── 12:00 ──── CREATION (not a layer — the constant)
  │                      Build. Code. Ship. The work itself.
  │
BEAT 6  ──── 17:00 ──── LAYER 2 COMPOUNDS learn (outcome loop)
  │                      check_outcomes → rejection_learner → block_outcomes
  │                      feedback_capture → validate_hypotheses
  │
BEAT 7  ──── 18:00 ──── LAYER 0 ATOMS publish (content loop)
  │                      linkedin_composer → build_block_index
  │                      (harvest from today's BEAT 4 + BEAT 5 work)
  │
BEAT 8  ──── 19:00 ──── LAYER 2 COMPOUNDS observe (snapshot)
  │                      snapshot → pipeline_status → monitor_pipeline
  │
BEAT 9  ──── 21:00 ──── LAYER 3 ORGANISMS govern (Monday only)
  │                      validate → validate_signals → verification_matrix
  │                      hygiene → triage → standards
  │
REST    ──── 22:00 ──── Clock resets. Loop begins again.
```

---

## THE WEEKLY MEASURE (bar structure)

```
         Mon        Tue        Wed        Thu        Fri        Sat/Sun
BEAT 4:  JOBS       GRANTS     CONSULT    BUILD      HYGIENE    REST
         score      research   crm        create     archive    backup
         enrich     draft      cultivate  create     hygiene    weekly_brief
         tailor     advance    propose    create     triage
         apply      submit     SOW        create
         submit                invoice    create
```

Each day is one bar. BEAT 4 changes its instrument per the weekly rhythm. Every other beat stays constant — the click track doesn't change, only the solo.

---

## THE QUARTERLY CYCLE (movement structure)

```
MONTH 1 ──── Discover + Build
  Week 1: Source → Score → Qualify (LOOP 1)
  Week 2: Research → Tailor → Build (LOOPS 2-3)
  Week 3: Submit → Outreach → Follow up (LOOPS 4-5)
  Week 4: Cultivate → Observe → Snapshot (LOOPS 6-7)

MONTH 2 ──── Learn + Publish
  Week 5: Outcomes arrive → Learn → Correlate (LOOP 8)
  Week 6: Content harvest → Draft → Audit → Publish (LOOP 9)
  Week 7: Standards audit → Recalibrate → Govern (LOOP 10)
  Week 8: Apply learnings → Adjust scoring → Next cycle

MONTH 3 ──── Compound + Grow
  Week 9:  New cycle with improved scoring
  Week 10: Network deepening (dormant → weak → moderate)
  Week 11: Product development (publish loop expansion)
  Week 12: Quarterly report → Recalibrate → Plan next quarter
```

---

## THE LIFECYCLE OF ONE ENTRY (from birth to archival)

```
TICK 0   ATOM       source_jobs discovers opportunity
TICK 1   COMPOUND   score evaluates (9 dimensions)
TICK 2   COMPOUND   research_contacts finds 3 people
TICK 3   COMPOUND   org_intelligence profiles the company
TICK 4   COMPOUND   text_match confirms keyword alignment
TICK 5   ORGANISM   enrich wires materials + blocks
TICK 6   COMPOUND   tailor_resume generates prompt
TICK 7   [HUMAN]    AI revision cycle (SOP-INST-001 Phases 2-5)
TICK 8   COMPOUND   tailor_resume --integrate splices output
TICK 9   ATOM       build_resumes → 1-page PDF
TICK 10  ATOM       build_cover_letters → 1-page PDF
TICK 11  ORGANISM   apply → full package (CL + resume + portal + DM)
TICK 12  COMPOUND   preflight → pre-submission check
TICK 13  [HUMAN]    submit via portal (human-gated)
TICK 14  COMPOUND   advance → status = submitted
TICK 15  COMPOUND   followup → Day 1-3 connect requests
TICK 16  COMPOUND   log_dm → record interactions
TICK 17  [WAIT]     Day 7 → dm_composer → first follow-up DM
TICK 18  [WAIT]     Day 14 → followup → final follow-up
TICK 19  COMPOUND   check_outcomes → response received (or silence)
TICK 20  COMPOUND   feedback_capture → record hypothesis
TICK 21  COMPOUND   rejection_learner → dimension analysis (if rejected)
TICK 22  COMPOUND   block_outcomes → update correlations
TICK 23  ATOM       linkedin_composer → publish content from the research
TICK 24  COMPOUND   snapshot → record in daily snapshot
TICK 25  [QUARTERLY] recalibrate → adjust scoring weights
TICK 26  COMPOUND   archive_research → close entry
```

26 ticks. One entry. Birth to archival. Every tick is a script. Every script is in a layer. Every layer fires in order. The clock never stops — it just starts the next entry.

---

## MULTI-AGENT CLOCK DISTRIBUTION

```
TICK     CLAUDE              GEMINI              CODEX               OPENCODE
─────    ─────────────       ──────────          ─────               ────────
0-1      morning digest      —                   —                   —
2-4      compose DMs         batch CSS/HTML       type hints          contact research
5-8      tailor + revise     file audits          dead code removal   funder research
9-11     apply (judgment)    build PDFs           —                   —
12-13    [HUMAN SUBMIT]      —                    —                   —
14-16    advance + log       bulk YAML updates    —                   —
17-18    DM composition      —                    —                   —
19-22    outcome analysis    —                    refactor learners   market research
23       content composition —                    —                   —
24-25    governance          test suite run        —                   —
```

Four agents on one clock. Non-competing beats. The Conductor scores for all instruments.

---

## CALENDAR DERIVATION (all pawns move forward)

Every entry in the pipeline is a pawn. Every pawn moves forward through the 26 ticks. The calendar is the sum of all pawns' positions.

```python
# The calendar is not planned — it is computed from the state machine
for entry in all_entries:
    tick = current_tick(entry)
    next_action = TICK_SEQUENCE[tick]
    due_date = compute_due_date(entry, tick)
    assign_to_agent(next_action)
    schedule(next_action, due_date)
```

No pawn moves backward. No tick is skipped. The clock propels every pawn forward at the BPM set by the weekly rhythm. The calendar IS the state machine — viewed from the macro perspective.

---

## PRINCIPLE

The smallest atomic pair (one script calling another) produces a function. That function has a tick. The ticks compose into a daily beat. The beats compose into a weekly bar. The bars compose into a quarterly movement. The movements compose into the lifecycle. The lifecycle IS the product.

Every plan starts with the archetype (which loop, which layer, which agent). Every plan ends with the logged return to source (outcome recorded, scoring updated, content published, entry archived). The distance between start and end is measured in ticks, not in time. Time is the medium. The clock is the structure. The pawns move forward in stride.
