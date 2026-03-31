---
name: Funder-fit gate lessons — Creative Capital + NLnet deferrals
description: Two deferrals in one session. The funder-fit gate saved weeks of wasted effort. Signals extracted for future targeting.
type: project
---

## Two Deferrals, One Pattern

Both Creative Capital and NLnet failed the funder-fit gate on the same day. The gate works. The lesson is upstream: research the funded portfolio BEFORE drafting, not after.

### Creative Capital (deferred 2026-03-30)
- **What they fund:** Sensory art — visual, performance, sound, film. Physical or experiential work.
- **What we proposed:** Infrastructure art — 117-repo governance system as creative medium.
- **Why it failed:** CC's panel evaluates artistic strength as the primary criterion. ORGANVM's artistic output is code, governance schemas, and documentation. No video, no exhibition history, no physical artifact. The "art" is invisible to a panel trained on sensory work.
- **Signal for future:** CC would require Dimension II from the Becoming the Thing roadmap (Artistic Evidence) — video of Alchemical Synthesizer, exhibition documentation, artist website. Until that evidence exists, CC is premature.

### NLnet NGI0 Commons Fund (deferred 2026-03-30)
- **What they fund:** Digital commons infrastructure primitives — libre silicon, compilers, protocols, type systems, editors, federated communication. Hardware to middleware to end-user tools. 89 funded projects in last 2 rounds: 0 governance/orchestration tools.
- **What we proposed:** Multi-repo governance engine (Cvrsvs Honorvm) — promotion state machines, dependency DAG validation, seed contract system.
- **Why it failed:** Governance is organizational infrastructure, not technical infrastructure. NLnet funds things developers `pip install` or `cargo build` to solve a technical problem. Nobody `pip install`s governance — they adopt it as organizational practice. The tool serves ecosystem maintainers (a small, specialized audience), not the broad developer commons.
- **Signal for future:** Reframe away from "governance engine" toward a specific technical primitive that developers actually install:
  1. **seed.yaml as an open standard** — like publiccode.yml but for multi-repo ecosystems. This IS a commons contribution. The spec + validator + schema package would fit NLnet's pattern.
  2. **Dependency DAG validator as standalone** — a `pip install dag-validator` that any monorepo or multi-repo project uses for CI. Technical primitive, broad audience.
  3. **Promotion state machine as a GitHub Action** — a reusable workflow that enforces lifecycle gates. Developers install GitHub Actions. This maps to NLnet's pattern (F-Droid buildinfra, firmware test automation).

## The Meta-Lesson

The funder-fit gate is the same as the scoring rubric's `mission_alignment` dimension: does the funder's actual portfolio match what you're proposing? Not their stated mission (which is always broad) — their **revealed preferences** (what they actually funded).

**Process fix:** Phase 1 of SOP-INST-001 (Research) must include Agent 2 (Past Winners Analysis) as a HARD GATE. If the funded portfolio shows 0 projects in your category across the last 2 rounds, the funder-fit gate fails and no draft begins. This saves the entire forced revision cycle (Phases 2-5).

**Revenue fix:** The grant pillar (Pillar 2) needs better funder-to-product matching. The three products (pipeline engine, in-midst-my-life, Cvrsvs Honorvm) each map to different funders:

| Product | Best-Fit Funders | Why |
|---------|-----------------|-----|
| Application Pipeline Engine | **Mozilla Builders, GitHub Fund, Omidyar Network** | Developer tool, open-source, workforce equity angle |
| in-midst-my-life | **Knight Foundation, Ford Foundation, Luminate** | Identity sovereignty, power asymmetry in hiring, civic tech |
| Cvrsvs Honorvm (reframed) | **NLnet (as seed.yaml spec), Sovereign Tech Fund, NumFOSS** | Open standard, infrastructure maintenance, European dimension |
| ORGANVM as art | **Creative Capital (after Dim II), ZKM, Eyebeam, Pioneer Works** | Only after video/exhibition evidence exists |

## What the 89 Funded Projects Teach About Product-Market Fit

The funded projects share traits ORGANVM's proposals lacked:
1. **Immediate installability** — `pip install`, `cargo build`, flash firmware. One command to value.
2. **Broad audience** — thousands of potential users, not dozens of ecosystem maintainers.
3. **Solves a pain point developers already feel** — not a governance problem they haven't recognized yet.
4. **Interoperability with existing ecosystems** — extends Nix, improves F-Droid, adds to Nextcloud. Not a standalone island.

The pipeline engine has ALL of these traits. Cvrsvs Honorvm has none (yet). The reframing work is to decompose the governance engine into primitives that each satisfy these four criteria independently.
