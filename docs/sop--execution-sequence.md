---
id: SOP-SYS-002
title: "Execution Sequence — The Complete Loop Timeline"
scope: system
organ: III
tier: T1
status: active
---

# Execution Sequence

161 scripts. 67,244 lines. 10 loops. 3 deprecated. 5 one-off. 26 library modules. This is the complete timeline — every force the system exerts, in the order it fires.

---

## SYSTEM INVENTORY

| Loop | Scripts | Lines | Weight |
|------|---------|-------|--------|
| SHARED LIBS | 25 | 8,862 | Foundation — serves all loops |
| 1. DISCOVER | 8 | 4,071 | 6% of system |
| 2. RESEARCH | 13 | 4,536 | 7% |
| 3. BUILD | 22 | 10,479 | 16% ← heaviest loop |
| 4. SUBMIT | 12 | 6,496 | 10% |
| 5. FOLLOW UP | 10 | 3,900 | 6% |
| 6. CULTIVATE | 6 | 2,584 | 4% ← lightest loop |
| 7. OBSERVE | 24 | 8,241 | 12% |
| 8. LEARN | 20 | 7,919 | 12% |
| 9. PUBLISH | 3 | 1,096 | 2% ← most underdeveloped |
| 10. GOVERN | 18 | 9,060 | 13% |

**Diagnosis:** PUBLISH (Loop 9) is 2% of the system — 3 scripts, 1,096 lines. This is the revenue-generating loop. It should be 10-15% minimum. BUILD (Loop 3) at 16% is the heaviest — appropriate, it produces the primary artifacts. CULTIVATE (Loop 6) at 4% is thin — network is wide (182 nodes) but has no depth tooling.

---

## DAILY TIMELINE (6:00 AM → 10:00 PM)

### ═══ 6:00 AM — AUTOMATIC (LaunchAgents fire) ═══

```
06:00  LOOP 5   check_deferred.py --alert          Check deferred entries for re-activation
06:15  LOOP 1   score.py --all --include-pool       Score research pool (daily intake triage)
06:15  LOOP 1   scan_orchestrator.py                Discover + ingest new opportunities
06:30  LOOP 7   monitor_pipeline.py --strict        Backup check + signal freshness
06:30  LOOP 7   daily_pipeline_health.py            System health telemetry
06:45  LOOP 7   calendar_export.py --output ...     Refresh iCal with pipeline deadlines
07:00  LOOP 10  agent.py --execute --yes            Autonomous agent actions
```

### ═══ 7:00 AM — MORNING RITUAL (Human triggers) ═══

```
07:00  LOOP 7   morning.py                          Morning digest: health + stale + followups + campaign
         ├→ standup.py                              Pipeline dashboard (all sections)
         ├→ followup.py                             Today's follow-up actions
         ├→ check_outcomes.py                       Entries awaiting response
         └→ campaign.py                             Deadline-aware campaign view
```

**Decision point:** Morning digest surfaces what needs attention. Human decides today's focus.

### ═══ 8:00 AM — LOOP 5: FOLLOW UP (highest daily leverage) ═══

```
08:00  LOOP 5   followup.py                         Scan all submitted entries for DM windows
08:10  LOOP 5   dm_composer.py --all-pending        Generate Protocol-validated DMs
         └→ protocol_validator.py                   Validate against 7 Protocol articles
08:20  LOOP 5   [HUMAN] Send DMs via LinkedIn       Human-gated delivery
08:30  LOOP 5   log_dm.py --contact <name>          Log to contacts + outreach-log + network
         └→ reconcile_outreach.py                   Sync if DMs sent outside system
```

### ═══ 9:00 AM — LOOP 6: CULTIVATE (network maintenance) ═══

```
09:00  LOOP 6   crm.py                              CRM dashboard — new acceptances?
09:10  LOOP 6   network_graph.py --ingest           Ingest new contacts + outreach into graph
09:15  LOOP 6   cultivate.py                        Relationship cultivation candidates
09:20  LOOP 6   warm_intro_audit.py                 Referral paths for active entries
```

### ═══ 9:30 AM — LOOP 1+2: DISCOVER + RESEARCH (per weekly rhythm) ═══

**Monday only (Jobs):**
```
09:30  LOOP 1   source_jobs.py                      Fetch from ATS APIs
09:40  LOOP 1   discover_jobs.py                    Skill-based discovery
09:50  LOOP 1   ingest_top_roles.py                 Top roles ≥ 7.0 score
10:00  LOOP 1   score.py --auto-qualify --yes        Promote qualified entries
10:10  LOOP 2   research_contacts.py --target <id>   3 fresh contacts per target
10:20  LOOP 2   org_intelligence.py --all            Org rankings
10:30  LOOP 2   text_match.py --target <id>          Keyword match analysis
```

**Tuesday only (Grants):**
```
09:30  LOOP 2   external_validator.py --fetch-only   Refresh market data
09:40  LOOP 2   research_analytics.py                Research landscape analysis
10:00  LOOP 2   [Aerarium SOP-INST-001]              Grant research (parallel agents)
```

**Wednesday only (Consulting):**
```
09:30  LOOP 6   crm.py --org <client>                Client relationship status
09:40  LOOP 2   org_intelligence.py --org <client>    Client intelligence
10:00  LOOP 2   skills_gap.py --target <id>           Skills gap for consulting scope
```

### ═══ 10:00 AM — LOOP 3: BUILD (material production) ═══

**Per-entry, when entry is in drafting/staged:**
```
10:00  LOOP 3   enrich.py --target <id>              Wire materials, blocks, variants
10:10  LOOP 3   tailor_resume.py --target <id>       Generate tailoring prompt
         └→ [AI REVISION CYCLE — SOP-INST-001 Phases 2-5]
            Phase 2: Raw material in scratch/
            Phase 3: Forced compression to character limits
            Phase 4: Verification (hall-monitor audit)
            Phase 5: Citrinitas (read-aloud purification)
10:30  LOOP 3   tailor_resume.py --target <id> --integrate   Splice AI output into template
10:35  LOOP 3   build_resumes.py --target <id>       Chrome headless → PDF (verify 1 page)
10:40  LOOP 3   recruiter_filter.py                  Canonical metrics validation
10:45  LOOP 3   check_metrics.py                     Block metric consistency
10:50  LOOP 3   materials_validator.py                Full materials audit
         └→ validate_sentence_completeness()         Catch truncated sentences
11:00  LOOP 3   apply.py --target <id>               Full pipeline: CL + resume + portal + DM + PDF
         ├→ URL liveness check
         ├→ Standards L1 audit
         ├→ Portal answer validation (blank required fields)
         ├→ Overlap check (CL vs resume)
         └→ Continuity test (all files present)
```

### ═══ 11:00 AM — LOOP 4: SUBMIT (human-gated) ═══

```
11:00  LOOP 4   preflight.py --target <id>           Pre-submission readiness check
11:10  LOOP 4   submit.py --target <id>              Generate paste-ready checklist
11:15  LOOP 4   [HUMAN] Open portal, paste, upload    Human submits via browser
11:20  LOOP 4   submit.py --target <id> --record      Record submission + update YAML
11:25  LOOP 4   advance.py --to submitted --id <id>  Advance status
11:30  LOOP 4   [FRESH OUTREACH]
         ├→ research_contacts.py --target <id>       3 new contacts
         ├→ [HUMAN] Send connect requests            Human-gated
         └→ log_dm.py / followup.py --log            Record actions
```

### ═══ 12:00 PM — DEEP BUILD (Creation-first — daily constant) ═══

```
12:00-  [CREATE] Build. Code. Ship. The creation IS the constant.
 5:00   This is not pipeline time — this is studio time.
        Whatever is being built today (ORGANVM, client work, open source)
        produces the artifacts that feed LOOP 9.
```

### ═══ 5:00 PM — LOOP 8: LEARN (outcome processing) ═══

```
17:00  LOOP 8   check_outcomes.py                    Scan for responses
17:10  LOOP 8   feedback_capture.py                  Record outcome hypotheses
17:15  LOOP 8   rejection_learner.py                 Rejection dimension analysis (if applicable)
17:20  LOOP 8   block_outcomes.py                    Block-outcome correlation update
```

### ═══ 6:00 PM — LOOP 9: PUBLISH (content production) ═══

```
18:00  LOOP 9   [HARVEST] Extract content themes from today's work
         ├→ What was built? (micro-content)
         ├→ What was applied? (application-as-research)
         ├→ What was learned? (outcome data)
         └→ What was observed? (system insight)
18:15  LOOP 9   linkedin_composer.py --audit          Audit existing Testament posts
18:20  LOOP 9   [DRAFT] Select mask (Narrator/Strategist/Architect/Integrator)
         └→ Write in scratch/ — SOP-INST-001 Phase 2
18:40  LOOP 9   linkedin_composer.py --audit <post>   Audit against 13 Testament articles
18:50  LOOP 9   [PUBLISH if 6/8+] Post to LinkedIn    Micro-content daily, Testament 2x/week
19:00  LOOP 9   [EXPAND weekly] Dev.to article        Cathedral → Storefront expansion
```

### ═══ 7:00 PM — LOOP 7: OBSERVE (end-of-day) ═══

```
19:00  LOOP 7   snapshot.py --save                    Save daily pipeline snapshot
19:10  LOOP 7   pipeline_status.py                    End-of-day status
```

### ═══ 9:00 PM — LOOP 10: GOVERN (weekly/periodic) ═══

**Monday evening:**
```
21:00  LOOP 10  validate.py --check-id-maps --check-rubric   Full validation
21:10  LOOP 10  validate_signals.py --strict                  Signal YAML integrity
21:15  LOOP 10  verification_matrix.py --strict               Module-to-test coverage
21:20  LOOP 10  hygiene.py                                    URL liveness, staleness, gates
21:30  LOOP 10  triage.py                                     Demote sub-threshold, resolve org-cap
```

**Sunday evening:**
```
21:00  LOOP 7   weekly_brief.py --save                Weekly executive summary
02:00  LOOP 7   backup_pipeline.py create             Weekly backup (LaunchAgent)
```

**Quarterly:**
```
       LOOP 8   recalibrate.py                        Scoring weight adjustment proposal
       LOOP 8   quarterly_report.py                   Full analytics
       LOOP 10  diagnose.py                           System diagnostic scorecard
       LOOP 10  generate_ratings.py                   Multi-model IRA rating session
       LOOP 10  diagnose_ira.py ratings/*.json        Inter-rater agreement report
       LOOP 10  standards.py --run-all                5-level hierarchical audit
```

---

## LIFECYCLE: One Entry's Journey Through All Loops

```
DAY 0   LOOP 1   source_jobs discovers opportunity
        LOOP 1   score.py scores at 8.4/10 → qualifies
DAY 0   LOOP 2   research_contacts finds 3 people
        LOOP 2   org_intelligence profiles the company
        LOOP 2   text_match confirms keyword alignment
DAY 1   LOOP 3   tailor_resume generates prompt → AI revises → integrate
        LOOP 3   build_resumes → 1-page PDF
        LOOP 3   apply.py → full package (CL + resume + portal + DM)
        LOOP 3   quality gates: sentence completeness ✓, page fill ✓, link liveness ✓
DAY 1   LOOP 4   submit via portal (human-gated)
        LOOP 4   3 connect requests sent, logged
DAY 2   LOOP 9   PUBLISH: extract content theme from application research
        LOOP 9   Testament post drafted, audited, published
DAY 3   LOOP 5   connect accepted → DM composed → sent → logged
DAY 7   LOOP 5   first follow-up DM (Day 7 window)
DAY 7   LOOP 6   network_graph updated with new edge
DAY 14  LOOP 5   final follow-up (Day 14-21 window)
DAY 14  LOOP 7   snapshot captures entry age, follow-up status
DAY 21  LOOP 8   check_outcomes → rejection received
        LOOP 8   feedback_capture → record hypothesis
        LOOP 8   rejection_learner → dimension analysis
        LOOP 8   block_outcomes → update block correlations
DAY 21  LOOP 9   PUBLISH: "What I Learned From This Rejection" → content
QUARTERLY LOOP 8  recalibrate → adjust scoring weights based on outcome patterns
          LOOP 10 standards audit → verify all loops healthy
```

---

## DEAD / RETIRED / DEPRECATED

| Script | Status | Reason | Replacement |
|--------|--------|--------|-------------|
| daily_batch.py | DEPRECATED | Replaced by campaign.py --execute | campaign.py |
| daily_pipeline.py | DEPRECATED | Replaced by standup.py --section plan | standup.py |
| verify_sources.py | DEPRECATED | Functionality absorbed into hygiene.py | hygiene.py |
| backfill_dates.py | ONE-OFF | Migration script, ran once | — |
| fix_json_metrics.py | ONE-OFF | One-time JSON repair | — |
| generate_from_templates.py | ONE-OFF | Initial template generation | — |
| migrate.py | ONE-OFF | Pipeline schema migration | — |
| migrate_batch_folders.py | ONE-OFF | Batch directory restructure | — |

---

## GAPS (what the system needs but doesn't have)

### LOOP 9: PUBLISH — critically underdeveloped (3 scripts, 1,096 lines = 2% of system)

| Need | Description | Priority |
|------|-------------|----------|
| content_harvester.py | Extract content themes from applications, outcomes, system changes. Input: entry YAML + cover letter + portal answers. Output: content brief with mask assignment. | P0 |
| content_calendar.py | Schedule content across channels (LinkedIn 2x/week, Dev.to 1x/week, micro daily). Track what's published, what's drafted, what's audited. | P1 |
| devto_publisher.py | Format Testament posts into Dev.to articles with code blocks, screenshots, canonical URLs. Cross-post to Hashnode. | P1 |
| demo_recorder.py | Script screen recordings of pipeline CLI and Inverted Interview flow. Generate demo assets for Product Hunt, YouTube. | P2 |
| newsletter_composer.py | Weekly digest for email subscribers (when audience exists). Pulls from weekly_brief + content calendar. | P2 |

### LOOP 6: CULTIVATE — thin (6 scripts, 2,584 lines = 4% of system)

| Need | Description | Priority |
|------|-------------|----------|
| acceptance_monitor.py | Auto-detect LinkedIn connection acceptances (via reconcile_outreach or API). Trigger DM composition immediately. | P0 |
| relationship_velocity.py | Track dormant→weak→moderate→strong transitions over time. Dashboard showing network deepening rate. | P1 |
| referral_tracker.py | Track referral requests made, referrals received, referral outcomes. The 8x hire rate multiplier needs measurement. | P1 |

### LOOP 4: SUBMIT — no browser automation for non-Greenhouse portals

| Need | Description | Priority |
|------|-------------|----------|
| universal_submitter.py | Browser automation for custom portals (Ashby, Workable, Lever native, company websites). Currently only Greenhouse has API submission. | P2 |

### CROSS-LOOP: identity.yaml integration

| Need | Description | Priority |
|------|-------------|----------|
| Replace 22 scripts' hardcoded values | Wire load_identity() into apply.py, build_cover_letters.py, dm_composer.py, recruiter_filter.py, etc. | P0 |
| identity_sync.py | Bidirectional sync between config/identity.yaml and in-midst-my-life /profiles/:id API. | P1 |
