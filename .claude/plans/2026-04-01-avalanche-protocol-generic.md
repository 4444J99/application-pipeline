# Avalanche Protocol — Generic Session Handoff Specification

**Created:** 2026-04-01 (Session S49)
**Type:** Reusable protocol template
**Domain:** Any multi-session workflow requiring forward-only momentum with natural stopping points

---

## Definition

An **avalanche** is an ordered chain of self-contained relay tasks where:

1. Each relay produces output that contains the next relay's input
2. The chain advances only when the user prompts continuation
3. Each relay has a natural stopping point where work is complete and committed
4. Failed or skipped relays produce traceable gaps, never silent drops
5. The chain is recoverable from any relay — no relay requires memory of prior conversation context

---

## Schema

```yaml
avalanche:
  id: AVL-{YYYY-MM-DD}-{slug}
  created: ISO date
  source_session: session ID
  domain: what this avalanche serves
  status: QUEUED | ACTIVE | PAUSED | COMPLETE | ABANDONED

  relays:
    - id: 1
      name: human-readable name
      status: QUEUED | ACTIVE | DONE | FAILED | SKIPPED
      trigger: what the user says to start this relay
      input: file path, URL, or prior relay output reference
      task: ordered steps (imperative, executable)
      output: what this relay produces (artifact, file, commit, API call)
      stopping_point: natural pause — what "done" looks like
      next_trigger: what starts the next relay
      dependencies: [relay IDs that must complete first] or null
      time_gate: ISO date if blocked until a future date, or null
      owner: agent | human | human+agent

  recovery:
    on_failure: what happens if a relay fails
    on_skip: how skipped relays are tracked
    on_abandon: how the chain closes gracefully
```

---

## Construction Rules

### 1. Relay Independence (The Snowball Property)

Each relay must be executable by a fresh agent session with no prior context beyond:
- The avalanche manifest file (this document)
- The relay's declared `input`
- The repo's CLAUDE.md and memory files

**Test:** Could a stranger with repo access execute this relay from the manifest alone? If no, the relay is under-specified.

### 2. Output-as-Input Chaining

```
relay[n].output → relay[n+1].input
```

Every relay's output section must name a concrete artifact (file path, commit hash, URL, logged entry) that the next relay can read. No implicit handoffs. No "the agent will remember."

### 3. Natural Stopping Points

Each relay ends at a point where:
- All changes are committed and pushed
- The user can inspect the work
- No dangling state exists (no half-written files, no uncommitted edits)
- The system is valid (`validate.py` passes, tests pass)

### 4. Forward-Only Momentum

Relays are ordered but the chain only moves forward. No relay re-executes a prior relay's work. If a prior relay's output is wrong, a new corrective relay is appended — the chain grows, it doesn't loop.

### 5. Trigger Vocabulary

Each relay declares multiple trigger phrases so the user doesn't need to remember exact syntax:
```yaml
trigger: "relay 3" or "security comment" or "prompt injection"
```

The agent pattern-matches against these. "Continue avalanche" always means "execute the next QUEUED relay."

### 6. Time Gates

Some relays are blocked until a future date (e.g., "day before interview"). Time-gated relays have status `BLOCKED` until the gate opens. The agent checks the current date against the gate before executing.

### 7. Owner Clarity

Each relay declares who executes it:
- **agent**: Claude does everything
- **human**: User does it, then reports back; agent logs the result
- **human+agent**: User does part (e.g., clicks a button), agent does the rest

---

## State Machine

```
QUEUED → ACTIVE → DONE
  ↓        ↓
SKIPPED  FAILED → (logged as IRF item)

BLOCKED → (date passes) → QUEUED → ...
```

The avalanche itself:
```
QUEUED → ACTIVE (first relay starts) → PAUSED (at stopping point)
  → ACTIVE (user triggers next) → PAUSED → ... → COMPLETE (terminal relay done)

At any point: → ABANDONED (user explicitly closes chain; remaining relays logged as IRF items)
```

---

## How to Create an Avalanche

### Step 1: Identify the Chain

After a session produces work that spans multiple future sessions, ask:
- What are the discrete tasks remaining?
- What order must they execute in?
- What does each task produce that the next needs?
- Where are the natural pauses?

### Step 2: Write the Manifest

Create `.claude/plans/{date}-{slug}-avalanche.md` using the schema above. Each relay gets:
- A clear input (file, URL, data)
- Imperative task steps (not descriptions — commands)
- A named output artifact
- A stopping point definition

### Step 3: Seed the Trigger

The last message of the creating session should reference the manifest location so the user knows where to find it. The first message of the next session should be one of the relay triggers.

### Step 4: Execute and Update

As each relay completes:
- Update the relay's `status` to `DONE`
- Update the state vector at the bottom of the manifest
- Commit the manifest update alongside the relay's work

---

## Instantiation Patterns

### Interview Conversion Avalanche
```
vacuum fill → contribution insertion → outreach → connect → day-before prep → post-screen debrief
```
See: `.claude/plans/2026-04-01-grafana-interview-avalanche.md`

### Application Submission Avalanche
```
score → qualify → tailor resume → compose cover letter → protocol-validate outreach → build PDF → submit portal → record submission → first follow-up
```

### Grant Cycle Avalanche
```
past-winner analysis → funder-fit gate → identity position selection → block composition → budget narrative → submission package → portal submit → acknowledgment tracking
```

### OSS Contribution Avalanche
```
repo study → issue selection → fork + branch → implement → test → PR → respond to review → merge tracking
```

### Consulting Engagement Avalanche
```
lead qualification → scope document → pricing → proposal draft → send proposal → follow-up → contract review → kickoff prep
```

### Session Close Avalanche (Universal)
```
verify work → hall-monitor audit → IRF update → memory sync → commit → push → handoff manifest
```

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correction |
|-------------|-------------|------------|
| Relay depends on conversation memory | Fresh session has no memory of prior conversation | Put all context in the manifest's `input` field |
| Relay output is implicit ("the agent knows") | Nothing implicit survives session boundaries | Name the artifact: file path, commit hash, URL |
| No stopping point defined | Agent continues past the natural pause into the next relay | Every relay ends with "commit, validate, stop" |
| Relay is too large (>1 hour of work) | Loses the avalanche's incremental-progress advantage | Split into sub-relays |
| Chain has no terminal relay | Avalanche runs forever | Last relay must say TERMINAL |
| Skipped relays are silent | Creates invisible gaps | Skipped relays → IRF items, always |

---

## Integration Points

| System | How Avalanches Connect |
|--------|----------------------|
| **IRF** | Failed/skipped relays become IRF items. Completed avalanches may close IRF items. |
| **Memory** | Avalanche creation is logged as a project memory. Completed avalanches update the memory. |
| **Plans** | Avalanche manifests live in `.claude/plans/`. They are plans with execution state. |
| **Signal Actions** | Relay completions that affect pipeline state get logged in `signal-actions.yaml`. |
| **Outreach Protocol** | Outreach relays must satisfy P-I through P-VII. The manifest references which articles apply. |
