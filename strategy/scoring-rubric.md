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

## Human-Judgment Dimensions

These require human assessment (or estimation from existing `fit.score` + `identity_position`):

- **mission_alignment**: From framing quality and identity position match
- **evidence_match**: From blocks_used coverage and portfolio relevance
- **track_record_fit**: From qualification assessment gaps
- **strategic_value**: From organization prestige and network potential
