# SOP: Diagnostic Inter-Rater Agreement (IRA) Grade Norming

| Field | Value |
|-------|-------|
| **SOP ID** | SOP-DIAG-IRA-001 |
| **Version** | 2.0 |
| **Effective Date** | 2026-03-13 |
| **Owner** | @4444J99 |
| **Review Cycle** | Quarterly (next: 2026-06-13) |
| **Scope** | Any ORGANVM organ or project with a system-grading rubric |

---

## 1. Purpose & Scope

This SOP defines a repeatable process for measuring system quality through multi-rater agreement. The goal is **grade norming** — converging on ground truth about system quality by comparing independent assessments from different perspectives.

**Applicable to any project that has:**
- A `system-grading-rubric.yaml` (or equivalent) defining weighted dimensions with scoring guides
- A diagnostic script that produces objective measurements and subjective rating prompts
- An IRA computation tool that computes ICC, kappa, and consensus from rating JSON files

**In scope:**
- N-dimension quality assessment using a weighted rubric
- Agreement computation using ICC(2,1), Cohen's kappa, and Fleiss' kappa
- Consensus formation and rubric refinement based on divergence patterns

**Out of scope:**
- Rater training or LLM fine-tuning
- Cross-project comparison (rubrics are project-specific)

---

## 2. Prerequisites

- Python 3.11+
- A grading rubric YAML with dimensions, weights, and scoring guides
- A diagnostic script that produces objective + subjective rating JSON
- An IRA computation script (e.g., `diagnose_ira.py`)
- Access to N >= 3 independent rater sessions (AI models or human)
- A `ratings/` directory at the project root

---

## 3. Phase 1 — Rubric Familiarization

Before rating, each rater (AI or human) must review:

1. **Read the rubric** (e.g., `strategy/system-grading-rubric.yaml`)
   - Understand all dimensions, their types (objective/subjective/mixed), and weights
   - Study the anchored scoring guide at levels 1, 3, 5, 7, 10

2. **Review evidence sources**: Each dimension lists specific files, commands, and sections to inspect

3. **Understand the scale**: Scores are continuous 1.0-10.0 with one decimal place. The anchored descriptors are reference points, not bins.

4. **Note the distinction**: Objective dimensions are measured automatically by the diagnostic tool. Subjective dimensions require human or AI judgment based on evidence.

**Time estimate:** 10-15 minutes per rater.

---

## 4. Phase 2 — Independent Rating

Each rater produces a rating file independently. **No discussion between raters before completing individual ratings.**

### 4.1 Objective Dimensions (Automated)

Run the diagnostic tool to collect objective measurements:

```bash
python scripts/diagnose.py --json --rater-id <rater-name> > ratings/<rater-name>.json
```

This produces scores for all objective dimensions defined in the rubric.

### 4.2 Subjective Dimensions (Rater-Scored)

Generate prompts for the subjective dimensions:

```bash
python scripts/diagnose.py --subjective-only
```

Each rater independently evaluates the subjective dimensions using the prompts and evidence sources listed in the rubric.

**For AI raters**: Copy each prompt into a fresh session with the target AI model. The AI reads the evidence and produces a score (1-10), strengths, weaknesses, and confidence level.

**For human raters**: Review the evidence sources listed in the rubric directly, then score each dimension.

### 4.3 Merge Scores

Manually add subjective scores to the JSON file produced in 4.1:

```json
{
  "rater_id": "rater-name",
  "timestamp": "2026-03-14T03:25:00+00:00",
  "rubric_version": "1.1",
  "dimensions": {
    "objective_dim_1": {"score": 9.5, "confidence": "high", "evidence": "..."},
    "subjective_dim_1": {"score": 8.5, "confidence": "medium", "evidence": "..."},
    "..."
  }
}
```

Save as `ratings/<rater-name>.json`.

### 4.4 Rating JSON Schema

Each rating file must include:
- `rater_id` (string) — unique identifier for this rater
- `timestamp` (ISO 8601) — when the rating was produced
- `rubric_version` (string) — version of the rubric used
- `dimensions` (object) — dimension key -> score object, where each score object has:
  - `score` (float, 1.0-10.0) — the rating
  - `confidence` (string: "high", "medium", "low") — rater's confidence
  - `evidence` (string) — justification for the score
  - `strengths` (list of strings, optional) — key strengths observed
  - `weaknesses` (list of strings, optional) — key weaknesses observed

---

## 5. Phase 3 — Agreement Computation

Once all raters have submitted files to `ratings/`:

```bash
# Basic IRA report
python scripts/diagnose_ira.py ratings/*.json

# With consensus scores
python scripts/diagnose_ira.py ratings/*.json --consensus

# Machine-readable output
python scripts/diagnose_ira.py ratings/*.json --consensus --json
```

### 5.1 Metrics Produced

| Metric | Method | Use Case |
|--------|--------|----------|
| **ICC(2,1)** | Two-way random, absolute agreement | Overall and per-dimension agreement on continuous scores |
| **Cohen's kappa** | Pairwise categorical | When scores are binned (critical/below/adequate/strong/exemplary) |
| **Fleiss' kappa** | Multi-rater categorical | 3+ raters on binned scores |
| **Consensus** | Median per dimension | Ground truth estimate |
| **Outlier flags** | 1.5 x IQR | Identify divergent raters |

### 5.2 Interpretation (Landis & Koch 1977)

| ICC/Kappa Range | Interpretation |
|----------------|----------------|
| < 0.00 | Poor |
| 0.00 - 0.20 | Slight |
| 0.21 - 0.40 | Fair |
| 0.41 - 0.60 | Moderate |
| 0.61 - 0.80 | Substantial |
| 0.81 - 1.00 | Almost Perfect |

**Target**: ICC >= 0.61 (substantial) for all dimensions.

---

## 6. Phase 4 — Consensus Formation

### 6.1 Review Divergence

If any dimension has ICC < 0.61 (below substantial agreement):

1. **Identify the divergent raters** from the outlier flags in the IRA report
2. **Compare evidence interpretations** — which evidence did raters weight differently?
3. **Discuss anchoring** — were raters using different reference points for the same score?

### 6.2 Rubric Refinement

If divergence persists after discussion:

1. **Sharpen the scoring guide** — add more specific anchors at levels 3, 5, 7
2. **Add evidence examples** — concrete file references that exemplify each level
3. **Re-rate** — repeat Phase 2 with the refined rubric
4. **Version bump** — update `rubric.version` and `effective_date`

### 6.3 Adjudication Protocol

For persistent disagreements (2+ rounds without convergence):

1. **Adopt the human anchor rater's score** as tiebreaker (if available)
2. **Otherwise, use the median** as consensus value
3. **Document the disagreement** in the archival record

---

## 7. Phase 5 — Archival & Trend Tracking

### 7.1 Save Consensus

After consensus formation, save the consensus scores:

```bash
mkdir -p signals/diagnostic-history
cp ratings/consensus-YYYY-MM-DD.json signals/diagnostic-history/
```

### 7.2 Trend Tracking

Over time, compare diagnostic scores across dates to detect:

- **Improvement trends** — score increases after targeted development
- **Regression alerts** — score decreases after changes
- **Dimension drift** — one dimension improving while another degrades

### 7.3 Cadence

| Event | Frequency |
|-------|-----------|
| Full IRA round | Quarterly |
| Objective-only snapshot | Monthly |
| Post-major-change assessment | As needed |

---

## 8. Quality Checks

### 8.1 Agreement Threshold

ICC >= 0.61 (substantial agreement) is the minimum for accepting consensus scores. Below this threshold, the rubric needs refinement before scores are actionable.

### 8.2 Outlier Flagging

Scores outside 1.5 x IQR from the median are flagged as outliers. Outlier raters should be asked to re-examine their evidence before consensus is formed.

### 8.3 Divergent Dimension Identification

Dimensions with the highest score ranges (max - min across raters) are candidates for rubric refinement. If a dimension consistently diverges across rounds, its scoring guide needs sharper anchors.

---

## 9. Recommended Rater Panel

For maximum coverage, use 3-5 raters with different perspectives:

| Rater | Role | Strengths |
|-------|------|-----------|
| Claude Opus | Primary AI | Strong on architecture, documentation |
| Claude Sonnet | Secondary AI | Fast iteration, different perspective on same family |
| GPT-4 | Cross-family AI | Independent training, different biases |
| Gemini Pro | Cross-family AI | Different strengths on code quality assessment |
| Human anchor | Tiebreaker | Domain expertise, contextual judgment |

**Minimum viable panel**: 3 raters (2 AI + 1 human, or 3 different AI models).

---

## Appendix A — Reference Implementation (Application Pipeline)

The application-pipeline repo is the reference implementation of this SOP:

| File | Purpose |
|------|---------|
| `strategy/system-grading-rubric.yaml` | 9-dimension rubric (v1.1): 5 objective + 4 subjective |
| `scripts/diagnose.py` | Diagnostic tool: 5 objective collectors, 4 subjective prompt generators |
| `scripts/diagnose_ira.py` | IRA computation: ICC(2,1), Cohen/Fleiss kappa, consensus |
| `scripts/audit_system.py` | System integrity audit: claims, wiring, logic |
| `ratings/*.json` | Individual rater score files |
| `signals/diagnostic-history/` | Archived consensus scores |

### Objective dimensions (automated):
- `test_coverage` — test count + verification matrix ratio
- `code_quality` — lint errors + type hint coverage
- `data_integrity` — validation + signal integrity errors
- `operational_maturity` — launchd agents + backup recency
- `claim_provenance` — statistical claim source traceability

### Subjective dimensions (rater-scored):
- `architecture` — module decomposition, dependency flow
- `documentation` — CLAUDE.md completeness, inline docs
- `analytics_intelligence` — scoring model, funnel analytics, trends
- `sustainability` — bus factor, automation, onboarding ease

### Quick commands:
```bash
python scripts/run.py diagnose              # Objective scorecard
python scripts/run.py ira                   # IRA report (auto-loads ratings/*.json)
python scripts/run.py sysaudit              # System integrity audit
python scripts/diagnose.py --subjective-only  # Prompts for AI raters
python scripts/diagnose.py --json --rater-id opus > ratings/opus.json
python scripts/diagnose_ira.py ratings/*.json --consensus
```

## Appendix B — Adapting for Other Projects

To apply this SOP to another ORGANVM organ or project:

1. **Create a rubric**: Define `strategy/system-grading-rubric.yaml` with dimensions relevant to the project. Each dimension needs: label, type (objective/subjective/mixed), weight, description, scoring_guide (anchored at 1, 3, 5, 7, 10), evidence_sources, and ira_config.

2. **Build a diagnostic script**: Implement objective collectors that return `{"score": float, "confidence": str, "evidence": str}` and subjective prompt generators that produce self-contained rating prompts.

3. **Reuse the IRA engine**: `diagnose_ira.py` is project-agnostic — it works on any set of rating JSON files that contain `rater_id` and `dimensions` with `score` values. Copy or symlink it into the new project.

4. **Configure IRA settings**: Set `min_raters`, `interpretation_bands`, and `consensus.outlier_iqr_factor` in the rubric YAML.

5. **Follow Phases 1-5**: The process (familiarize, rate independently, compute agreement, form consensus, archive) is identical regardless of the specific dimensions.
