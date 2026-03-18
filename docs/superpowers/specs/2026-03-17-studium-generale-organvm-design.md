# Studium Generale ORGANVM — Design Specification

**Date:** 2026-03-17
**Status:** Approved
**Scope:** Internal university, research engine, and publication house for the ORGANVM eight-organ system

---

## 1. Purpose

The Studium Generale ORGANVM exists for three reasons, in this order:

### 1.1 Self-Fulfillment (Primary)

The practitioner grows by doing the work. Research is not a means to publication — publication is a byproduct of research. The SGO exists because understanding is intrinsically valuable: the act of taking a question seriously, pursuing it through formal methodology, and producing a defended answer makes the practitioner more capable, more rigorous, and more intellectually alive. Every defended work changes the person who wrote it. That change is the primary output. The paper is the receipt.

This is not decorative philosophy. It is a design constraint. The SGO must never optimize for publication volume, citation count, or credential accumulation at the expense of intellectual depth. If a question requires three years of study before it yields a publishable paper, the SGO supports that timeline. The Studium is not a factory; it is a practice.

### 1.2 Promotion (Secondary)

Defended works demonstrate capability. They serve as portfolio assets, grant application evidence, and proof that the practitioner operates at institutional depth. "Promotion" here carries dual meaning:

- **External promotion:** The works promote the practitioner's professional standing — demonstrated research capability, formal methodology, published contributions to knowledge
- **ORGANVM promotion:** The works participate in the organ system's promotion state machine (LOCAL → CANDIDATE → PUBLIC_PROCESS → GRADUATED → ARCHIVED), governed by the same rules as every other ORGANVM artifact (see Section 5)

### 1.3 Proof of Theoretical Power (Tertiary)

The SGO's defended works, certified by the self-checking authority with ICC scores and disagreement patterns, constitute proof that the ORGANVM system can produce knowledge at academic standard. When the system publishes a paper on arXiv and it receives citations, or submits to a journal and passes peer review, the external validation proves that the internal institution is real — not aspirational, not decorative, but functionally equivalent to the academic institutions it parallels.

This proof compounds: each external validation strengthens the SGO's credibility, which strengthens the authority's calibration data, which strengthens the next defense, which produces a stronger work. The proof of theoretical power is not a one-time demonstration but a self-reinforcing cycle.

## 2. Overview

The Studium Generale ORGANVM (SGO) is a self-sovereign academic organ — an internal university housed within ORGAN-I (Theoria) with cross-organ intake authority. It intakes questions from any organ (formally through commissions and informally through an inquiry log), researches them through structured methodology, produces tiered academic works (papers, theses, dissertations), defends them before the self-checking authority's IRA panel (serving as Faculty Senate), publishes through ORGAN-V (Logos) and external channels, and archives in ORGAN-I's research corpus.

The SGO forms a symbiotic dual organism with the self-governing evaluative authority: the SGO produces knowledge; the authority certifies it. The authority's IRA machinery (ICC, kappa, consensus, persona-driven panels) serves as the academic review infrastructure. The SGO gives the authority its highest-stakes purpose (certifying original contributions to knowledge). The authority gives the SGO its credibility mechanism (statistical agreement across diverse evaluative perspectives).

## 3. Organ Placement

- **Parent organ:** ORGAN-I (Theoria)
- **Repository:** `organvm-i-theoria/studium-generale/`
- **Cross-organ authority:** May intake research commissions from any organ
- **Publication channel:** ORGAN-V (Logos) for internal + external distribution
- **Governance source:** ORGAN-IV (Taxis) governance protocols apply; the self-checking authority provides the defense mechanism
- **Dependency flow:** Consumes from I (theory), produces for V (publication) and META (institutional knowledge). Does not violate I→II→III unidirectional constraint — the SGO is a Theoria sub-organ, not a new organ.

## 4. Institutional Structure

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

## 5. Three Tiers of Academic Work

| Tier | Name | Scope | Panel Size | ICC Threshold | Length |
|------|------|-------|------------|---------------|--------|
| I | **Paper** | Single question, focused | 4 (Standing only) | > 0.61 | 10-25 pages |
| II | **Thesis** | Multi-chapter argument | 5 (Standing + 1 Guest) | > 0.70 | 50-100 pages |
| III | **Dissertation** | Original contribution, generalizable | 6 (Standing + 2 Guests) | > 0.75 + Provost review | 100-300 pages |

## 6. Promotion State Machine Integration

SGO works participate in the same promotion state machine as every other ORGANVM artifact. This ensures academic works are governed by the same lifecycle discipline as code repositories, essays, and governance documents.

### 5.1 State Mapping

| ORGANVM State | SGO Analog | Trigger | Governance |
|---------------|------------|---------|------------|
| **LOCAL** | Draft in progress | Author begins work | No formal review; work is private to the author |
| **CANDIDATE** | Submitted for defense | Author declares work ready; submits metadata | Defense panel is convened; evidence assembly begins |
| **PUBLIC_PROCESS** | Under defense / revision | Panel evaluates; ICC computed; verdict rendered | If "Revise": returns to LOCAL-equivalent with feedback. If "Pass": advances |
| **GRADUATED** | Published externally | Defended work submitted to arXiv, journal, or conference | External peer review provides validation data |
| **ARCHIVED** | Historical record | Work superseded by later research, or question resolved | Preserved in archive; cited by successor works |

### 5.2 Transition Rules

- **LOCAL → CANDIDATE**: Author self-declares. No gate — anyone (the Provost, in practice) can submit work for defense at any time. Premature submission is punished by the defense itself (low ICC, "Revise" verdict).
- **CANDIDATE → PUBLIC_PROCESS**: Automatic upon panel convocation. The act of convening the panel moves the work into public process.
- **PUBLIC_PROCESS → GRADUATED**: Requires defense pass (ICC ≥ tier threshold). For dissertations, additionally requires Provost review.
- **PUBLIC_PROCESS → LOCAL**: "Revise" verdict returns the work to draft state with dimension-specific feedback. The work retains its ID and history — revision is not restart.
- **GRADUATED → ARCHIVED**: Provost decision, typically when successor work supersedes the original or when the research question is resolved by subsequent developments.
- **No state skipping**: A work cannot jump from LOCAL to GRADUATED. Every work must be defended. This is the same anti-shortcut principle that governs ORGANVM repository promotion.

### 5.3 seed.yaml Contract

Every SGO work has a `seed.yaml` declaring its promotion state, faculty membership, and metadata — the same contract structure used by every ORGANVM repository:

```yaml
id: SGO-2026-D-002
title: "Recursive Institutional Governance Through Multi-Model Evaluative Consensus"
organ: I  # Theoria
sub_organ: studium-generale
faculty: [governance, meta-cognition]
tier: dissertation
status: LOCAL  # → CANDIDATE → PUBLIC_PROCESS → GRADUATED → ARCHIVED
author: "@4444J99"
commission:
  from_organ: IV
  question: "What governance architecture ensures viability for AI-augmented institutions?"
defense:
  panel: null  # populated upon CANDIDATE transition
  icc: null
  verdict: null
  date: null
publications:
  arxiv: null
  journal: null
  conference: null
created: "2026-03-15"
last_modified: "2026-03-17"
```

## 7. The Inquiry Log (Informal Intake)

### 6.1 Purpose

The commission system (Section 8) handles formal intake — an organ submits a structured YAML request. But research does not begin with formal requests. It begins with noticing: a failure that reveals a gap, a pattern that suggests a principle, a conversation that surfaces a question, a reading that provokes a connection.

The **Inquiry Log** is the SGO's researcher's notebook — a low-friction capture mechanism for observations, questions, and hunches that have not yet crystallized into formal commissions.

### 6.2 Structure

```yaml
# studium-generale/commissions/inquiry-log.yaml
entries:
  - id: INQ-2026-001
    date: "2026-03-15"
    source: "threshold calibration crisis in application pipeline"
    observation: "A scoring model recalibration made the 9.0 threshold unattainable. No automated metric detected this. The IRA facility caught it through subjective dimension assessment."
    question: "Under what conditions do semantic failures evade syntactic quality checks?"
    potential_faculty: [governance, meta-cognition]
    potential_tier: paper
    status: raw  # raw → developing → commissioned → absorbed

  - id: INQ-2026-002
    date: "2026-03-17"
    source: "designing the SGO itself"
    observation: "The act of designing a self-governing academic institution required synthesizing Beer, Ashby, Maturana/Varela, Luhmann, psychometrics, and institutional theory. No single tradition suffices."
    question: "Is there a general theory of self-governing evaluative institutions that unifies these traditions?"
    potential_faculty: meta-cognition
    potential_tier: dissertation
    status: developing
```

### 6.3 Lifecycle

| Status | Meaning | Transition |
|--------|---------|-----------|
| **raw** | Captured observation, not yet explored | Author reflects; adds context over days/weeks |
| **developing** | Question is sharpening; literature connections forming | Author decides: worth a commission? |
| **commissioned** | Promoted to formal Research Commission | Enters the commission pipeline (Section 8) |
| **absorbed** | Folded into an existing commission or work | Linked to the absorbing work's ID |
| **dormant** | Not currently active but preserved | May reactivate if context changes |

### 6.4 Governance

- **No approval needed** to add entries. The log is the Provost's private notebook. Anything can go in.
- **Quarterly review**: The Provost reviews the inquiry log during epistemic audits. Raw entries older than 90 days are either developed, absorbed, or marked dormant.
- **The log is the SGO's immune system**: It detects what the formal commission system cannot — the questions that no organ knows to ask, because they emerge from practice rather than planning.

## 8. Defense Protocol

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

## 9. Defense Rubric

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

## 10. Research Pipeline

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

## 11. Inaugural Dissertations

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

## 12. Filesystem Architecture

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
      │   ├── inquiry-log.yaml         # Informal intake (researcher's notebook)
      │   ├── active/                   # In-progress formal commissions
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

## 13. Per-Organ Rubric Proposals

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

## 14. The Dual Organism Symbiosis

The self-checking authority and the SGO are two expressions of one institutional function: **the capacity to evaluate rigorously.**

- Authority evaluates pipeline software quality → operational QA
- Authority evaluates a dissertation → academic peer review
- Same ICC machinery. Same personas. Same consensus. Different rubric, different evidence, different stakes.

The SGO pulls the authority toward greater rigor (certifying original knowledge is harder than certifying code quality). The authority gives the SGO credibility (statistical agreement that no self-published paper can match).

Together: the SGO produces knowledge → the authority certifies it → certification data feeds into methodology → methodology produces better knowledge → better knowledge demands more rigorous certification → the authority evolves.

This is the autopoietic academic organism: immune system (authority) ensures health; nervous system (SGO) ensures intelligence. Neither viable alone. Together, an institution.

## 15. Implementation Roadmap

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

## 16. Operational Costs

| Activity | Frequency | Cost |
|----------|-----------|------|
| Paper defense (4 API calls) | As needed | ~$0.20-0.40 |
| Thesis defense (5 API calls) | As needed | ~$0.25-0.50 |
| Dissertation defense (6 API calls) | Rare | ~$0.30-0.60 |
| Quarterly governance audit | 4/year | ~$0.40 + human time |
| Annual total (est. 20 papers, 4 theses, 2 dissertations) | — | ~$10-15 + operator hours |
