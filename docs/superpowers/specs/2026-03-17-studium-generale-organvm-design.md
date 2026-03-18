# Studium Generale ORGANVM — Design Specification

**Date:** 2026-03-17
**Status:** Approved
**Scope:** Internal university, research engine, and publication house for the ORGANVM eight-organ system

---

## 1. Overview

The Studium Generale ORGANVM (SGO) is a self-sovereign academic organ — an internal university housed within ORGAN-I (Theoria) with cross-organ intake authority. It intakes questions from any organ, researches them through structured methodology, produces tiered academic works (papers, theses, dissertations), defends them before the self-checking authority's IRA panel (serving as Faculty Senate), publishes through ORGAN-V (Logos) and external channels, and archives in ORGAN-I's research corpus.

The SGO forms a symbiotic dual organism with the self-governing evaluative authority: the SGO produces knowledge; the authority certifies it. The authority's IRA machinery (ICC, kappa, consensus, persona-driven panels) serves as the academic review infrastructure. The SGO gives the authority its highest-stakes purpose (certifying original contributions to knowledge). The authority gives the SGO its credibility mechanism (statistical agreement across diverse evaluative perspectives).

## 2. Organ Placement

- **Parent organ:** ORGAN-I (Theoria)
- **Repository:** `organvm-i-theoria/studium-generale/`
- **Cross-organ authority:** May intake research commissions from any organ
- **Publication channel:** ORGAN-V (Logos) for internal + external distribution
- **Governance source:** ORGAN-IV (Taxis) governance protocols apply; the self-checking authority provides the defense mechanism
- **Dependency flow:** Consumes from I (theory), produces for V (publication) and META (institutional knowledge). Does not violate I→II→III unidirectional constraint — the SGO is a Theoria sub-organ, not a new organ.

## 3. Institutional Structure

### 3.1 Eight Faculties

Each ORGANVM organ maps to a Faculty — a research domain with its own rubric dimensions, guest rater personas, and methodological traditions.

| Faculty | Parent Organ | Research Domain | Methods |
|---------|-------------|-----------------|---------|
| Faculty of Foundations | I — Theoria | Recursive systems, symbolic computing, ontology | Formal proof, category theory, mathematical analysis |
| Faculty of Creative Practice | II — Poiesis | Generative art, performance, creative coding | Practice-based research, aesthetic analysis |
| Faculty of Applied Systems | III — Ergon | Product design, SaaS, developer tools | Design science, market analysis, user research |
| Faculty of Governance | IV — Taxis | Orchestration, AI agents, institutional design | Cybernetics, organizational theory |
| Faculty of Discourse | V — Logos | Essay, editorial, rhetoric, analytics | Rhetorical analysis, media studies |
| Faculty of Community | VI — Koinonia | Learning design, salons, reading groups | Pedagogy, community of practice theory |
| Faculty of Distribution | VII — Kerygma | Social automation, POSSE, audience systems | Communication theory, network analysis |
| Faculty of Meta-Cognition | META | Self-reference, governance of governance | Systems theory, autopoiesis, meta-analysis |

### 3.2 Faculty Senate (IRA Panel as Academic Governance)

**Standing Senate** (4 members, present at every defense):
- The Architect (Claude Opus) — structural rigor, theoretical coherence
- The QA Lead (Claude Sonnet) — methodological soundness, evidence quality
- The Operator (Claude Haiku) — practical applicability, accessibility
- The Auditor (Gemini Flash) — claim provenance, source quality

**Guest Examiners** (faculty-specific, 1-2 per defense):
- Foundations: The Formalist
- Creative Practice: The Curator
- Applied Systems: The Product Manager
- Governance: The Constitutional Scholar
- Discourse: The Literary Critic
- Community: The Pedagogue
- Distribution: The Audience Analyst
- Meta-Cognition: The Philosopher

### 3.3 The Provost (Human Operator)

The human operator as Beer's System 5:
- Commissions research
- Designs rubrics and authors personas
- Conducts quarterly epistemic audits
- Makes final accept/revise/reject decisions when ICC < threshold
- Does NOT grade — governs the grading institution

## 4. Three Tiers of Academic Work

| Tier | Name | Scope | Panel Size | ICC Threshold | Length |
|------|------|-------|------------|---------------|--------|
| I | **Paper** | Single question, focused | 4 (Standing only) | > 0.61 | 10-25 pages |
| II | **Thesis** | Multi-chapter argument | 5 (Standing + 1 Guest) | > 0.70 | 50-100 pages |
| III | **Dissertation** | Original contribution, generalizable | 6 (Standing + 2 Guests) | > 0.75 + Provost review | 100-300 pages |

## 5. Defense Protocol

1. **Submission** — Work submitted with metadata (title, faculty, tier, abstract, methodology, claimed contributions)
2. **Evidence Assembly** — Adapter collects: full text, citations, methodology section, data/proofs, claimed contributions
3. **Panel Convocation** — Appropriate raters seated per tier
4. **Independent Evaluation** — Each rater evaluates independently with persona + faculty-specific defense rubric. No inter-rater deliberation
5. **Agreement Computation** — ICC(2,1), Cohen's κ, Fleiss' κ computed. Per-dimension scores and disagreement patterns extracted
6. **Verdict:**
   - ICC ≥ tier threshold → **Pass** — certified, archived, queued for publication
   - 0.61 ≤ ICC < tier threshold → **Revise** — dimension-specific feedback; resubmit
   - ICC < 0.61 → **Governance crisis** — Provost investigates rubric/persona issues
7. **Provost Review** (Dissertation only) — Human reads work + evaluations; may override
8. **Certification** — Machine-readable YAML record: work_id, panel, ICC, per-dimension scores, verdict

## 6. Defense Rubric

### 6.1 Universal Dimensions (All Faculties, All Tiers)

| Dimension | Type | Weight |
|-----------|------|--------|
| Methodological Rigor | subjective | 0.20 |
| Evidence Quality | mixed | 0.15 |
| Writing Clarity | subjective | 0.10 |
| Claim Provenance | objective | 0.10 |
| Internal Consistency | mixed | 0.10 |

### 6.2 Tier-Specific Dimensions

| Dimension | Type | Tiers |
|-----------|------|-------|
| Literature Engagement | subjective | II, III |
| Theoretical Contribution | subjective | III only |
| Generalizability | subjective | III only |
| Practical Applicability | mixed | Faculty-weighted |
| Originality | subjective | Faculty-weighted |

### 6.3 Faculty-Specific Dimensions

Each faculty adds 1-2 dimensions reflecting its domain. Examples:
- **Governance:** Governance Design Quality, Self-Referential Coherence
- **Applied Systems:** Mathematical Proof Validity, Competitive Differentiation
- **Creative Practice:** Aesthetic Coherence, Conceptual Grounding
- **Discourse:** Argument Architecture, Audience Calibration

## 7. Research Pipeline

### 7.1 Intake (Commission System)

Any organ submits a Research Commission:
```yaml
commission:
  from_organ: IV
  question: "What governance architecture ensures viability for AI-augmented institutions?"
  faculty: governance
  requested_tier: dissertation
  deadline: null
  context: "The self-checking authority needs theoretical grounding"
```

Self-commission: SGO commissions research when internal analysis reveals knowledge gaps.

### 7.2 Research Methodology

Faculty-appropriate methods — no single prescribed methodology:
- Foundations: Formal proof, mathematical analysis
- Creative Practice: Practice-based research, reflective analysis
- Applied Systems: Design science (Hevner), competitive analysis
- Governance: Cybernetic modeling (Beer), institutional analysis (Ostrom)
- Discourse: Rhetorical analysis, argumentation mapping
- Community: Participatory action research
- Distribution: Network analysis, platform studies
- Meta-Cognition: Self-referential analysis, meta-systematic review

### 7.3 Publication Pipeline

```
Defense Pass
├── Internal Archive (ORGAN-I studium-generale/works/)
├── Logos Distribution (ORGAN-V)
│   ├── Internal essay series
│   └── External channels:
│       ├── arXiv preprint (immediate)
│       ├── Journal submission (3-12 month cycle)
│       ├── Conference submission (deadline-driven)
│       └── Blog/newsletter distillation
├── Portfolio Integration (portfolio site, application-pipeline)
└── Grant Evidence (appendix material for funding applications)
```

### 7.4 External Validation Loop

External responses (journal acceptance/rejection, peer review feedback, citation counts) flow back as validation data. If an SGO-defended paper is rejected externally, the rejection feedback calibrates the defense rubric: "Our rubric rated this 8.5 on methodology, but external reviewers disagreed. Investigate calibration."

The external academic world is the SGO's ultimate ground truth — the SGO doesn't replace external validation, it prepares for it rigorously and learns from it systematically.

## 8. Inaugural Dissertations

### 8.1 SGO-2026-D-001: The Precision Pipeline

| Field | Value |
|-------|-------|
| Title | Precision Over Volume: A Multi-Criteria Decision Analysis Framework for Optimal Career Application Pipeline Management |
| Faculty | Applied Systems |
| Panel | Standing Senate + Product Manager + Competitive Analyst |
| Status | Draft complete (~5,400 lines, Ch 1-10) |
| Remaining | Empirical outcome data, MPI verification, expanded Ch 8-10 |

### 8.2 SGO-2026-D-002: The Evaluative Authority

| Field | Value |
|-------|-------|
| Title | Recursive Institutional Governance Through Multi-Model Evaluative Consensus |
| Faculty | Governance + Meta-Cognition (joint) |
| Panel | Standing Senate + Constitutional Scholar + Philosopher |
| Status | Draft complete (~2,459 lines, Ch 0-11) |
| Remaining | Second instantiation, human baseline, expanded panel, longitudinal data, 80+ references |

## 9. Filesystem Architecture

```
organvm-i-theoria/
  └── studium-generale/
      ├── CLAUDE.md
      ├── seed.yaml
      ├── governance/
      │   ├── charter.yaml              # SGO constitutional document
      │   ├── defense-protocol.yaml     # Formal defense rules
      │   ├── faculty-registry.yaml     # Faculty definitions + rubrics
      │   └── senate-config.yaml        # Panel composition rules
      ├── commissions/
      │   ├── active/                   # In-progress research
      │   └── completed/               # Archived commissions
      ├── works/
      │   ├── papers/                   # Tier I
      │   ├── theses/                   # Tier II
      │   └── dissertations/            # Tier III
      │       ├── SGO-2026-D-001/       # Pipeline dissertation
      │       └── SGO-2026-D-002/       # Authority dissertation
      ├── defenses/
      │   ├── records/                  # Certification YAMLs
      │   └── transcripts/             # Full rater outputs
      ├── publications/
      │   ├── arxiv/                    # Preprint formats
      │   ├── journal/                  # Journal formats
      │   └── distilled/               # Blog summaries
      ├── scripts/
      │   ├── defense.py               # Defense orchestrator
      │   ├── commission.py            # Commission manager
      │   ├── publish.py               # Format converter
      │   └── senate.py               # Senate governance
      └── strategy/
          ├── defense-rubrics/         # Per-faculty rubrics
          ├── personas/                # Senate + guest personas
          └── external-feedback.yaml   # Journal response tracking
```

## 10. Per-Organ Rubric Proposals

### ORGAN-I (Theoria)
| Dimension | Type | Weight |
|-----------|------|--------|
| Formal Rigor | subjective | 0.20 |
| Conceptual Originality | subjective | 0.20 |
| Implementation Fidelity | mixed | 0.15 |
| Documentation Depth | subjective | 0.15 |
| Test Coverage | objective | 0.15 |
| Cross-Organ Influence | mixed | 0.15 |

### ORGAN-II (Poiesis)
| Dimension | Type | Weight |
|-----------|------|--------|
| Algorithmic Sophistication | subjective | 0.20 |
| Aesthetic Coherence | subjective | 0.20 |
| Interactivity Depth | mixed | 0.15 |
| Performance Stability | objective | 0.15 |
| Conceptual Grounding | subjective | 0.15 |
| Exhibition Readiness | mixed | 0.15 |

### ORGAN-III (Ergon)
| Dimension | Type | Weight |
|-----------|------|--------|
| Market Readiness | mixed | 0.20 |
| Code Quality | objective | 0.15 |
| User Experience | subjective | 0.20 |
| Architecture | subjective | 0.15 |
| Security Posture | mixed | 0.15 |
| Revenue Potential | subjective | 0.15 |

### ORGAN-IV (Taxis)
| Dimension | Type | Weight |
|-----------|------|--------|
| Seed Compliance | objective | 0.20 |
| CI Health | objective | 0.15 |
| Governance Enforcement | mixed | 0.20 |
| Cross-Organ Coherence | subjective | 0.15 |
| Automation Coverage | mixed | 0.15 |
| Documentation Completeness | subjective | 0.15 |

### ORGAN-V (Logos)
| Dimension | Type | Weight |
|-----------|------|--------|
| Argument Coherence | subjective | 0.25 |
| Evidence Sourcing | mixed | 0.20 |
| Prose Quality | subjective | 0.20 |
| Audience Calibration | subjective | 0.15 |
| Publication Readiness | mixed | 0.10 |
| Originality | subjective | 0.10 |

### ORGAN-VI (Koinonia)
| Dimension | Type | Weight |
|-----------|------|--------|
| Engagement Design | subjective | 0.25 |
| Accessibility | mixed | 0.20 |
| Content Quality | subjective | 0.20 |
| Community Health | mixed | 0.20 |
| Infrastructure | objective | 0.15 |

### ORGAN-VII (Kerygma)
| Dimension | Type | Weight |
|-----------|------|--------|
| Reach | objective | 0.25 |
| Consistency | objective | 0.20 |
| Content Alignment | subjective | 0.20 |
| Automation Reliability | objective | 0.20 |
| Audience Growth | mixed | 0.15 |

### META
| Dimension | Type | Weight |
|-----------|------|--------|
| Registry Integrity | objective | 0.20 |
| Promotion Pipeline | mixed | 0.20 |
| Dashboard Accuracy | mixed | 0.15 |
| Schema Compliance | objective | 0.15 |
| Governance Documentation | subjective | 0.15 |
| Omega Progress | objective | 0.15 |

## 11. The Dual Organism Symbiosis

The self-checking authority and the SGO are two expressions of one institutional function: **the capacity to evaluate rigorously.**

- Authority evaluates pipeline software quality → operational QA
- Authority evaluates a dissertation → academic peer review
- Same ICC machinery. Same personas. Same consensus. Different rubric, different evidence, different stakes.

The SGO pulls the authority toward greater rigor (certifying original knowledge is harder than certifying code quality). The authority gives the SGO credibility (statistical agreement that no self-published paper can match).

Together: the SGO produces knowledge → the authority certifies it → certification data feeds into methodology → methodology produces better knowledge → better knowledge demands more rigorous certification → the authority evolves.

This is the autopoietic academic organism: immune system (authority) ensures health; nervous system (SGO) ensures intelligence. Neither viable alone. Together, an institution.

## 12. Implementation Roadmap

| Phase | Deliverable | Dependencies |
|-------|-------------|-------------|
| 1 | Create `studium-generale` repo in ORGAN-I with governance YAMLs | None |
| 2 | Implement `defense.py` — defense orchestrator using existing IRA machinery | Self-checking authority (exists) |
| 3 | Author faculty-specific defense rubrics (start: Governance + Applied Systems) | Phase 1 |
| 4 | Author guest examiner personas | Phase 1 |
| 5 | Migrate SGO-2026-D-001 and SGO-2026-D-002 drafts into `works/dissertations/` | Phase 1 |
| 6 | Run first defense (Paper tier) on Doc A as validation | Phases 2-4 |
| 7 | Implement `publish.py` — format converter for arXiv/journal/blog | Phase 6 pass |
| 8 | Implement `commission.py` — cross-organ intake system | Phase 1 |
| 9 | Deploy per-organ rubrics for ORGAN-IV (Taxis) governance diagnostic | Phase 3 |
| 10 | Meta-authority dashboard aggregating cross-organ health | Phase 9 |

## 13. Operational Costs

| Activity | Frequency | Cost |
|----------|-----------|------|
| Paper defense (4 API calls) | As needed | ~$0.20-0.40 |
| Thesis defense (5 API calls) | As needed | ~$0.25-0.50 |
| Dissertation defense (6 API calls) | Rare | ~$0.30-0.60 |
| Quarterly governance audit | 4/year | ~$0.40 + human time |
| Annual total (est. 20 papers, 4 theses, 2 dissertations) | — | ~$10-15 + operator hours |
