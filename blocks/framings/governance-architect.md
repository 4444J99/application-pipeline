---
title: "Governance / Compliance Architect"
category: framings
tags: [governance, compliance, ai-safety, responsible-ai, human-oversight, state-machine, audit, policy]
identity_positions: [governance-architect]
tracks: [job]
related_projects: [organvm-system, ontologia]
tier: single
---

# Framing: Governance / Compliance Architect

**For:** AI safety, responsible AI, EU AI Act compliance, trust & safety engineering
**Identity position:** Governance architect building human-oversight infrastructure as running code

## Opening

The eight-organ system I built implements the governance patterns that AI regulation demands: human oversight (promotion requires explicit approval through a 5-state machine — no skipping), transparency (every entity mutation is logged with lineage tracking), proportionality (dependency flow is unidirectional by design), and accountability (17-criterion maturity scorecard with threshold-based advisory policies). These aren't compliance documents — they're running infrastructure with 2,500+ tests.

**Key framing note:** The system IS a governance implementation. The state machine, the dependency graph, the advisory system are the primary artifacts.

## Key Claims
- **Promotion state machine:** 5 states (LOCAL → CANDIDATE → PUBLIC_PROCESS → GRADUATED → ARCHIVED), state-skipping prohibited
- **Dependency graph validation:** Unidirectional flow I→II→III, 0 back-edge violations across 50+ edges
- **Ontologia registry:** 1,833 entities with permanent ULID identity, mutation operations with lineage tracking
- **Threshold advisories:** Metric-based policies fire when CI coverage < 20%, test coverage < 30%
- **17-criterion omega scorecard:** Binary maturity assessment with auto-computed criteria
- **Audit trail:** Append-only JSONL event log for all governance decisions

## Lead Evidence

- governance-rules.json defining cross-organ constraints
- Promotion state machine with full test coverage
- Advisory system evaluating 6 policies per pulse cycle
- Staleness detection for repos not validated in 30+ days
- Every mutation records lineage (DERIVED_FROM, SUPERSEDES, MERGED_INTO, SPLIT_FROM)

## What to Acknowledge
- System governs code repositories, not deployed AI models (yet)
- Governance patterns are transferable to AI system oversight
- Independent practice — one operator
