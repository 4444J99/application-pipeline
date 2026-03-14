# System Standards Framework

The standards framework provides hierarchical quality assurance for the application pipeline. It models the pipeline as an academic institution: each level adds an independent oversight body that audits a broader scope. Every level runs three independent gates; a level passes when at least two of three gates pass (quorum: 2/3).

## Five-Level Hierarchy

| Level | Name | Academic Analogy | Scope | Regulators |
|-------|------|-----------------|-------|------------|
| 1 | Course | Course-level review | Per-entry | Rubric scoring, evidence match, historical outcome |
| 2 | Department | Department oversight | Schema + CI | Entry validation, rubric integrity, wiring |
| 3 | University | University accreditation | System quality | Diagnostic composite, integrity audit, IRA |
| 4 | National | National accreditation | Outcome validation | Dimension correlation, weight drift, hypothesis accuracy |
| 5 | Federal | Federal oversight | Source legitimacy | Source quality tiers, benchmark alignment, temporal freshness |

Level 1 is per-entry and invoked separately (via `check_entry`). The system-level audit runs Levels 2-5.

## Three Enforcement Tiers

| Tier | Name | Gate Type | Consequence |
|------|------|-----------|-------------|
| 1 | Operational Integrity | Hard | CI blocks on failure |
| 2 | Systemic Quality | Soft | Diagnostic flags, no CI block |
| 3 | Empirical Validity | Advisory | Activates when minimum sample size met |

Hard gates (Tier 1) correspond to Level 2 gates. Soft gates (Tier 2) correspond to Levels 3-4. Advisory gates (Tier 3) correspond to Level 5 and any gate guarded by `min_sample`.

## Triad Quorum Rule

Each level runs exactly three independent gates. The level passes if at least two of the three gates pass. A failing gate does not block the other two from running within the same level.

In gated mode (default), a failing level stops the cascade — Levels 3-5 are skipped if Level 2 fails. In run-all mode (`--run-all`), all levels execute regardless of failures.

## Evidence Lifecycle

Standards with empirical gates (Levels 4-5) follow a three-stage evidence lifecycle:

1. **assumed** — threshold set by market benchmarks; no pipeline-specific data yet
2. **calibrating** — some outcome data collected but below `min_sample` threshold
3. **validated** — minimum sample met; gate is fully active

The lifecycle state is visible in the JSON output under each gate's evidence field. Advisory gates in the `calibrating` or `assumed` state will fail with an "insufficient data" notice — this is expected behavior, not a system error.

## Quick Commands

```
python scripts/run.py standards             # Full hierarchical audit (gated)
python scripts/standards.py --run-all       # All levels regardless of failures
python scripts/standards.py --level 2       # Level 2 only (CI gate)
python scripts/standards.py --json          # Machine-readable output
pipeline standards --json                    # Via Typer CLI
```

Common usage patterns:

- **Daily CI check**: `python scripts/standards.py --level 2` — fast, hard-gated schema + rubric + wiring check
- **Full system audit**: `python scripts/run.py standards` — runs the full cascade, stops on first failure
- **Diagnostic pass**: `python scripts/standards.py --run-all` — inspect all levels even when upstream fails
- **Programmatic output**: `python scripts/standards.py --run-all --json | python -m json.tool`

## Reference

Architectural design document: `docs/superpowers/specs/2026-03-14-standards-validation-criteria-design.md`

YAML standards registry: `strategy/system-standards.yaml` — defines all 25+ standards with level, tier, gate type, description, and validator mapping.
