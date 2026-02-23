# Architecture: Storefront vs. Cathedral

## The Problem

Application materials were scattered across three locations, built as a cathedral: deep, immersive, comprehensive. The covenant-ark alone is 255 lines of canonical identity, metrics, and evidence. The 42 published essays total ~142K words. The tracker covers 42 targets across 6 tracks.

The market operates as a triage system. A grant reviewer spends 60 seconds on first pass. A hiring manager scans for 30 seconds. A residency panel reads 200 applications in an afternoon.

**The cathedral earned no attention because nobody had time to enter it.**

## The Solution: Two-Layer Architecture

### Layer 1: Storefront (60 seconds)

Every piece of material has a version that can be consumed in under 60 seconds:
- `blocks/identity/60s.md` — 100-word elevator pitch
- Project descriptions as single paragraphs
- Evidence as bullet lists, not narratives
- Cover letters that lead with the hook, not the context

The storefront layer is what earns attention. It must be scannable, specific, and signal-rich.

### Layer 2: Cathedral (for those who enter)

The full depth is preserved and accessible:
- `blocks/identity/cathedral.md` — the immersive artist statement
- `blocks/projects/` — full project narratives with technical depth
- `strategy/` — the complete funding strategy with benefits cliff analysis

The cathedral layer is what converts interest into commitment. It rewards attention with substance.

## Design Principles

### 1. Blocks as Atoms, Submissions as Molecules

Instead of writing fresh applications for each target, compose from a library of tested blocks. Each block is:
- **Self-contained** — makes sense without context
- **Tiered** — available at depth levels appropriate to block type (see `blocks/README.md`)
- **Tracked** — usage recorded in pipeline YAML for conversion analysis

The `compose.py` script assembles target-appropriate packages from the block library.

### 2. Pipeline as State Machine

Every application moves through a defined lifecycle:

```
research → qualified → drafting → staged → submitted → acknowledged → interview → outcome
```

Each stage has clear entry/exit criteria. `pipeline_status.py` reports current state and upcoming deadlines.

### 3. Variant Tracking with Outcome Attribution

Every submission records:
- Which block versions were used
- Which identity position was chosen
- Which framing was applied

After 10+ submissions, `conversion_report.py` reveals which combinations correlate with success.

### 4. Benefits Cliff Awareness

Every target's compensation is checked against Medicaid/SNAP/Fair Fares thresholds. The schema includes `benefits_cliff_note` to surface impact before accepting.

### 5. Separation of Concerns

| Directory | Contains | Purpose |
|-----------|----------|---------|
| `targets/` | Research about opportunities | Intelligence |
| `blocks/` | Composable narrative atoms | Content |
| `variants/` | Versioned assemblies | Testing |
| `pipeline/` | Conversion state machine | Tracking |
| `signals/` | Outcome data | Analytics |

## Migration Rationale

Three source locations → one structured repo:
1. **portfolio/intake/** had raw materials mixed with unrelated reports
2. **corpvs-testamentvm/applications/** had per-target docs without reusable structure
3. **corpvs-testamentvm/docs/applications/** had the richest content but monolithic organization

The new structure separates intelligence from materials from tracking, making each independently useful and composable.
