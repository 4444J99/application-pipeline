# The Outreach Protocol: A Formal System for Multi-Turn Conversational Rhetoric

**Date:** 2026-03-24
**Status:** DESIGN
**Location:** `application-pipeline/docs/superpowers/specs/`
**Sibling:** `organvm-iv-taxis/orchestration-start-here/docs/testament-formalization.md`

---

## 1. Purpose

The Testament formalizes rhetoric within a single text unit. The Protocol formalizes rhetoric **across** text units in a conversational sequence. Where the Testament is thermodynamics (laws governing a single system), the Protocol is statistical mechanics (laws governing how systems interact across state transitions).

The Protocol governs all outreach messaging — LinkedIn connect notes, post-acceptance DMs, cold emails, follow-up sequences — as a unified formal system with axioms, theorems, proofs, algorithms, and mathematics.

## 2. Relationship to the Testament

The Protocol **imports** the Testament's primitive functions (κ, χ, δ, ω, θ) and all 13 axioms. Every individual message must independently satisfy all 13 Testament articles. The Protocol adds inter-message constraints — it does not relax intra-message constraints.

Formally:

```
∀m ∈ M: Testament(m) ∧ Protocol(M)
```

**Vacuous satisfaction:** Testament articles whose structural preconditions are unmet
are vacuously satisfied. For short-form messages (connect notes, DMs):
- Art. IV (Non-Submersible Units, 4-8 sections) — no sections exist → axiom precondition unmet → vacuously true
- Art. V (Collision Geometry, multi-thread convergence) — single short message has one thread → vacuously true
- Art. VII (Citation Discipline, endnote format) — no citations present → vacuously true

This is mathematically correct (∀x ∈ ∅: P(x) is trivially true) but stated explicitly
to prevent implementation confusion in validators.

## 3. Deliverables

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| Protocol formalization doc | `organvm-iv-taxis/orchestration-start-here/docs/outreach-protocol-formalization.md` | Formal spec (Logic/Algorithm/Mathematics per article) |
| Protocol validator module | `application-pipeline/scripts/protocol_validator.py` | Programmatic enforcement of all 7 articles |
| DM composer module | `application-pipeline/scripts/dm_composer.py` | Composes acceptance DMs using Protocol + Testament constraints |
| Upgraded outreach templates | `application-pipeline/scripts/outreach_templates.py` | Connect note generation with P-I hook planting validation |
| Upgraded outreach engine | `application-pipeline/scripts/outreach_engine.py` | Full lifecycle management with Protocol enforcement |
| Test suite | `application-pipeline/tests/test_protocol_validator.py`, `tests/test_dm_composer.py` | Coverage for all 7 articles + cross-article couplings |

## 4. Foundational Definitions

### 4.1 Domain Extension

```
M = {m₁, m₂, ..., mₙ}           — message sequence (chronologically ordered turns)
A ∈ {pending, accepted, declined}  — acceptance boundary state
Sender, Recipient ∈ Agents         — the two parties
Channel ∈ {linkedin, email, ...}   — communication platform

Turn(mᵢ) ∈ {outbound, inbound}    — who sent it
Phase(mᵢ) = { pre_boundary  if A = pending at time(mᵢ)
             { post_boundary if A = accepted at time(mᵢ)
```

### 4.2 Primitive Functions (Protocol-Specific)

```
H : M → 𝒫(Claim)                  — hook extractor: set of recoverable claims in a message
ρ : M → [0, 1]                    — self-description ratio: |self-referential content| / |total content|
Q : M → Question ∪ {∅}            — terminal question extractor
Φ : M × M → [0, 1]               — continuity score (asymmetric: Φ(mᵢ → mⱼ))
E : Question → [0, 1]             — effort to answer (lower = easier)
Σ : Question → [0, 1]             — salience to recipient (higher = harder to ignore)
I : M → [0, 1]                    — inhabitation score: degree message addresses recipient's daily world
```

### 4.3 The Conversational State Vector

```
S = (a, τ, μ, ω) ∈ [0,1]⁴

where:
  a = attention    — recipient's remaining attention budget (depletes per message)
  τ = trust        — recipient's trust in sender (builds with demonstrated understanding)
  μ = curiosity    — recipient's desire to know more (driven by intrigue)
  ω = obligation   — recipient's felt need to respond (driven by questions about their world)

Each message m transforms S:
  S_{n+1} = T(m_{n+1}, S_n)

The acceptance event is a phase transition:
  S_post = Λ(S_pre)

  Λ preserves τ (trust earned in the connect persists)
  Λ resets a partially (acceptance opens a new attention window)
  Λ amplifies μ if hook was strong (they accepted because they were curious)
  Λ creates ω > 0 (social reciprocity — accepting creates mild obligation to engage)
```

### 4.4 Conservation Law

```
Theorem 0 (Conservation of Conversational Energy):

  Define conversational energy:
    E(S) = a · (τ·ω + μ)

  where τ·ω captures trust-obligation coupling (high trust amplifies felt obligation)
  and μ (curiosity) remains independently additive.

  The total energy budget is finite and bounded:
    E(S₀) ≤ E_max (platform-dependent constant)

  Each OUTBOUND message consumes attention:
    a_{n+1} < a_n  for consecutive outbound turns within a phase

  INBOUND messages (recipient turns) may partially restore attention:
    a_post_inbound ≥ a_pre_inbound  (recipient engagement signals interest)

  The acceptance boundary provides a larger restoration:
    a_post_accept > a_pre_accept  (the act of accepting signals renewed willingness)

  THEREFORE: the Protocol's laws are all energy-optimal —
  they minimize attention cost while maximizing the τ·ω + μ product.

  This is the conversational analogue of the principle of least action.
```

---

## 5. The Seven Articles

### Article P-I — The Seed Axiom (Hook Planting)

#### Logic

```
Definition:
  Claim = atomic proposition about the sender's work that is:
    (a) specific — not generic self-description
    (b) recoverable — can be referenced in a future message without restatement
    (c) falsifiable OR frame-novel — either makes a checkable claim OR introduces
        a novel conceptual framing that recontextualizes known information

  H(m) = set of claims planted in message m

Axiom P-I:
  ∀m ∈ M where Turn(m) = outbound ∧ Phase(m) = pre_boundary:
    H(m) ≠ ∅ ∧ 1 ≤ |H(m)| ≤ H_max(channel)

  where H_max(linkedin) = 2, H_max(email) = 4

  Every outbound pre-boundary message plants at least one and at most
  H_max recoverable claims.

Theorem P-I.1 (Specificity Requirement):
  ∀h ∈ H(m):
    ¬generic(h) ∧ ¬substitutable(h)

  where:
    generic(h) ≡ h could describe >50% of professionals in the field
    substitutable(h) ≡ replacing sender's name with another's preserves truth

  Proof:
    1. Assume generic(h)
    2. Then h carries no distinguishing information: κ(h) ≈ 0
    3. By Testament Art. I (Knowledge Imperative), κ > 0 required
    4. Contradiction — ∎

Theorem P-I.2 (Recoverability):
  ∀h ∈ H(m_connect):
    ∃ reference function ref(h) such that:
      ref(h) can appear in m_dm ∧
      |ref(h)| ≤ |h| / 2  — the reference is at most half the original length

Theorem P-I.3 (Validity Gate):
  ∀h ∈ H(m):
    specific(h) ∧ (falsifiable(h) ∨ frame_novel(h))

  where:
    falsifiable(h) ≡ ∃ test(h) that could evaluate to false
    frame_novel(h) ≡ h recontextualizes known information via novel conceptual framing

  "I'm a software engineer" — INVALID (generic, neither falsifiable nor novel)
  "50 dependency edges with 0 violations" — VALID (falsifiable, specific)
  "governance-as-artwork" — VALID (frame-novel, specific)

Theorem P-I.4 (Notification Window):
  For platforms with notification truncation (LinkedIn mobile ≈ 100 chars):
    The primary hook h₁ ∈ H(m) must satisfy:
      position(h₁, m) ≤ notification_window(channel)

  A hook planted beyond the truncation point may never be seen.
```

#### Algorithm

```python
def validate_hook_planting(connect_note: Message, channel: str = "linkedin") -> list[Claim]:
    """Extract and validate hooks from a connect note."""
    claims = extract_claims(connect_note)

    if not claims:
        raise ProtocolViolation("P-I: no recoverable claims found")

    h_max = {"linkedin": 2, "email": 4}.get(channel, 3)
    notification_window = {"linkedin": 100, "email": None}.get(channel)

    valid_hooks = []
    for claim in claims:
        if is_generic(claim):
            continue
        if not (is_falsifiable(claim) or is_frame_novel(claim)):
            continue
        if reference_length(claim) > len(claim.text) / 2:
            continue
        valid_hooks.append(claim)

    if not valid_hooks:
        raise ProtocolViolation(
            "P-I: claims found but none are specific + (falsifiable | frame-novel) + recoverable"
        )

    if len(valid_hooks) > h_max:
        valid_hooks = valid_hooks[:h_max]  # Trim to platform limit

    # Notification window check
    if notification_window and valid_hooks:
        primary = valid_hooks[0]
        if primary.position_in(connect_note) > notification_window:
            raise ProtocolViolation(
                f"P-I: primary hook appears at char {primary.position_in(connect_note)}, "
                f"beyond notification window of {notification_window}"
            )

    return valid_hooks


def is_generic(claim: Claim) -> bool:
    """Would >50% of professionals in the field satisfy this claim?"""
    has_number = bool(re.search(r'\d+', claim.text))
    has_proper_noun = bool(re.search(r'[A-Z][a-z]+(?:\s[A-Z][a-z]+)*', claim.text))
    has_novel_frame = claim.framing_novelty > 0.5
    return not (has_number or has_proper_noun or has_novel_frame)


def is_falsifiable(claim: Claim) -> bool:
    """Could this claim be checked and found to be wrong?"""
    return claim.has_checkable_assertion


def is_frame_novel(claim: Claim) -> bool:
    """Does this claim recontextualize known information via novel framing?"""
    return claim.framing_novelty > 0.7
```

#### Mathematics

```
Define the hook space:
  ℋ = {h ∈ Claim : specific(h) ∧ (falsifiable(h) ∨ frame_novel(h)) ∧ recoverable(h)}

The hook density of a connect note:
  η(m) = |H(m) ∩ ℋ| / |words(m)|

  For LinkedIn (300 char limit): η(m) ≥ 1/50 (at least one valid hook per 50 words)

The recovery function:
  ρ_ref : ℋ → W*  where |ρ_ref(h)| ≤ |h| / 2

Hook strength:
  σ_H(h) = specificity(h) × validity(h) × compactness(h)

  where:
    validity(h) = max(falsifiability(h), frame_novelty(h))
    compactness(h) = 1 - |ρ_ref(h)| / |h|

  σ_H ∈ (0, 1]. Maximized when the hook is maximally specific, valid, and compact.
```

---

### Article P-II — Conservation of Thread (Continuity Obligation)

#### Logic

```
Definition:
  Φ(mᵢ → mⱼ) = asymmetric continuity measure:
    coverage of H(mᵢ) in opening(mⱼ)

  Φ measures what fraction of hooks from mᵢ are addressed in mⱼ's opening.
  Asymmetric: mⱼ must continue mᵢ, but mᵢ need not anticipate mⱼ.

Axiom P-II:
  ∀ consecutive outbound messages (mᵢ, mⱼ) where Phase(mᵢ) = pre ∧ Phase(mⱼ) = post:
    Φ(mᵢ → mⱼ) > τ_continuity

  The post-boundary message MUST continue the pre-boundary hook.
  τ_continuity > 0 — zero continuity (complete restart) violates the axiom.

Theorem P-II.1 (Thread Is Not Restatement):
  Φ(mᵢ → mⱼ) > τ ∧ mⱼ ≠ restatement(mᵢ)

  Proof:
    1. Let mⱼ = restatement(mᵢ)
    2. Then κ(mⱼ | mᵢ) = 0 — no new knowledge given mᵢ as context
    3. By Testament Art. I, κ > 0 required
    4. Contradiction — continuity must DEVELOP the hook, not repeat it  ∎

Theorem P-II.2 (Development Obligation):
  Let h ∈ H(mᵢ) be a hook planted in the connect note.
  Let dev(h, mⱼ) = the development of h in the DM.

  dev(h, mⱼ) must satisfy:
    depth(dev(h, mⱼ)) > depth(h)

  The DM takes the hook deeper — adds detail, consequence, or implication
  that the connect note's character limit prevented.

Theorem P-II.3 (The Acceptance Boundary as Information Gate):
  The acceptance event reveals information not available pre-boundary:
    - Recipient's full name (LinkedIn often abbreviates pre-connection)
    - Recipient's current headline/role
    - Mutual connections
    - Recent activity

  The DM MAY incorporate this revealed information,
  but MUST still satisfy Φ > τ with the original hook.
  New information supplements the thread; it doesn't replace it.
```

#### Algorithm

```python
def validate_continuity(connect: Message, dm: Message) -> ContinuityAnalysis:
    """Verify that the DM continues the connect note's thread."""
    hooks = validate_hook_planting(connect)

    references_found = []
    for hook in hooks:
        ref = find_reference(hook, dm)
        if ref:
            references_found.append((hook, ref))

    if not references_found:
        return ContinuityAnalysis(
            valid=False,
            diagnosis="P-II: DM does not reference any hook from connect note",
        )

    for hook, ref in references_found:
        if is_restatement(hook, ref):
            return ContinuityAnalysis(
                valid=False,
                diagnosis=f"P-II: hook '{hook.text[:30]}...' is restated, not developed",
            )
        if depth(ref) <= depth(hook):
            return ContinuityAnalysis(
                valid=False,
                diagnosis="P-II: development does not go deeper than original hook",
            )

    coverage = len(references_found) / len(hooks)

    return ContinuityAnalysis(
        valid=coverage > CONTINUITY_THRESHOLD,
        score=coverage,
        hooks_referenced=[h.text for h, _ in references_found],
    )
```

#### Mathematics

```
The continuity function (asymmetric):

  Φ(mᵢ → mⱼ) = |{h ∈ H(mᵢ) : referenced(h, opening(mⱼ))}| / |H(mᵢ)|

  where opening(mⱼ) = first 30% of mⱼ's content.

  Axiom P-II requires: Φ(mᵢ → mⱼ) > τ_continuity ∈ (0, 1)

Development depth is a partial order:
  depth: Claim → ℕ where
    depth(h) = number of logical steps from h to its most basic premise

  Theorem P-II.2 requires:
    ∀h ∈ H(mᵢ): depth(dev(h, mⱼ)) > depth(h)

Thread conservation:
  Let thread(m₁, ..., mₙ) = ∩ᵢ semantic_field(mᵢ)

  Conservation: thread ≠ ∅ across the full sequence.
  The intersection of semantic fields is non-empty —
  the thread is never fully abandoned.

  Analogous to conservation of momentum: the "direction" of the
  conversation is preserved even as content evolves.
```

---

### Article P-III — Attention Economics (Self-Description Ratio Decay)

#### Logic

```
Definition:
  ρ(m) = |self_referential_content(m)| / |total_content(m)|

  self_referential_content = sentences where the grammatical subject
  is the sender or the sender's work/system/project.

Axiom P-III (Monotonic Decay — Sender-Initiated Content):
  ∀ consecutive outbound INITIATING messages (mᵢ, mⱼ) where i < j:
    ρ(mⱼ) < ρ(mᵢ)

  Self-description ratio STRICTLY DECREASES across sender-initiated turns.
  Responsive turns (answering a recipient's direct question) may temporarily
  spike ρ — this is a REINVESTMENT, not a violation.

Theorem P-III.1 (The Gate-Is-Passed Principle):
  ρ(m_connect) ∈ [0.6, 0.9]  — connect is mostly self-introduction
  ρ(m_dm)     ∈ [0.15, 0.35] — DM is mostly about the recipient

  Proof:
    1. The connect note's PURPOSE is identification → ρ must be high
    2. Upon acceptance, identification is resolved (profile viewed, note read)
    3. Repeating identification has κ ≈ 0 (Art. I violation)
    4. Therefore ρ must drop — DM's purpose shifts to engagement
    5. Engagement requires understanding the recipient's world  ∎

Theorem P-III.2 (The Asymptotic Floor):
  lim_{n→∞} ρ(mₙ) > 0

  Self-description never reaches zero — the sender's perspective IS the
  conversation. But it becomes a lens, not the subject.
  ρ_∞ ≈ 0.10-0.15 (10-15% self-reference in mature exchanges).

Corollary P-III.1 (The Monologue Detector):
  ρ(m_dm) > 0.6 → PROTOCOL VIOLATION

  A post-acceptance DM that is >60% about the sender is a monologue.
```

#### Algorithm

```python
def compute_self_description_ratio(message: Message, sender: Agent) -> float:
    """ρ(m) = proportion of self-referential content."""
    sentences = message.sentences()
    self_ref = sum(1 for s in sentences if refers_to(grammatical_subject(s), sender))
    return self_ref / len(sentences) if sentences else 0.0


def validate_ratio_decay(
    sequence: list[Message], sender: Agent
) -> DecayAnalysis:
    """Verify monotonic decay of self-description ratio across initiating turns."""
    initiating = [m for m in sequence if m.turn == "outbound" and m.is_initiating]
    ratios = [(m, compute_self_description_ratio(m, sender)) for m in initiating]

    violations = []
    for i in range(len(ratios) - 1):
        m_prev, rho_prev = ratios[i]
        m_next, rho_next = ratios[i + 1]
        if rho_next >= rho_prev:
            violations.append(DecayViolation(
                message=m_next, rho=rho_next, expected_below=rho_prev,
            ))

    if len(ratios) >= 2:
        dm_rho = ratios[1][1]
        if dm_rho > 0.6:
            violations.append(MonologueViolation(
                message=ratios[1][0], rho=dm_rho,
                diagnosis="post-acceptance DM is >60% self-referential",
            ))

    return DecayAnalysis(
        valid=len(violations) == 0,
        ratios=[(m.id, r) for m, r in ratios],
        violations=violations,
    )
```

#### Mathematics

```
The self-description ratio follows exponential decay:

  ρ(n) = ρ_∞ + (ρ₀ - ρ_∞) · e^(-λn)

where:
  ρ₀ = initial ratio (connect note, typically 0.7-0.8)
  ρ_∞ = asymptotic floor (0.10-0.15)
  λ = decay constant (platform-dependent)
  n = initiating turn number

For the two-message case (connect → DM), λ = 1.5 (LinkedIn-calibrated):
  ρ(1) ≈ 0.12 + 0.63 · 0.22 ≈ 0.26

  Matches the empirical target range [0.15, 0.35].

The attention cost of self-description:
  C_self(m) = ρ(m) · a(Sₙ)

  High ρ burns attention without building obligation or curiosity.
  Low ρ conserves attention while investing in engagement.
```

---

### Article P-IV — The Terminal Question Imperative (Response Architecture)

#### Logic

```
Definition:
  Q(m) = the substantive question that terminates message m, or ∅ if none
  E(q) ∈ [0, 1] = effort required to answer (0 = trivial, 1 = dissertation)
  Σ(q) ∈ [0, 1] = salience to recipient (0 = irrelevant, 1 = defining concern)

Axiom P-IV:
  ∀m ∈ M where Turn(m) = outbound ∧ Phase(m) = post_boundary:
    Q(m) ≠ ∅

  Every post-boundary outbound message terminates with a question.

Theorem P-IV.1 (The Effort-Salience Inversion):
  The optimal question maximizes: Σ(q) / E(q)

  Proof (by exhaustion):
    Case 1: E HIGH, Σ HIGH → deferred → forgotten ✗
    Case 2: E LOW, Σ LOW → not worth answering ✗
    Case 3: E HIGH, Σ LOW → worst case ✗
    Case 4: E LOW, Σ HIGH → response nearly involuntary ✓  ∎

Theorem P-IV.2 (Question Placement):
  Q(m) must be the TERMINAL element of m.

  Proof:
    1. Let Q(m) appear mid-message, followed by additional content C
    2. C arrives after Q, consuming attention
    3. Recency bias: C, not Q, occupies working memory at decision point
    4. Response probability maximized when Q is the last thing read  ∎

  This is the Protocol's analogue of Testament Art. XIII (power position).

Theorem P-IV.3 (Question Singularity):
  For the SUBSTANTIVE question: exactly 1 per outbound message.

  Multiple substantive questions dilute obligation:
    ω(q₁ ∧ q₂) < ω(q₁) because decision fatigue reduces response probability.

  Exception: On channels with >500 character budget, ONE logistical facilitation
  question ("Would Thursday work?") is permitted alongside the substantive question.
  The logistical question reduces effort by providing a concrete next step.
```

#### Algorithm

```python
def validate_terminal_question(message: Message) -> QuestionAnalysis:
    """Verify P-IV: terminal question with optimal effort-salience."""
    questions = extract_questions(message)
    substantive = [q for q in questions if not q.is_logistical]
    logistical = [q for q in questions if q.is_logistical]

    if not substantive:
        return QuestionAnalysis(
            valid=False,
            diagnosis="P-IV: no substantive question found",
        )

    if len(substantive) > 1:
        return QuestionAnalysis(
            valid=False,
            diagnosis=f"P-IV: {len(substantive)} substantive questions — singularity violated",
        )

    if len(logistical) > 1:
        return QuestionAnalysis(
            valid=False,
            diagnosis="P-IV: multiple logistical questions",
        )

    if logistical and message.channel_char_limit and message.channel_char_limit <= 500:
        return QuestionAnalysis(
            valid=False,
            diagnosis="P-IV: logistical question not permitted on short-form channels",
        )

    q = substantive[0]

    if not is_terminal(q, message):
        return QuestionAnalysis(
            valid=False,
            diagnosis="P-IV: substantive question is not the terminal element",
        )

    effort = estimate_effort(q)
    salience = estimate_salience(q, message.recipient)
    ratio = salience / max(effort, 0.01)

    return QuestionAnalysis(
        valid=True,
        question=q.text,
        effort=effort,
        salience=salience,
        ratio=ratio,
        optimal=ratio > EFFORT_SALIENCE_THRESHOLD,
    )
```

#### Mathematics

```
The response probability:
  P(response | q) = sigmoid(α · Σ(q) / E(q) - β)

For LinkedIn DMs: α ≈ 3.0, β ≈ 1.5

  Σ/E = 0.5 → P ≈ 0.50
  Σ/E = 1.0 → P ≈ 0.82
  Σ/E = 2.0 → P ≈ 0.95
  Σ/E = 3.0 → P ≈ 0.99

The question quality metric:
  Q* = Σ(q) · (1 - E(q))

  Q* ∈ [0, 1]. Optimal region: Q* > 0.5

The singularity constraint:
  For n substantive questions:
    ω_total = max(ω(qᵢ)) · (1 / n^γ)   where γ ≈ 0.7

  n=1: full obligation. n=2: 62%. n=3: 48%.
  Singularity (n=1) is strictly optimal.
```

---

### Article P-V — The Inhabitation Principle (Domain Targeting)

#### Logic

```
Definition:
  inhabit(r, domain) ≡ r navigates domain daily as part of their work
  I(q, r) ∈ [0, 1] = degree to which question q addresses something r inhabits

Axiom P-V:
  ∀ q = Q(m) where Turn(m) = outbound:
    I(q, recipient) > τ_inhabit

  The terminal question must address the recipient's daily world.

Theorem P-V.1 (The Sender's Domain Is Not The Target):
  I(q, recipient) > τ → ¬about_sender(q)

  Proof:
    1. Let q be about the sender's domain exclusively
    2. Recipient's knowledge of q's answer is limited → E(q) HIGH
    3. Not about something they live inside → Σ(q) LOW
    4. By P-IV, Σ/E must be maximized → contradiction  ∎

Theorem P-V.2 (The Tension Principle):
  The highest-salience questions address TENSIONS the recipient manages.

  ∀ recipient r with role R in organization O:
    ∃ tension_set Ψ(r) = {ψ₁, ..., ψₖ}

  Optimal q satisfies: q ∈ Ψ(recipient)

  Why tensions:
    - No settled answer → recipient has thought about it
    - Professional → responding doesn't feel invasive
    - Invite opinion → low effort
    - Demonstrate research → builds τ (trust)

Theorem P-V.3 (The Decision-Reference Heuristic):
  Alongside tension-matching, questions referencing a PUBLIC DECISION
  by the recipient ("You chose X over Y — what convinced you?")
  achieve higher Σ because they reference a specific, observable commitment.

  decision_salience(q) ≥ tension_salience(q) when the decision is:
    (a) public (verifiable from their profile, posts, or company announcements)
    (b) non-trivial (involved a meaningful tradeoff)
    (c) recent (within the recipient's active memory)

Theorem P-V.4 (The Research Prerequisite):
  I(q, r) > τ_inhabit → research(sender, r) has been performed

  A question cannot address the recipient's daily world without research.
  This is not a separate rule — it falls out of P-V directly.
```

#### Algorithm

```python
def validate_inhabitation(question: Question, recipient: Agent) -> InhabitationAnalysis:
    """Verify that the question addresses the recipient's daily world."""
    if question.only_references(question.sender):
        return InhabitationAnalysis(
            valid=False,
            diagnosis="P-V: question is about sender's domain, not recipient's",
        )

    tensions = identify_tensions(recipient)
    decisions = identify_public_decisions(recipient)

    tension_score = max(
        (semantic_similarity(question.text, t.description), t)
        for t in tensions
    )[0] if tensions else 0.0

    decision_score = max(
        (semantic_similarity(question.text, d.description), d)
        for d in decisions
    )[0] if decisions else 0.0

    inhabitation = compute_inhabitation(question, recipient)

    return InhabitationAnalysis(
        valid=inhabitation > INHABITATION_THRESHOLD,
        score=inhabitation,
        tension_score=tension_score,
        decision_score=decision_score,
    )


def identify_tensions(recipient: Agent) -> list[Tension]:
    """Infer tensions from role, org, and org-size/stage context."""
    tensions = []
    org_size = recipient.org_size or "unknown"

    if "Head of Engineering" in recipient.role:
        tensions.append(Tension("reliability vs velocity"))
        if org_size == "startup":
            tensions.append(Tension("shipping speed vs technical debt"))
        elif org_size == "enterprise":
            tensions.append(Tension("platform standardization vs team autonomy"))

    if "CEO" in recipient.role or "Founder" in recipient.role:
        tensions.append(Tension("founding thesis vs market reality"))
        tensions.append(Tension("growth vs culture preservation"))

    if "Artistic Director" in recipient.role:
        tensions.append(Tension("institutional mission vs contemporary relevance"))
        tensions.append(Tension("accessibility vs rigor"))

    return tensions
```

#### Mathematics

```
The inhabitation function:
  I(q, r) = Σᵢ wᵢ · overlap(q, domainᵢ(r))

  where overlap(q, d) = semantic_similarity(q.text, d.description)
  implemented as TF-IDF cosine similarity (using the project's existing
  text_match.py engine) or embedding-based cosine similarity when available.

Empirical weights:
  w_tension = 0.35, w_decision = 0.30, w_role = 0.20, w_org = 0.10, w_public = 0.05

The inhabitation threshold: τ_inhabit = 0.35

The tension/decision salience boost:
  When q ∈ Ψ(r): Σ(q) = Σ_base(q) + 0.30
  When q references a public decision: Σ(q) = Σ_base(q) + 0.35
```

---

### Article P-VI — The Bare Resource Principle

#### Logic

```
Axiom P-VI.1 (Terminal Placement):
  ∀ resource r in message m:
    position(r, m) = terminal_segment(m) — after the question

Axiom P-VI.2 (Bare Presentation):
  ∀ resource r in message m:
    frame(r) = ∅

  No label, no explanation. The URL appears alone.

Theorem P-VI.1 (Resources Are Not Arguments):
  argument_weight(r) = 0 for all resources.

  Proof:
    1. A resource is evidence available on demand
    2. The argument was already made in the message body
    3. Framing creates a new claim requiring validation (Art. I overhead)
    4. Bare placement avoids overhead while preserving access  ∎

Theorem P-VI.2 (The Confidence Signal):
  frame(r) = ∅ → perceived_confidence(sender) increases.

  Bare links signal confidence. Explained links signal insecurity.
  "Here's my portfolio" = "I'm worried you won't click."
  A bare URL = "It speaks for itself."
```

#### Algorithm

```python
FRAMING_PATTERNS = [
    r"(?i)check out", r"(?i)here'?s my", r"(?i)take a look",
    r"(?i)you can (?:see|find|view)", r"(?i)portfolio:",
    r"(?i)link:", r"(?i)github:",
]

def validate_resource_placement(message: Message) -> ResourceAnalysis:
    """Verify P-VI: resources are bare and terminal."""
    resources = extract_urls(message)
    if not resources:
        return ResourceAnalysis(valid=True, resources=[])

    violations = []
    for r in resources:
        if not is_in_terminal_segment(r, message):
            violations.append(PlacementViolation(resource=r.url))
        surrounding = get_surrounding_text(r, message, window=20)
        if any(re.search(p, surrounding) for p in FRAMING_PATTERNS):
            violations.append(FramingViolation(resource=r.url, frame=surrounding))

    return ResourceAnalysis(
        valid=len(violations) == 0,
        resources=[r.url for r in resources],
        violations=violations,
    )
```

#### Mathematics

```
The attention cost of framing:
  C_frame = |frame(r)| · (1/a)

By conservation (Theorem 0), unnecessary attention cost is strictly suboptimal.
Since framing adds cost without increasing click probability:

  P(click | bare) ≈ P(click | frame) + ε   where ε ≈ 0.02-0.05

  argmin_placement [C_attention] subject to P(click) ≥ P_min
  Solution: bare, terminal.
```

---

### Article P-VII — Thread Parity and Closure

#### Logic

```
Definition:
  turns_sender(T) = |{m ∈ T : outbound}|
  turns_recipient(T) = |{m ∈ T : inbound}|
  parity(T) = turns_sender / max(turns_recipient, 1)
  visibility(T) ∈ {public, private}
  rs = relationship_strength ∈ [0, 10]

Axiom P-VII.1 (Parity Constraint):
  parity(T) ≤ π_max(visibility, rs)

  where:
    π_max(public, rs) = 2.0 + 0.5 · min(rs / 5, 1.0)
    π_max(private, rs) = 3.0 + 0.5 · min(rs / 5, 1.0)

  Cold outreach (rs=1): π_max = 2.1 (public), 3.1 (private)
  Warm contact (rs=5):  π_max = 2.5 (public), 3.5 (private)
  Strong tie (rs=10):   π_max = 2.5 (public), 3.5 (private) — capped

Axiom P-VII.2 (Closure Detection):
  A thread is CLOSED when ∃ mₙ ∈ T:
    is_terminal_acknowledgment(mₙ) ∧
    ¬contains_question(mₙ) ∧
    ¬invites_response(mₙ)

  Sending another message after closure violates the axiom.

Theorem P-VII.1 (The Diminishing Returns Law):
  Attention cost increases with thread length:
    C(n) = c₀ · (1 + α·n)  where α = context-loading penalty

  Obligation gain decreases:
    Δω(n) = ω₀ · e^(-λ_ω · n)

  Break-even: n* where Δω(n*) = C(n*)
  Numerical solution for LinkedIn: n* ≈ 2.3

  Practical: n* = 2 for cold (rs < 3), n* = 3 for warm (rs ≥ 3).

Theorem P-VII.2 (Escalation Gate):
  If turns_recipient = 0 after n_max outbound: STOP.

  Escalation to higher-bandwidth channel appropriate when:
    mutual_turns ≥ 4 ∧
    |recent_inbound| > |recent_outbound|

  (Recipient investing more than sender → ready for richer channel.)

Theorem P-VII.3 (The Suzanne Rule — Archetype of Warm Closure):
  A public thread with structure (s, r, s, r, s) where the final s:
    - References the recipient by name
    - Contains definitive attribution ("That was you")
    - Completes an emotional arc

  is CLOSED. Parity = 3/2 = 1.5 ≤ π_max. Optimal warm-path closure.

  Corollary: If recipient responds after closure, the thread REOPENS.
  The sender never reopens a closed thread unilaterally.
```

#### Algorithm

```python
def validate_thread_health(
    thread: list[Message], relationship_strength: float = 1.0
) -> ThreadAnalysis:
    """Validate parity, closure, and escalation readiness."""
    outbound = [m for m in thread if m.turn == "outbound"]
    inbound = [m for m in thread if m.turn == "inbound"]
    parity = len(outbound) / max(len(inbound), 1)
    visibility = thread[0].visibility if thread else "private"

    rs = relationship_strength
    pi_max = (2.0 if visibility == "public" else 3.0) + 0.5 * min(rs / 5, 1.0)

    violations = []

    if parity > pi_max:
        violations.append(ParityViolation(ratio=parity, limit=pi_max))

    cold = rs < 3
    n_max = 2 if cold else 3
    if len(outbound) >= n_max and len(inbound) == 0:
        violations.append(DiminishingReturns(
            outbound_count=len(outbound), inbound_count=0,
            diagnosis=f"{len(outbound)}+ outbound with 0 inbound — stop",
        ))

    closed = is_closed(thread[-1]) if thread else True

    escalation_ready = False
    if len(inbound) >= 2 and len(outbound) >= 2:
        if len(inbound[-1].text) > len(outbound[-1].text):
            escalation_ready = True

    return ThreadAnalysis(
        valid=len(violations) == 0,
        parity=parity,
        pi_max=pi_max,
        closed=closed,
        escalation_ready=escalation_ready,
        violations=violations,
    )
```

#### Mathematics

```
The parity function:
  π(T) = |{m ∈ T : outbound}| / max(|{m ∈ T : inbound}|, 1)

  Constraint: π(T) ≤ π_max(visibility, rs)

The diminishing returns curve with context-loading penalty:
  Δω(n) = ω₀ · e^(-λ_ω · n)
  C(n) = c₀ · (1 + α·n)         where α ≈ 0.3

  Break-even: n* solves ω₀ · e^(-λ_ω · n*) = c₀ · (1 + α·n*)
  For LinkedIn: n* ≈ 2.3 (cold), ≈ 3.1 (warm)

Thread energy at closure:
  E_close = a_remaining · (τ_final · ω_final + μ_final)

  Optimal: E_close > 0 — end while energy remains.
  Worst: E_close = 0 — thread exhausted all conversational energy.
```

---

## 6. Cross-Article Coupling

```
Theorem C-1 (Protocol-Testament Integration):
  ∀m ∈ M: Testament(m) ∧ Protocol(M)

Theorem C-2 (The Seed-Harvest Isomorphism):
  P-I (Hook) and P-IV (Question) are structurally isomorphic:
    Hook = claim planted for future development (next MESSAGE)
    Question = claim planted for immediate response (next TURN)

  Both satisfy: specific ∧ recoverable ∧ (falsifiable ∨ frame_novel)

Theorem C-3 (The ρ-I Directional Coupling):
  ∂ρ/∂n < 0 → capacity for I increases

  As self-description decreases across turns, more content budget
  becomes available for recipient-focused inhabitation. This is a
  DIRECTIONAL coupling, not a strict conservation: ρ(m) + I(m) ≈ 1
  holds only when content is binary (about sender or about recipient).
  Messages referencing third parties, shared context, or abstract topics
  may have both low ρ and low I simultaneously.

  The soft constraint: ρ(m) + I(m) ≥ 0.7 (at least 70% of content
  is either self-referential or recipient-focused; at most 30% is
  neutral/third-party).

Theorem C-4 (The Energy-Closure Bound):
  max_turns ≤ E₀ / c₀

  Hard upper bound on thread length, independent of content.
  Purely thermodynamic.
```

---

## 7. Implementation Architecture

### Phase 1: Formal Specification (this document + protocol formalization doc)

Write the Protocol formalization to `organvm-iv-taxis/orchestration-start-here/docs/outreach-protocol-formalization.md` in the same format as `testament-formalization.md`.

### Phase 2: Protocol Validator Module

New file: `scripts/protocol_validator.py`

```
ProtocolValidator
├── validate_hook_planting(connect_note, channel) → list[Claim]
├── validate_continuity(connect, dm) → ContinuityAnalysis
├── validate_ratio_decay(sequence, sender) → DecayAnalysis
├── validate_terminal_question(message) → QuestionAnalysis
├── validate_inhabitation(question, recipient) → InhabitationAnalysis
├── validate_resource_placement(message) → ResourceAnalysis
├── validate_thread_health(thread, rs) → ThreadAnalysis
└── validate_full_sequence(sequence) → ProtocolReport
```

Each validator returns a dataclass with `valid: bool`, diagnostics, and scores. `validate_full_sequence` runs all seven and produces a composite report.

### Phase 3: DM Composer Module

New file: `scripts/dm_composer.py`

```
DMComposer
├── compose_acceptance_dm(connect_note, recipient, entry) → ComposedDM
│   ├── extract_hooks(connect_note)           — P-I
│   ├── develop_hooks(hooks, recipient)        — P-II
│   ├── compute_ratio_target(turn_number)      — P-III
│   ├── generate_terminal_question(recipient)  — P-IV + P-V
│   ├── place_resources(portfolio_url)          — P-VI
│   └── validate_full(composed_dm)             — all articles
├── compose_followup_dm(thread, recipient) → ComposedDM
└── assess_thread_state(thread) → ThreadState
```

Inputs: connect note text, recipient Agent (from contacts.yaml), pipeline entry. Outputs: composed DM text + validation report.

### Phase 4: Integration with Existing Pipeline

**`outreach_templates.py`:**
- Upgrade `generate_connect_note()` to run P-I validation as a post-generation gate. Generation produces candidate text; `validate_hook_planting()` runs on the result; if it fails, the template is regenerated with tighter constraints. Not a wrapper — a feedback loop.
- Expand `position_hooks` dict from 5 to all 9 canonical identity positions (add: documentation-engineer, governance-architect, platform-orchestrator, founder-operator). Same expansion for `position_evidence` in `generate_cold_email()`.
- New function: `generate_acceptance_dm_template(entry, connect_note_text)` that invokes DMComposer.

**`outreach_engine.py`:**
- Add `"acceptance"` to the lifecycle stages alongside the existing `PROTOCOL` dict (connect/email/followup).
- New function: `prepare_acceptance_dm(entry_id, connect_note_text)` triggered when an acceptance is logged in outreach-log.yaml (type: acceptance).
- Wiring: recipient `Agent` constructed from `contacts.yaml` via `pipeline_lib.load_contacts()` → filter by name/org → construct Agent dataclass with role, org, org_size, known tensions.
- The existing `prepare_outreach()` flow (which operates on `submitted`/`staged` entries) remains unchanged. Acceptance DMs are a parallel path, not a modification of the existing pipeline.

**`followup.py`:**
- Import `validate_thread_health()` from `protocol_validator.py`.
- Before generating follow-up actions for a contact, check thread health. If P-VII flags diminishing returns or closure, suppress the follow-up and log the reason.

**`run.py`:**
- Add `protocol <entry-id>` quick command: runs Protocol validation on all outreach messages for an entry.
- Add `compose-dm <entry-id>` quick command: composes an acceptance DM using DMComposer and prints to stdout.

**New shared types** (in `protocol_types.py`, following the project's module decomposition pattern):
- `Message`, `Agent`, `Claim`, `Tension`, `Question` — core domain types
- `ContinuityAnalysis`, `DecayAnalysis`, `QuestionAnalysis`, `InhabitationAnalysis`, `ResourceAnalysis`, `ThreadAnalysis`, `ProtocolReport` — result dataclasses

### Phase 5: Test Coverage

```
tests/test_protocol_validator.py
  - test_hook_planting_valid_falsifiable
  - test_hook_planting_valid_frame_novel
  - test_hook_planting_rejects_generic
  - test_hook_planting_notification_window
  - test_continuity_detects_restart
  - test_continuity_rejects_restatement
  - test_continuity_accepts_development
  - test_ratio_decay_monotonic
  - test_ratio_decay_allows_reinvestment
  - test_monologue_detection
  - test_terminal_question_present
  - test_question_singularity
  - test_effort_salience_optimal
  - test_inhabitation_rejects_sender_domain
  - test_tension_matching
  - test_decision_reference
  - test_resource_bare_terminal
  - test_resource_rejects_framing
  - test_parity_cold_outreach
  - test_parity_warm_contact
  - test_closure_detection
  - test_diminishing_returns
  - test_suzanne_rule
  - test_full_sequence_validation
  - test_cross_article_rho_i_coupling

tests/test_dm_composer.py
  - test_compose_acceptance_dm_stripe
  - test_compose_acceptance_dm_ars_electronica
  - test_compose_acceptance_dm_posthog
  - test_composed_dm_passes_all_protocol_articles
  - test_composed_dm_passes_all_testament_articles
  - test_compose_rejects_hookless_connect_note
  - test_compose_handles_missing_recipient_data
  - test_compose_handles_no_portfolio_url
  - test_compose_refuses_followup_after_closure

tests/test_cross_article_couplings.py
  - test_seed_harvest_isomorphism_hook_validity_implies_question_validity
  - test_seed_harvest_isomorphism_question_validity_implies_hook_validity
  - test_energy_closure_bound_thread_exceeding_budget_flagged
  - test_energy_closure_bound_thread_within_budget_passes
  - test_rho_i_directional_coupling_low_rho_enables_high_i
  - test_rho_i_soft_floor_enforced
  - test_testament_integration_all_13_articles_on_composed_dm

tests/test_outreach_templates.py (EXISTING — add Protocol-integrated tests)
  - test_generate_connect_note_passes_hook_planting
  - test_generate_connect_note_all_9_positions_covered
  - test_connect_note_primary_hook_in_notification_window

tests/test_outreach_engine.py (EXISTING — add acceptance DM tests)
  - test_prepare_acceptance_dm_produces_valid_output
  - test_acceptance_dm_wires_recipient_from_contacts
```

---

## 8. Three-Persona Hardening — Integrated Revisions

| Article | Revision | Source |
|---------|----------|--------|
| P-I | Hook validity: `specific ∧ (falsifiable ∨ frame_novel)` | Rhetorician |
| P-I | `|H(m)| ≤ 2` for ≤300 char platforms. Primary hook within notification window | Practitioner |
| P-II | Continuity function is asymmetric: coverage of hooks, not cosine similarity | Mathematician |
| P-III | Decay on sender-initiated turns only. Reinvestment spikes permitted in responses | Rhetorician |
| P-IV | Singularity = 1 substantive. 1 logistical facilitation allowed on >500 char channels | Rhetorician |
| P-V | Decision-reference heuristic alongside tension-matching. Org-size context | Practitioner |
| Thm 0 | Energy function: `E = a · (τ·ω + μ)` with trust-obligation coupling | Mathematician |
| P-VII | `C(n) = c₀ · (1 + α·n)` — increasing context-load cost. n* ≈ 2 cold, 3 warm | Mathematician |
| P-VII | `π_max` scales with relationship_strength | Practitioner |

All revisions are incorporated into the articles above.
