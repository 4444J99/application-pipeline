# Avalanche Manifest: Grafana Interview Conversion

**Created:** 2026-04-01 (Session S49)
**Trigger:** User prompts in new session
**Status:** QUEUED — waiting for first relay

---

## How This Works

Each relay is a self-contained task. When prompted, execute the current relay, produce its output, and surface the next relay's trigger. The avalanche stops at each natural stopping point. It only continues when the user says go.

The chain is ordered by dependency — each relay's output is the next relay's input.

---

## Relay 1: Fill the Vacuums

**Trigger:** "continue avalanche" or "grafana prep" or session start
**Input:** `pipeline/submitted/grafana-labs-staff-ai-engineer-people-technology-nasa-remote.yaml`
**Task:**
- Fetch job posting from `https://job-boards.greenhouse.io/grafanalabs/jobs/5830873004`
- Populate: `target.application_url` (specific URL), `target.description`, `amount.value: 192000` (midpoint), `fit.framing`, `fit.extracted_keywords`
- Add `network` section: `referral_source: null`, `relationship_strength: cold`, `org_insider_contact: Ryan McKellips`
- Validate: `python scripts/validate.py`

**Output:** Clean entry with 0 N/A vacuums. Commit.
**Stopping point:** Entry is complete. User reviews.
**Next relay trigger:** "relay 2" or "contribution"

---

## Relay 2: Contextual Insertion — CLAUDE.md PR

**Trigger:** "relay 2" or "contribution" or "metrics-drilldown"
**Input:** `https://github.com/grafana/metrics-drilldown/issues/1146`
**Task:**
- Clone `grafana/metrics-drilldown` to a worktree
- Read their codebase structure, existing docs, contribution guidelines
- Write a CLAUDE.md that follows their conventions + your expertise
- Open PR referencing issue #1146
- Log PR URL

**Output:** Open PR on Grafana repo. Visible artifact on your GitHub profile.
**Stopping point:** PR submitted. User reviews.
**Next relay trigger:** "relay 3" or "security comment"

---

## Relay 3: Contextual Insertion — MCP Security Comment

**Trigger:** "relay 3" or "security comment" or "prompt injection"
**Input:** `https://github.com/grafana/mcp-grafana/issues/680`
**Task:**
- Read the issue and existing comments
- Read grafana/mcp-grafana source for how they handle tool results and context injection
- Draft a substantive comment on prompt injection defense patterns (grounded in your MCP server experience + security-implementation-guide knowledge)
- Post comment

**Output:** Thoughtful security comment visible on their MCP repo.
**Stopping point:** Comment posted. User reviews.
**Next relay trigger:** "relay 4" or "email"

---

## Relay 4: Send the Email

**Trigger:** "relay 4" or "send email" or "reply to ryan"
**Input:** Gmail draft ID `r2689591423182279605` (thread `19d44c671abf5c5f`)
**Task:**
- Show user the draft for final review
- User confirms
- Send via Gmail MCP
- Delete old zero-hook draft (`r2774883502487243219`)
- Log outreach action in pipeline entry `follow_up` list
- Log in `signals/outreach-log.yaml`

**Output:** Email sent. Outreach logged.
**Stopping point:** Email confirmed sent. User reviews.
**Next relay trigger:** "relay 5" or "linkedin connect" (user-executed — 24h after email)

---

## Relay 5: LinkedIn Connect (User-Executed)

**Trigger:** "relay 5" or "linkedin" (next day, after email lands)
**Input:** Ryan McKellips LinkedIn: `https://www.linkedin.com/in/ryan-mckellips13/`
**Task (user does this manually):**
- Connect with note: "Building AI pipelines across Greenhouse and Workday — looking forward to our conversation Monday."
- Report back to Claude

**Agent task on report-back:**
- Log connect in `signals/outreach-log.yaml`
- Update `signals/contacts.yaml` Ryan McKellips entry with LinkedIn URL
- Update pipeline entry `follow_up` list
- Mark IRF-APP-073 as DONE

**Output:** Two-channel presence established (email + LinkedIn).
**Stopping point:** Connect sent. Avalanche pauses until Monday.
**Next relay trigger:** "relay 6" or "monday prep" (2026-04-05, day before)

---

## Relay 6: Day-Before Prep

**Trigger:** "relay 6" or "monday prep" (Sunday Apr 5 or Monday morning)
**Input:** `pipeline/submissions/grafana-labs-full-dossier.md`, interview prep doc
**Task:**
- Check if any Tier 1 PRs/comments were merged or responded to
- Check Guide.co portal for any updates (Google Meet link, new messages)
- Refresh dossier with any new Grafana news (GrafanaCON 2026 is Apr 20-22 — 2 weeks out)
- Run `python scripts/interview_prep.py --target grafana-labs-staff-ai-engineer-people-technology-nasa-remote` to regenerate with latest data
- Produce a 1-page briefing card: 5 STAR stories, 5 questions, 3 key numbers, 2 things NOT to say

**Output:** Briefing card. User reads before call.
**Stopping point:** User is prepped. Avalanche pauses until after the call.
**Next relay trigger:** "relay 7" or "post-screen" (after Mon 10:30 AM call)

---

## Relay 7: Post-Screen Debrief

**Trigger:** "relay 7" or "post-screen" or "how did it go" (user initiates after call)
**Input:** User's verbal debrief of the call
**Task:**
- Log interaction via `python scripts/crm.py --log --name "Ryan McKellips" --type call --note "<debrief>"`
- Update entry status if advancing (interview → next stage name if known)
- Update conversion-log with screen outcome
- Update dossier §XIII with new intelligence from the call
- If advancing: begin Relay 8 (HM interview prep)
- If rejected: log outcome, update entry to `outcome`, extract learnings, close the chain

**Output:** Pipeline fully updated. Next stage intelligence gathering begins (or chain closes gracefully).
**Stopping point:** TERMINAL — chain either escalates to HM prep or closes.

---

## State Vector

```
relay_1: QUEUED     (fill vacuums)
relay_2: QUEUED     (CLAUDE.md PR)
relay_3: QUEUED     (security comment)
relay_4: QUEUED     (send email)
relay_5: QUEUED     (linkedin connect — user)
relay_6: BLOCKED    (time-gated: 2026-04-05)
relay_7: BLOCKED    (time-gated: 2026-04-06 post-call)
```

## Recovery Protocol

If a relay fails or is skipped:
- The chain continues — relays are ordered but not strictly dependent (except 4→5 timing)
- Failed relays get logged as IRF items
- The avalanche never dies — it either completes or produces a traceable gap
