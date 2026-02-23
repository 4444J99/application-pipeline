# Cover Letter: OpenAI — Software Engineer, Applied Evals

**Role:** Software Engineer, Applied Evals
**Apply:** https://openai.com/careers/software-engineer-applied-evals-san-francisco/
**Salary:** ~$230,000–$385,000

---

organ-audit.py runs monthly health checks across 101 repositories. platinum-validation.py sweeps the full system against 1,267 audited links and 39 dependency edges. Five GitHub Actions workflows enforce constitutional constraints on every merge — no circular dependencies, no back-edges, transitive depth capped at 4. These are evaluation systems built because manual review doesn't scale. That's the same problem the Software Engineer, Applied Evals role at OpenAI solves.

## Why Applied Evals

Evaluation is governance. When you're evaluating multi-turn and tool-using systems, you're deciding what "good" means for an agent operating autonomously. The eight-organ system required making exactly these decisions for 101 repositories across 8 organizations: What does a healthy repo look like? What dependency patterns indicate architectural risk? When should a promotion be blocked? The answers became the automated validation described above — running continuously without human intervention.

## What I'd Bring

**Evaluation frameworks, battle-tested.** I built a multi-layered validation system for the eight-organ system:
- **organ-audit.py:** Monthly health monitoring across all 101 repos — checks documentation status, link integrity, cross-reference accuracy
- **platinum-validation.py:** Full system sweep verifying every repo against 1,267 audited links and 39 dependency edges
- **validate-dependencies workflow:** Blocks merges that would violate constitutional constraints (no circular dependencies, no back-edges, transitive depth <= 4)

These aren't toy scripts. They enforce quality at a scale where eyeballing it doesn't work.

**Agent harness design.** agentic-titan is a multi-agent orchestration framework with 1,095 tests across 18 development phases. The test framework itself IS an agent harness — it evaluates agent coordination, message passing, fault tolerance, and graceful degradation. a-i-council--coliseum takes this further: multi-agent deliberation where AI agents debate positions and synthesize conclusions — evaluating the quality of that synthesis requires exactly the kind of multi-turn eval infrastructure this role builds.

**Production systems end-to-end.** I shipped the eight-organ system from architecture through deployment: 82+ CI/CD pipelines, automated health audits, dependency validation, promotion state machine. I own the full lifecycle — from prototyping with real workflows to building reliable pipelines and integrating signals.

**Feedback loops that strengthen systems.** The system uses a tiered documentation approach (Bronze/Silver/Gold) where validation results feed directly into the next sprint. Regression monitoring, golden datasets (the registry-v2.json as source of truth), and drift detection (monthly audits comparing current state to expected state) — these are eval patterns applied to infrastructure.

## Evidence

- **agentic-titan:** 1,095 tests, 18 phases, agent evaluation harness (organvm-iv-taxis/agentic-titan)
- **recursive-engine:** 1,254 tests, 85% coverage (organvm-i-theoria/recursive-engine--generative-entity)
- **a-i-council--coliseum:** Multi-agent deliberation requiring synthesis evaluation (organvm-ii-poiesis/a-i-council--coliseum)
- **organvm-corpvs-testamentvm:** Validation infrastructure for 101-repo system (meta-organvm/organvm-corpvs-testamentvm)
- **Portfolio:** https://4444j99.github.io/portfolio/

I don't just build AI agents; I build the evaluation infrastructure that makes them reliable.
