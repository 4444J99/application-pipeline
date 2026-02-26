# Scoring Rubric

Formalized multi-dimensional scoring matrix for application fit assessment.
Replaces intuitive single-number scoring with auditable, weighted composite.

## Dimensions

| Dimension | Weight | Key | Description |
|-----------|--------|-----|-------------|
| Mission Alignment | 25% | `mission_alignment` | How well our work fits their stated mission |
| Evidence Match | 20% | `evidence_match` | Whether we can demonstrate what they require |
| Track Record Fit | 15% | `track_record_fit` | Whether our credentials match their expectations |
| Financial Alignment | 10% | `financial_alignment` | Benefits cliff risk and compensation structure |
| Effort-to-Value Ratio | 10% | `effort_to_value` | Probability × value relative to effort required |
| Strategic Value | 10% | `strategic_value` | Credibility signal and network value if accepted |
| Deadline Feasibility | 5% | `deadline_feasibility` | Whether materials can be ready in time |
| Portal Friction | 5% | `portal_friction` | Submission mechanical complexity |

**Total: 100%**

## Scoring Scale (1–10 per dimension)

### Mission Alignment (25%)

| Score | Description |
|-------|-------------|
| 1–2 | Work doesn't fit their stated mission |
| 3–4 | Tangential connection requiring significant stretching |
| 5–6 | Plausible fit with some reframing needed |
| 7–8 | Clear alignment, work fits naturally into their program |
| 9–10 | Work exemplifies their mission; we are the target applicant |

### Evidence Match (20%)

| Score | Description |
|-------|-------------|
| 1–2 | They want things we can't demonstrate (team projects, gallery shows) |
| 3–4 | Most evidence is indirect or requires heavy reframing |
| 5–6 | Some direct evidence, some gaps that can be narrated around |
| 7–8 | Strong evidence for most requirements; minor gaps |
| 9–10 | Every requirement has verifiable proof in blocks/portfolio |

### Track Record Fit (15%)

| Score | Description |
|-------|-------------|
| 1–2 | They expect credentials we don't have and can't reframe |
| 3–4 | Major gaps (gallery exhibitions, institutional affiliations, team leadership) |
| 5–6 | Some gaps but reframeable via ORGANVM system scale |
| 7–8 | Credentials match with minor gaps; portfolio compensates |
| 9–10 | Credentials exceed expectations for the opportunity |

### Financial Alignment (10%)

| Score | Description |
|-------|-------------|
| 1–2 | Amount triggers benefits cliff with no mitigation path |
| 3–4 | Above safe threshold, mitigation unclear or requires NYLAG |
| 5–6 | Above threshold but Essential Plan or stacking covers it |
| 7–8 | Within safe stacking ceiling; minimal cliff risk |
| 9–10 | No cliff risk at all (under $20k, in-kind, or no compensation) |

### Effort-to-Value Ratio (10%)

| Score | Description |
|-------|-------------|
| 1–2 | Months of work for very low probability of success |
| 3–4 | High effort, moderate probability |
| 5–6 | Moderate effort, moderate probability |
| 7–8 | Moderate effort, good probability; OR low effort, moderate probability |
| 9–10 | Low effort, high probability; blocks already cover most requirements |

### Strategic Value (10%)

| Score | Description |
|-------|-------------|
| 1–2 | No credibility signal even if accepted |
| 3–4 | Minor credibility signal, limited network value |
| 5–6 | Moderate credibility boost and some network access |
| 7–8 | Strong credibility signal; opens doors to adjacent opportunities |
| 9–10 | Transformative credibility (Creative Capital, Prix Ars, Whiting) |

### Deadline Feasibility (5%)

| Score | Description |
|-------|-------------|
| 1–2 | Already passed or <24 hours remaining |
| 3–4 | 1–3 days, materials not fully ready |
| 5–6 | 1–2 weeks, some preparation needed |
| 7–8 | 2+ weeks, blocks mostly ready for assembly |
| 9–10 | Rolling/TBA deadline or materials already fully staged |

### Portal Friction (5%)

| Score | Description |
|-------|-------------|
| 1–2 | Multi-stage review, recommendation letters, portfolio committee |
| 3–4 | Complex portal with many custom fields and specific formats |
| 5–6 | Standard portal, some custom writing required |
| 7–8 | Simple web form or email submission |
| 9–10 | One-click, already staged, or pure paste-from-blocks |

## Job Rubric

Job applications use a separate weight distribution that emphasizes human-judgment dimensions (75% vs 60% for creative). This is necessary because auto-derived dimensions (financial, effort, deadline, portal) are nearly identical across auto-sourced job entries and don't differentiate between them. The title-based role fit is the primary differentiating signal.

### Job Weights

| Dimension | Weight | What it measures (job context) |
|-----------|--------|-------------------------------|
| Mission Alignment | 35% | Role matches professional identity (role fit) |
| Evidence Match | 25% | Can demonstrate specific technical skills |
| Track Record Fit | 15% | Background makes you competitive |
| Strategic Value | 10% | Company prestige + career trajectory value |
| Financial Alignment | 5% | Compensation adequacy |
| Effort-to-Value | 5% | Application effort |
| Deadline Feasibility | 3% | Urgency |
| Portal Friction | 2% | Portal complexity |

**Total: 100%**

### Job Qualification Threshold

- **Creative entries** (grant, prize, fellowship, residency, program, writing, emergency, consulting): **5.0**
- **Job entries**: **5.5**

The higher job threshold accounts for the wider score spread from job weights. With creative weights, most jobs compressed into a narrow 4.0–6.9 band. With job weights and raised tier ceilings, the spread widens to ~3.6–8.5+, making 5.5 an effective cut: tier-1 and tier-2 roles pass, tier-3 and tier-4 roles are skipped.

### Role Fit Tiers

Title-based role-fit estimation for auto-sourced job entries. Blocks are now wired to jobs via `enrich.py --blocks`, which enables evidence bonuses in scoring.

| Tier | Mission | Evidence | Track Record | Example |
|------|---------|----------|-------------|---------|
| Tier-1 (strong) | 9 | 9 | 7 | DevEx, Agent SDK, Claude Code, DevRel |
| Tier-2 (moderate) | 7 | 6 | 5 | Software Engineer, Full Stack, Platform |
| Tier-3 (weak) | 5 | 4 | 3 | Forward Deployed, Applied AI, Growth |
| Tier-4 (poor) | 3 | 2 | 2 | ML Engineer, iOS, Security, Mobile |

### Why Two Rubrics

The original creative rubric was designed for grants and residencies where:
- `financial_alignment` measures benefits-cliff risk (will this push me off Medicaid?)
- `effort_to_value` measures blocks coverage (how many reusable narrative blocks are ready?)
- The 60/40 human/auto split provides good differentiation

For jobs, these dimensions behave completely differently:
- All auto-sourced jobs with unknown salary get the same `financial_alignment` score (5)
- The auto-derived 40% becomes nearly identical across all jobs, compressing scores

The job rubric fixes this by shifting weight to the dimensions that actually differentiate: role fit (mission_alignment), skills match (evidence_match), and background competitiveness (track_record_fit). Additionally, `enrich.py --blocks` wires identity-matched blocks to job entries, enabling the evidence coverage bonus in `effort_to_value` and the blocks bonus in `estimate_human_dimensions`.

## Composite Score Calculation

```
composite = (
    mission_alignment * 0.25 +
    evidence_match * 0.20 +
    track_record_fit * 0.15 +
    financial_alignment * 0.10 +
    effort_to_value * 0.10 +
    strategic_value * 0.10 +
    deadline_feasibility * 0.05 +
    portal_friction * 0.05
)
```

Result is rounded to one decimal place and stored as `fit.score`.

### `original_score` Field

`fit.original_score` preserves the original human gut-feel score that was set before the signal-based rubric existed. It is no longer used in any computation — all dimensions are derived from structured data signals. The field is retained purely for historical reference.

- `fit.original_score` — Frozen historical baseline (read-only, not used in scoring).
- `fit.score` — The computed composite from all 8 signal-derived dimensions.

### Job Financial Alignment

For job entries, `financial_alignment` scores higher salary = higher score:

| Salary | Score | Rationale |
|--------|-------|-----------|
| $0 (unknown) | 5 | Slight penalty for unknown comp |
| $1–$50K | 6 | Low compensation |
| $50K–$100K | 7 | Adequate compensation |
| $100K–$150K | 8 | Good compensation |
| >$150K | 9 | Strong compensation |

This differs from creative entries where higher amounts *decrease* the score due to benefits cliff risk.

## Effort Level Classification

Separate from score — classifies the *work required to submit*, not the quality of fit.

| Level | Key | Time Estimate | Description | Examples |
|-------|-----|---------------|-------------|----------|
| Quick | `quick` | 15–45 min | Paste blocks, fill form, submit | PEN America, Awesome Foundation, GitHub Sponsors, writing pitches |
| Standard | `standard` | 1–2 hours | Compose from blocks, customize framing, fill portal | Prix Ars, Artadia, most residencies |
| Deep | `deep` | 3–6 hours | Custom narrative, project description, budget, multi-section | Creative Capital, Doris Duke, LACMA, Whiting |
| Complex | `complex` | 1–2 days | Requires new materials (video, detailed budget, recs) | Watermill (video), ZKM, Tulsa Fellowship |

### Time Estimates for Daily Batch Planning

| Level | Min (minutes) | Max (minutes) | Default (minutes) |
|-------|---------------|---------------|-------------------|
| quick | 15 | 45 | 30 |
| standard | 60 | 120 | 90 |
| deep | 180 | 360 | 270 |
| complex | 480 | 960 | 720 |

## Auto-Derivable Dimensions

These dimensions can be estimated from existing pipeline data:

- **deadline_feasibility**: From `deadline.date` (days until) and `deadline.type`
- **financial_alignment**: From `amount.value` and `benefits_cliff_note`
- **portal_friction**: From `target.portal` type
- **effort_to_value**: Partially from `amount.value`, `track`, and `submission.blocks_used` count

## Signal-Based Dimensions

Mission alignment, evidence match, and track record fit are computed from structured data signals. No human gut-feel input. Each dimension is the sum of 4 signals, clamped to [1, 10].

Use `score.py --explain --target <id>` to see the signal breakdown for any entry.

### Mission Alignment (4 signals, max 10)

| Signal | Range | Source |
|--------|-------|--------|
| Position-Profile Match | 0–4 | `entry.fit.identity_position` vs `profile.primary_position` / `secondary_position`. Primary=4, secondary=2, no profile=2 (neutral), no match=0. |
| Track-Position Affinity | 0–3 | Hardcoded matrix of (track, position) fit scores. |
| Organ-Position Coherence | 0–2 | Overlap between `fit.lead_organs` and position's expected organs, normalized. |
| Framing Specialization | 0–1 | Has a `framings/*` block in `submission.blocks_used`: 1, else 0. |

**Track-Position Affinity Matrix:**

|  | systems-artist | creative-tech | community-prac | educator | independent-eng |
|--|----------------|---------------|----------------|----------|-----------------|
| grant | 3 | 2 | 2 | 1 | 1 |
| residency | 3 | 3 | 2 | 1 | 1 |
| prize | 3 | 2 | 1 | 1 | 1 |
| fellowship | 2 | 3 | 2 | 2 | 2 |
| program | 2 | 2 | 3 | 2 | 2 |
| writing | 1 | 2 | 3 | 2 | 1 |
| emergency | 2 | 1 | 3 | 1 | 1 |
| consulting | 1 | 2 | 1 | 1 | 3 |

**Position Expected Organs:**
- `systems-artist` → I, II, META
- `creative-technologist` → I, III, IV
- `community-practitioner` → V, VI, META
- `educator` → V, VI
- `independent-engineer` → III, IV

### Evidence Match (4 signals, max 10)

| Signal | Range | Source |
|--------|-------|--------|
| Block-Portal Coverage | 0–3 | `len(blocks_used) / len(portal_fields)`. Ratio ≥1.0=3, ≥0.5=2, >0=1, 0/0=0. |
| Slot Name Alignment | 0–3 | Fuzzy matches between `blocks_used` keys and `portal_fields[].name`. |
| Evidence Depth | 0–2 | Has `evidence/*` block (+1), has `methodology/*` block (+1). |
| Materials Readiness | 0–2 | `materials_attached` non-empty (+1), `portfolio_url` set (+1). |

### Track Record Fit (4 signals, max 10)

| Signal | Range | Source |
|--------|-------|--------|
| Credential-Track Relevance | 0–4 | Best credential score for the entry's track (see table below). |
| Track Experience | 0–3 | Count of same-track entries at submitted+ status. 3+=3, 2=2, 1=1, 0=0. |
| Position Depth | 0–2 | Position has a `blocks/framings/{position}.md` on disk: 2, position set but no block: 1, none: 0. |
| Differentiators Coverage | 0–1 | Profile has ≥3 `evidence_highlights`: 1, else 0. |

**Credential Relevance Matrix:**

| Credential | writing | grant | residency | prize | program | fellowship | emergency | consulting |
|-----------|---------|-------|-----------|-------|---------|-----------|-----------|------------|
| MFA Creative Writing | 4 | 3 | 3 | 3 | 2 | 2 | 2 | 1 |
| Meta Fullstack Dev | 1 | 1 | 1 | 1 | 3 | 3 | 1 | 4 |
| Teaching 11yr | 2 | 2 | 2 | 1 | 4 | 3 | 1 | 2 |
| Construction PM | 0 | 1 | 1 | 0 | 1 | 1 | 1 | 3 |

### No Human Override

All 8 dimensions are always recomputed from data. `original_score` is preserved in YAML for historical reference but no longer feeds computation. The dependency is unidirectional:

```
structured data → compute all 8 dims → composite → fit.score
```

### Compressed Score Review

Use `score.py --review-compressed` to identify entries in a narrow score band. Because dimensions are now signal-based, score compression should be less severe — entries with different structured data (position, blocks, portal fields, organs) will naturally differentiate.
