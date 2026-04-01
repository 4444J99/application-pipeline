# GRAFANA LABS — FULL INVESTIGATORY DOSSIER

**Prepared:** 2026-04-01
**Purpose:** Interview intelligence for Staff AI Engineer, People Technology | NASA | Remote
**Classification:** Internal prep — do not share externally

---

## I. CORPORATE PROFILE

| Field | Value |
|-------|-------|
| **Founded** | 2014 (as Raintank) |
| **HQ** | New York, NY (remote-first) |
| **CEO** | Raj Dutt (co-founder) |
| **CTO** | Tom Wilkie |
| **Co-founders** | Raj Dutt, Torkel Odegaard (Grafana creator), Anthony Woods |
| **COO** | Douglas Hanna (ex-Zendesk VP Ops) |
| **CISO** | Thomas Owen |
| **CLO** | Lora Blum |
| **Employees** | ~1,795 |
| **Revenue** | $400M+ ARR (2025) |
| **Valuation** | $9B (Series E, March 2026) |
| **Total funding** | $908M across all rounds |
| **Customers** | 7,000+ |
| **IPO status** | Private. No announced timeline. CEO has referenced "preparing for IPO" in internal communications per Glassdoor reviews |
| **GrafanaCON 2026** | April 20-22, Barcelona. Grafana 13, Loki new storage engine, Alloy OTel engine, k6 2.0, AI features |

## II. PRODUCT UNIVERSE

### The LGTM Stack (Loki, Grafana, Tempo, Mimir)

| Product | Function | Stars | Language | Key Fact |
|---------|----------|-------|----------|----------|
| **Grafana** | Visualization & dashboarding | 72.9K | TypeScript | The core product. Version 13 launching at GrafanaCON |
| **Loki** | Log aggregation ("Prometheus for logs") | 27.9K | Go | New storage engine coming |
| **Tempo** | Distributed tracing | 5.2K | Go | Minimal dependency — only needs object storage |
| **Mimir** | Metrics long-term storage | 5.0K | Go | Scales to 1B+ active series |
| **k6** | Load testing | 30.3K | Go | v2.0 launching at GrafanaCON |
| **Pyroscope** | Continuous profiling | 11.3K | Go | Acquired 2023 (merged with Phlare) |
| **Alloy** | OTel collector distribution | 3.0K | Go | New OTel engine coming |
| **Beyla** | eBPF auto-instrumentation | 2.0K | Go | Zero-code instrumentation |
| **OnCall** | Incident response | 3.9K | Python | Slack-native |
| **mcp-grafana** | MCP server for Grafana | 2.7K | Go | Direct overlap with your MCP expertise |

### Cloud Products
- **Grafana Cloud** — hosted LGTM stack + AI tools
- **Grafana Enterprise** — self-managed with support/security
- **Grafana Assistant** — AI agent for observability (GA Oct 2025, 10x user growth in 90 days)
- **Assistant Investigations** — autonomous agent for incident response (preview)

### AI Strategy
- Grafana Assistant: context-aware AI agent, correlates across metrics/logs/traces/profiles
- MCP server support: connect external AI tools to Grafana instances
- Assistant Investigations: autonomous incident response agent
- 84% of orgs exploring AI in observability (2025 internal survey)
- Key thesis: "actually useful AI" — practical over hype, human-in-the-loop

## III. ACQUISITIONS

| Year | Company | Domain | Strategic Value |
|------|---------|--------|-----------------|
| 2018 | Kausal | Monitoring | Early infrastructure |
| 2021 | k6 | Load testing | Filled performance testing gap |
| 2023 | Pyroscope | Continuous profiling | Completed observability triad → quadrant |
| 2023 | Asserts.ai | AI observability | First AI acquisition — entity graph for observability |
| 2024 | TailCtrl | Trace sampling | Tempo enhancement |
| 2025 | VolkovLabs | Grafana plugins | Community plugin ecosystem absorption |

**Pattern:** Grafana acquires open source projects that fill gaps in the LGTM stack. Each acquisition adds a signal type (metrics → logs → traces → profiles → load → AI). The People Technology AI role is the same pattern applied internally.

## IV. COMPETITIVE LANDSCAPE

| Competitor | Model | Strength | Grafana's Edge |
|------------|-------|----------|----------------|
| **Datadog** | SaaS, proprietary | All-in-one, deep integrations | Open source, no vendor lock-in, 10x cheaper at scale |
| **Splunk** (Cisco) | SaaS + on-prem | Log analytics legacy, enterprise | Community, composability, modern architecture |
| **New Relic** | SaaS | APM pioneer, unified UI | AGPL keeps it truly open; NR is consumption-priced |
| **Elastic** | Source-available | Search/log power | Grafana stayed OSI-approved (AGPL vs SSPL) |
| **Dynatrace** | SaaS | AI-ops (Davis AI) | Grafana's AI is newer but open + MCP-integrated |

**Market position:** Grafana is the "open composable" alternative to proprietary SaaS observability. Their moat is community (72.9K stars), ecosystem (1000+ integrations), and price (fraction of Datadog at scale).

## V. LICENSING & PHILOSOPHY

- **2021:** Relicensed core projects from Apache 2.0 → AGPL v3
- **Rationale:** Prevent AWS/cloud vendors from strip-mining OSS (MongoDB/Elastic went non-OSI; Grafana stayed OSI-approved)
- **CEO quote:** "it's hard to say you're an open source company when you're using a license that isn't accepted by OSI"
- Plugins, agents, libraries remain Apache-licensed
- "Big tent" philosophy: integrate with everything, lock into nothing

## VI. CULTURE INTELLIGENCE

### Positive Signals
- Remote-first since founding (not pandemic-converted)
- Software engineers rate 4.9/5 on Glassdoor
- Work-life balance: 4.6/5
- Culture/values: 4.6/5
- Career opportunities: 4.7/5
- Open source DNA — engineers contribute to OSS as core work
- Guide.co candidate portal = transparency in hiring

### Risk Signals
- Some reviews cite "silent layoffs" — people disappeared without warning
- Leadership turbulence mentioned in recent reviews
- CEO referenced dampening career growth prospects as IPO prep
- Remote culture can be "Slack-overwhelming and isolating"
- Feedback culture described as inconsistent — some managers excellent, some toxic

### Interview Process Intelligence
- Average process: 22 days
- Difficulty rating: 2.94/5 (moderate)
- Process rated "well thorough" with good recruiter communication
- Guide.co portal shows full pipeline upfront (unusual transparency)

## VII. YOUR RECRUITER: RYAN McKELLIPS

| Field | Value |
|-------|-------|
| **Title** | Global Senior Technical Recruiter |
| **LinkedIn** | https://www.linkedin.com/in/ryan-mckellips13/ |
| **Prior roles** | Global Talent Acquisition Lead at Nikola; Senior Technical Recruiter at Acclivity Healthcare |
| **Reputation** | "tremendously talented headhunter... can find the A players for virtually any role" |
| **Pattern** | Moved from healthcare → automotive (Nikola) → tech (Grafana). Understands non-traditional paths. |

**Implication:** Ryan has seen career pivots. Your systems-artist-to-engineer arc won't faze him. Lead with outcomes, not pedigree.

## VIII. THE PEOPLE TECHNOLOGY ROLE — DEEP READ

### What "People Technology" Means at Grafana
This is the internal tools team that manages the HR/People tech stack: Workday (HRIS), Greenhouse (ATS), Docebo (LMS), Tangelo (onboarding), Salesforce (GTM). Currently staffed with People Technology Analysts (Workday config, reporting, admin). You would be the **first engineer** on this team.

### What "NASA" Means
"NASA" appears to be an internal team/region code in Grafana's Greenhouse setup — it appears in the job title but not in the confirmation email (which says "US | Remote"). Not the space agency. Likely "North America, South America" or a similar geographic grouping.

### The Greenfield Opportunity
- No existing AI engineer on the team
- You'd architect the AI layer from scratch
- Data sources: BigQuery + Workday + Greenhouse + Docebo + Tangelo + Salesforce
- Scope: People Ops, Talent Acquisition, Enablement, Finance, GTM
- Staff-level: set technical direction, mentor, influence AI governance org-wide

### Adjacent Roles (Team Context)
- People Technology Analyst (US, EST/CST) — Workday SME, reporting, admin
- People Technology Analyst — Workday (UK) — international mirror
- These are your future collaborators, not peers. You'd be the engineering layer they don't currently have.

## IX. ORGANVM ↔ GRAFANA STRATEGIC ALIGNMENT

### Direct Technical Overlaps

| Grafana Need | ORGANVM Evidence | Strength |
|-------------|------------------|----------|
| BigQuery data pipelines | 160+ Python pipeline scripts, YAML state machine | STRONG |
| Greenhouse API integration | `greenhouse_submit.py`, `alchemize.py` — already built | EXACT MATCH |
| AI-powered workflows | AI-conductor: human directs, AI generates, human reviews | STRONG |
| Cross-system data integration | 8-organ architecture, registry-v2.json, seed.yaml contracts | STRONG |
| AI governance | Self-Governing Evaluative Authority, VSM System 3*, promotion state machine | UNIQUE |
| MCP infrastructure | MCP servers running locally, mcp_server.py in this repo | DIRECT |
| Staff-level system design | 113 repos, 8 orgs, governance-rules.json, dependency enforcement | STRONG |
| Workday/HR systems | Less direct — but pipeline CRM (contacts.yaml, 113 contacts, network graph) is analogous | MODERATE |

### Your MCP Angle
Grafana's `mcp-grafana` (2.7K stars) is their bridge between AI agents and observability data. You already build and run MCP servers. On the People Technology team, you could build an MCP server that connects AI agents to People data — the same pattern Grafana uses for observability, applied to HR/People analytics. This is a sentence Ryan has never heard from a candidate before.

### The "First AI Engineer" Narrative
Frame it as: "I've already been the first AI engineer — for my own 8-organization system. I built the pipelines, the governance, the evaluation authority, and the automation layer from zero. Grafana's People Technology team needs exactly that same trajectory."

## X. QUESTIONS HIERARCHY (by interview stage)

### Recruiter Screen (Monday)
1. "What does the People Technology team look like today — headcount, reporting structure?"
2. "Is this role under People leadership or Engineering leadership?"
3. "What's the highest-priority AI use case they want to tackle first?"
4. "How does this role connect to Grafana's broader AI efforts — Assistant, MCP?"
5. "What does the first 6 months look like for this hire?"

### Hiring Manager (Stage 2)
1. "Which People data systems have the most untapped potential for AI?"
2. "How do you think about AI governance for People data — PII, bias, compliance?"
3. "What's the relationship between this team and the Grafana Cloud AI team?"

### Technical (Stages 3-4)
1. "What's the current data architecture — is BigQuery the warehouse, or are there multiple?"
2. "Are there existing data pipelines I'd inherit, or is this truly greenfield?"
3. "How does Grafana dogfood its own observability stack for internal systems?"

### Wayfinder (Culture — Stage 5)
1. "How does Grafana balance the 'big tent' open source philosophy with enterprise security requirements?"
2. "What does 'staff-level influence' look like in a remote-first org of 1,800?"

---

## XI. CONTRIBUTION INSERTION POINTS (Contextual Insertion Map)

### Tier 1: High Signal, Direct Overlap (Do Before Monday)

| Repo | Issue | Why It Matters |
|------|-------|----------------|
| **grafana/mcp-grafana** | [#680: Security — Prompt injection via dashboard data](https://github.com/grafana/mcp-grafana/issues/680) | You build MCP servers AND have security-implementation-guide skills. A thoughtful comment here about prompt injection defense patterns shows depth. |
| **grafana/mcp-grafana** | [#641: camelCase vs snake_case parameter breaking](https://github.com/grafana/mcp-grafana/issues/641) | Simple, fixable, high-visibility. A PR here before the interview is a concrete artifact Ryan can see. |
| **grafana/mcp-grafana** | [#620: Topic-based documentation organization](https://github.com/grafana/mcp-grafana/issues/620) | You're a documentation-engineer. A comment proposing a CLAUDE.md-style approach shows you know the repo. |
| **grafana/metrics-drilldown** | [#1146: Add CLAUDE.md for Claude Code context](https://github.com/grafana/metrics-drilldown/issues/1146) | They ASKED for CLAUDE.md. You literally wrote the spec for these. This is a layup. |

### Tier 2: Ecosystem Presence (Do This Week)

| Repo | Issue | Why |
|------|-------|-----|
| **grafana/grafana** | [#120907: OAuth timeout config](https://github.com/grafana/grafana/issues/120907) | Auth/OAuth — you have `oauth-flow-architect` skill. Comment or PR. |
| **grafana/k6** | [#5305: Move Sobek option parsing](https://github.com/grafana/k6/issues/5305) | Go refactor, good-first-issue. Shows Go competency. |
| **grafana/mimir** | [#13476: path-prefix breaks static assets](https://github.com/grafana/mimir/issues/13476) | Bug fix, good-first-issue. Quick win. |

### Tier 3: Study-Only (Ingest, Don't Touch)

| Repo | What To Learn |
|------|---------------|
| **grafana/oncall** | Python-based incident response — closest to People Technology stack patterns |
| **grafana/alloy** | OTel collector — pipeline architecture patterns applicable to People data pipelines |
| **grafana/grafana** (TypeScript) | Frontend patterns if coding interview involves Grafana plugin work |

## XII. HUMAN ACTOR STUDY (Communication Primitives)

### Founders

**Torkel Ödegaard** (Creator, CGO)
- Origin: Solo hobby project, Dec 5 2013. First commit. Built because dashboarding tools were ugly.
- Core drive: "I enjoy seeing people use metrics more through beautiful and easy to use software"
- Passion: Visual beauty as functional driver. UIs that look good ARE more fun to work with.
- Lens for you: Your `canvas-design` skill + ORGANVM dashboard aesthetics speaks this language.

**Raj Dutt** (CEO)
- Philosophy: "We don't build technology for the buyer. We build technology for the practitioner."
- Mantra: "90% of our users will never pay us, and that's by design."
- Outside passion: **Aviation** — private pilot's license (20 years), motorglider rating.
- Strategic frame: "Big tent" — integrate everything, lock in nothing.
- Lens for you: Your 8-organ "big tent" (ORGANVM) + practitioner-first design mirrors this exactly. If Raj's name ever comes up: "I build for practitioners, not buyers — that's why ORGANVM has CLAUDE.md files, not sales decks."

**Tom Wilkie** (CTO)
- Philosophy: "Organizations aren't choosing between OpenTelemetry and Prometheus – they're using both."
- Frame: Composability over consolidation. Right tool for right job.
- Public presence: The Register, New Stack, conference keynotes.
- Lens for you: Your dependency graph (I→II→III, no back-edges) IS composability with governance. Same principle, different domain.

### AI Team (Your Future Collaborators?)

**Sven Großmann** (Staff SWE — Grafana Assistant creator)
- Built Assistant in a hackathon. Won first place. Shipped to production.
- Speaks at conferences about agentic AI in observability.
- Communication primitive: **Hackathon → Product pipeline**. Innovation through structured play.
- Lens for you: Your pipeline IS a hackathon-to-production system. 160+ scripts started as experiments.

**Matias Chomicki** (Staff SWE — Assistant co-creator)
- LinkedIn: https://www.linkedin.com/in/matias-chomicki-a9546b14/
- Co-built the original LLM integration for Grafana frontend.

**Bogdan Matei** (Staff SWE — Assistant co-creator)
- Blog author at grafana.com.
- Part of the original hackathon trio.

**Mat Ryer** (Principal SWE)
- Hosts "Grafana's Big Tent" podcast.
- Prediction: "We may start to see the first true 'model observability SLOs' — tracking prediction freshness and hallucination rate."
- Communication primitive: **Podcast host = connector**. Links ideas across teams publicly.
- Lens for you: Mat's SLO prediction maps to your IRA facility — you already track "hallucination rate" via inter-rater agreement. Same problem, different name.

### LinkedIn Post Primitives (What Their People Share)

| Pattern | Example | What It Teaches |
|---------|---------|-----------------|
| **Hackathon origin story** | Sven's Assistant blog | Innovation framed as play → production. Frame your pipeline this way. |
| **"Big tent" philosophy** | Raj/Tom keynotes | Composability, not consolidation. Your 8-organ model IS this. |
| **Open source as identity** | Torkel's origin story | OSS isn't strategy, it's DNA. Your 113 repos, AGPL-aware, speak this. |
| **Practical AI > hype** | "Actually useful AI" blog series | Human-in-the-loop, measurable outcomes. Your AI-conductor methodology. |
| **Visual beauty as function** | Torkel's motivation | Dashboards, UIs, canvas art. Your generative art + portfolio. |

## XIII. THE DIRT AND THE CROWN JEWELS

### Crown Jewels (Proudly Displayed)

| What They Show | Reality |
|----------------|---------|
| 72.9K GitHub stars | Legitimate. Largest OSS observability project. Earned. |
| $400M ARR, 7K customers | Real growth. Not hype. Revenue-backed by practitioners, not enterprise sales. |
| "Big tent" philosophy | Genuine differentiator vs Datadog/Splunk. They mean it — AGPL over SSPL proves commitment. |
| Remote-first since founding | Not pandemic-converted. Real async culture. Guide.co transparency confirms. |
| Hackathon → product pipeline | Grafana Assistant literally started as a hackathon. Culture rewards builders. |
| 4.9/5 SWE Glassdoor rating | Engineers love it. The product work is intellectually satisfying. |

### The Dirt (What Mouths Not Approved Sing)

| Signal | Source | Severity | Your Play |
|--------|--------|----------|-----------|
| **"Silent layoffs"** — people disappeared without warning or reason | Glassdoor, Blind (multiple reviews) | MEDIUM | Ask about team stability in HM interview. "How long has the People Technology team existed?" |
| **Leadership turbulence** — "psychologically unsafe environment," "feedback weaponized" | Glassdoor 2025 | MEDIUM | This is team/manager dependent. People Technology is new — you'd be defining the culture, not inheriting toxicity. |
| **CEO: "dampen career growth prospects" for IPO prep** | Glassdoor | MEDIUM | Pre-IPO companies freeze promos. Staff level is already high. This affects IC5→IC6, not your entry. |
| **"Cut throat, people don't last, very isolated"** | Glassdoor March 2025 | LOW-MED | Remote isolation risk is real. Mitigated by: you thrive in solo deep work (113 repos prove this). |
| **Slack culture overwhelming** — "performative meetings, constant notifications" | Multiple reviews | LOW | Async-heavy is your operating mode. This is a feature for you, not a bug. |
| **"Stingy with raises and promotions"** | Blind | LOW | Negotiate well upfront. $175K-$210K range. Push for top of band. |
| **No public IPO timeline** | Multiple sources | INFO | $9B valuation, $908M raised. IPO likely 2027-2028. Equity matters — ask about refreshers. |
| **C-suite "narcissist tendencies"** | Blind (1 review) | LOW | Single data point. Grain of salt. But watch for it in HM interview. |
| **Daily reporting on Google Sheets** | Glassdoor | LOW | Likely team-specific, not org-wide. Clarify in Team Interview. |

### Net Assessment

**Risk level: MODERATE-LOW.** The negative signals are real but concentrated in sales/non-engineering functions. Engineering reviews are consistently strong (4.9/5). The People Technology team is greenfield — you'd be setting the culture, not inheriting dysfunction. The biggest actual risk is pre-IPO compensation stinginess and the remote isolation factor, both of which you can negotiate around.

**The crown is real.** Grafana's open source legitimacy, product quality, and engineering culture are not performative. The $9B valuation is backed by $400M ARR from practitioners, not enterprise deals. This is one of the few companies where "we build for practitioners" is verifiable truth, not marketing.

---

## XIV. SOP: FIRST INTERVIEW CONVERSION (Standardized for Reuse)

### Trigger
Email from recruiter containing: interview invitation, scheduling link, positive response to application.

### Sequence (Ordered, All Steps Mandatory)

**Phase 1: Pipeline Registration (Day 0)**
1. Search Gmail for original application confirmation → extract submission date
2. Create pipeline entry in `pipeline/submitted/` with status `interview`
3. Log recruiter as contact via `crm.py --add`
4. Link contact to entry via `crm.py --link`
5. Append to `signals/conversion-log.yaml`
6. Log signal action via `log_signal_action.py`
7. Generate interview prep via `interview_prep.py --target`

**Phase 2: Intelligence Gathering (Day 0-1)**
8. Full company dossier: financials, product universe, leadership, acquisitions, competitors
9. Role deep-read: what the team does, who leads it, what the title codes mean
10. Human actor study: blog authors, conference speakers, communication primitives
11. Glassdoor/Blind deep dive: crown jewels vs dirt
12. GitHub ecosystem scan: repos, open issues, contribution opportunities

**Phase 3: Contextual Insertion (Day 0-2)**
13. Star key repos on GitHub (ambient presence)
14. Identify contribution insertion points (Tier 1: high signal, Tier 2: ecosystem, Tier 3: study-only)
15. Execute Tier 1 contributions (comment, PR, or issue engagement)
16. Engage with company blog post on LinkedIn (your voice, not generic)

**Phase 4: Protocol-Compliant Outreach (Day 1-2)**
17. Draft reply email with P-I hook, P-III ratio, P-IV terminal question, P-V inhabitation
18. Send reply email (after contextual insertion is seeded)
19. Connect with recruiter on LinkedIn with hook note (24h after email)
20. Track LinkedIn connect as hanging action in pipeline

**Phase 5: Prep (Day 2-5)**
21. Update interview prep with intelligence findings
22. Rehearse STAR stories mapped to role requirements
23. Prepare stage-specific questions (recruiter → HM → team → coding → culture)
24. Review contribution artifacts (ensure they're merged or visible)

**Phase 6: Post-Screen (Day 0 after call)**
25. Log interaction via `crm.py --log`
26. Update entry status if advancing
27. Update conversion-log with outcome
28. Begin next-stage intelligence gathering

### Hanging Actions Register

| Action | Status | Due | Notes |
|--------|--------|-----|-------|
| LinkedIn connect with Ryan McKellips | PENDING | 2026-04-02 | After email lands. Hook: "Building AI pipelines across Greenhouse and Workday" |
| Send revised reply email | PENDING | 2026-04-01 | After Tier 1 contribution lands |
| Comment on mcp-grafana #680 (prompt injection) | PENDING | 2026-04-02 | Security angle |
| PR for metrics-drilldown #1146 (CLAUDE.md) | PENDING | 2026-04-02 | Layup — they asked for it |
| Comment on mcp-grafana #620 (docs organization) | PENDING | 2026-04-03 | Documentation-engineer angle |
| LinkedIn blog engagement | PENDING (USER) | 2026-04-02 | User handles — their voice |
| Update interview prep post-research | DONE | 2026-04-01 | Completed this session |

---

*This dossier will be updated after each interview stage with new intelligence.*
