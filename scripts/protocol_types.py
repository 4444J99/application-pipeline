"""Protocol types — domain types for the Outreach Protocol formal system.

Core dataclasses for messages, agents, claims, tensions, questions,
and all validation result types used by protocol_validator.py and dm_composer.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Core domain types
# ---------------------------------------------------------------------------

@dataclass
class Agent:
    """A participant in a conversation (sender or recipient)."""

    name: str
    organization: str = ""
    role: str = ""
    org_size: str = ""  # startup, growth, enterprise, unknown
    relationship_strength: float = 1.0
    linkedin: str = ""
    pipeline_entries: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_contact(cls, contact: dict) -> Agent:
        """Construct from a contacts.yaml entry."""
        return cls(
            name=contact.get("name", ""),
            organization=contact.get("organization", ""),
            role=contact.get("role", ""),
            relationship_strength=contact.get("relationship_strength", 1.0),
            linkedin=contact.get("linkedin", ""),
            pipeline_entries=contact.get("pipeline_entries", []),
            tags=contact.get("tags", []),
        )


@dataclass
class Claim:
    """A recoverable claim planted in a message (a hook)."""

    text: str
    position: int = 0  # character offset in the message
    is_falsifiable: bool = False
    is_frame_novel: bool = False
    specificity_score: float = 0.0

    @property
    def is_valid(self) -> bool:
        return self.specificity_score > 0.0 and (self.is_falsifiable or self.is_frame_novel)


@dataclass
class Tension:
    """A tradeoff or ongoing debate a recipient navigates daily."""

    description: str
    source: str = ""  # role-inferred, org-inferred, public-decision


@dataclass
class Question:
    """A question extracted from a message."""

    text: str
    position: int = 0  # character offset
    is_substantive: bool = True
    is_logistical: bool = False


@dataclass
class Message:
    """A single message in a conversational sequence."""

    text: str
    turn: str = "outbound"  # outbound | inbound
    phase: str = "post_boundary"  # pre_boundary | post_boundary
    channel: str = "linkedin"
    visibility: str = "private"  # public | private
    is_initiating: bool = True  # False if responding to a direct question
    sender: Agent | None = None
    recipient: Agent | None = None

    def sentences(self) -> list[str]:
        """Split into sentences (simple heuristic)."""
        raw = re.split(r'(?<=[.!?])\s+', self.text.strip())
        return [s for s in raw if s.strip()]

    @property
    def char_limit(self) -> int | None:
        limits = {"linkedin": 300 if self.phase == "pre_boundary" else None}
        return limits.get(self.channel)


# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------

@dataclass
class HookAnalysis:
    """Result of P-I hook planting validation."""

    valid: bool
    hooks: list[Claim] = field(default_factory=list)
    diagnosis: str = ""


@dataclass
class ContinuityAnalysis:
    """Result of P-II continuity validation."""

    valid: bool
    score: float = 0.0
    hooks_referenced: list[str] = field(default_factory=list)
    diagnosis: str = ""


@dataclass
class DecayViolation:
    """A single ratio decay violation."""

    message_index: int = 0
    rho: float = 0.0
    expected_below: float = 0.0


@dataclass
class DecayAnalysis:
    """Result of P-III ratio decay validation."""

    valid: bool
    ratios: list[tuple[int, float]] = field(default_factory=list)
    violations: list[DecayViolation] = field(default_factory=list)
    diagnosis: str = ""


@dataclass
class QuestionAnalysis:
    """Result of P-IV terminal question validation."""

    valid: bool
    question: str = ""
    effort: float = 0.0
    salience: float = 0.0
    ratio: float = 0.0
    diagnosis: str = ""


@dataclass
class InhabitationAnalysis:
    """Result of P-V inhabitation validation."""

    valid: bool
    score: float = 0.0
    tension_score: float = 0.0
    decision_score: float = 0.0
    diagnosis: str = ""


@dataclass
class ResourceViolation:
    """A single resource placement violation."""

    url: str = ""
    diagnosis: str = ""


@dataclass
class ResourceAnalysis:
    """Result of P-VI resource placement validation."""

    valid: bool
    resources: list[str] = field(default_factory=list)
    violations: list[ResourceViolation] = field(default_factory=list)


@dataclass
class ThreadAnalysis:
    """Result of P-VII thread health validation."""

    valid: bool
    parity: float = 0.0
    pi_max: float = 2.0
    closed: bool = False
    escalation_ready: bool = False
    diagnosis: str = ""


@dataclass
class ProtocolReport:
    """Composite result of all 7 article validations."""

    valid: bool
    p1_hooks: HookAnalysis | None = None
    p2_continuity: ContinuityAnalysis | None = None
    p3_decay: DecayAnalysis | None = None
    p4_question: QuestionAnalysis | None = None
    p5_inhabitation: InhabitationAnalysis | None = None
    p6_resources: ResourceAnalysis | None = None
    p7_thread: ThreadAnalysis | None = None
    violations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable summary."""
        lines = []
        checks = [
            ("P-I  Hook Planting", self.p1_hooks),
            ("P-II Continuity", self.p2_continuity),
            ("P-III Ratio Decay", self.p3_decay),
            ("P-IV Terminal Question", self.p4_question),
            ("P-V  Inhabitation", self.p5_inhabitation),
            ("P-VI Resources", self.p6_resources),
            ("P-VII Thread Health", self.p7_thread),
        ]
        for label, result in checks:
            if result is None:
                status = "SKIP"
            elif result.valid:
                status = "PASS"
            else:
                status = "FAIL"
            lines.append(f"  {status}  {label}")
        overall = "PASS" if self.valid else "FAIL"
        lines.insert(0, f"  Protocol Validation: {overall}")
        if self.violations:
            lines.append("")
            for v in self.violations:
                lines.append(f"  ✗ {v}")
        return "\n".join(lines)
