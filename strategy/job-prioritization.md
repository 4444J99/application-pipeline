# Job Application Prioritization

Strategic analysis of 7 active job entries, ranked by fit-to-effort ROI.

**Date:** 2026-02-24
**Identity Position:** independent-engineer (all entries)
**Score Range:** 4.5-6.3

## Submission Order

| # | Entry | Score | Tier | Key Rationale |
|---|-------|-------|------|---------------|
| 1 | anthropic-se-claude-code | 6.3 | Tier 1 | Best fit — CLI tools + agentic systems built daily |
| 2 | huggingface-dev-advocate | 5.4 | Tier 1 | Full body of work as evidence (writing + teaching + OSS) |
| 3 | cohere-applied-ai | 5.4 | Tier 2 | agentic-titan maps directly to role requirements |
| 4 | together-ai | 5.4 | Tier 2 | DX + documentation strength |
| 5 | runway-mts | 5.7 | Tier 3 | High score but ML research infra gap lowers probability |
| 6 | anthropic-fde | 5.0 | Tier 4 | Structural gap: no enterprise customer-facing experience |
| 7 | openai-se-evals | 4.5 | Tier 4 | Hard gap: limited ML knowledge for evals discipline |

## Tier Definitions

- **Tier 1 — Apply Now:** Strongest ROI, submit immediately
- **Tier 2 — Apply with Targeted Narrative:** Good fit with specific evidence, needs framing work
- **Tier 3 — Apply If Time Permits:** Decent score but lower advance probability
- **Tier 4 — Deprioritize:** Structural gaps make effort better spent on Tier 1-2

## Tier 1 — Apply Now

### 1. Anthropic SE Claude Code (6.3)

**Why first:** This is the best fit by a wide margin. You build CLI developer tools and agentic systems *every day* — this pipeline, alchemize.py, greenhouse_submit.py, the entire scripts/ directory IS the kind of work this role does. Claude Code is a CLI tool for developers; the ORGANVM system is 103 repos of CLI-driven Python/TypeScript infrastructure. Mission alignment at 8 is the highest of any job entry.

**Evidence that lands:**
- 21K code files, 3.6K tests, 94 CI/CD pipelines
- agentic-titan (1,095 tests)
- Governance dependency graph (43 validated edges, 0 violations)
- This application pipeline itself (Python CLI tooling, YAML-driven state machine)

**Honest gaps:** No team engineering, no production users. But the scale and testing discipline are real, and the role values independent builders.

**Strategic value:** 8 — Anthropic is the highest-signal employer in the AI space.

### 2. HuggingFace Developer Advocate (5.4)

**Why second:** The role where the *full* body of work is evidence, not just engineering. Dev advocacy is the intersection of engineering + communication + community — all three are demonstrated strengths.

**Evidence that lands:**
- 42 essays (810K+ words) = sustained technical writing
- 11 years teaching 2,000+ students = proven communication with diverse audiences
- 103 public repos across 8 GitHub orgs = open-source at scale
- Documentation coverage (100% CLAUDE.md + seed.yaml)
- Community infrastructure (ORGAN-VI)

**Honest gaps:** Limited ML knowledge (but dev advocacy doesn't require training models). No prior dev advocate title (but teaching IS advocacy).

**Strategic value:** 5 — HuggingFace community visibility opens doors in open-source ML.

## Tier 2 — Apply with Targeted Narrative

### 3. Cohere Applied AI (5.4)

**Why tier 2:** Agentic workflows match agentic-titan directly. Multi-agent orchestration, 1,095 tests, 18 development phases — this is the exact domain. The role title says "agentic workflows," and there's a flagship repo that IS an agentic workflow framework.

**Gap to bridge:** Track record at 4 is still modest. No enterprise deployment of agentic systems.

### 4. Together AI Lead DX (5.4)

**Why tier 2:** Developer experience + documentation is a real strength. 810K+ words of documentation, 100% README coverage, 42 essays on methodology. The DX role values someone who can make complex systems understandable — that's what the essays and teaching demonstrate.

**Gap to bridge:** "Lead" implies team management experience, which is missing.

## Tier 3 — Apply If Time Permits

### 5. Runway MTS Research Tooling (5.7)

**Why high score but lower tier?** The score is 5.7 (second highest), but Runway's research tooling role leans more toward ML research infrastructure than systems engineering. The creative-AI bridge is real (ORGAN-II), but the role likely needs more hands-on ML pipeline experience than the system demonstrates. Good application, but lower probability of advancing past screen.

## Tier 4 — Deprioritize

### 6. Anthropic FDE (5.0)

**Why deprioritize despite Anthropic's strategic value:** "Forward-deployed" means customer-facing enterprise engineering — building custom solutions for enterprise customers on-site. The core gap (no enterprise customer-facing tech experience) is structural, not frameable. Teaching shows communication skills, but not the enterprise deployment context FDE requires. The high strategic value (8) makes it tempting, but the probability is low enough that effort is better spent on the SE Claude Code application.

### 7. OpenAI SE Evals (4.5)

**Why deprioritize:** Applied evals is a specialized ML discipline. The testing infrastructure (3.6K test files, 85% coverage) is evaluation-*adjacent* but not evaluation work. Limited ML knowledge (acknowledged in covenant-ark Section J) is a hard gap for this role. Lowest mission alignment and strategic value of the group.

## Key Insight

The strongest applications are the ones where the *specific* work maps to the *specific* role — not just "I have engineering metrics." Anthropic SE Claude Code works because CLI tools are built daily. HuggingFace works because of writing, teaching, and building in public. Cohere works because agentic-titan exists. The weakest applications are where experience that doesn't exist would need to be claimed (enterprise deployment, ML evals).

## Score Breakdown Reference

| Entry | Mission | Evidence | Track | Financial | Effort | Strategic | Deadline | Portal | Composite |
|-------|---------|----------|-------|-----------|--------|-----------|----------|--------|-----------|
| anthropic-se-claude-code | 8 | 6 | 5 | 3 | 5 | 8 | 9 | 5 | 6.3 |
| runway-mts | 7 | 6 | 5 | 3 | 5 | 5 | 9 | 5 | 5.7 |
| cohere-applied-ai | 7 | 5 | 4 | 3 | 5 | 5 | 9 | 5 | 5.4 |
| together-ai | 7 | 5 | 5 | 3 | 5 | 4 | 9 | 5 | 5.4 |
| huggingface-dev-advocate | 7 | 5 | 4 | 3 | 5 | 5 | 9 | 5 | 5.4 |
| anthropic-fde | 5 | 4 | 4 | 3 | 5 | 8 | 9 | 5 | 5.0 |
| openai-se-evals | 5 | 4 | 3 | 3 | 5 | 4 | 9 | 6 | 4.5 |

## Tags Convention

Pipeline entries tagged with:
- `job-tier-1` through `job-tier-4` — priority tier
- `submit-order-N` — recommended submission sequence
- `deprioritize` — effort better redirected to higher tiers
