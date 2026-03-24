#!/usr/bin/env python3
"""Protocol Validator — enforces the 7 articles of the Outreach Protocol.

Validates messages and message sequences against the formal system defined in
docs/superpowers/specs/2026-03-24-outreach-protocol-formalization-design.md

Usage:
    python scripts/protocol_validator.py --connect "message text" --channel linkedin
    python scripts/protocol_validator.py --dm "dm text" --connect "connect text"
    python scripts/protocol_validator.py --thread thread.yaml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from protocol_types import (
    Agent,
    Claim,
    ContinuityAnalysis,
    DecayAnalysis,
    DecayViolation,
    HookAnalysis,
    InhabitationAnalysis,
    Message,
    ProtocolReport,
    Question,
    QuestionAnalysis,
    ResourceAnalysis,
    ResourceViolation,
    Tension,
    ThreadAnalysis,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOTIFICATION_WINDOW = {"linkedin": 100}
HOOK_MAX = {"linkedin": 2, "email": 4}
CONTINUITY_THRESHOLD = 0.3
INHABITATION_THRESHOLD = 0.35
EFFORT_SALIENCE_THRESHOLD = 1.0
MONOLOGUE_THRESHOLD = 0.6

FRAMING_PATTERNS = [
    r"(?i)check out",
    r"(?i)here'?s my",
    r"(?i)take a look",
    r"(?i)you can (?:see|find|view)",
    r"(?i)portfolio\s*:",
    r"(?i)link\s*:",
    r"(?i)github\s*:",
]

# Patterns that indicate specificity (numbers, proper nouns, novel framings)
NUMBER_PATTERN = re.compile(r"\d[\d,]*")
PROPER_NOUN_PATTERN = re.compile(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+")
URL_PATTERN = re.compile(r"https?://\S+")
QUESTION_PATTERN = re.compile(r"[^.!]*\?")

# Frame-novel indicators — conceptual framings that recontextualize
NOVEL_FRAMES = [
    "governance-as-artwork",
    "governance-as-medium",
    "correctness guarantees",
    "state transition invariants",
    "promotion state machine",
    "non-submersible units",
    "AI-conductor",
    "cathedral",
    "storefront",
    "knowledge architecture",
    "institutional system",
    "creative medium",
    "conversion funnels",
    "A/B variant tracking",
    "snapshot trend analysis",
    "product analytics",
    "multi-model orchestration",
    "documentation governance",
    "open-source analytics",
    "multi-agent orchestration",
    "agentic",
    "forward-only transitions",
    "CI-enforced validation",
    "quality ratchet",
    "evaluation framework",
    "inter-rater agreement",
    "dependency edges",
]


# ---------------------------------------------------------------------------
# P-I: Hook Planting
# ---------------------------------------------------------------------------

def extract_claims(message: Message) -> list[Claim]:
    """Extract candidate claims from a message."""
    claims = []
    # Split on sentence boundaries, then on em-dashes and semicolons
    segments = re.split(r"[.!;]|\s—\s", message.text)
    for i, seg in enumerate(segments):
        seg = seg.strip()
        if len(seg) < 10:
            continue
        pos = message.text.find(seg)
        claim = Claim(
            text=seg,
            position=pos if pos >= 0 else 0,
            is_falsifiable=bool(NUMBER_PATTERN.search(seg)),
            is_frame_novel=any(f.lower() in seg.lower() for f in NOVEL_FRAMES),
            specificity_score=_specificity(seg),
        )
        claims.append(claim)
    return claims


def _specificity(text: str) -> float:
    """Compute specificity score ∈ [0, 1]."""
    score = 0.0
    if NUMBER_PATTERN.search(text):
        score += 0.4
    if PROPER_NOUN_PATTERN.search(text):
        score += 0.3
    if any(f.lower() in text.lower() for f in NOVEL_FRAMES):
        score += 0.3
    return min(score, 1.0)


def validate_hook_planting(
    connect_note: Message, channel: str = "linkedin"
) -> HookAnalysis:
    """P-I: Validate hook planting in a connect note."""
    claims = extract_claims(connect_note)
    h_max = HOOK_MAX.get(channel, 3)
    notif_window = NOTIFICATION_WINDOW.get(channel)

    valid_hooks = [c for c in claims if c.is_valid]

    if not valid_hooks:
        return HookAnalysis(
            valid=False,
            hooks=[],
            diagnosis="P-I: no specific + (falsifiable | frame-novel) claims found",
        )

    valid_hooks = valid_hooks[:h_max]

    # Notification window check
    if notif_window and valid_hooks:
        primary = valid_hooks[0]
        if primary.position > notif_window:
            return HookAnalysis(
                valid=False,
                hooks=valid_hooks,
                diagnosis=(
                    f"P-I: primary hook at char {primary.position}, "
                    f"beyond notification window of {notif_window}"
                ),
            )

    return HookAnalysis(valid=True, hooks=valid_hooks)


# ---------------------------------------------------------------------------
# P-II: Conservation of Thread (Continuity)
# ---------------------------------------------------------------------------

def _word_set(text: str) -> set[str]:
    """Lowercase word set for overlap computation."""
    return {w.lower() for w in re.findall(r"\w{3,}", text)}


def validate_continuity(
    connect: Message, dm: Message
) -> ContinuityAnalysis:
    """P-II: Verify DM continues the connect note's thread."""
    hook_result = validate_hook_planting(connect, connect.channel)
    if not hook_result.valid or not hook_result.hooks:
        return ContinuityAnalysis(
            valid=False,
            score=0.0,
            diagnosis="P-II: connect note has no valid hooks to continue",
        )

    # Asymmetric coverage: what fraction of hook content appears in DM opening
    dm_opening = dm.text[:int(len(dm.text) * 0.4)]
    dm_words = _word_set(dm_opening)

    hooks_referenced = []
    for hook in hook_result.hooks:
        hook_words = _word_set(hook.text)
        if not hook_words:
            continue
        overlap = len(hook_words & dm_words) / len(hook_words)
        if overlap > 0.2:
            hooks_referenced.append(hook.text)

    coverage = len(hooks_referenced) / len(hook_result.hooks) if hook_result.hooks else 0.0

    # Check for pure restatement (DM opening too similar to connect)
    connect_words = _word_set(connect.text)
    dm_all_words = _word_set(dm.text)
    if connect_words and dm_all_words:
        restatement_ratio = len(connect_words & dm_all_words) / len(connect_words)
        if restatement_ratio > 0.8 and len(dm.text) <= len(connect.text) * 1.3:
            return ContinuityAnalysis(
                valid=False,
                score=coverage,
                hooks_referenced=hooks_referenced,
                diagnosis="P-II: DM is a near-restatement of the connect note",
            )

    return ContinuityAnalysis(
        valid=coverage >= CONTINUITY_THRESHOLD,
        score=coverage,
        hooks_referenced=hooks_referenced,
        diagnosis="" if coverage >= CONTINUITY_THRESHOLD
        else "P-II: insufficient hook coverage in DM opening",
    )


# ---------------------------------------------------------------------------
# P-III: Attention Economics (Self-Description Ratio Decay)
# ---------------------------------------------------------------------------

SELF_REF_PATTERNS = [
    r"\bI\b", r"\bI['']m\b", r"\bI['']ve\b", r"\bmy\b", r"\bmine\b",
    r"\bme\b", r"\bI['']d\b", r"\bI['']ll\b",
]
SELF_REF_RE = re.compile("|".join(SELF_REF_PATTERNS), re.IGNORECASE)


def compute_self_description_ratio(message: Message) -> float:
    """ρ(m) — proportion of self-referential sentences."""
    sentences = message.sentences()
    if not sentences:
        return 0.0
    self_ref = sum(1 for s in sentences if SELF_REF_RE.search(s))
    return self_ref / len(sentences)


def validate_ratio_decay(sequence: list[Message]) -> DecayAnalysis:
    """P-III: Verify monotonic decay across sender-initiated outbound turns."""
    initiating = [m for m in sequence if m.turn == "outbound" and m.is_initiating]
    if len(initiating) < 2:
        return DecayAnalysis(valid=True, ratios=[], violations=[])

    ratios = [(i, compute_self_description_ratio(m)) for i, m in enumerate(initiating)]
    violations = []
    DECAY_FLOOR = 0.05  # Below this, self-reference is effectively absent

    for idx in range(len(ratios) - 1):
        i_prev, rho_prev = ratios[idx]
        i_next, rho_next = ratios[idx + 1]
        # Vacuous satisfaction: if both are below the floor, nothing to decay
        if rho_prev < DECAY_FLOOR and rho_next < DECAY_FLOOR:
            continue
        if rho_next >= rho_prev:
            violations.append(DecayViolation(
                message_index=i_next,
                rho=rho_next,
                expected_below=rho_prev,
            ))

    # Monologue check on post-boundary DM
    if len(ratios) >= 2:
        _, dm_rho = ratios[1]
        if dm_rho > MONOLOGUE_THRESHOLD:
            violations.append(DecayViolation(
                message_index=1,
                rho=dm_rho,
                expected_below=MONOLOGUE_THRESHOLD,
            ))

    diagnosis = ""
    if violations:
        diagnosis = f"P-III: {len(violations)} decay violation(s)"

    return DecayAnalysis(
        valid=len(violations) == 0,
        ratios=ratios,
        violations=violations,
        diagnosis=diagnosis,
    )


# ---------------------------------------------------------------------------
# P-IV: Terminal Question Imperative
# ---------------------------------------------------------------------------

def extract_questions(message: Message) -> list[Question]:
    """Extract questions from a message."""
    questions = []
    for match in QUESTION_PATTERN.finditer(message.text):
        text = match.group().strip()
        if len(text) < 10:
            continue
        pos = match.start()
        is_logistical = any(
            kw in text.lower()
            for kw in ["thursday", "friday", "monday", "tuesday", "wednesday",
                        "saturday", "sunday", "this week", "next week",
                        "15 minutes", "30 minutes", "quick call"]
        )
        questions.append(Question(
            text=text,
            position=pos,
            is_substantive=not is_logistical,
            is_logistical=is_logistical,
        ))
    return questions


def _is_terminal(question: Question, message: Message) -> bool:
    """Check if question is in the terminal segment of the message."""
    # Terminal = last 40% of the message (excluding URLs at the very end)
    text_no_urls = URL_PATTERN.sub("", message.text).rstrip()
    # For short messages (< 400 chars), use last 50%; for longer, last 40%
    ratio = 0.5 if len(text_no_urls) < 400 else 0.6
    threshold = len(text_no_urls) * ratio
    return question.position >= threshold


def estimate_effort(question: Question) -> float:
    """E(q) ∈ [0, 1] — effort to answer. Lower = easier."""
    text = question.text.lower()
    # Binary questions
    if text.startswith(("do you", "does ", "is ", "are ", "has ", "have ", "would ")):
        return 0.15
    # Opinion about own domain
    if any(kw in text for kw in ["how do you", "what do you think", "what convinced"]):
        return 0.25
    # Comparative / tradeoff questions
    if any(kw in text for kw in ["tension", "tradeoff", "balance", "handle"]):
        return 0.30
    # Open-ended
    return 0.50


def estimate_salience(question: Question, recipient: Agent | None) -> float:
    """Σ(q) ∈ [0, 1] — salience to recipient. Higher = harder to ignore."""
    if not recipient:
        return 0.5  # Can't estimate without recipient data
    text = question.text.lower()
    score = 0.3  # baseline

    # Org reference
    if recipient.organization and recipient.organization.lower() in text:
        score += 0.2
    # Role reference
    if recipient.role:
        role_words = {w.lower() for w in recipient.role.split() if len(w) > 3}
        text_words = {w.lower() for w in text.split()}
        if role_words & text_words:
            score += 0.15
    # Tension indicators
    tension_words = ["tension", "tradeoff", "balance", "handle", "chose",
                     "convinced", "bet", "decision", "challenge"]
    if any(tw in text for tw in tension_words):
        score += 0.25

    return min(score, 1.0)


def validate_terminal_question(message: Message) -> QuestionAnalysis:
    """P-IV: Validate terminal question presence and quality."""
    questions = extract_questions(message)
    substantive = [q for q in questions if q.is_substantive]

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

    q = substantive[0]

    if not _is_terminal(q, message):
        return QuestionAnalysis(
            valid=False,
            question=q.text,
            diagnosis="P-IV: substantive question not in terminal segment",
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
        diagnosis="" if ratio >= EFFORT_SALIENCE_THRESHOLD
        else f"P-IV: effort/salience ratio {ratio:.2f} below threshold {EFFORT_SALIENCE_THRESHOLD}",
    )


# ---------------------------------------------------------------------------
# P-V: Inhabitation Principle
# ---------------------------------------------------------------------------

ROLE_TENSIONS = {
    "head of engineering": [
        Tension("reliability vs velocity", "role-inferred"),
        Tension("technical debt vs feature delivery", "role-inferred"),
    ],
    "engineering": [
        Tension("shipping speed vs code quality", "role-inferred"),
    ],
    "ceo": [
        Tension("founding thesis vs market reality", "role-inferred"),
        Tension("growth vs culture preservation", "role-inferred"),
    ],
    "co-ceo": [
        Tension("founding thesis vs market reality", "role-inferred"),
        Tension("co-leadership alignment vs speed", "role-inferred"),
    ],
    "founder": [
        Tension("founding thesis vs market reality", "role-inferred"),
        Tension("growth vs culture preservation", "role-inferred"),
    ],
    "artistic director": [
        Tension("institutional mission vs contemporary relevance", "role-inferred"),
        Tension("accessibility vs rigor", "role-inferred"),
    ],
    "recruiter": [
        Tension("candidate volume vs quality", "role-inferred"),
        Tension("speed to hire vs due diligence", "role-inferred"),
    ],
}


def identify_tensions(recipient: Agent) -> list[Tension]:
    """Infer tensions from recipient's role and org."""
    tensions = []
    role_lower = recipient.role.lower()
    for key, ts in ROLE_TENSIONS.items():
        if key in role_lower:
            tensions.extend(ts)
    return tensions


def validate_inhabitation(
    question: Question, recipient: Agent
) -> InhabitationAnalysis:
    """P-V: Verify question addresses recipient's daily world."""
    text = question.text.lower()

    # Check if question is about sender exclusively (no recipient references)
    has_recipient_ref = False
    if recipient.organization and recipient.organization.lower() in text:
        has_recipient_ref = True
    if recipient.role:
        role_words = {w.lower() for w in recipient.role.split() if len(w) > 3}
        if role_words & {w.lower() for w in text.split()}:
            has_recipient_ref = True
    # "you" / "your" references
    if re.search(r"\byou\b|\byour\b", text):
        has_recipient_ref = True

    if not has_recipient_ref:
        return InhabitationAnalysis(
            valid=False,
            score=0.0,
            diagnosis="P-V: question does not reference recipient's world",
        )

    # Tension matching
    tensions = identify_tensions(recipient)
    tension_score = 0.0
    for t in tensions:
        t_words = {w.lower() for w in t.description.split() if len(w) > 3}
        q_words = {w.lower() for w in text.split()}
        overlap = len(t_words & q_words) / max(len(t_words), 1)
        tension_score = max(tension_score, overlap)

    # Decision-reference heuristic
    decision_score = 0.0
    decision_words = ["chose", "decided", "bet on", "chose to", "committed",
                      "convinced", "picked", "went with"]
    if any(dw in text for dw in decision_words):
        decision_score = 0.6

    # Composite inhabitation score
    score = (
        0.35 * tension_score
        + 0.30 * decision_score
        + 0.20 * (0.8 if has_recipient_ref else 0.0)
        + 0.15 * (0.5 if recipient.organization.lower() in text else 0.0)
    )

    return InhabitationAnalysis(
        valid=score >= INHABITATION_THRESHOLD or has_recipient_ref,
        score=score,
        tension_score=tension_score,
        decision_score=decision_score,
        diagnosis="" if score >= INHABITATION_THRESHOLD
        else "P-V: inhabitation score below threshold",
    )


# ---------------------------------------------------------------------------
# P-VI: Bare Resource Principle
# ---------------------------------------------------------------------------

def validate_resource_placement(message: Message) -> ResourceAnalysis:
    """P-VI: Verify resources are bare and terminal."""
    urls = URL_PATTERN.findall(message.text)
    if not urls:
        return ResourceAnalysis(valid=True, resources=[])

    violations = []
    text_no_urls = message.text
    for url in urls:
        text_no_urls = text_no_urls.replace(url, "")

    text_no_urls = text_no_urls.rstrip()

    for url in urls:
        pos = message.text.find(url)

        # Terminal placement: URL should be after the main text content
        main_text_end = len(text_no_urls.rstrip())
        if pos < main_text_end * 0.7:
            violations.append(ResourceViolation(
                url=url,
                diagnosis="resource appears in the body, not terminal segment",
            ))

        # Bare presentation: no framing language around the URL
        start = max(0, pos - 30)
        surrounding = message.text[start:pos]
        if any(re.search(p, surrounding) for p in FRAMING_PATTERNS):
            violations.append(ResourceViolation(
                url=url,
                diagnosis=f"resource has framing language: '{surrounding.strip()}'",
            ))

    return ResourceAnalysis(
        valid=len(violations) == 0,
        resources=urls,
        violations=violations,
    )


# ---------------------------------------------------------------------------
# P-VII: Thread Parity and Closure
# ---------------------------------------------------------------------------

CLOSURE_PATTERNS = [
    r"(?i)that was you",
    r"(?i)this was you",
    r"(?i)you gave me",
    r"(?i)you did that",
]


def is_closed(message: Message) -> bool:
    """Detect if a message functions as thread closure."""
    has_question = bool(QUESTION_PATTERN.search(message.text))
    has_invitation = any(
        kw in message.text.lower()
        for kw in ["would love to", "let me know", "thoughts?", "curious",
                    "open to", "interested in"]
    )
    has_definitive = any(
        re.search(p, message.text) for p in CLOSURE_PATTERNS
    )

    if has_definitive:
        return True
    if not has_question and not has_invitation:
        return True
    return False


def validate_thread_health(
    thread: list[Message],
    relationship_strength: float = 1.0,
) -> ThreadAnalysis:
    """P-VII: Validate parity, closure, and diminishing returns."""
    if not thread:
        return ThreadAnalysis(valid=True, closed=True)

    outbound = [m for m in thread if m.turn == "outbound"]
    inbound = [m for m in thread if m.turn == "inbound"]
    parity = len(outbound) / max(len(inbound), 1)
    visibility = thread[0].visibility

    rs = relationship_strength
    pi_max = (2.0 if visibility == "public" else 3.0) + 0.5 * min(rs / 5.0, 1.0)

    diagnosis_parts = []

    if parity > pi_max:
        diagnosis_parts.append(
            f"parity {parity:.1f} exceeds limit {pi_max:.1f}"
        )

    # Diminishing returns
    cold = rs < 3
    n_max = 2 if cold else 3
    if len(outbound) >= n_max and len(inbound) == 0:
        diagnosis_parts.append(
            f"{len(outbound)} outbound with 0 inbound — stop"
        )

    thread_closed = is_closed(thread[-1])

    # Escalation readiness
    escalation_ready = False
    if len(inbound) >= 2 and len(outbound) >= 2:
        if len(inbound[-1].text) > len(outbound[-1].text):
            escalation_ready = True

    diagnosis = "; ".join(diagnosis_parts) if diagnosis_parts else ""

    return ThreadAnalysis(
        valid=len(diagnosis_parts) == 0,
        parity=parity,
        pi_max=pi_max,
        closed=thread_closed,
        escalation_ready=escalation_ready,
        diagnosis=diagnosis,
    )


# ---------------------------------------------------------------------------
# Composite validator
# ---------------------------------------------------------------------------

def validate_full_sequence(
    connect: Message | None = None,
    dm: Message | None = None,
    thread: list[Message] | None = None,
    recipient: Agent | None = None,
    relationship_strength: float = 1.0,
) -> ProtocolReport:
    """Run all applicable Protocol articles on a message sequence."""
    violations = []
    p1 = p2 = p3 = p4 = p5 = p6 = p7 = None

    # P-I: Hook Planting (on connect note)
    if connect:
        p1 = validate_hook_planting(connect, connect.channel)
        if not p1.valid:
            violations.append(p1.diagnosis)

    # P-II: Continuity (connect → DM)
    if connect and dm:
        p2 = validate_continuity(connect, dm)
        if not p2.valid:
            violations.append(p2.diagnosis)

    # P-III: Ratio Decay (sequence of outbound messages)
    if connect and dm:
        sequence = [connect, dm]
        p3 = validate_ratio_decay(sequence)
        if not p3.valid:
            violations.append(p3.diagnosis)

    # P-IV: Terminal Question (on DM)
    if dm:
        if recipient:
            dm.recipient = recipient
        p4 = validate_terminal_question(dm)
        if not p4.valid:
            violations.append(p4.diagnosis)

    # P-V: Inhabitation (on DM's question)
    if dm and recipient and p4 and p4.valid and p4.question:
        q = Question(text=p4.question)
        p5 = validate_inhabitation(q, recipient)
        if not p5.valid:
            violations.append(p5.diagnosis)

    # P-VI: Resources (on DM)
    if dm:
        p6 = validate_resource_placement(dm)
        if not p6.valid:
            for v in p6.violations:
                violations.append(f"P-VI: {v.diagnosis}")

    # P-VII: Thread Health
    if thread:
        p7 = validate_thread_health(thread, relationship_strength)
        if not p7.valid:
            violations.append(f"P-VII: {p7.diagnosis}")

    return ProtocolReport(
        valid=len(violations) == 0,
        p1_hooks=p1,
        p2_continuity=p2,
        p3_decay=p3,
        p4_question=p4,
        p5_inhabitation=p5,
        p6_resources=p6,
        p7_thread=p7,
        violations=violations,
    )
