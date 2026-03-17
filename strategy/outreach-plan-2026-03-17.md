# Outreach Plan — March 17, 2026

14 companies across 3 tiers. Work top-down. Log every action.

---

## Tier 1: Active Applications (Today)

### [ ] 1. Anduril — Lead Technical Writer, Intelligence Systems
- **Status:** Active (Day 2)
- **Search:** LinkedIn → "Technical Writing" OR "Documentation" at Anduril Industries
- **Connection message:**
  > Hi [Name] — I build docs-as-code infrastructure at system scale: 739K words across 113 repos, CLAUDE.md governance in every one, automated schema validation on every CI run. Applied for the Lead Technical Writer role on Intelligence Systems. Would love to connect.
- **If accepted — DM:**
  > Thanks for connecting. I wanted to share context beyond the resume — my system uses machine-readable seed.yaml contracts per repo, automated schema validation on every CI run, and a promotion state machine that governs how documentation moves between maturity levels. It's the same rigor Anduril applies to hardware documentation, applied to software governance. Happy to walk through it if useful.
  >
  > Portfolio: https://4444j99.github.io/portfolio/
  > GitHub: https://github.com/meta-organvm
- **Log:** `python scripts/followup.py --log anduril-lead-technical-writer-intelligence-systems --channel linkedin --contact "[Name]" --note "Connection request sent"`

---

### [ ] 2. Harvey AI — Mid/Senior/Staff SWE, Agents
- **Status:** Active (Day 0)
- **Search:** LinkedIn → "Engineering Manager" OR "Head of AI" OR "CTO" at Harvey
- **Connection message:**
  > Hi [Name] — I build multi-agent orchestration systems: agentic-titan framework (845 tests, 9 topology patterns), Claude Agent SDK integration, AI-conductor methodology. Applied for the Agents SWE role. I think the topology patterns translate directly to legal workflows.
- **If accepted — DM:**
  > Thanks for connecting. What drew me to Harvey specifically: the problem of building agents that operate on domain-specific corpora (contracts, case law, regulatory text) under strict accuracy constraints is the same problem I've been solving in the governance domain — where the "corpus" is 82,000 files across 12 organizations and the "accuracy constraint" is that a single misclassified dependency breaks the build. The agent patterns I've built (task decomposition, self-correction loops, structured tool invocation) were designed for exactly this kind of high-stakes, document-dense work.
  >
  > GitHub: https://github.com/labores-profani-crux/agentic-titan
- **Log:** `python scripts/followup.py --log harvey-ai-midseniorstaff-software-engineer-agents --channel linkedin --contact "[Name]" --note "Connection request sent"`

---

### [ ] 3. LangChain — Senior Backend Engineer, Enterprise Readiness & Identity
- **Status:** Active (Day 0)
- **Search:** LinkedIn → "Engineering Manager" OR "VP Engineering" OR "Head of Platform" at LangChain
- **Connection message:**
  > Hi [Name] — I've built enterprise-readiness infrastructure: promotion state machine governing 113 repos, role-based access across 8 orgs, 50 validated dependency edges with 0 violations. Applied for the Enterprise Readiness & Identity role. The architectural patterns overlap.
- **If accepted — DM:**
  > Thanks for connecting. The reason I applied specifically for Enterprise Readiness: I've been building the exact primitives your enterprise customers need — identity declarations via seed.yaml contracts (every repo declares what it produces and consumes), promotion gates that enforce maturity before exposure, and a registry that serves as single source of truth across organizational boundaries. These aren't theoretical — they govern 113 live repositories with automated CI enforcement. I'd be bringing patterns to LangSmith/LangGraph that are already running in production, not designing them from scratch.
  >
  > GitHub: https://github.com/meta-organvm/organvm-engine
- **Log:** `python scripts/followup.py --log langchain-senior-backend-engineer-enterprise-readiness-identity --channel linkedin --contact "[Name]" --note "Connection request sent"`

---

## Tier 2: Expired — Reconnect (This Week)

### [ ] 4. Cloudflare — Models Engineer, Developer Relations
- **Status:** Expired (Day 21, no response)
- **Search:** LinkedIn → "Developer Relations" OR "Developer Experience" at Cloudflare
- **Connection message:**
  > Hi [Name] — I applied for the Models Engineer DevRel role a few weeks ago. Regardless of that position, I wanted to connect — I maintain a 113-repo system with 104 CI/CD pipelines and I'm interested in what Cloudflare is building in the AI inference space. Would love to stay in touch.
- **Log:** `python scripts/followup.py --log cloudflare-models-engineer-developer-relations --channel linkedin --contact "[Name]" --note "Reconnect — expired role"`

---

### [ ] 5. Figma — SWE Developer Experience
- **Status:** Expired (Day 21, no response)
- **Search:** LinkedIn → "Developer Experience" at Figma
- **Connection message:**
  > Hi [Name] — I build developer tooling infrastructure: CLI tools, YAML schema validation, automated quality gates across 113 repos. Applied for the DevEx SWE role. Even if that one's filled, I'd love to connect — DX at Figma's scale is fascinating.
- **Log:** `python scripts/followup.py --log figma-software-engineer-developer-experience --channel linkedin --contact "[Name]" --note "Reconnect — expired role"`

---

### [ ] 6. Perplexity — Full Stack SWE, Applied AI
- **Status:** Expired (Day 21, no response)
- **Search:** LinkedIn → "Engineering" at Perplexity
- **Connection message:**
  > Hi [Name] — full-stack builder: Python + TypeScript, multi-agent orchestration, 23,470 tests across 20 repos. Applied for the Applied AI role. Interested in what Perplexity is doing with agentic search.
- **Log:** `python scripts/followup.py --log perplexity-full-stack-software-engineer-applied-ai --channel linkedin --contact "[Name]" --note "Reconnect — expired role"`

---

### [ ] 7. Replit — SWE Product Infrastructure
- **Status:** Expired (Day 21, no response)
- **Search:** LinkedIn → "Engineering" OR "Product" at Replit
- **Connection message:**
  > Hi [Name] — I build developer infrastructure: 82K files across 12 orgs, documentation governance, AI-conductor methodology. Applied for Product Infrastructure. The overlap between what I build and what Replit enables for others is direct.
- **Log:** `python scripts/followup.py --log replit-software-engineer-product-infrastructure-typescript-devex --channel linkedin --contact "[Name]" --note "Reconnect — expired role"`

---

### [ ] 8. Supabase — Developer Relations Engineer
- **Status:** Expired (Day 21, no response)
- **Search:** LinkedIn → "Developer Relations" OR "DevRel" at Supabase
- **Connection message:**
  > Hi [Name] — documentation architect: 739K words of structured docs, 100+ courses taught (2,000+ students), MFA in Creative Writing. Applied for DevRel. I think the teaching + technical writing combination is unusual and valuable.
- **Log:** `python scripts/followup.py --log supabase-developer-relations-engineer-san-francisco-ca --channel linkedin --contact "[Name]" --note "Reconnect — expired role"`

---

## Tier 3: Rejected — Plant Seeds (Next Week)

### [ ] 9. Anthropic — Developer Education + Education Platform
- **Status:** Rejected
- **Search:** LinkedIn → "Developer Relations" OR "Education" OR "Developer Experience" at Anthropic
- **Connection message:**
  > Hi [Name] — I applied for the Dev Education and Education Platform roles. Didn't work out this time, but I build daily with Claude Code (literally — 113-repo system governed by CLAUDE.md files) and I'm documenting the AI-conductor methodology in a series of published essays. Would love to stay connected for future opportunities.
- **Log:** `python scripts/followup.py --log anthropic-developer-education-lead --channel linkedin --contact "[Name]" --note "Seed — rejected, future alignment"`

---

### [ ] 10. Stripe — Full Stack DevEx + Alliances
- **Status:** Rejected
- **Search:** LinkedIn → "Developer Experience" at Stripe
- **Connection message:**
  > Hi [Name] — applied for DevEx roles at Stripe. The work didn't align this round, but I maintain platform governance infrastructure (promotion state machines, dependency validation) that rhymes with how Stripe thinks about developer tools. Hoping to stay connected.
- **Log:** `python scripts/followup.py --log stripe-full-stack-engineer-developer-experience-product-platform --channel linkedin --contact "[Name]" --note "Seed — rejected"`

---

### [ ] 11. GitLab — Staff Backend DevEx
- **Status:** Rejected
- **Search:** LinkedIn → "Developer Experience" at GitLab
- **Connection message:**
  > Hi [Name] — I operate across 8 GitHub organizations with automated governance, and I've studied how GitLab approaches DevEx at scale. Applied previously — would love to stay in the network for future alignment.
- **Log:** `python scripts/followup.py --log gitlab-staff-backend-engineer-developer-experience-ruby --channel linkedin --contact "[Name]" --note "Seed — rejected"`

---

### [ ] 12. Runway — MTS Research Tools
- **Status:** Rejected
- **Search:** LinkedIn → "Engineering" OR "Research" at Runway
- **Connection message:**
  > Hi [Name] — systems artist building creative infrastructure at institutional scale. Applied for Research Tools. The intersection of generative AI and governance-as-artwork is my primary practice. Would love to connect.
- **Log:** `python scripts/followup.py --log runway-mts --channel linkedin --contact "[Name]" --note "Seed — rejected"`

---

### [ ] 13. Together AI — Lead DX Engineer
- **Status:** Rejected
- **Search:** LinkedIn → "Developer Experience" at Together AI
- **Connection message:**
  > Hi [Name] — I build AI orchestration infrastructure with a documentation-first methodology: 739K words, 23,470 tests, governance architecture. Applied for the DX Lead. Interested in what Together is doing with open models.
- **Log:** `python scripts/followup.py --log together-ai --channel linkedin --contact "[Name]" --note "Seed — rejected"`

---

### [ ] 14. Deepgram — Staff Developer Advocate
- **Status:** Rejected
- **Search:** LinkedIn → "Developer Advocacy" at Deepgram
- **Connection message:**
  > Hi [Name] — 100+ courses taught, MFA in Creative Writing, and a 113-repo system documented in 49 published essays. Applied for Staff Dev Advocate. The teaching + building combination is my core practice.
- **Log:** `python scripts/followup.py --log deepgram-staff-developer-advocate --channel linkedin --contact "[Name]" --note "Seed — rejected"`

---

## Rules

1. **One connection per company.** Find the most relevant person — hiring manager > team lead > recruiter.
2. **Never say "following up on my application"** in Tier 2/3. Lead with what you bring.
3. **Log every action** with the followup.py command. This feeds network_proximity scoring.
4. **If they accept and respond** — that's a warm lead. Create a pipeline entry if no active one exists.
5. **300 character limit** on LinkedIn connection messages. The DM comes after they accept.
