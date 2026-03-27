# The Materials Protocol: A Formal System for Submission Materials Production

**Date:** 2026-03-27
**Status:** DESIGN
**Siblings:** `testament-formalization.md` (text rhetoric), `outreach-protocol-formalization-design.md` (conversational rhetoric)
**Location:** `application-pipeline/docs/superpowers/specs/`

---

## 1. Purpose

The Materials Protocol is the third formal system in the ORGANVM rhetorical triad:

```
TESTAMENT (13 articles)           → governs TEXT (essays, posts, long-form)
OUTREACH PROTOCOL (7 articles)    → governs CONVERSATION (DMs, connect notes, threads)
MATERIALS PROTOCOL (12 articles)  → governs SUBMISSIONS (resumes, cover letters, portal answers)
```

The Testament governs how to WRITE. The Outreach Protocol governs how to CONVERSE. The Materials Protocol governs how to PRESENT — the construction of documents that represent the author to strangers in high-stakes evaluation contexts (hiring managers, grant juries, recruiters).

## 2. Relationship to Parent Systems

The Materials Protocol IMPORTS axioms from:

- **Testament Art. I** (Knowledge Imperative): κ(p) > 0 — every paragraph carries non-zero knowledge
- **Testament Art. II** (Cascading Causation): connector(bᵢ, bᵢ₊₁) ∈ {BUT, THEREFORE} — no AND_THEN
- **Testament Art. III** (Triple Layer): θ(p, d) > 0 for all d ∈ {pathos, ethos, logos}
- **Testament Art. XII** (Charged Language): χ(w) > threshold for chosen words
- **Testament Art. XIII** (Power Position): terminal word of each paragraph carries maximum weight
- **Outreach Protocol P-I** (Hook Planting): specific, recoverable, falsifiable/frame-novel
- **Outreach Protocol P-V** (Inhabitation): questions/answers address recipient's daily world
- **Voice Constitution INV-01 through INV-08**: eight identity invariants
- **Voice Constitution AP-01 through AP-11**: eleven anti-patterns with penalty weights
- **Storefront Playbook Rules 1-4**: number-first, one-claim, vocabulary matching, storefront-first

The Materials Protocol adds INTER-DOCUMENT constraints that none of the parent systems address: how a resume relates to a cover letter, how both relate to portal answers, how visual identity is preserved across PDFs, and how the production pipeline enforces all of this automatically.

## 3. Foundational Definitions

### Domain

```
D_resume = structured HTML document with sections: HEADER, PROFILE, SKILLS, PROJECTS, EXPERIENCE, EDUCATION, CERTIFICATIONS
D_coverletter = prose document with sections: HEADER, BODY (4-5 paragraphs), SIGNATURE
D_portal = set of (question, answer) pairs sourced from ATS API
D_package = {resume, coverletter, portal_answers, entry_yaml, outreach_dm}
```

### Primitive Functions

```
fill : Document → [0, 1]           — page fill ratio (content area / total page area)
words : Document → ℕ               — word count
entries : Resume → ℕ               — experience entry count
layout : Resume → {vertical, columnar, grid}  — layout classification
overlap : (Doc, Doc) → [0, 1]      — 4-word phrase overlap ratio
template : Document → Template      — the CSS/HTML template used
canonical : MetricName → Value      — the CANONICAL dict lookup
employer : Resume → String          — the employer name in the first experience entry
projects : Resume → list[Project]   — the projects listed
voice_score : Document → [0, 1]     — Voice Constitution compliance score
```

### The Evaluation Context

```
Reviewer ∈ {hiring_manager, grant_jury, recruiter, ATS_parser}
Time_budget ∈ {6_seconds (ATS scan), 30_seconds (initial read), 2_minutes (deep read)}

The Materials Protocol optimizes for the 30-second read:
  P(advance | 30_seconds) is the target metric.

Axiom 0 (The Attention Budget):
  A reviewer allocates attention monotonically: first impression is irreversible.
  Dead space, formatting inconsistency, or generic language in the first 3 seconds
  terminates the evaluation.
```

---

## 4. The Twelve Articles

### Article M-I — The Page-Fill Imperative

#### Logic

```
Definition:
  fill(d) = area_content(d) / area_page(d)

Axiom M-I:
  ∀d ∈ {resume, coverletter}:
    0.95 ≤ fill(d) ≤ 0.98

  Every submission document fills 95-98% of its page.

Theorem M-I.1 (The Dead Space Penalty):
  fill(d) < 0.90 → P(advance | 30_seconds) decreases by ≥ 30%

  Proof:
    1. A reviewer scanning at 30 seconds registers page fill before content
    2. Dead space signals "not enough to say" — a credibility judgment
    3. The judgment is pre-conscious and irreversible (Axiom 0)
    4. Empirical: half-page cover letters (fill ≈ 0.50) triggered this feedback
       three times in this pipeline's history  ∎

Theorem M-I.2 (The Overflow Penalty):
  fill(d) > 1.0 → document spills to page 2
  → P(page_2_read) < 0.10

  A 2-page resume for a non-executive role signals inability to prioritize.

Corollary M-I.1:
  For cover letters: 550 ≤ words(d) ≤ 700
  For resumes: content length calibrated to 8.4pt Georgia at 0.45in margins
```

#### Algorithm

```python
def validate_page_fill(document: Document) -> FillAnalysis:
    """M-I: Validate page fill ratio."""
    if document.type == "coverletter":
        word_count = len(document.text.split())
        if word_count < 500:
            return FillAnalysis(valid=False, diagnosis=f"M-I: {word_count} words — RED FLAG (min 550)")
        if word_count < 550:
            return FillAnalysis(valid=False, diagnosis=f"M-I: {word_count} words — below target (550-700)")
        if word_count > 750:
            return FillAnalysis(valid=False, diagnosis=f"M-I: {word_count} words — may overflow (target 550-700)")

    if document.type == "resume":
        if document.pdf_pages != 1:
            return FillAnalysis(valid=False, diagnosis=f"M-I: resume is {document.pdf_pages} pages — must be exactly 1")

    return FillAnalysis(valid=True)
```

#### Mathematics

```
The fill function models the relationship between content volume and page capacity:

  fill(d) = Σᵢ height(elementᵢ) / page_height

For a fixed template (8.5x11, 0.45in margins, 8.4pt Georgia):
  page_height_available ≈ 9.6in
  line_height ≈ 0.12in at 8.4pt
  max_lines ≈ 80

For cover letters at 9pt Georgia with 1.35 line-height:
  page_height_available ≈ 9.1in (accounting for header)
  chars_per_line ≈ 85
  lines_per_paragraph ≈ 6-8
  paragraphs_for_full_page ≈ 5 at 110-140 words each
  target_words = 5 × 120 = 600 (center of 550-700 range)
```

---

### Article M-II — Structural Integrity

#### Logic

```
Definition:
  entries(r) = count of <div class="entry"> blocks in the EXPERIENCE section
  layout(r) = classification of CSS layout model used for entries

Axiom M-II.1 (Minimum Entry Count):
  ∀ resume r: entries(r) ≥ 4

  The four mandatory entries:
    E₁ = (ORGANVM, "Software Engineer & [role-specific]", 2020–Present)
    E₂ = (Instructor, "Composition & Technical Communication", 2015–Present)
    E₃ = (Digital Marketing Manager, MDC Foundation, 2023–2024)
    E₄ = (Multimedia Specialist, AJP Media Arts, 2011–2020)

  These demonstrate 18 years of career breadth across 4 domains.

Axiom M-II.2 (Vertical Layout):
  ∀ resume r: layout(r) = vertical_stacked

  Each entry is a full-width block. NEVER columnar, grid, or side-by-side.

  Proof (by contradiction):
    1. Assume layout(r) = columnar
    2. Each entry occupies width/n of the page (n = number of columns)
    3. Bullet text wraps at 2-3 words per line → unreadable
    4. Dead space between columns wastes 40-60% of horizontal real estate
    5. The 30-second reviewer sees sparse, thin columns instead of substantive content
    6. Contradicts M-I (page fill) and Axiom 0 (first impression)  ∎

Axiom M-II.3 (Template Fidelity):
  ∀ resume r: template(r) ∈ BASE_TEMPLATES

  The resume HTML must be derived from one of the 9 base templates in
  materials/resumes/base/. The tailor_resume.py prompt rewrites CONTENT
  within the template structure. It does NOT invent new layouts.

Theorem M-II.1 (The Base-Not-Output Principle):
  Structural changes to resumes MUST be made to base templates.
  Output files in batch-NN/ are historical artifacts — never patch them.

  The pipeline is: base → tailor → build → output
  Patching output bypasses the pipeline and creates drift.
```

#### Algorithm

```python
def validate_structural_integrity(resume: Resume) -> StructuralAnalysis:
    """M-II: Validate resume structure."""
    violations = []

    # M-II.1: Entry count
    entry_count = resume.html.count("entry-header")
    if entry_count < 4:
        violations.append(f"M-II.1: {entry_count} entries — minimum 4")

    # M-II.2: Layout
    if "grid-template-columns" in resume.html or "column-count" in resume.html:
        violations.append("M-II.2: columnar layout detected — must be vertical stacked")
    if "display: flex" in resume.html and "flex-direction: row" in resume.html:
        violations.append("M-II.2: flexbox row layout detected — must be vertical stacked")

    # M-II.3: Template fidelity
    # Check that the HTML structure matches a known base template
    required_classes = ["entry-header", "entry-title", "entry-org", "entry-dates",
                        "project-title", "project-desc", "section-label", "section-content"]
    for cls in required_classes:
        if cls not in resume.html:
            violations.append(f"M-II.3: missing class '{cls}' — template structure broken")
            break

    return StructuralAnalysis(valid=len(violations) == 0, violations=violations)
```

---

### Article M-III — Identity Sovereignty

#### Logic

```
Axiom M-III.1 (ORGANVM Attribution):
  ∀ document d in package:
    employer(d) = "ORGANVM"

  The system's name is the employer. Not "Independent Engineer,"
  not "Self-Employed," not "Freelance."

Axiom M-III.2 (Forbidden Terms):
  ∀ document d in package:
    ¬contains(d, "Independent Engineer") ∧
    ¬contains(d, "Self-Employed") ∧
    ¬contains(d, "Freelance")

  These terms signal unemployment to a recruiter.
  ORGANVM signals studio operation.

Theorem M-III.1 (Identity Position Alignment):
  ∀ package P targeting role R:
    ∃ position p ∈ {9 canonical positions}:
      framing(P) ∈ vocabulary(p) ∧ projects(P) ∈ domain(p)

  Every package must be framed from one of the 9 identity positions.
  The position determines vocabulary, project selection, and emphasis.
```

#### Algorithm

```python
FORBIDDEN_TERMS = ["Independent Engineer", "Self-Employed", "Freelance", "Self Employed"]

def validate_identity(package: Package) -> IdentityAnalysis:
    """M-III: Validate identity sovereignty."""
    violations = []

    for doc in package.all_documents():
        for term in FORBIDDEN_TERMS:
            if term.lower() in doc.text.lower():
                violations.append(f"M-III.2: '{doc.name}' contains '{term}'")

    # Check employer in resume
    if "ORGANVM" not in package.resume.html:
        violations.append("M-III.1: 'ORGANVM' not found in resume")

    return IdentityAnalysis(valid=len(violations) == 0, violations=violations)
```

---

### Article M-IV — Metric Canonicality

#### Logic

```
Definition:
  CANONICAL = {
    repos: 113, words: "739K", tests_total: "23,470", cicd: 104,
    files: "82K", dependency_edges: 50, essays: 49, orgs: 8,
    sprints: 33, courses: "100+", students: "2,000+",
    views: "17.5M+", agentic_tests: "1,095+", recursive_tests: "1,254",
  }

Axiom M-IV:
  ∀ metric m appearing in any document d:
    value(m, d) = CANONICAL[m]

  All metrics must match the CANONICAL dict in recruiter_filter.py.
  No other source of metric values is authoritative.

Theorem M-IV.1 (Propagation):
  When CANONICAL is updated (e.g., repos 113 → 120), the update
  propagates to all materials via recruiter_filter.py --fix.
  Manual propagation across individual files is forbidden.
```

#### Algorithm

```python
def validate_metrics(package: Package) -> MetricAnalysis:
    """M-IV: Validate all metrics against CANONICAL."""
    from recruiter_filter import CANONICAL
    violations = []

    for doc in package.all_documents():
        text = doc.text
        # Check each canonical metric
        for key, value in CANONICAL.items():
            # Look for the wrong version of this metric
            # (This is a heuristic — full implementation uses regex patterns)
            pass  # Delegated to recruiter_filter.py's existing logic

    return MetricAnalysis(valid=len(violations) == 0, violations=violations)
```

---

### Article M-V — Content Complementarity

#### Logic

```
Definition:
  overlap(d₁, d₂) = |phrases₄(d₁) ∩ phrases₄(d₂)| / max(|phrases₄(d₁)|, 1)

  where phrases₄(d) = set of all 4-word sequences in d (lowercased, stripped)

Axiom M-V.1 (Non-Redundancy):
  overlap(resume, coverletter) < τ_overlap

  where τ_overlap = 0.03 (3% — roughly < 5 shared 4-word phrases)

Axiom M-V.2 (Complementary Roles):
  role(resume) = WHAT   — structured evidence (metrics, bullets, project names)
  role(coverletter) = WHY  — narrative (motivation, constraint-driven engineering, career arc)
  role(portal_answers) = HOW  — direct evidence per specific question

  The three documents form a triptych. Each panel shows a different face
  of the same person. Together they are complete; individually they are
  distinct.

Theorem M-V.1 (The Overlap Test):
  If a recruiter reads the cover letter after the resume and encounters
  the same phrases, the cover letter's marginal information gain is zero:
    κ(CL | resume) ≈ 0

  By Testament Art. I (Knowledge Imperative), κ > 0 is required.
  Therefore overlap must be minimized.
```

#### Algorithm

```python
def validate_complementarity(resume: Document, coverletter: Document) -> OverlapAnalysis:
    """M-V: Validate content complementarity."""
    import re

    def phrases_4(text):
        words = re.findall(r'\w{3,}', text.lower())
        return {' '.join(words[i:i+4]) for i in range(len(words)-3)}

    resume_text = re.sub(r'<[^>]+>', ' ', resume.html)
    cl_text = coverletter.text

    resume_phrases = phrases_4(resume_text)
    cl_phrases = phrases_4(cl_text)

    shared = resume_phrases & cl_phrases
    ratio = len(shared) / max(len(cl_phrases), 1)

    return OverlapAnalysis(
        valid=len(shared) <= 5,
        shared_phrases=list(shared)[:10],
        ratio=ratio,
        diagnosis=f"M-V: {len(shared)} shared phrases (max 5)" if len(shared) > 5 else "",
    )
```

---

### Article M-VI — Visual Identity Parity

#### Logic

```
Axiom M-VI:
  template(coverletter) ≅ template(resume)

  where ≅ means: same font family, same header structure (name centered,
  contact info, border-bottom), same page dimensions, same margin ratios.

  The two PDFs must look like they came from the same person and the
  same design system. A hiring manager receives both in the same email
  or portal upload — visual inconsistency signals carelessness.

Theorem M-VI.1 (Template Source):
  coverletter.html must be generated from:
    materials/resumes/base/cover-letter-template.html

  which was derived from the resume template's CSS.
  The bare `<p>` wrapper (font-size: 11pt, margin: 1in) is NOT acceptable.
```

#### Algorithm

```python
def validate_visual_parity(package: Package) -> ParityAnalysis:
    """M-VI: Validate visual identity parity between resume and cover letter."""
    resume_html = package.resume.html
    cl_html = package.coverletter.html if package.coverletter else ""

    violations = []

    # Check that cover letter uses the proper template
    if cl_html and "border-bottom: 1.5pt solid" not in cl_html:
        violations.append("M-VI: cover letter missing header border — not using matching template")

    if cl_html and "Anthony James Padavano" not in cl_html:
        violations.append("M-VI: cover letter missing full name in header")

    # Check font consistency
    if cl_html and "Georgia" not in cl_html:
        violations.append("M-VI: cover letter not using Georgia font — must match resume")

    return ParityAnalysis(valid=len(violations) == 0, violations=violations)
```

---

### Article M-VII — The Storefront Gate

#### Logic

```
Definition (from Storefront Playbook):
  storefront(text) = the first 60 seconds of reading
  cathedral(text) = the full depth available on request

Axiom M-VII.1 (Number First):
  ∀ opening sentence s of {resume.profile, coverletter.paragraph_1}:
    contains_number(s) = true

  "113 repositories" beats "I design complex systems."
  Numbers are scannable. Concepts require committed attention.

Axiom M-VII.2 (One Claim Per Sentence):
  ∀ sentence s in storefront region:
    claims(s) ≤ 1

  Multiple claims dilute each other at scanning speed.

Axiom M-VII.3 (Vocabulary Matching):
  ∀ document d targeting audience A:
    vocabulary(d) ∈ vocabulary_expected(A)

  | If they ask about... | Say...                                    | Not...                    |
  |---------------------|-------------------------------------------|---------------------------|
  | "Your practice"     | "systems art"                             | "creative infrastructure" |
  | "Innovation"        | "AI-augmented solo production"            | "AI-conductor model"      |
  | "Technical approach"| "automated governance, CI/CD"             | "promotion state machine" |

Axiom M-VII.4 (Storefront First):
  Structure: opening hook (storefront) → evidence → depth → close
  Never lead with the cathedral. The reviewer earns the cathedral
  by choosing to keep reading.
```

---

### Article M-VIII — Project Rotation

#### Logic

```
Definition:
  PROJECT_MENU = {all 113+ repositories, organized by domain}
  DEFAULT_5 = {ORGANVM System, agentic-titan, agent--claude-smith, Application Pipeline, Portfolio}
  selected(r) = the 5 projects listed on resume r

Axiom M-VIII.1 (Menu Size):
  |PROJECT_MENU_PRESENTED| ≥ 15

  The tailor prompt must present at least 15 projects for selection.

Axiom M-VIII.2 (Domain Relevance):
  ∀ project p ∈ selected(r):
    domain(p) ∩ domain(target_role) ≠ ∅

  Projects must be relevant to the specific role, not generic.

Axiom M-VIII.3 (Default as Fallback):
  DEFAULT_5 is the FALLBACK set, not the primary selection.
  If domain-relevant projects exist, they take priority.

Domain-specific rotation:
  DevRel: essays, portfolio, teaching tools, public-process
  AI/ML: agentic-titan, IRA facility, multi-model evaluation, recursive-engine
  Platform: CI/CD infrastructure, LaunchAgents, registry governance, pulse daemon
  Arts: generative art repos, Metasystem Master, p5.js, Krypto-Velamen
  FinServ: governance framework, audit trails, state machine, dependency validation
  Curriculum/Education: classroom-rpg-aetheria, adaptive-personal-syllabus, praxis-perpetua
```

---

### Article M-IX — Triple Layer Enforcement

#### Logic

```
Imported from Testament Art. III:

Axiom M-IX:
  ∀ paragraph p in {coverletter, portal_answers.free_text}:
    θ(p, pathos) > 0 ∧ θ(p, ethos) > 0 ∧ θ(p, logos) > 0

  pathos = felt truth, honest questions, human stakes
  ethos = embedded competence signals, demonstrated expertise
  logos = evidence, mechanism, causation

  A paragraph that is pure logos (textbook) fails.
  A paragraph that is pure pathos (diary) fails.
  A paragraph that is pure ethos (resume bullet) fails.

  The cover letter must integrate all three in every paragraph.
  The Anthropic 2026-03-19 example demonstrates this:
    "I build with Claude Code every day" — ethos (competence)
    "Not as a curiosity" — pathos (honest framing)
    "as the primary tool governing 113 repositories" — logos (evidence)
```

---

### Article M-X — Voice Constitution Compliance

#### Logic

```
Imported from Voice Constitution:

Axiom M-X:
  ∀ document d in package:
    ∀ AP ∈ {AP-01, ..., AP-11}:
      anti_pattern_score(d, AP) = 0

  No anti-pattern may appear in any submission material.

Key anti-patterns for submission context:
  AP-01: Generic corporate smoothness ("leverage core competencies")
  AP-02: Chatty filler ("It's worth noting that...")
  AP-03: Emotional reassurance replacing specification
  AP-08: Enthusiasm replacing architecture ("I'm passionate about...")
  AP-09: Generic motivational filler

Theorem M-X.1:
  ∀ cover letter CL:
    CL must follow the 5-stage chain:
      intuition → distinction → structure → protocol → expansion

    Opening: a distinction about the role or domain (not "I am applying for...")
    Body: structural argument with evidence
    Close: expansion toward what the work enables
```

---

### Article M-XI — The Inhabitant Gate

#### Logic

```
Imported from Outreach Protocol P-V:

Axiom M-XI:
  ∀ free-text portal answer a:
    inhabitation(a, recipient_org) > τ_inhabit

  Free-text answers must address the RECIPIENT's world.
  "Tell us about your experience with X" → answer about X at THEIR scale,
  not a restatement of your resume.

  The answer demonstrates understanding of their problem space,
  not just possession of relevant skills.
```

---

### Article M-XII — Word Count Enforcement

#### Logic

```
Axiom M-XII:
  550 ≤ words(coverletter) ≤ 700

  This is not arbitrary. At 9pt Georgia with the matching template:
    550 words ≈ 90% page fill
    700 words ≈ 98% page fill

  Below 550: dead space (M-I violation)
  Above 700: overflow risk (M-I violation)

  The word count constraint is a DERIVED consequence of M-I
  for the specific template parameters. It is stated separately
  because word count is measurable before PDF rendering.
```

---

## 5. Cross-Article Coupling

```
Theorem C-1 (Materials-Testament Integration):
  ∀ paragraph p in coverletter:
    Testament(p) ∧ Materials(package)

  Each paragraph satisfies all 13 Testament articles independently.
  The Materials Protocol adds inter-document constraints.

Theorem C-2 (The Triptych Principle):
  resume + coverletter + portal_answers form a triptych:
    information(resume ∪ CL ∪ answers) > information(resume) + information(CL) + information(answers)

  The whole is greater than the sum because each document references
  different facets of the same body of work. Overlap reduces the
  information gain; complementarity increases it.

Theorem C-3 (Pipeline Integrity):
  ∀ package P: P must be produced by:
    apply.py → tailor_resume.py → build_resumes.py → build_cover_letters.py

  Manual file creation, direct HTML editing of batch-NN files, or
  subagent-written raw files violate pipeline integrity.
  The pipeline IS the enforcement mechanism.
```

---

## 6. Three-Persona Hardening

*[To be conducted after initial formalization — Rhetorician, Mathematician, Practitioner review in round-robin]*

---

## 7. Implementation Architecture

### materials_validator.py

```python
class MaterialsValidator:
    def validate_package(self, package_dir: Path) -> MaterialsReport:
        """Run all 12 Materials Protocol articles."""
        results = {
            "M-I":   self.validate_page_fill(package_dir),
            "M-II":  self.validate_structural_integrity(package_dir),
            "M-III": self.validate_identity(package_dir),
            "M-IV":  self.validate_metrics(package_dir),
            "M-V":   self.validate_complementarity(package_dir),
            "M-VI":  self.validate_visual_parity(package_dir),
            "M-VII": self.validate_storefront(package_dir),
            "M-VIII": self.validate_project_rotation(package_dir),
            "M-IX":  self.validate_triple_layer(package_dir),
            "M-X":   self.validate_voice_compliance(package_dir),
            "M-XI":  self.validate_inhabitation(package_dir),
            "M-XII": self.validate_word_count(package_dir),
        }
        return MaterialsReport(results=results)
```

### Integration Points

- **apply.py**: calls `MaterialsValidator.validate_package()` after generating all files, before declaring READY
- **tailor_resume.py**: prompt template embeds M-II, M-III, M-IV, M-VIII as HARD RULES
- **build_cover_letters.py**: enforces M-I, M-VI, M-XII during PDF generation
- **recruiter_filter.py**: enforces M-IV across all materials

### Verification

```bash
# Gold standard must PASS:
python scripts/materials_validator.py --package applications/2026-03-19/anthropic--engineering-editorial-lead/

# Broken batch must FAIL:
python scripts/materials_validator.py --package applications/2026-03-27/datadog--*/

# After fix, all must PASS:
python scripts/apply.py --target <id>  # continuity test includes all 12 M-articles
```
