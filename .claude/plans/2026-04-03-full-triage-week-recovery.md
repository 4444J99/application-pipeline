# Full Pipeline Triage — Week of Disengagement Recovery

## Context

One week of zero engagement: no applications, no LinkedIn activity, no email responses, no follow-ups logged. The automated infrastructure held (health 8.2/10, 3 agent runs executed 4,820 actions), but the human-side relationship layer decayed: 30 overdue follow-ups, 0 submissions in 8 days, org cap violations from auto-sourced entries piling up unreviewed.

**Most critical item:** Grafana Labs recruiter screen is Monday April 6 at 10:30 AM EDT — the pipeline's first positive conversion. Everything else orbits that.

---

## Phase 1: Grafana Interview Prep (30 min)

Interview prep doc already exists (`pipeline/submissions/grafana-labs-staff-ai-engineer-people-technology-nasa-remote-interview-prep.md`, prepared Apr 1). It's solid — STAR stories, company intel, alignment map, questions to ask.

**Actions:**
1. Run `python scripts/interview_prep.py --target grafana-labs-staff-ai-engineer-people-technology-nasa-remote` to refresh/regenerate
2. Run `python scripts/org_intelligence.py --target grafana-labs-staff-ai-engineer-people-technology-nasa-remote` for latest org intel
3. Run `python scripts/skills_gap.py --target grafana-labs-staff-ai-engineer-people-technology-nasa-remote` for gap analysis
4. Review the Guide.co candidate portal: `https://app3.guide.co/guide/grafana/hEmYUXEc`
5. Verify 4 deferred Grafana roles have correct `resume_date: 2026-04-07` (reactivate after interview)

**Key interview facts:**
- 30-min recruiter screen, audio only, Google Meet
- BrightHire AI notetaker active
- Ryan McKellips (recruiter)
- First AI engineer on People Technology team — greenfield
- Interview pipeline: Intro Call → HM Interview → Team → Coding → Wayfinder → Offer
- Comp: $174,986 - $209,983 USD base

---

## Phase 2: Today's Final Follow-ups (20 min)

Three entries hit Day 14 TODAY — last chance for final follow-up before the window closes:

| Entry | Day | Action |
|-------|-----|--------|
| `anthropic-engineering-editorial-lead` | 14 | Final follow-up |
| `cursor-software-engineer-enterprise-platform` | 14 | Final follow-up |
| `render-software-engineer-billing` | 14 | Final follow-up |

**Actions:**
1. For each: send LinkedIn message or email (actual human action — LinkedIn/email)
2. Log each via: `python scripts/followup.py --log <entry-id> --channel linkedin --contact "<name>" --note "Day 14 final follow-up" --type dm`

---

## Phase 3: Overdue Follow-up Batch (45 min)

26 total overdue actions. Prioritize by company strategic value and recency:

### Tier 1 — High-value companies, 14-17 days overdue (do today)
| Entry | Day | Action Needed |
|-------|-----|---------------|
| Harvey AI (agents role) | 17 | First DM follow-up |
| LangChain (enterprise readiness) | 17 | First DM follow-up |
| OpenAI (FDE) | 17 | LinkedIn connect |
| Stripe (smart contract) | 17 | LinkedIn connect |
| Doppler (staff full-stack) | 17 | LinkedIn connect |

### Tier 2 — Recent submissions (do today/tomorrow)
| Entry | Day | Action Needed |
|-------|-----|---------------|
| Coinbase (various) | ~14 | LinkedIn connect |
| Tailscale (Go core) | varies | Check status |
| Toast (senior backend) | varies | Check status |
| Webflow (FDE) | varies | Check status |
| Temporal (OSS server) | varies | Check status |

### Tier 3 — Aged (36-38 days) — triage decision needed
| Entry | Day | Status |
|-------|-----|--------|
| Supabase DevRel | 38 | Way past all windows |
| Gay & Lesbian Review | 36 | Writing track |
| Logic Magazine | 36 | Writing track |
| MIT Tech Review / Wired / Aeon | 36 | Writing track |
| Noema Magazine | 36 | Writing track |
| Awesome Foundation | 37 | Grant |
| Doris Duke / Mozilla | 38 | Grant |

**Decision for Tier 3:** These are past all follow-up windows. Options:
- Writing submissions (GLR, Logic, MIT TR, Noema): Close follow-up tracking. These are editorial submissions — follow-up protocols don't apply the same way.
- Grant submissions (Awesome, Doris Duke): One final "checking in" message, then close follow-up.
- Supabase: 38 days with no response = likely dead. Mark accordingly.

**Logging:** After each real-world action (LinkedIn connect, DM, email), log via `followup.py --log` or `log_dm.py`.

---

## Phase 4: Precision Compliance Fix (15 min)

Currently 16 actionable entries, cap is 10. Org cap violated (Affirm x2, Instacart x2).

### Org Cap Resolution

**Affirm:** Keep `affirm-senior-software-engineer-full-stack-zero-to-one-labs` (ZT1 innovation lab, AI-native, agentic workflows — better ORGANVM fit). Defer `affirm-senior-software-engineer-infrastructure` (security infra, less aligned).

**Instacart:** Keep `instacart-senior-software-engineer-data-governance-foundations` (data governance, US remote, stronger match). Close or defer `instacart-senior-software-engineer-ii-page-builder-retailer-platform` (frontend/Canada-only, stale 72h).

### Reducing from 16 to 10

After org cap fixes (16 → 14), need to drop 4 more. Candidates for deferral by lowest freshness-weighted score:
- `dbt-labs-senior-developer-experience-advocate` — stale 72h, score 0.0 weighted
- `instacart-senior-software-engineer-ii-page-builder-retailer-platform` — stale 72h, Canada-only
- `mongodb-senior-software-engineer-atlas-stream-processing` — stale 72h, score 0.0 weighted
- `scale-ai-senior-software-engineer` — stale 72h, score 0.0 weighted

**Actions:**
1. Defer Affirm Infrastructure: `python scripts/advance.py --id affirm-senior-software-engineer-infrastructure --to deferred --yes`
2. Close Instacart Page Builder: `python scripts/advance.py --id instacart-senior-software-engineer-ii-page-builder-retailer-platform --to deferred --yes`
3. Defer the 4 stale-scored entries (or archive if postings are dead)
4. Verify: `python scripts/standup.py` should show ≤10 actionable, no org cap violations

---

## Phase 5: ZKM Rauschenberg (30 min — separate session if needed)

- **Deadline:** April 12 (9 days)
- **Current status:** drafting
- **Track:** residency, score 7.0

**Actions:**
1. Run `python scripts/compose.py --target zkm-rauschenberg-residencies` to draft from blocks
2. Run `python scripts/tailor_resume.py --target zkm-rauschenberg-residencies` for resume
3. Move to staged when materials ready
4. Can be done tomorrow — interview prep and follow-ups are higher urgency

---

## Phase 6: Hygiene Pass (15 min)

**Actions:**
1. `python scripts/hygiene.py --auto-expire --dry-run` — preview expired entry cleanup
2. `python scripts/hygiene.py --auto-expire --yes` — execute
3. `python scripts/hygiene.py --company-focus --limit 1` — verify org cap resolved
4. `python scripts/hygiene.py --rotate-signals --dry-run` — preview stale signal rotation
5. `python scripts/hygiene.py --rotate-signals --yes` — execute
6. `python scripts/snapshot.py --save` — record post-triage state

---

## Phase 7: LinkedIn & Email Catch-up (human-driven, 30 min)

This is the non-automatable part. The pipeline can generate templates and log actions, but you need to:

1. **LinkedIn:** Open LinkedIn, review notifications, accept pending connections, respond to messages
2. **Email:** Check for any recruiter responses, interview invitations, rejection notices
3. **Log outcomes:** For any email responses received, run `python scripts/check_outcomes.py` and `python scripts/check_email.py`
4. **Update entries:** If any responses received, update pipeline YAML status fields accordingly

---

## Execution Sequence (recommended order)

| # | Phase | Time | What I Do | What You Do |
|---|-------|------|-----------|-------------|
| 1 | Interview Prep | 15 min | Run prep scripts, generate refreshed materials | Review the prep doc |
| 2 | Precision Compliance | 10 min | Defer/close entries, resolve org cap | Approve deferral choices |
| 3 | Hygiene | 10 min | Auto-expire, rotate signals, snapshot | — |
| 4 | Follow-up Export | 5 min | Export templates for all overdue actions | — |
| 5 | **LinkedIn/Email** | **30 min** | — | **Send messages, check inbox** |
| 6 | Log Actions | 10 min | Log all follow-ups you completed | Tell me what you sent |
| 7 | ZKM Rauschenberg | 30 min | Compose draft, tailor resume | Review draft |
| 8 | Final Standup | 5 min | Run standup to verify clean state | — |

**Total estimated: ~2 hours** (1h automated, 30min human LinkedIn/email, 30min review)

---

## Verification

After all phases complete:
- `python scripts/standup.py` — health should remain ≥ 8.0, actionable ≤ 10, no org cap violations
- `python scripts/followup.py --overdue` — overdue count should drop significantly
- `python scripts/freshness_monitor.py` — no fresh entries should have gone stale
- `python scripts/hygiene.py --company-focus --limit 1` — no org cap violations
- `git status` — commit all changes as session work

---

## Files Modified

| File | Change |
|------|--------|
| `pipeline/active/*.yaml` | Defer/close org-cap violators and stale entries |
| `pipeline/submitted/*.yaml` | Add follow_up entries as actions are logged |
| `signals/outreach-log.yaml` | New follow-up action entries |
| `signals/contacts.yaml` | Updated contact interaction dates |
| `signals/signal-actions.yaml` | Audit trail of deferrals/closes |
| `pipeline/submissions/grafana-*-interview-prep.md` | Refreshed interview prep |
