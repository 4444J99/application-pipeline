---
title: "Multi-agent orchestration using Claude Agent SDK with subagent spawning"
category: projects
tags: [agent, ai, ci-cd, docker, governance, orchestration, testing, typescript]
identity_positions: [creative-technologist, independent-engineer]
tracks: [job, fellowship]
related_projects: [agentic-titan]
tier: full
review_status: auto-generated
stats:
  languages: [typescript]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Multi-agent orchestration using Claude Agent SDK with subagent spawning

## One-Line
Multi-agent orchestration using Claude Agent SDK with subagent spawning, state persistence, and self-correction

## Short (100 words)
Multi-agent orchestration using Claude Agent SDK with subagent spawning, state persistence, and self-correction. Part of ORGAN-IV (Taxis).

## Full
**Product Overview:** Software systems that rely on a single monolithic AI agent hit a ceiling: the agent accumulates context until it degrades, it cannot parallelize distinct concerns, and a failure in one subtask can poison the entire session. **agent--claude-smith** solves this by decomposing AI-assisted work into a _multi-agent orchestration_ pattern where a central `Orchestrator` spawns purpose-built subagents, each with its own session, tool permissions, retry budget, and security constraints. The system ships four built-in agents — a code reviewer, a task executor, a security auditor, and an AI bridge for external service integration — but the real power lies in the extensible registry and the chezmoi-based configuration templating that lets operators define new agents as TOML templates rendered per-machine. Agents are spawned, supervised, paused, resumed, cancelled, and garbage-collected through a unified session management layer backed by atomic file persistence. The name references a deliberate inversion: rather than one "Agent Smith" replicating endlessly without governance, Claude Smith is an _orchestrated_ agent system where every spawn is registered, permission-checked, cycle-validated, and audit-logged. The orchestrator enforces acyclic spawn graphs, bounded concurrency, per-agent tool whitelists, and comprehensive command validation before any shell operation executes. This is governance-first AI orchestration.

**Architecture:** ### Core Flow When `spawnAgent()` is called on the `Orchestrator`, the following sequence executes: ``` 1. Look up agent definition in AgentRegistry (Zod-validated) 2. Resolve secrets via SecretResolver (1Password SDK or env fallback) 3. Create or resume SessionState via SessionManager 4. Set up AbortController for timeout enforcement 5. Execute via Anthropic Messages API with agent's system prompt 6. Track via SelfCorrectionHooks for safety and audit logging 7. Persist result and complete/fail session ``` For parallel execution, `spawnParallel()` maintains result ordering matching the input request array regardless of completion order, using pre-allocated result slots with index tracking and configurable concurrency limits. ### Component Map ``` src/ ├── index.ts # Entry point, CLI, factory (createOrchestrator) ├── core/ │ ├── orchestrator.ts # Central coordinator: spawn, parallel, resume, cancel │ ├── agent-registry.ts # Agent definitions, cycle detection (DFS), spawn validation │ └── session-manager.ts # Session lifecycle: create/pause/resume/complete/fail ├── agents/ │ ├── types.ts # Zod schemas: ExtendedAgentDefinition, AgentSpawnRequest, SessionState │ ├── code-reviewer.ts

## Links
- GitHub: https://github.com/organvm-iv-taxis/agent--claude-smith
- Organ: ORGAN-IV (Taxis) — Orchestration
