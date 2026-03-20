# Submission Script — NLnet NGI Zero Commons Fund

**Created:** 2026-02-18
**Revised:** 2026-03-19
**Time to complete:** ~45-60 minutes
**URL:** https://nlnet.nl/commonsfund/
**Deadline:** April 1, 2026
**Award:** EUR 5,000-50,000+
**Identity position:** Open-Source Infrastructure Developer
**Benefits cliff:** International grant = SNAP-safe.

---

> This is a step-by-step paste-and-submit guide. All answers are pre-written.
> Identity framing: **Open-Source Infrastructure Developer** — Reusable governance tooling for multi-repository open-source projects.

---

## Pre-flight (3 minutes)

- [ ] Open application: https://nlnet.nl/commonsfund/
- [ ] Confirm eligibility requirements
- [ ] Have ready: GitHub org links, technical documentation links, architecture diagrams
- [ ] Review identity position: **Open-Source Infrastructure Developer**

---

## Abstract

**~200 words — copy between the lines:**

---

Managing multi-repository open-source projects at scale remains an unsolved infrastructure problem. As projects grow beyond a handful of repos — into organizational ecosystems with dozens or hundreds of interconnected components — there are no standardized protocols for declaring inter-project dependencies, enforcing governance rules, or tracking organizational health across repository boundaries.

ORGANVM Governance Toolkit addresses this gap by extracting and packaging three reusable open-source components from a battle-tested 113-repository system: (1) seed.yaml, a per-repo manifest protocol for declaring project metadata, dependency edges, and event subscriptions — functioning as a package.json for organizational governance; (2) a JSON Schema suite for multi-repository registries with formal promotion state machines (LOCAL, CANDIDATE, PUBLIC_PROCESS, GRADUATED, ARCHIVED); and (3) a Python governance engine providing automated dependency validation, promotion pipelines, health monitoring, and system-wide metrics computation.

The system is operational and validated: 3,235 automated tests, 6 published JSON Schemas, 104 CI workflows, 50 enforced dependency edges with zero violations, and a 32-day zero-incident soak test. All code is MIT-licensed and published on GitHub. This proposal funds the extraction of these components into standalone, well-documented libraries that any multi-repo project can adopt independently.

---

## Project Description

**Copy between the lines:**

---

### Problem

Open-source projects increasingly organize into multi-repository ecosystems — monorepo alternatives where related projects span multiple GitHub organizations, each with independent CI, releases, and maintainers. Kubernetes has 80+ repos across multiple orgs. The Apache Foundation coordinates hundreds. Individual developers maintaining personal infrastructure (dotfiles, homelab configs, side projects) accumulate dozens of repos with invisible interdependencies.

No standardized tooling exists for this coordination layer. Projects resort to ad-hoc scripts, tribal knowledge documented in wikis, and manual dependency tracking. There is no equivalent of package.json or Cargo.toml that declares how repositories relate to each other at the organizational level — what they produce, what they consume, what events they subscribe to, and what governance rules constrain their promotion through lifecycle stages.

This absence creates concrete problems: dependency violations go undetected until they cause breakage; repositories drift out of compliance with organizational standards; health monitoring requires bespoke dashboards per project; and new contributors cannot discover how components interconnect.

### Solution

ORGANVM Governance Toolkit extracts three proven components from an operational 113-repository system into standalone, reusable open-source libraries:

**1. seed.yaml — Inter-Repository Manifest Protocol**

A YAML-based per-repo file (with a published JSON Schema) that declares:
- Organ/group membership and GitHub organization
- Implementation status, tier classification, and promotion state
- Typed `produces` edges: what artifacts this repo generates, and who consumes them
- Typed `consumes` edges: what artifacts this repo depends on, and their source
- Event `subscriptions`: what cross-repo events trigger actions in this repo
- CI agent declarations: workflow triggers and descriptions

This is analogous to how package.json declares npm dependencies, but at the organizational governance level rather than the code dependency level. A seed.yaml file looks like this:

```yaml
schema_version: "1.0"
organ: Meta
repo: organvm-engine
org: meta-organvm

metadata:
  implementation_status: ACTIVE
  tier: flagship
  promotion_status: CANDIDATE

produces:
  - type: governance-policy
    description: "Registry validation and governance audit results"
    consumers: [ORGAN-IV, META-ORGANVM]

consumes:
  - type: registry
    source: META-ORGANVM
    description: "Reads registry-v2.json as primary data source"

subscriptions:
  - event: registry.updated
    source: META-ORGANVM
    action: Re-validate registry against governance rules
```

The seed discovery engine crawls a workspace, collects all seed.yaml files, and constructs a directed dependency graph. This graph is then validated against governance rules (no circular dependencies, no forbidden back-edges, maximum transitive depth) — the same class of constraint checking that package managers do for code, applied to organizational structure.

**2. Registry Schema and Lifecycle State Machine**

A JSON Schema defining multi-repository registries with:
- Per-organ (group) organization with repository arrays
- Formal promotion state machine: LOCAL → CANDIDATE → PUBLIC_PROCESS → GRADUATED → ARCHIVED
- Implementation status tracking (ACTIVE, PROTOTYPE, SKELETON, DESIGN_ONLY, ARCHIVED)
- Tier classification (flagship, standard, stub, archive, infrastructure)
- CI workflow tracking, revenue model fields, dependency arrays, validation timestamps

The state machine enforces that repositories cannot skip lifecycle stages — a LOCAL repo must pass through CANDIDATE and PUBLIC_PROCESS before reaching GRADUATED. Each transition has prerequisite checks (CI workflow present, tests passing, documentation complete).

**3. Governance Engine**

A Python toolkit (`organvm-engine`, MIT license) providing:
- **Registry operations:** Load, query, validate, and update multi-repo registries against the JSON Schema
- **Dependency graph validation:** Build directed graphs from seed.yaml edges, detect cycles, enforce forbidden-edge rules, compute blast-radius impact analysis
- **Promotion pipeline:** Automated state transitions with prerequisite gate checks
- **System metrics:** Cross-repo health computation — test coverage aggregation, CI pass rates, documentation completeness, timeseries tracking
- **Omega scorecard:** 17-criterion binary maturity assessment with automated and manual evaluation modes
- **Context file generation:** Auto-generate developer context files (CLAUDE.md, GEMINI.md, AGENTS.md) from templates, injecting per-repo dependency edges and governance state

The engine has 21 domain modules, 3,235 tests, and runs on Python 3.11+ with minimal dependencies (PyYAML, jsonschema).

### Technical Architecture

The toolkit follows a layered architecture:

```
seed.yaml files (per-repo)  ──→  Seed Discovery Engine  ──→  Dependency Graph
                                                                    ↓
Registry (JSON)  ──→  Registry Loader  ──→  Governance Validator  ←─┘
                                                    ↓
                                            Promotion Pipeline
                                                    ↓
                                          Metrics / Scorecard / Dashboard
```

All data formats have published JSON Schemas (6 total: registry-v2, seed-v1, governance-rules, dispatch-payload, soak-test, system-metrics). The schemas are the interoperability contract — any tool that reads these schemas can participate in the governance ecosystem.

The engine exposes a unified CLI (`organvm`) with 23 command groups and can also run as an MCP (Model Context Protocol) server, exposing the full system graph to AI coding assistants.

### Validation and Maturity

This is not a proposal to build something from scratch. The system is operational:

- **113 repositories** across 8 GitHub organizations, all using seed.yaml
- **3,235 automated tests** in the core engine (pytest, 21 test modules)
- **6 published JSON Schemas** with validation scripts and example files
- **104 CI workflows** across the repository ecosystem
- **50 dependency edges** enforced with zero violations
- **32-day zero-incident soak test** (continuous monitoring)
- **7/17 omega maturity criteria** met and tracked
- **27 constitutional specifications** grounded in 130 peer-reviewed academic sources
- **48 published essays** documenting methodology and design decisions
- **Stakeholder portal** live at stakeholder-portal-ten.vercel.app

The funding request covers extraction, documentation, packaging, and community-building — not initial development.

### Impact

The target users are:

1. **Open-source maintainers** managing multi-repo projects (5-500 repos) who need structured governance without building bespoke tooling
2. **Research groups** coordinating codebases across labs, with compliance and reproducibility requirements
3. **Solo developers and small teams** whose personal infrastructure has grown beyond ad-hoc management
4. **Organizations adopting InnerSource** patterns who need cross-team dependency visibility

The seed.yaml protocol is designed to be adoptable incrementally — a project can start with a single seed.yaml declaring basic metadata and add dependency edges as needed, without adopting the full engine. The JSON Schemas can be consumed by any language or tool. The governance engine is one implementation; the protocols are the lasting contribution.

---

## Milestones

---

### Milestone 1: Protocol Specification and Schema Extraction (EUR 7,000)

**Duration:** 6 weeks

**Deliverables:**
- Formal specification document for the seed.yaml protocol (v1.0), including YAML syntax, field semantics, edge types, subscription model, and extension points
- Published JSON Schema suite (seed-v1, registry-v2, governance-rules) as standalone npm and PyPI packages with versioned releases
- Machine-readable governance rules format specification with documented constraint types (acyclic, forbidden-edge, max-depth, prerequisite-gate)
- Example seed.yaml files for common project structures (monorepo, multi-repo, federated org)
- Protocol comparison document: seed.yaml vs. package.json, Cargo.toml, go.mod, .github/CODEOWNERS — positioning within existing ecosystem

**Verification:** Published schema packages on npm/PyPI. Specification passes review by 2 external open-source maintainers.

### Milestone 2: Standalone Governance Engine (EUR 9,000)

**Duration:** 8 weeks

**Deliverables:**
- `organvm-governance` Python package extracted from the monolithic engine, installable via `pip install organvm-governance`
- Seed discovery: workspace crawling, seed.yaml parsing, dependency graph construction
- Registry management: load, query, validate, update operations against JSON Schema-validated registries
- Dependency validation: cycle detection, forbidden-edge enforcement, transitive depth limits, blast-radius impact analysis
- Promotion pipeline: state machine transitions with configurable prerequisite gates
- System metrics: health computation, CI status aggregation, documentation completeness scoring
- Full test suite (target: 1,500+ tests for the extracted package)
- API documentation (Sphinx) and CLI reference

**Verification:** Package published on PyPI. Test suite passes on Python 3.11, 3.12, 3.13. CI green on GitHub Actions.

### Milestone 3: Integration and Interoperability (EUR 8,000)

**Duration:** 6 weeks

**Deliverables:**
- GitHub Action for seed.yaml validation (marketplace-published): validates seed files on push, checks dependency edges against governance rules
- MCP (Model Context Protocol) server exposing governance graph to AI coding assistants (Claude, Copilot, Cursor) — extracted from existing 88-tool implementation
- Pre-commit hook for seed.yaml schema validation
- REST API mode for the governance engine (FastAPI, OpenAPI spec published)
- Integration tests demonstrating adoption in 3 external open-source projects of varying scale (5-repo, 20-repo, 50+ repo)

**Verification:** GitHub Action published on marketplace. MCP server functional with Claude Code and VS Code Copilot. REST API deployed to demo instance.

### Milestone 4: Documentation, Tutorials, and Adoption (EUR 6,000)

**Duration:** 6 weeks

**Deliverables:**
- "Getting Started" guide: add seed.yaml to an existing multi-repo project in 15 minutes
- Architecture guide: how the protocol, schemas, and engine compose
- Migration guide: adopting governance tooling incrementally (seed-only, seed+registry, full engine)
- Video walkthrough (20-30 min) demonstrating setup and daily workflow
- Published case study: lessons from governing 113 repositories with this toolkit
- Conference talk proposal submitted to FOSDEM, PyCon, or Open Source Summit

**Verification:** Documentation site live. Getting Started guide validated by 3 new users completing setup without assistance.

### Milestone 5: Sustainability and Community (EUR 8,000)

**Duration:** 8 weeks

**Deliverables:**
- Contribution guide, issue templates, and governance model for the project itself (using its own tools — dogfooding)
- Plugin architecture for custom governance rules (Python entry points)
- Nix flake and Docker image for reproducible development environment
- Security audit of the governance engine (dependency analysis, input validation review)
- Sustainability plan execution: GitHub Sponsors setup, Open Collective page, partnership outreach to 5 organizations managing 50+ repos
- Final report documenting adoption metrics, community feedback, and roadmap for v2.0

**Verification:** At least 10 GitHub stars and 3 external contributors. Plugin architecture demonstrated with 2 community-contributed rule sets.

**Total: EUR 38,000**

---

## NGI Relevance

---

ORGANVM Governance Toolkit contributes to the Next Generation Internet in three ways:

**Decentralized coordination infrastructure.** The seed.yaml protocol enables federated governance across organizational boundaries without requiring a central authority. Each repository declares its own edges and subscriptions; the governance engine validates constraints without mandating a single hosting platform or CI provider. This aligns with NGI's vision of decentralized, interoperable internet infrastructure.

**Open protocols over proprietary platforms.** GitHub, GitLab, and Gitea each have proprietary mechanisms for cross-repo coordination (GitHub Actions reusable workflows, GitLab includes, Gitea federation). The seed.yaml protocol is platform-agnostic — it works with any git hosting and any CI system. The JSON Schemas are published under open licenses and can be consumed by any tooling ecosystem. This reduces lock-in to proprietary forges.

**Sovereignty and transparency.** The governance engine enforces rules that are version-controlled, auditable, and human-readable. Promotion decisions, dependency constraints, and health metrics are stored as JSON — not locked in a SaaS dashboard. Project maintainers retain full sovereignty over their governance data. The constitutional specification methodology (27 specs grounded in 130 academic sources) demonstrates how governance design itself can be transparent and academically rigorous.

The project also contributes to the broader NGI goal of enabling small actors to operate at larger scale. The system was built and operated by a single developer managing 113 repositories — demonstrating that proper tooling can give individuals and small teams organizational capacity previously requiring dedicated DevOps staff.

---

## Sustainability Plan

---

**Short-term (during grant):**
- Build adopter base through documentation, GitHub Actions marketplace presence, and conference talks
- Establish feedback loops with 5-10 early-adopter projects

**Medium-term (12-18 months post-grant):**
- GitHub Sponsors and Open Collective for ongoing maintenance funding
- Consulting services for organizations adopting the toolkit at scale (50+ repos)
- Partnership with academic institutions using the governance tools for research reproducibility

**Long-term (2+ years):**
- Hosted governance dashboard (freemium SaaS) for teams that want visualization without self-hosting
- Integration partnerships with git forges (Forgejo, Gitea) to embed seed.yaml as a first-class citizen
- Potential foundation stewardship (under an existing umbrella like the Python Software Foundation or Software Freedom Conservancy)

The core protocol and engine will always remain MIT-licensed and community-governed. Revenue activities fund maintenance; they do not gate access to the tooling.

---

## Open-Source Licensing

---

All deliverables will be released under permissive open-source licenses:

| Component | License | Repository |
|-----------|---------|------------|
| seed.yaml specification | CC-BY-4.0 | `meta-organvm/seed-protocol` |
| JSON Schema suite | MIT | `meta-organvm/schema-definitions` |
| Governance engine | MIT | `meta-organvm/organvm-engine` |
| GitHub Action | MIT | `meta-organvm/seed-validate-action` |
| MCP server | MIT | `meta-organvm/organvm-mcp-server` |
| Documentation | CC-BY-4.0 | `meta-organvm/governance-toolkit-docs` |

Existing code is already MIT-licensed and public on GitHub. The grant does not fund proprietary development.

---

## Bio

**~100 words — copy between the lines:**

---

Open-source infrastructure developer. Creator of the ORGANVM governance toolkit: a system coordinating 113 repositories across 8 GitHub organizations through automated dependency validation, promotion state machines, and cross-repo health monitoring. The core engine has 3,235 tests, 21 domain modules, and 6 published JSON Schemas. 18 years professional experience spanning systems architecture, software engineering, college instruction (11 years, 2,000+ students), and project management. Background in both creative systems design (MFA) and production engineering (Meta Full-Stack Developer certification). Based in New York City. All work is MIT-licensed and published on GitHub.

---

## Work Samples (ordered for this audience)

### Sample 1: Governance Engine

**URL:** `https://github.com/meta-organvm/organvm-engine`

Core Python package: 21 domain modules, 3,235 tests, unified CLI with 23 command groups. Registry management, dependency graph validation, promotion pipelines, system metrics, omega scorecard.

### Sample 2: JSON Schema Definitions

**URL:** `https://github.com/meta-organvm/schema-definitions`

6 canonical JSON Schemas (registry-v2, seed-v1, governance-rules, dispatch-payload, soak-test, system-metrics) with validation scripts and example files.

### Sample 3: Governance Corpus

**URL:** `https://github.com/meta-organvm/organvm-corpvs-testamentvm`

Planning and governance documentation: 404K+ words, registry-v2.json (source of truth for 113 repos), 27 constitutional specifications grounded in 130 academic sources, 48 published essays.

### Sample 4: MCP Server

**URL:** `https://github.com/meta-organvm/organvm-mcp-server`

Model Context Protocol server exposing the full governance graph (88 tools across 16 tool groups) to AI coding assistants. Demonstrates protocol-level interoperability.

### Sample 5: Stakeholder Portal

**URL:** `https://stakeholder-portal-ten.vercel.app/`

Next.js intelligence portal providing live repo browsing, constitutional corpus display, and system health visualization. Demonstrates the governance data surface.

## Key Differentiators (if asked "what makes this different")

1. **Protocol-first design** — seed.yaml is a specification, not just a feature of a specific tool. Any ecosystem can implement it.
2. **Battle-tested at scale** — not a prototype; operational across 113 repositories with 32-day zero-incident soak test.
3. **Minimal dependencies** — the governance engine requires only PyYAML and jsonschema. No heavy frameworks, no cloud services, no vendor lock-in.
4. **Academically grounded** — 27 constitutional specs cite 130 peer-reviewed sources from systems theory, governance design, and software architecture.
5. **Incrementally adoptable** — start with a single seed.yaml, add governance rules later. No all-or-nothing commitment.

---

## Links to Submit

| Resource | URL |
|----------|-----|
| Governance Engine | https://github.com/meta-organvm/organvm-engine |
| Schema Definitions | https://github.com/meta-organvm/schema-definitions |
| Governance Corpus | https://github.com/meta-organvm/organvm-corpvs-testamentvm |
| MCP Server | https://github.com/meta-organvm/organvm-mcp-server |
| Stakeholder Portal | https://stakeholder-portal-ten.vercel.app/ |
| GitHub (personal) | https://github.com/4444J99 |
| GitHub (meta org) | https://github.com/meta-organvm |
| Published Essays | https://organvm-v-logos.github.io/public-process/ |

---

## Post-submit

- [ ] Record submission date in 04-application-tracker.md
- [ ] Screenshot confirmation page/email
- [ ] Update status: `nlnet-commons` → SUBMITTED
- [ ] Note expected response timeline
