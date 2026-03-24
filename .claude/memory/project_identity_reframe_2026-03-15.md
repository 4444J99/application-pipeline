---
name: Identity Reframe — Documentation Architect, not Independent Engineer
description: Ecosystem scan reveals the work is 70% documentation/governance, not coding. Leading with independent-engineer is leading with the weakest position.
type: project
---

## The Numbers (verified 2026-03-15)

80,436 files across 12 org directories:
- 46,754 JSON (data/config — 58%)
- 23,993 Markdown (documentation — 30%)
- 8,464 code files across 22 languages (10%)
- 1,150 YAML config files

21,449 test functions across 20 repos (not 2,349, not 3,421):
- Python/pytest: 12,493 (58%)
- TypeScript/vitest+jest: 8,956 (42%)

Code is polyglot: Python 31%, TypeScript+TSX 32%, HTML 26%, plus 19 other languages.

## What This Means

The system is 70% documentation and governance, 10% code. It's a documentation architecture project implemented in code — not an engineering project with docs bolted on.

Position derivation from organ activity:
- documentation-engineer: 1.0 (strongest)
- independent-engineer: 0.24 (weakest)

Engagement data: track_record_fit (-1.94) negatively correlates with getting read. Leading with coding credentials buries the differentiator.

## What Must Change

1. **Default identity position** for job-track entries should be `documentation-engineer` or `platform-orchestrator`, not `independent-engineer`
2. **Test count in materials**: use 21,449 across 20 repos (not 2,349 or 3,421 from a subset)
3. **Language framing**: "22 languages, polyglot systems architecture" not "Python and TypeScript"
4. **The MFA and teaching** (100+ courses, 2000+ students) is the dominant skill, not a footnote
5. **24K markdown files** is the lead evidence — governance-as-documentation-architecture

## How to Apply

- `classify_position.py` should weight documentation/governance patterns higher
- `score_constants.py` ROLE_FIT_TIERS should reflect that documentation roles are tier-0, not tier-1
- Cover letters and resumes should lead with the documentation governance story
- The corpus fingerprint naturally reflects this (134 blocks, mostly documentation content)
- Next sourcing run: prioritize documentation-engineer, platform-orchestrator, governance-architect roles
