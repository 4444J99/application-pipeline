# AI Engineering Role Research

**Researched:** 2026-02-11
**Companies surveyed:** 7 (Anthropic, OpenAI, HuggingFace, Runway, Together AI, Cohere, Mistral)
**Roles assessed:** 35+
**Top recommendations:** 7 roles across 5 companies

> **Note (2026-02-16):** Fit scores in this document reflect the original research assessment. These scores were significantly revised downward in [09-qualification-assessment.md](./09-qualification-assessment.md) after honest gap analysis. Use the qualification assessment for current scores.

---

## Fit Assessment Criteria

Profile strengths mapped against role requirements:

| Strength | Evidence |
|----------|----------|
| Systems architecture | 100 repos, 8 orgs, dependency validation, promotion state machine |
| Agent orchestration | agentic-titan (1,095 tests, 18 phases), multi-agent coordination |
| Production infrastructure | 82+ CI/CD pipelines, 5 governance automations, automated health audits |
| Testing rigor | 1,095 tests (agentic-titan) + 1,254 tests (recursive-engine) |
| Documentation at scale | ~404K+ words, every README portfolio-quality |
| Governance-as-safety | Constitutional constraints, no-back-edge rules, transitive depth limits |
| Developer tools | Orchestration tooling, registry design, audit scripts |

**Profile gap:** No explicit ML model training experience (PyTorch/TensorFlow research). Strongest fit is roles emphasizing systems engineering, developer tools, orchestration, and documentation over pure ML research.

---

## TIER 1 — Apply Immediately (Strongest Fit)

### 1. Anthropic — Forward Deployed Engineer, Custom Agents

| Field | Detail |
|-------|--------|
| **Title** | Forward Deployed Engineer, Custom Agents |
| **Team** | Custom Agents, Applied AI |
| **Location** | San Francisco or New York City (hybrid 25%, travel 25-50%) |
| **Salary** | $280,000–$400,000 |
| **Apply** | https://job-boards.greenhouse.io/anthropic/jobs/5074695008 |
| **Deadline** | Rolling |

**Requirements:** 4+ years technical customer-facing role, production LLM experience (prompt engineering, agent development, evaluation frameworks), Python proficiency, autonomous operation under ambiguity.

**Why this fits:**
- Building MCP servers, sub-agents, and agent skills IS what the eight-organ system does — orchestration artifacts deployed to production
- The "identify and codify repeatable deployment patterns" responsibility maps directly to registry-v2.json and governance-rules.json
- Forward-deployed model values someone who can represent the company at the highest technical level while communicating clearly — ~404K+ words of documentation proves this
- Agent development experience from agentic-titan directly applicable

**Spotlight repos:** agentic-titan, a-i-council--coliseum, organvm-corpvs-testamentvm, narratological-algorithmic-lenses

**Fit score:** 9/10

---

### 2. Anthropic — Software Engineer, Claude Code

| Field | Detail |
|-------|--------|
| **Title** | Software Engineer, Claude Code |
| **Team** | Claude Code (developer tools) |
| **Location** | New York City, San Francisco, or Seattle (hybrid 25%) |
| **Salary** | $320,000–$560,000 |
| **Apply** | https://job-boards.greenhouse.io/anthropic/jobs/4816198008 |
| **Deadline** | Rolling |

**Requirements:** 5+ years experience, expert React (hooks, context, suspense), full-stack with UX specialization, LLM and prompt engineering experience, safety/compliance project experience. Nice-to-have: CLI tools, container orchestration, TypeScript at scale.

**Why this fits:**
- Passion for developer tools demonstrated by building orchestration-start-here as entry point to 100-repo system
- LLM orchestration patterns (chaining, tool-use) central to agentic-titan's architecture
- Container orchestration and CLI experience from CI/CD workflows and validation scripts
- "Contribute across the stack from front-end UI to back-end infrastructure" matches full-stack organ system

**Spotlight repos:** agentic-titan, recursive-engine--generative-entity, linguistic-atomization-framework, organvm-corpvs-testamentvm

**Fit score:** 8/10

---

### 3. OpenAI — Software Engineer, Applied Evals

| Field | Detail |
|-------|--------|
| **Title** | Software Engineer, Applied Evals |
| **Team** | Applied AI |
| **Location** | San Francisco (hybrid 3 days/week) |
| **Salary** | ~$230,000–$385,000 (estimated from peer roles) |
| **Apply** | https://openai.com/careers/software-engineer-applied-evals-san-francisco/ |
| **Deadline** | Rolling |

**Requirements:** 4+ years software engineering, experience shipping production systems end-to-end, familiarity with LLM evaluation methods, experience with multi-agent workflows, tool use, or long context patterns.

**Why this fits:**
- "Designing agent harnesses" is exactly what agentic-titan's 18-phase test framework does
- Multi-turn and tool-using system evaluation maps to orchestration validation (dependency checks, health audits, cross-reference verification)
- "Prototyping with users to building reliable pipelines" mirrors the progression from genesis docs to automated workflows
- Evaluation framework building = what platinum-validation.py does across 100 repos

**Spotlight repos:** agentic-titan, recursive-engine--generative-entity, a-i-council--coliseum, organvm-corpvs-testamentvm

**Fit score:** 8/10

---

### 4. Hugging Face — Developer Advocate Engineer, Hub/Enterprise

| Field | Detail |
|-------|--------|
| **Title** | Developer Advocate Engineer, Hub/Enterprise |
| **Team** | Product |
| **Location** | US Remote or EMEA Remote |
| **Salary** | $120,000–$160,000 (US) |
| **Apply (US)** | https://apply.workable.com/huggingface/j/4C12FB7880 |
| **Apply (EMEA)** | https://apply.workable.com/huggingface/j/E732F4B8FC |
| **Deadline** | Rolling |

**Requirements:** Proven ability to create clear, engaging, technically accurate content (written, code, video). Developer-first mindset. Passion for ML products. Strong sense of ownership for content quality. Contribute technically to libraries like Transformers and Datasets.

**Why this fits:**
- Explicitly "deeply technical, not a marketing position" — author docs, blog posts, tutorials; build demos with code repos; contribute to libraries
- ~404K+ words of portfolio-quality documentation IS the portfolio for this role
- HF hires 30-40% from their open-source community and values "people who tell us where to go" — self-directed operators
- "Ownership for content quality" aligns with the AI-conductor quality methodology
- Remote-first, async, minimal meetings matches the AI-conductor workflow model
- Cover letter required explaining why you want to work in open source — the eight-organ public documentation corpus answers this

**Alt roles at HF:**
- Data/Infrastructure Advocate Engineer (US: https://apply.workable.com/huggingface/j/5CA82A9A98/)
- Hub Success Engineer (US: https://apply.workable.com/huggingface/j/01710FD21C)
- Open-Source ML Engineer (Intl: https://apply.workable.com/huggingface/j/56232F23CB)

**Spotlight repos:** organvm-corpvs-testamentvm, my-knowledge-base, metasystem-master, .github (org profile)

**Fit score:** 8/10

---

## TIER 2 — Strong Fit (Apply This Month)

### 5. Together AI — Lead DX Engineer, Documentation

| Field | Detail |
|-------|--------|
| **Title** | Lead DX Engineer - Documentation |
| **Team** | Developer Experience (Product) |
| **Location** | San Francisco or New York |
| **Salary** | $160,000–$240,000 + equity |
| **Apply** | https://job-boards.greenhouse.io/togetherai/jobs/4903661007 |
| **Deadline** | Rolling |

**Requirements:** 5+ years technical writing/engineering/developer education, experience building AI applications with LLMs, proven track record creating docs/guides/cookbooks for developer tools, Python and TypeScript proficiency, knowledge of LLM APIs (structured outputs, function calling).

**Why this fits:**
- **This is the single strongest documentation match.** Founding team member for documentation. ~404K+ words of documentation is the portfolio.
- LLM API experience from agentic-titan (tool-use, orchestration patterns)
- "Create documentation, guides, and cookbooks" — every organ system README IS a guide/cookbook
- Founding role means shaping the documentation culture, not following existing patterns

**Spotlight repos:** organvm-corpvs-testamentvm, metasystem-master, my-knowledge-base, narratological-algorithmic-lenses

**Fit score:** 9/10

---

### 6. Cohere — Applied AI Engineer, Agentic Workflows

| Field | Detail |
|-------|--------|
| **Title** | Applied AI Engineer — Agentic Workflows |
| **Team** | Applied-ML (Modeling department) |
| **Location** | San Francisco, New York, Toronto, Montreal, London (remote-flexible) |
| **Salary** | Not disclosed |
| **Apply** | https://jobs.ashbyhq.com/cohere/1fa01a03-9253-4f62-8f10-0fe368b38cb9 |
| **Deadline** | Rolling |

**Requirements:** Production engineering (Python/TypeScript), hands-on multi-step reasoning agents (ReAct, Plan-and-Execute), familiarity with frontier models, RAG systems, vector databases, orchestration frameworks (LangGraph, CrewAI), evaluation framework building, enterprise customer experience, mentoring.

**Why this fits:**
- "Orchestration systems as agentic workflow design" — the entire eight-organ system IS an orchestration framework
- Multi-step reasoning agents = what agentic-titan implements across 18 phases
- Evaluation framework building maps directly to organ-audit.py and validation scripts
- Customer-facing dimension requires documentation/communication skills — ~404K+ words

**Spotlight repos:** agentic-titan, a-i-council--coliseum, recursive-engine--generative-entity, organvm-corpvs-testamentvm

**Fit score:** 7/10

---

### 7. Runway — MTS, Research Tooling & Data Platform

| Field | Detail |
|-------|--------|
| **Title** | Member of Technical Staff, Research Tooling & Data Platform |
| **Team** | Engineering |
| **Location** | Remote (North America / Europe) |
| **Salary** | $240,000–$290,000 |
| **Apply** | https://job-boards.greenhouse.io/runwayml/jobs/4650196005 |
| **Deadline** | Rolling |

**Requirements:** 4+ years backend-focused engineering, strong in 2+ of: Platform/Infrastructure (vector DBs, AWS, K8s), ML Domain Knowledge (model training, evaluation, dataset management), Product Engineering (TypeScript/React, UX design). Self-directed, pragmatic.

**Why this fits:**
- Building internal platform that ML researchers use — mirrors how registry-v2.json and orchestration tooling serve the eight-organ system
- Product engineering + infrastructure sensibility = exactly the creative-technical hybrid profile
- "User empathy, clean UX" in infrastructure roles is unusual and matches the portfolio-quality-README philosophy
- Runway's mission ("merging art and science") directly resonates with creative-technical practice

**Spotlight repos:** metasystem-master, recursive-engine--generative-entity, classroom-rpg-aetheria, your-fit-tailored

**Fit score:** 7/10

---

## TIER 3 — Worth Monitoring

### Anthropic — Founding Design Engineer, Education Labs
- $300K–$405K, SF/NYC
- 6+ years full-stack, React expert, Python backend
- "Technology enhancing human capabilities" — strong philosophical match
- Apply: https://job-boards.greenhouse.io/anthropic/jobs/4669581008 (inferred)

### Anthropic — AI Safety Fellow
- $3,850/week, 4-month fellowship, Berkeley or London
- Python, ML safety research, empirical projects
- 40% conversion to full-time — good backdoor entry
- Apply: https://job-boards.greenhouse.io/anthropic/jobs/5023394008

### OpenAI — Software Engineer, Agent Infrastructure
- $230K–$385K, SF/NYC (hybrid 3 days)
- Container orchestration, Terraform, distributed systems
- Apply: https://jobs.ashbyhq.com/openai/c1316397-25bb-4add-9e9d-0e3ea8ba929a

### OpenAI — Software Engineer, API Engineer
- $230K–$385K, SF (hybrid 3 days)
- API design, developer products, product thinking
- Apply: https://jobs.ashbyhq.com/openai/22781653-051b-4c75-8725-b80233c67b1e

### HuggingFace — Data/Infrastructure Advocate Engineer
- US Remote
- Developer advocacy, documentation, infrastructure
- Apply: https://apply.workable.com/huggingface/j/5CA82A9A98/

### HuggingFace — Developer Advocate Engineer, Hub/Enterprise
- US Remote
- Platform advocacy, enterprise customer success
- Inferred from: https://www.useparallel.com/app/candidate/job/66c5b71cd66ee52a162d5432

### Together AI — ML Platform Engineer
- $160K–$250K, SF (4 days in-office)
- Multi-cluster orchestration, Kubernetes internals, IaC
- Apply: https://job-boards.greenhouse.io/togetherai/jobs/4835988007

---

## Geographic and Logistics Summary

| Company | Location | Remote? | In-Office Req |
|---------|----------|---------|---------------|
| Anthropic | SF, NYC, Seattle | No | 25% minimum |
| OpenAI | SF, NYC | No | 3 days/week |
| HuggingFace | Anywhere | Yes | None |
| Runway | NA/Europe | Yes | Optional offices |
| Together AI | SF, NYC | No | 4 days/week |
| Cohere | SF, NYC, Toronto, Montreal, London | Flexible | Varies |
| Mistral | Paris | No | Hybrid |

**Note:** Mistral roles are Paris-based, which may require relocation. Cohere has the broadest geographic flexibility. HuggingFace is fully remote.

---

## Application Priority Queue

| Priority | Company | Role | Action |
|----------|---------|------|--------|
| 1 | Anthropic | FDE, Custom Agents | Apply this week |
| 2 | Anthropic | SE, Claude Code | Apply this week |
| 3 | OpenAI | SE, Applied Evals | Apply this week |
| 4 | Together AI | Lead DX Engineer, Docs | Apply this week |
| 5 | HuggingFace | OS ML Engineer | Apply by end of Feb |
| 6 | Cohere | Applied AI, Agentic Workflows | Apply by end of Feb |
| 7 | Runway | MTS, Research Tooling | Apply by end of Feb |

---

## Sources

- Anthropic Careers: https://www.anthropic.com/careers (414 open positions, Greenhouse)
- OpenAI Careers: https://openai.com/careers/search/ (Ashby)
- HuggingFace Careers: https://apply.workable.com/huggingface/ (Workable)
- Runway Careers: https://runwayml.com/careers (31 open positions, Greenhouse)
- Together AI Careers: https://job-boards.greenhouse.io/togetherai (40 open positions, Greenhouse)
- Cohere Careers: https://jobs.ashbyhq.com/cohere (Ashby)
- Mistral AI Careers: https://jobs.lever.co/mistral (Lever)
