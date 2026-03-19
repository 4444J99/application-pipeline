# Open-Source Contribution Map — `context[current-work] > relevant[open-source]`

**Testament:** Your daily ORGANVM work is the seed. The open-source ecosystem is the soil. You don't context-switch to "do open source" — your current work *is* the contribution, deployed to a different repository.

**Generated:** March 19, 2026
**Network orgs scanned:** 54
**Repos with contribution alignment:** 42
**Orgs with no viable OSS targets:** Cursor, Perplexity, Ramp, Harvey AI, Toast, Render, Replit

---

## Where This Practice Lives

The `context > relevant` pattern is not a repo — it's a **cross-organ governance flow**. But the *work* needs a home. Here's the architecture:

### The Seed: ORGAN-IV (Taxis — Orchestration)

ORGAN-IV already contains `agentic-titan` (multi-agent orchestration), `agent--claude-smith` (Claude SDK), and `a-i--skills` (101 skills). External agent framework contributions are a natural extension of this organ's mandate: **orchestrate all**.

**Convention:** `contrib--{org}-{project}` directories within ORGAN-IV for agent/orchestration contributions. Each is a fork workspace with cross-references back to the pipeline.

### The Soil: Other Organs for Domain-Specific Contributions

| Organ | Contribution Domain | Example |
|-------|-------------------|---------|
| **ORGAN-IV (Taxis)** | Agent frameworks, orchestration, MCP servers | Hive, LangChain, LiveKit Agents |
| **ORGAN-I (Theoria)** | ML libraries, model tooling, research code | Hugging Face, Snorkel, W&B Weave |
| **ORGAN-III (Ergon)** | Developer tools, SDKs, commercial OSS | Stripe SDK, Coinbase AgentKit, Railway |
| **ORGAN-V (Logos)** | Documentation, curriculum, content tools | dbt docs, Anthropic cookbooks |
| **META-ORGANVM** | Registry, governance, cross-cutting infra | OpenAI Codex, Temporal SDK |

### The Root: Pipeline Integration

Every contribution is tracked in `4444J99/application-pipeline`:
- `signals/outreach-log.yaml` — logs the PR/issue/contribution action
- `signals/contacts.yaml` — upgrades relationship strength on engagement
- `signals/network.yaml` — org reachability improves with contribution history
- `applications/YYYY-MM-DD/` — cross-reference files linking to organ work directories

---

## TIER 1 — Highest Alignment (Your Current Work IS Their Codebase)

These repos are architecturally isomorphic to what you build daily.

### 1. adenhq/hive ★9,633 [Python]
- **What:** Autonomous, adaptive AI agent framework — node graphs, self-healing, HITL, MCP
- **Your overlap:** Promotion state machine, multi-agent orchestration, MCP servers, 23,470 tests
- **Target issues:** #2805 (integrations), #6613 (versioning), #6612 (parallel tests)
- **Organ:** IV (Taxis) → `contrib--adenhq-hive/` ← **ALREADY CREATED**
- **Status:** Email sent, follows done, repo starred

### 2. langchain-ai/deepagents ★15,555 [Python]
- **What:** Agent harness with planning tools, code execution, web browsing
- **Your overlap:** AI-conductor methodology, agent orchestration, planning systems
- **Contribution angle:** Testing infrastructure, planning node patterns, documentation
- **Organ:** IV (Taxis) → `contrib--langchain-deepagents/`

### 3. livekit/agents ★9,756 [Python]
- **What:** Framework for building realtime voice AI agents
- **Your overlap:** Multi-agent coordination, state management, real-time systems
- **Contribution angle:** Testing patterns, agent lifecycle management, documentation
- **Organ:** IV (Taxis) → `contrib--livekit-agents/`
- **Network:** Already connected with David Zhao (Co-Founder), Russ d'Sa, Adrian Cowham

### 4. anthropics/skills ★97,758 [Python]
- **What:** Public repository for Agent Skills (you already use this ecosystem)
- **Your overlap:** You literally built 101 skills in `a-i--skills/`
- **Contribution angle:** New skills from your collection, skill quality patterns, validation
- **Organ:** IV (Taxis) → direct contribution from `a-i--skills/`
- **Network:** Connected with Alex Albert, Anthony Morris, Scott Goodfriend

### 5. wandb/weave ★1,061 [Python]
- **What:** Toolkit for developing AI-powered applications (eval, tracing, monitoring)
- **Your overlap:** Multi-model evaluation, IRA facility, experiment tracking patterns
- **Contribution angle:** Evaluation patterns, testing infrastructure
- **Organ:** I (Theoria) → `contrib--wandb-weave/`
- **Network:** Lorenzo Porras (AI Solutions Engineer) accepted + DM sent

---

## TIER 2 — Strong Alignment (Domain Expertise Transfers Directly)

### 6. dbt-labs/dbt-mcp ★514 [Python]
- **What:** MCP server for interacting with dbt
- **Your overlap:** MCP server infrastructure, data pipeline architecture
- **Contribution angle:** MCP patterns, testing, documentation
- **Organ:** III (Ergon) → `contrib--dbt-mcp/`
- **Network:** Beth Hipple + Juan Manuel Perafan accepted + DMs sent

### 7. elevenlabs/elevenlabs-mcp ★1,269 [Python]
- **What:** Official ElevenLabs MCP server
- **Your overlap:** MCP server experience (filesystem, memory, sequential thinking)
- **Contribution angle:** MCP patterns, error handling, documentation
- **Organ:** IV (Taxis) → `contrib--elevenlabs-mcp/`
- **Network:** Connected with John Chang (FDE), Vijay Pemmaraju (FDE)

### 8. elastic/mcp-server-elasticsearch ★629 [Rust]
- **What:** MCP server for Elasticsearch
- **Your overlap:** MCP infrastructure, search/observability patterns
- **Contribution angle:** Documentation, testing patterns (Rust is in your stack)
- **Organ:** III (Ergon) → `contrib--elastic-mcp/`
- **Network:** Connected with Carly Richmond, JD Armada, Josh Devins

### 9. huggingface/mcp-course ★876 [MDX]
- **What:** Course on Model Context Protocol
- **Your overlap:** 100+ courses taught, MCP server experience, curriculum design
- **Contribution angle:** Course content, examples, exercises — no code review needed
- **Organ:** V (Logos) → `contrib--hf-mcp-course/`
- **Network:** Merve Noyan (ML Advocacy Engineer), Thomas Simonini (Dev Advocate)

### 10. openai/codex ★66,356 [Rust]
- **What:** Lightweight coding agent in your terminal
- **Your overlap:** CLI tooling, agent orchestration, terminal-based workflows
- **Contribution angle:** Documentation, testing, terminal UX patterns
- **Organ:** IV (Taxis) → `contrib--openai-codex/`
- **Network:** Colin Jarvis (Global Head FDE), Omer Khan, Sean Saito, Sam Passaglia, Manan Mehta

### 11. coinbase/agentkit ★1,162 [TypeScript]
- **What:** "Every AI Agent deserves a wallet" — agent + crypto toolkit
- **Your overlap:** Agent orchestration, state machines, TypeScript
- **Contribution angle:** Agent patterns, testing, state management
- **Organ:** III (Ergon) → `contrib--coinbase-agentkit/`
- **Network:** Connected with Emmitt Smith, Rohan Agarwal, Sumithra MK

### 12. snorkel-team/snorkel ★5,936 [Python]
- **What:** Quick training data generation with weak supervision
- **Your overlap:** Data pipeline architecture, evaluation methodology
- **Contribution angle:** Testing, documentation, pipeline patterns
- **Organ:** I (Theoria) → `contrib--snorkel/`
- **Network:** Connected with Gerald Kanapathy (Head of Delivery)

---

## TIER 3 — Moderate Alignment (Skills Transfer, Less Direct)

### 13. anthropics/claude-code ★80,070 [Shell]
- **What:** The tool you use daily
- **Your overlap:** Power user, 101 skills, hooks, MCP integration
- **Contribution angle:** Skills, documentation, bug reports, usage patterns
- **Organ:** IV (Taxis)

### 14. anthropics/claude-cookbooks ★35,381 [Jupyter Notebook]
- **What:** Recipes for using Claude effectively
- **Your overlap:** AI-conductor methodology, multi-model evaluation, production patterns
- **Contribution angle:** Notebook examples from your real-world patterns
- **Organ:** V (Logos)

### 15. cloudflare/moltworker ★9,681 [TypeScript]
- **What:** Run agents on Cloudflare Workers
- **Your overlap:** Agent orchestration, serverless patterns
- **Organ:** III (Ergon)
- **Network:** Craig Dennis (Dev Educator, viewed profile 1d ago)

### 16. railwayapp/nixpacks ★3,487 [Rust]
- **What:** App source + Nix packages + Docker = Image
- **Your overlap:** CI/CD, deployment, containerization
- **Organ:** III (Ergon)
- **Network:** Jake Cooper (CEO), Jake Runzer (Founding Engineer)

### 17. cohere-ai/cohere-toolkit ★3,161 [TypeScript]
- **What:** Prebuilt components for Cohere API
- **Your overlap:** Multi-model orchestration, toolkit architecture
- **Organ:** IV (Taxis)
- **Network:** Meor Amer (DevRel), Ryan Wirth (MTS)

### 18. PostHog/posthog ★(private/org) [Python/TypeScript]
- **What:** Open-source product analytics
- **Your overlap:** Conversion funnels, A/B tracking, event analytics
- **Organ:** III (Ergon)
- **Network:** Lucas Faria (Product Engineer) accepted + DM sent, Daniel Zaltsman, James Hawkins (CEO)

### 19. togethercomputer/MoA ★2,875 [Python]
- **What:** Mixture-of-Agents — multi-model ensemble
- **Your overlap:** Multi-model orchestration, evaluation across providers
- **Organ:** I (Theoria)
- **Network:** Hassan El Mghari, Jibu Chacko

### 20. supabase/etl ★2,202 [Rust]
- **What:** Stream Postgres data anywhere in real-time
- **Your overlap:** Data pipeline architecture, real-time systems
- **Organ:** III (Ergon)
- **Network:** Craig Cannon, Jon Meyers, Michaela Burpoe

---

## TIER 1B — Major Discoveries from Full Scan

These weren't in the initial map but rank as high as Tier 1.

### 21. langchain-ai/langgraph ★26,897 [Python]
- **What:** Build resilient language agents as graphs — state machines for AI
- **Your overlap:** This IS your promotion state machine. Graph-based FSM with forward-only enforcement, multi-agent coordination, pydantic models.
- **Contribution angle:** State machine patterns, testing, workflow engine design
- **Organ:** IV (Taxis) → `contrib--langchain-langgraph/`
- **Network:** Connected with Ankush Gola (Co-Founder), Erick Friis, Jacob Lee, Eric Han

### 22. openai/openai-agents-python ★20,128 [Python]
- **What:** Lightweight framework for multi-agent workflows
- **Your overlap:** Multi-agent orchestration, AI-conductor methodology, planning systems
- **Contribution angle:** Agent lifecycle, testing infrastructure, documentation
- **Organ:** IV (Taxis) → `contrib--openai-agents/`
- **Network:** Colin Jarvis (Global Head FDE), Omer Khan, 4 more FDEs connected

### 23. makenotion/notion-mcp-server ★4,065 [TypeScript]
- **What:** Official Notion MCP Server
- **Your overlap:** MCP server infrastructure — you build and deploy these
- **Contribution angle:** MCP patterns, error handling, testing
- **Organ:** IV (Taxis) → `contrib--notion-mcp/`
- **Network:** Breandan O'Ceallachain (Solutions Engineer) accepted + DM sent

### 24. cloudflare/agents ★4,578 [TypeScript]
- **What:** Build and deploy AI Agents on Cloudflare Workers
- **Your overlap:** Multi-agent orchestration, state machines on serverless
- **Contribution angle:** Agent state management, workflow patterns
- **Organ:** IV (Taxis) → `contrib--cloudflare-agents/`
- **Network:** Craig Dennis (Dev Educator) — already connected, viewed profile 1d ago

### 25. openai/evals ★18,042 [Python]
- **What:** Framework for evaluating LLMs — open-source benchmark registry
- **Your overlap:** IRA facility, multi-model evaluation, scoring rubrics, pytest harnesses
- **Contribution angle:** Eval harnesses, testing patterns, quality rubrics
- **Organ:** I (Theoria) → `contrib--openai-evals/`

### 26. huggingface/smolagents ★26,158 [Python]
- **What:** Barebones library for agents that think in code
- **Your overlap:** Agent workflow engine, multi-agent patterns
- **Contribution angle:** Agent patterns, testing, documentation
- **Organ:** IV (Taxis) → `contrib--hf-smolagents/`
- **Network:** Merve Noyan + Thomas Simonini connected

### 27. DataDog/integrations-core ★1,099 [Python]
- **What:** 800+ Python integrations for Datadog Agent — each with tests and CI
- **Your overlap:** 23,470-test scale pattern. This IS your testing philosophy at scale.
- **Contribution angle:** New integration, test infrastructure, CI patterns
- **Organ:** III (Ergon) → `contrib--datadog-integrations/`
- **Network:** Brandon West (Advocacy Lead), Ameet Talwalkar (Chief Scientist) connected

### 28. PostHog/posthog ★32,135 [Python]
- **What:** All-in-one developer analytics — product analytics, session replay, A/B testing
- **Your overlap:** Conversion funnels, A/B tracking, event analytics, pytest at scale
- **Contribution angle:** Analytics pipeline, testing, observability
- **Organ:** III (Ergon) → `contrib--posthog/`
- **Network:** Lucas Faria (Product Engineer) accepted + DM sent

### 29. temporalio/sdk-python ★993 [Python]
- **What:** Temporal Python SDK for durable workflow execution
- **Your overlap:** Your pipeline's state machine IS a Temporal workflow conceptually
- **Contribution angle:** SDK testing, workflow patterns, documentation
- **Organ:** IV (Taxis) → `contrib--temporal-sdk/`
- **Network:** Mason Egger + Cecil Phillip both accepted + DMs sent

## TIER 2B — MCP Ecosystem (Emerging, High Impact)

Every MCP server is a contribution target where you have direct expertise.

| Repo | Stars | Lang | Org Network Status |
|------|-------|------|--------------------|
| `makenotion/notion-mcp-server` | 4,065 | TS | Breandan accepted |
| `elevenlabs/elevenlabs-mcp` | 1,269 | Python | John Chang, Vijay connected |
| `elastic/mcp-server-elasticsearch` | 629 | Rust | Carly Richmond, JD Armada connected |
| `dbt-labs/dbt-mcp` | 514 | Python | Beth Hipple, Juan Manuel accepted |
| `railwayapp/railway-mcp-server` | 165 | TS | Jake Cooper connected |
| `PostHog/mcp` | 143 | TS | Lucas Faria accepted |
| `webflow/mcp-server` | 108 | TS | Utkarsh Sengar connected |
| `wandb/wandb-mcp-server` | 41 | Python | Lorenzo Porras accepted |
| `scaleapi/mcp-atlas` | 49 | Python | Aidan Sims connected |
| `DopplerHQ/mcp-server` | 0 | TS | Emily Curry connected |

**Strategy:** MCP is the emerging protocol. You built MCP servers. Every one of these is a low-friction, high-signal contribution — and you have contacts at every single org.

---

## Contribution Cadence

| Week | Action | Budget | Why Now |
|------|--------|--------|---------|
| **This week (Mar 19-23)** | AdenHQ/Hive — claim issue, submit first PR | 1 PR | Inbound lead, email sent, 5 follows done |
| **Week 2 (Mar 24-30)** | LangGraph — state machine patterns | 1 PR | 4 LangChain contacts connected, your FSM IS their domain |
| **Week 3 (Mar 31-Apr 6)** | Anthropic Skills — contribute 1-2 skills from a-i--skills | 1 PR | 3 Anthropic contacts, you have 101 skills ready |
| **Week 4 (Apr 7-13)** | MCP ecosystem — dbt-mcp or notion-mcp | 1 PR | Beth Hipple + Juan Manuel + Breandan all accepted DMs |
| **Week 5 (Apr 14-20)** | Temporal SDK or LiveKit Agents | 1 PR | Mason Egger + Cecil Phillip both accepted, deep DM exchange |
| **Ongoing** | 1 PR/week, rotating by current ORGANVM work context + warmest network contact |

---

## Rules

1. **Never context-switch.** The contribution emerges from what you're already building.
2. **Claim before coding.** Follow each project's CONTRIBUTING.md — don't waste work on unassigned issues.
3. **Documentation first.** Most projects accept doc PRs without assignment. Lowest friction entry.
4. **Log everything.** Every PR, issue comment, and contribution gets logged to outreach-log.yaml.
5. **1 PR/week maximum.** Quality over volume. Each PR is a relationship-building artifact, not a checkbox.
6. **Prioritize orgs with accepted connections.** The DM → contribution → referral pipeline is the conversion funnel.
