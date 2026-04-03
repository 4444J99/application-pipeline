# Session Plan: Four-Stream Hygiene + Prep Pass

**Date:** 2026-04-02
**Context:** Handoff review surfaced 5 pressure points beyond the 3 declared. Pipeline health 7.2/10 but precision mode violated 5.7x (57/10 cap). Creative Capital closes today. Grafana screen in 4 days. ZKM in 10 days. 20+ overdue follow-ups. User selected all four work streams.

---

## Stream 1: Hygiene Triage (clears the decks — do first)

### 1a. Creative Capital final disposition
- **File:** `pipeline/closed/creative-capital-2027.yaml` — already in `closed/`. Confirm it has terminal outcome. No action needed if properly closed.

### 1b. Bulk archive stale auto-sourced entries (cap violation: 57 → ≤10)
The 57 actionable entries are almost all auto-sourced `qualified` jobs at 72h+ stale. Strategy:

1. **Run `python scripts/hygiene.py --flash --dry-run`** — preview what 72h flash would archive
2. **Run `python scripts/hygiene.py --company-focus --limit 1 --dry-run`** — identify per-company defer targets
3. **Keep max 1 per org** (the highest-scoring fresh entry). Archive the rest to `research_pool/` or close:
   - **Toast**: keep `toast-senior-backend-engineer` (submitted, immutable). Archive 16 active qualified.
   - **Samsara**: keep 1 (highest score: `samsara-senior-software-engineer-growth` at 7.2, WARM). Archive 13.
   - **Coinbase**: keep 1 (`coinbase-senior-software-engineer-blockchain-data-storage` at 8.5). Archive 4.
   - **Grafana**: keep the interview entry (submitted, immutable). Archive 3 remaining active (or defer — see 1c).
   - **Ramp**: keep `ramp-software-engineer-argentina` (8.3). Archive 1.
   - **Neo4j**: keep `neo4j-developer-advocate` (7.1). Archive 1.
4. **Run `python scripts/hygiene.py --flash --yes`** for the 72h purge
5. **Run `python scripts/hygiene.py --prune-research --older-than 30 --dry-run`** — preview stale research_pool cleanup (1,694 entries)
6. **Post-triage target:** ≤10 actionable entries

### 1c. Grafana-specific defer decision
With a live interview at Grafana, the 3 other Grafana qualified entries should be **deferred** (not archived) with reason `"interview_active"` and `resume_date: "2026-04-07"` (day after screen). If the screen goes well, they become leverage (internal mobility). If not, they reactivate.

### 1d. Deferred entries audit
6 deferred entries have no `resume_date`. Set resume dates or archive:
- Anthropic Voice Platform, Stripe Stream Compute, Toast Enterprise Financial, Snorkel Pre-Sales, Cursor Client Infra, Notion DevEx — all `strategic_hold`. Set `resume_date: "2026-04-15"` (2-week review) or close stale ones.

### 1e. Research pool cleanup
- `python scripts/hygiene.py --prune-research --older-than 90 --yes` — archive entries >90 days old with no score

**Verification:** `python scripts/run.py standup` — precision compliance section should show ≤10 actionable, ≤1 per org.

---

## Stream 2: Grafana Interview Prep (Mon Apr 6)

Execute avalanche relays 1-4 from `.claude/plans/2026-04-01-grafana-interview-avalanche.md`:

### Relay 1: Fill entry vacuums
- Read `pipeline/submitted/grafana-labs-staff-ai-engineer-people-technology-nasa-remote.yaml`
- Fetch job posting from Greenhouse URL
- Populate N/A fields: `target.description`, `amount.value`, `fit.framing`, `fit.extracted_keywords`, `network` section
- Validate: `python scripts/validate.py`
- Commit

### Relay 2: CLAUDE.md PR on grafana/metrics-drilldown
- Clone to worktree, read codebase, write CLAUDE.md, open PR referencing issue #1146
- **Decision point:** User must confirm this is genuine interest, not performance (per handoff)

### Relay 3: MCP security comment on grafana/mcp-grafana#680
- Read issue, draft substantive prompt injection defense comment
- **Decision point:** Same authenticity check

### Relay 4: Send email to Ryan McKellips
- Surface draft for review, send via Gmail, delete old draft, log outreach

**Relay 5-7:** Time-gated for Apr 3-6. Not this session.

**Verification:** Entry has 0 N/A vacuums. Outreach logged. PRs visible.

---

## Stream 3: ZKM Rauschenberg (10 days to deadline)

**Current state:** `drafting`, score 7.0, identity position: systems-artist. Has variant IDs assigned but `materials_ready` is null. Portal fields: resume, artist_statement, project_description, work_samples.

### Steps:
1. Check which variant files actually exist:
   - `materials/variants/cover-letters/zkm-rauschenberg-alchemized.md`
   - `materials/variants/statements/zkm-rauschenberg-artist-statement.md`
   - `materials/variants/project-descriptions/zkm-rauschenberg-proposal.md`
2. For missing materials, compose using blocks: `identity/5min`, `projects/organvm-system`, `methodology/governance-as-art`, `evidence/differentiators`, `framings/systems-artist`
3. Build/select work samples — portfolio URL exists, but ZKM likely wants direct samples
4. Tailor resume: `python scripts/tailor_resume.py --target zkm-rauschenberg --wire`
5. Build PDF: `python scripts/build_resumes.py --target zkm-rauschenberg`
6. Run compose: `python scripts/compose.py zkm-rauschenberg`
7. Advance to staged: `python scripts/advance.py zkm-rauschenberg --to staged`
8. Note: still needs at least 1 outreach action before `submitted`

**Verification:** `python scripts/run.py gate zkm-rauschenberg` passes. Materials exist at all variant paths.

---

## Stream 4: Follow-up Blitz

### Triage overdue actions into 3 buckets:

**A. Final follow-up + close loop** (>21 days, past all protocol windows):
- Supabase (Day 37) — final follow-up, then move to `outcome: no_response`
- Gay & Lesbian Review, Logic Magazine, MIT TR/Wired/Aeon, Noema Magazine (Day 35) — writing submissions, final follow-up
- Awesome Foundation (Day 36)

**B. First/second follow-up** (7-16 days):
- Harvey AI (Day 16), LangChain (Day 16), OpenAI (Day 16), Stripe (Day 16) — DM follow-up
- Anthropic Editorial (Day 13), Cursor Enterprise (Day 13), Render (Day 13) — LinkedIn connect + DM
- Doppler (Day 16) — connect + follow-up

**C. Research fresh contacts** (per feedback: never recycle):
- For each submitted entry needing outreach, research 3 fresh contacts
- Log via `python scripts/log_dm.py` or `python scripts/followup.py --log`

### Execution:
1. For each entry in bucket A: compose final follow-up, log, advance to outcome if no response
2. For each entry in bucket B: research contacts, compose Protocol-validated DM, log
3. Update `signals/outreach-log.yaml` and `signals/contacts.yaml` for each action

**Verification:** `python scripts/run.py followup` shows 0 overdue after processing.

---

## Execution Order

1. **Stream 1** (hygiene) — 20 min. Clears noise, restores compliance.
2. **Stream 2** (Grafana relays 1-4) — 40 min. Time-critical, highest conversion probability.
3. **Stream 3** (ZKM) — 30 min. 10-day deadline, materials assembly.
4. **Stream 4** (follow-ups) — 30 min. Relationship maintenance.

Total estimated: ~2 hours.

## Post-Session Verification

```bash
python scripts/run.py standup          # Health should be ≥8.0, compliance ≤10
python scripts/run.py freshness        # Stale count should drop dramatically
python scripts/run.py followup         # Overdue count should drop to <5
python scripts/validate.py             # 0 validation errors
pytest tests/ -q --tb=no              # No regressions
```

## Handoff Requirements

Per feedback_session_handoff_protocol.md: write handoff file at `.claude/plans/2026-04-02-session-handoff-S53.md` before close. Include: what happened, user state, decisions, artifacts, hanging actions, what next session must know.
