# Doris Duke / Mozilla AMT Lab — GivingData Form Responses

**Target:** doris-duke-amt
**Portal:** https://dorisduke.givingdata.com/portal/campaign/AMT2026
**Deadline:** March 2, 2026, 12:00 PM ET (NOON — not midnight)
**Generated:** 2026-02-23
**Status:** DRAFT — review, revise in your voice, then paste into GivingData

---

## Project Title

Omni-Dromenon: A Real-Time Audience-Participatory Engine for Live Performance

---

## Dropdown/Select Fields

| Field | Selection | Specify |
|-------|-----------|---------|
| Lead Discipline | Other | Performance Technology / Interdisciplinary |
| Lead Applicant | Technician | — |
| Project Type(s) | Technology/Tools, New Work, Systemic/Fieldwide Solutions | — |
| Experience with Technology | Experienced | — |
| Geography | Northeast | — |
| Grant Amount Requested | $150k | Consider $100k to reduce benefits cliff risk |

---

## Concept Description (250 words max)

> Clearly describe your big idea. What is your project intended to address? How does the project engage new perspectives or approaches to the performing arts through the use of technology?

Audience feedback in live performance is coarse — applause or silence. Existing interactive tools are either too simple (voting apps) or too complex (custom Max/MSP patches rebuilt for each piece). No general-purpose engine lets audiences continuously shape live art across genres while preserving performer authority.

Omni-Dromenon is an open-source performance engine where audience members control continuous parameters — mood, tempo, intensity, texture — via their phones. Inputs aggregate through a three-axis weighted consensus algorithm: spatial proximity (closer to stage = more influence), temporal recency (current energy outweighs historical average), and cluster agreement (emerging consensus self-amplifies). The performer retains graduated override — absolute, blend, or lock — ensuring constant negotiation with the audience, never subordination.

Genre presets encode aesthetic priorities: Ballet weights spatial proximity highest because the dancer's physical relationship to nearby audience is primary. Electronic Music weights temporal responsiveness because rhythmic immediacy drives the form. Theatre balances all three axes because narrative requires spatial awareness, momentum, and collective agreement simultaneously.

The technical infrastructure exists: a TypeScript monorepo with WebSocket server, React performer and audience interfaces, OSC bridge to SuperCollider/Max/MSP, four working examples (generative music, generative visual, choreographic interface, theatre dialogue), and Docker deployment. The grant funds what software cannot accomplish alone: three live deployments with performing artists — one dance, one theatre, one music — testing the engine in real venue conditions, refining presets from performer feedback, and publishing all tools and playbooks as open-source resources for the field.

**[~248 words]**

---

## Feasibility (100 words max)

> What are some challenges you anticipate when implementing your idea or approach, and how do you plan to mitigate these challenges?

The core engine, React interfaces, audio synthesis bridge, and four genre-specific examples are built and documented. The challenge is translating working software into live performance: venue WiFi reliability, audience onboarding friction, and performer comfort with digital control surfaces. Mitigation: a workshop series with collaborating performers before each public deployment, iterating on the interface and onboarding flow. A festival rider and venue deployment playbooks are already documented. An iPhone quick-start guide exists for audience participation. Performer recruitment through NYC performing arts networks, supported by the $30,000 collaborator budget.

**[~88 words]**

---

## Field Survey (100 words max)

> Are you aware of other individuals or organizations working on similar ideas? If yes, explain how your work complements that of others or fills a gap.

Interactive performance tools span a spectrum: audience voting apps provide binary input, Troikatronix Isadora and QLab handle cue-based performance, and custom Max/MSP patches enable deep interactivity but must be rebuilt for each new piece. No existing tool aggregates continuous audience input through spatial, temporal, and consensus weighting while preserving performer override authority — working across dance, music, theatre, and installation without custom rebuilds. Related work includes Mimi Yin's choreographic interfaces at NYU ITP, Kinetic Light's accessibility-centered dance technology (a 2024 AMT Lab grantee), and TeamLab's immersive installations. Omni-Dromenon fills the general-purpose gap between these specialized approaches.

**[~99 words]**

---

## Field Impact (100 words max)

> How does this project impact the performing arts field? How do you plan on evaluating the impact of the project?

The engine, genre presets, and deployment playbooks will be published as open-source tools any performing arts organization can adopt — lowering the barrier to audience-participatory performance from months of custom development to a single configuration file. The project shifts the audience-performer relationship: audiences become co-performers operating a collective instrument, not passive viewers. Impact evaluation through performer satisfaction surveys after each deployment, audience engagement metrics (input frequency, consensus convergence patterns, override usage), and adoption tracking of the open-source tools. Methodology documentation published through existing public-process essay practice, making the refinement process a field contribution.

**[~99 words]**

---

## About You (150 words max per person, 300 words max total)

> Please provide background on your work and, if applicable, describe a previous project that demonstrates your approach to, and engagement with, new digital tools, innovative data practices, or production methods.

Systems artist, creative technologist, and writer based in NYC. MFA in Creative Writing (FAU, 2015–2018). 11 years teaching at 8+ institutions, 2,000+ students. 18 years professional experience spanning creative systems design, education, multimedia production, and technology. LGBTQ+.

The project demonstrating my engagement with new digital tools is Omni-Dromenon itself — a TypeScript pnpm monorepo I built as the ORGAN-II flagship of my eight-organ creative-institutional system. The engine implements real-time WebSocket consensus aggregation, three-axis spatial/temporal/cluster weighting, React performer and audience interfaces, an OSC bridge to SuperCollider and Max/MSP, four working examples (generative music, generative visual, choreographic interface, theatre dialogue), and Docker infrastructure for venue deployment. I use AI as a compositional instrument: directing code generation, iterating on architecture, applying editorial judgment — analogous to conducting, where creative intelligence is structural. Teaching background (11 years, 2,000+ students) directly relevant to the community participation dimension of live deployment.

**[~148 words]**

---

## Budget Overview ($150,000)

| GivingData Category | Amount | Description |
|---------------------|--------|-------------|
| Fees or Salary / Core Team Members | $50,000 | Lead artist/technologist (8 months: 2 prep + 6 prototyping + deployment) |
| Fees / Consultants, Collaborators, Performers | $30,000 | 6–8 performing artists (dancers, musicians, theater) for workshop and deployment cycles |
| Equipment | $8,000 | Venue-specific hardware: portable WiFi routers, projection, audio interfaces, stage monitors |
| Licenses | $0 | Open-source toolchain — no license costs |
| Workshops | $7,000 | Performer training on the system, pre-deployment iteration sessions |
| Travel | $10,000 | AMT Lab cohort meetings, presenting work at partner events |
| Materials | $5,000 | Audio/visual production materials, printed audience quick-start guides |
| Space (rental) | $15,000 | Rehearsal and performance space (NYC) for 3 deployment cycles |
| Overhead (10% cap) | $15,000 | Administrative, accounting, insurance, workspace costs |
| Contingency & Misc. | $0 | Absorbed into equipment and workshop lines |
| Other | $10,000 | Open-source publication, performance documentation, video capture |
| **Total** | **$150,000** | |

**Note:** Overhead at exactly 10% ($15K of $150K). Equipment increased from original estimate to cover venue-specific portable infrastructure (WiFi routers are critical — venue WiFi is unreliable for 100+ simultaneous WebSocket connections). If selecting $100K tier, scale proportionally: Salary $35K, Collaborators $20K, Equipment $5K, Travel $8K, Space $10K, Overhead $10K, other categories reduced accordingly.

---

## Attachments Checklist

### 1. Resume PDF
- [ ] Use `materials/resumes/multimedia-specialist.pdf` — verify one-page, current
- [ ] Emphasize: systems art practice, MFA, creative technology credentials, Omni-Dromenon Engine
- [ ] Include: TypeScript, WebSocket, React, OSC/SuperCollider, Docker — technical stack is a strength here

### 2. Work Samples PDF (combined single file)
- [ ] Option A (images — recommended):
  - Image 1: Omni-Dromenon architecture diagram (three-layer system with audience/performer/consensus flow)
  - Image 2: Performance SDK screenshot — performer dashboard with override panel + audience slider interface
  - Caption each image with brief context connecting to live performance use case
- [ ] Option B (video/audio links embedded in PDF):
  - Video 1: Screen recording of the engine running with audience inputs flowing through consensus (~1 min)
  - Video 2: Performer override demo — showing absolute/blend/lock modes in action (~1 min)
  - Include URLs with passwords (if needed) INSIDE the PDF
- [ ] Combine into single PDF, clearly labeled
- [ ] Max: 2 images OR 2 video/audio (2 min total) — not both

---

## Pre-Submission Reminders

- [ ] Submissions are **final upon upload** — no revisions after submission
- [ ] Form auto-saves — use "Save and Come Back Later" between sessions
- [ ] Deadline is **NOON ET** on March 2, not midnight
- [ ] AI declaration: disclose AI usage honestly — AI used as compositional tool for code generation and architectural iteration; all creative decisions, system design, and application content reflect original work
- [ ] Fiscal sponsor field: leave blank or note "Fractured Atlas available upon request" — not required at this stage
- [ ] Core team members: leave blank if applying as individual (no confirmed collaborators yet)
- [ ] After submitting: `python scripts/submit.py --target doris-duke-amt --record`

---

## Word Count Verification

| Field | Limit | Draft Count | Status |
|-------|-------|-------------|--------|
| Concept Description | 250 | ~248 | OK |
| Feasibility | 100 | ~88 | OK |
| Field Survey | 100 | ~99 | OK |
| Field Impact | 100 | ~99 | OK |
| About You | 150 | ~148 | OK |
