---
id: SOP-SYS-003
title: "Session Handoff Avalanche — The Momentum Relay"
scope: system
organ: III
tier: T1
status: active
---

# Session Handoff Avalanche

## Purpose
To eliminate session-boundary friction. The Avalanche Protocol ensures that the end of one session is the inevitable ignition of the next, maintaining forward motion through structured information relay.

## The Protocol

### 1. Natural Stopping Points (NSP)
A session must never end in an "unstable" state. An NSP is defined as:
- All orchestration tasks completed.
- All modifications committed and pushed.
- All IRF items updated.
- No "staged but unexecuted" logic remaining.

### 2. The Avalanche Seed (The Relay)
The final output of every session MUST include a `<avalanche_seed>` block. This is the "soul" that persists when the physical session manifestation dies.

**Structure:**
```yaml
<avalanche_seed>
session_id: S[NN]
status: [STABLE/IGNITION]
head: [High Priority Item ID]
momentum: |
  The exact command to run first in the next session.
context: |
  Concise summary of the breakthrough/state unblocked.
vacuums:
  - List of gaps to be filled.
checksum: [Git SHA]
</avalanche_seed>
```

### 3. The Forward Motion (The Ignition)
The `momentum` field is not a suggestion; it is the "first rock" of the next avalanche. The next agent, upon receiving the seed, MUST execute the momentum command as its first action.

## Implementation: `scripts/handoff_seed.py`
This script aggregates current state, recent git logs, and IRF P0s to generate the seed.

## Governance
- **Inevitable**: No session exits without a seed.
- **Expulsion**: The seed is the only information required to resume.
- **Parity**: Local and remote must be 1:1 before seed generation.
