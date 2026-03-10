# Plan: Persona Repositioning — Evidence-First, Not Identity-First

## Context

The current application materials (portfolio brief, cover letters, Creative Lab Five responses, track docs) position via **identity claims**: "I'm an artist-engineer who treats orchestration as primary output." This framing triggers imposter syndrome because it asks the reader to accept a self-description. Worse, it echoes the same pattern that lost 3,000 jobs — applying for roles by describing who you want to be, rather than showing what you've done.

The realization: **what I've done is what I am**. The organvm system, the 97 repos, the 404K words, the governance architecture, the 33 sprints over 5 years — that IS the identity. The Eno/Reznor/Wilson/Malick/Scott lineage describes a METHOD, not a persona. The method is: design environments, work alone at full intensity, assemble in the edit, make the process visible. The evidence speaks.

Essay 41 ("The Solo Auteur Method") already captures this philosophy perfectly. But the **application materials** — the things that actually get submitted — still use the old framing. This plan rewrites them.

## The Shift

| Before (Identity-First) | After (Evidence-First) |
|--------------------------|------------------------|
| "I'm an artist-engineer who treats orchestration as primary output" | "I built a system that coordinates 97 repos. Here's how it works." |
| "My background is in building autonomous creative systems" | "Over 5 years I assembled 97 repositories into a governed system with 35 dependency edges and 0 violations." |
| "I care about governance-as-safety because I've built it" | "The system enforces governance rules as data: registry-v2.json, governance-rules.json, 5 automated workflows. 0 critical alerts since launch." |
| Cover letter template opens: "I'm applying for X. My background is..." | Opens with a concrete thing the system does, then connects to the role |
| "artist-engineer" label used 4+ times across materials | Remove the label entirely. Let the reader name what they see. |

**Principle: Never tell them what you are. Show them what you built. Let them decide what that makes you.**

## Files to Modify

### Priority 1: Immediate Submissions (X1, X3)

#### 1. `docs/applications/05-google-creative-lab-five-responses.md`
- **Q1** — Currently good (leads with the no-back-edges rule). No cultural references present. Minor tightening only.
- **Q2** — Currently good. "Build the system that reveals the system" is evidence-first. No changes needed.
- **Q3** — Currently leads with "I built..." which is correct. Tighten: cut "I'm most proud" framing (evaluative self-talk). Just state what it does and what that demonstrates.
- **Notes section** — Update voice check from "Does this sound like an artist who happens to engineer?" to: "Does every sentence describe something built, something the system does, or a verifiable fact?"

#### 2. `docs/applications/cover-letters/` (all 7 files)
Each cover letter currently opens with: "I'm applying for X. My background is in building autonomous creative systems with production-grade governance — I'm an artist-engineer who treats orchestration and infrastructure as primary outputs."

Rewrite every opening to lead with **a concrete thing the system does** that maps to what the company needs. No identity labels. No "my background is." Structure:

```
[One sentence: what the system does that's relevant to THIS role]
[One sentence: a specific metric or mechanism]
[Then: how this connects to the role]
```

Files:
- `anthropic-fde-custom-agents.md` — Lead with governance-as-data, connect to safety
- `anthropic-se-claude-code.md` — Lead with the CLI/tooling built
- `cohere-applied-ai-agentic-workflows.md` — Lead with multi-agent orchestration
- `huggingface-dev-advocate-hub-enterprise.md` — Lead with documentation volume + quality
- `openai-se-applied-evals.md` — Lead with test infrastructure (2,349 tests, validation scripts)
- `runway-mts-research-tooling.md` — Lead with creative-systems infrastructure
- `together-ai-lead-dx-documentation.md` — Lead with "404K words of documentation that defines what the system becomes" (this one is already close)

### Priority 2: Master Positioning Docs

#### 3. `docs/applications/00-portfolio-brief.md`
- **One-Paragraph Summary** — Already evidence-first ("I designed and implemented..."). Good. But remove evaluative language ("genuinely impressive") and identity labels.
- **"Positioning by Track"** section — Rewrite to remove "Lead with:" imperative framing. Instead, state what the evidence IS for each track. The evidence doesn't change; the frame around it does.
- **"The Method"** section (lines 98-102) — Currently says "I build creative systems using AI tools the way Brian Eno uses generative systems." Double problem: identity-first AND cultural reference. Rewrite to pure method description: "The system was built using AI tools as compositional instruments — the architectural vision, governance design, and editorial judgment are the creative work; AI provides execution capacity. This is solo production at full intensity across 33 development sprints." No Eno. No comparisons. Just method.
- **"Process as Product"** section (lines 92-96) — Already strong. Keep.
- **"Who This Is For"** table — Already evidence-first. Keep.

#### 4. `docs/applications/01-track-ai-engineering.md`
- **Identity line** (line 4): "Independent systems builder who designs autonomous creative infrastructure with production-grade governance" — Remove this label. Replace with a one-line evidence statement.
- **Cover Letter Template** (lines 66-85) — Rewrite opening per the new pattern. Remove "I'm an artist-engineer."
- **Interview Preparation** section — Rewrite answers to lead with evidence, not claims.

#### 5. `docs/applications/09-qualification-assessment.md`
- **"Your Actual Profile"** section — The professional experience list is already evidence-first. Good.
- **"What you have built (genuinely impressive)"** — Remove the "(genuinely impressive)" parenthetical. Just list what was built. The reader decides if it's impressive.
- **Summary** section — Remove "Your strongest assets are real:" (defensive). Just state the assets.

#### 6. `site-data/about.json`
- Remove identity labels from `system_summary` and `strategic_context`
- Keep the evidence (numbers, metrics, architecture descriptions)

### Priority 3: Track Docs (if time)

#### 7. `docs/applications/02-track-grants.md` — Scan for identity-first language, rewrite to evidence-first
#### 8. `docs/applications/03-track-residencies.md` — Same scan and rewrite

## What NOT to Change

- **Essay 41** ("The Solo Auteur Method") — Reflective writing, not application material. Identity language and cultural references (Eno, Reznor, Wilson, Malick, Scott) are appropriate here. Leave it.
- **The facts/metrics** — 97 repos, 404K words, 2,349 tests, 33 sprints, etc. These don't change.
- **Cultural references** — Remove ALL Eno/Reznor/Wilson/Malick/Scott references from cover letters AND application responses (including Creative Lab Five). Cover letters = pure evidence. Cultural references belong in essays, artist statements, and interviews where the reader has time to understand the analogy. In a cover letter, they read as name-dropping.

## The Voice Rule

Apply this test to every sentence in every application document:

> **Does this sentence describe something I built, something the system does, or a verifiable fact? Or does it describe how I see myself?**

If it's the latter, rewrite it or cut it. The reader should never encounter the phrase "I am a..." or "My background is in..." — only "I built...", "The system does...", "This demonstrates..."

Exception: First-person experience statements ("I designed", "I implemented", "I spent 5 years") are fine — they describe actions taken, not identities claimed.

## Verification

After all edits:
1. `grep -ri "artist-engineer" docs/applications/` — Should return 0 results (only in essays)
2. `grep -ri "my background is" docs/applications/` — Should return 0 results
3. `grep -ri "I am a" docs/applications/cover-letters/` — Should return 0 results
4. Every cover letter opens with a concrete evidence statement, not a self-description
5. The portfolio brief has zero identity labels in its positioning sections
6. Read each cover letter opening aloud: does it sound like someone showing work, or someone asking to be believed?
