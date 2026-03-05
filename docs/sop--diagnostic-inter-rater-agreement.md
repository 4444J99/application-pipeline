# SOP: Diagnostic Inter-Rater Agreement

| Field | Value |
|-------|-------|
| **SOP ID** | SOP-DIAG-IRA-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-03-05 |
| **Owner** | @4444J99 |
| **Review Cycle** | Quarterly (next: 2026-06-05) |
| **Scope** | Application pipeline quality measurement |

---

## 1. Purpose & Scope

This SOP defines the process for running diagnostic quality assessments across multiple AI model raters and computing inter-rater agreement (IRA) metrics. The goal is **grade norming** — converging on ground truth about system quality by comparing independent assessments from different perspectives.

**In scope:**
- 8-dimension quality assessment of the application pipeline codebase
- Agreement computation using ICC(2,1), Cohen's kappa, and Fleiss' kappa
- Consensus formation and rubric refinement based on divergence patterns

**Out of scope:**
- Rating other codebases (rubric is pipeline-specific)
- Rater training or LLM fine-tuning

---

## 2. Prerequisites

- Python 3.11+
- Repository cloned with all pipeline data intact
- `strategy/system-grading-rubric.yaml` at version 1.0+
- Access to N ≥ 3 independent rater sessions (AI models or human)
- `ratings/` directory created at repo root

---

## 3. Phase 1 — Rubric Familiarization

Before rating, each rater (AI or human) must review:

1. **Read the rubric**: `strategy/system-grading-rubric.yaml`
   - Understand all 8 dimensions, their types (objective/subjective/mixed), and weights
   - Study the anchored scoring guide at levels 1, 3, 5, 7, 10

2. **Review evidence sources**: Each dimension lists specific files, commands, and sections to inspect

3. **Understand the scale**: Scores are continuous 1.0–10.0 with one decimal place. The anchored descriptors are reference points, not bins.

4. **Note the distinction**: Objective dimensions (test_coverage, code_quality) are measured automatically. Subjective dimensions (architecture, documentation, analytics_intelligence, sustainability) require judgment.

**Time estimate:** 10–15 minutes per rater.

---

## 4. Phase 2 — Independent Rating

Each rater produces a rating file independently. **No discussion between raters before completing individual ratings.**

### 4.1 Objective Dimensions (Automated)

Run the diagnostic tool to collect objective measurements:

```bash
python scripts/diagnose.py --json --rater-id <rater-name> > ratings/<rater-name>.json
```

This produces scores for: `test_coverage`, `code_quality`, `data_integrity`, `operational_maturity`.

### 4.2 Subjective Dimensions (Rater-Scored)

Generate prompts for the subjective dimensions:

```bash
python scripts/diagnose.py --subjective-only
```

Each rater independently evaluates the 4 subjective dimensions:
- `architecture` — Module decomposition, separation of concerns
- `documentation` — CLAUDE.md completeness, inline docs, handoff readiness
- `analytics_intelligence` — Scoring model, funnel analytics, trend detection
- `sustainability` — Bus factor, automation, onboarding ease

**For AI raters**: Copy each prompt into a fresh session with the target AI model. The AI reads the evidence and produces a score (1–10), strengths, weaknesses, and confidence level.

**For human raters**: Review the evidence sources listed in the rubric directly, then score each dimension.

### 4.3 Merge Scores

Manually add subjective scores to the JSON file produced in 4.1:

```json
{
  "rater_id": "claude-opus",
  "dimensions": {
    "test_coverage": {"score": 9.5, "confidence": "high", "evidence": "..."},
    "architecture": {"score": 8.5, "confidence": "medium", "evidence": "..."},
    ...
  }
}
```

Save as `ratings/<rater-name>.json`.

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
| **Outlier flags** | 1.5 × IQR | Identify divergent raters |

### 5.2 Interpretation (Landis & Koch 1977)

| ICC/Kappa Range | Interpretation |
|----------------|----------------|
| < 0.00 | Poor |
| 0.00 – 0.20 | Slight |
| 0.21 – 0.40 | Fair |
| 0.41 – 0.60 | Moderate |
| 0.61 – 0.80 | Substantial |
| 0.81 – 1.00 | Almost Perfect |

**Target**: ICC ≥ 0.61 (substantial) for all dimensions.

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

## 8. Recommended Rater Panel

For maximum coverage, use 3–5 raters with different architectures and training:

| Rater | Role | Strengths |
|-------|------|-----------|
| Claude Opus | Primary AI | Strong on architecture, documentation |
| Claude Sonnet | Secondary AI | Fast iteration, different perspective on same family |
| GPT-4 | Cross-family AI | Independent training, different biases |
| Gemini Pro | Cross-family AI | Different strengths on code quality assessment |
| Human anchor | Tiebreaker | Domain expertise, contextual judgment |

**Minimum viable panel**: 3 raters (2 AI + 1 human, or 3 different AI models).

---

## Appendix A — File Locations

| File | Purpose |
|------|---------|
| `strategy/system-grading-rubric.yaml` | 8-dimension rubric definition |
| `scripts/diagnose.py` | Diagnostic tool (objective + subjective prompts) |
| `scripts/diagnose_ira.py` | IRA computation engine |
| `ratings/*.json` | Individual rater score files |
| `signals/diagnostic-history/` | Archived consensus scores |

## Appendix B — Quick Reference

```bash
# Morning after IRA round:
python scripts/diagnose.py                              # Objective scorecard
python scripts/diagnose.py --subjective-only            # Prompts for AI raters
python scripts/diagnose.py --json --rater-id opus > ratings/opus.json
python scripts/diagnose_ira.py ratings/*.json --consensus  # Agreement report
```
