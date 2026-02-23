# Blocks: Composable Narrative Building Blocks

Blocks are the atomic content units of the application pipeline. Each block is self-contained, reusable, and referenced by path in pipeline YAML entries.

## Tier System

Different block types use different depth tiers depending on their purpose.

### identity/ — 4 tiers

The identity blocks are the core narrative at escalating depth. Only this category uses the full 4-tier system.

| Tier | File | Target Length | Purpose |
|------|------|---------------|---------|
| 60s | `60s.md` | ~75 words | Elevator pitch. Number-first per storefront playbook. |
| 2min | `2min.md` | ~150 words | Extended pitch with methodology and lineage. |
| 5min | `5min.md` | ~400 words | Distinct composition with evidence and "why solo?" answer. |
| cathedral | `cathedral.md` | ~700+ words | Full immersive statement for contexts that reward depth. |

### projects/ — 3 tiers

Each project block describes a single flagship repo at three levels.

| Tier | Section | Target Length | Purpose |
|------|---------|---------------|---------|
| one-line | `## One-Line` | 1 sentence | For bullet lists and quick references. |
| short | `## Short` | ~100 words | For application summaries and project descriptions. |
| full | (below short) | 200+ words | Full description with links and technical detail. |

### methodology/ — 2 tiers

Methodology blocks explain approaches and frameworks.

| Tier | Section | Target Length | Purpose |
|------|---------|---------------|---------|
| one-line | `## One-Line` | 1 sentence | Quick descriptor. |
| short | `## Short` | ~150 words | Narrative explanation with key evidence. |

### evidence/ — Single tier

Evidence blocks are tabular/list format. No depth tiers — they present verifiable claims with proof.

- `metrics-snapshot.md` — Quantitative metrics table
- `differentiators.md` — Numbered list of competitive advantages
- `system-overview.md` — Narrative + evidence table
- `work-samples.md` — Ordered table of work samples with URLs

### framings/ — Single tier

Framing blocks are audience-specific opening + claims + evidence templates. Each targets a specific identity position and application track.

- `systems-artist.md` — For art grants, residencies, prizes
- `creative-technologist.md` — For tech grants, roles, accelerators
- `educator-researcher.md` — For education grants, fellowships
- `ai-orchestrator.md` — For AI-specific grants, tech roles

## Referencing Blocks in Pipeline YAML

Use relative paths from `blocks/` in `submission.blocks_used`:

```yaml
submission:
  blocks_used:
    artist_statement: identity/2min
    project_description: projects/organvm-system
    methodology: methodology/ai-conductor
    evidence: evidence/differentiators
    framing: framings/systems-artist
```

The `.md` extension is optional — `compose.py` and `validate.py` append it automatically.

## Relationship to Profiles

**Blocks** are reusable narrative modules — generic, composable, authored manually. They live in `blocks/` and are referenced by path in pipeline YAML `submission.blocks_used`.

**Profiles** are target-specific pre-written content — artist statements at 3 lengths, bios, identity narratives, work sample lists. They live in `targets/profiles/*.json` (44 profiles).

**`draft.py`** synthesizes both: for each portal section, it first checks for a matching block, then falls back to profile content. This means entries don't need `blocks_used` fully populated to produce a working draft — the profile provides a baseline, blocks provide overrides.

**`compose.py --profile`** also supports this fallback: when a referenced block is missing, it pulls from the profile instead.

## Source of Truth

All metrics in blocks derive from the covenant-ark document in `organvm-corpvs-testamentvm`. Update covenant-ark first, then propagate here. Run `python scripts/check_metrics.py` to verify consistency.
