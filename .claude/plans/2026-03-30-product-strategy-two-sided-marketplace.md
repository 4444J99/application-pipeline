# Product Strategy: The Two-Sided Application Marketplace

**Date:** 2026-03-30
**Products:** application-pipeline (ORGAN-III) + in-midst-my-life (ORGAN-III)
**Thesis:** One product manages the search. The other manages the identity. Together they're a marketplace.

---

## The Two Products

### Application Pipeline — "The Outbound Engine"
**What it does:** Manages the candidate's campaign. Score opportunities, tailor materials, submit through ATS portals, track outreach, enforce quality, measure conversion.

**Who uses it:** Anyone applying to things — jobs, grants, residencies, fellowships, consulting engagements.

**Core primitives:**
- Forward-only state machine (research → qualified → staged → submitted → outcome)
- Multi-dimension scoring rubric (configurable per track: jobs, grants, consulting)
- ATS integration layer (Greenhouse, Lever, Ashby APIs)
- Outreach protocol engine (contact research, DM composition, follow-up cadence)
- Quality gates (sentence completeness, page fill, link liveness, portal validation)
- Material tailoring (resume/CL generation from identity config + base templates)
- Contact CRM (210+ contacts, relationship strength, interaction history)
- Analytics (funnel conversion, velocity, block-outcome correlation)

**Analogy:** Salesforce for job seekers. The CRM + pipeline + campaign orchestration, but for applications instead of deals.

### in-midst-my-life — "The Inbound Engine"
**What it does:** Manages the candidate's identity. 16 masks, 5-factor compatibility scoring, Inverted Interview (employer answers YOUR questions), dynamic CV curation, verifiable credentials.

**Who uses it:** Candidates presenting themselves + employers evaluating candidates.

**Core primitives:**
- Immutable identity ledger (single source of truth, never compressed)
- 16 identity masks across 3 categories (cognitive, expressive, operational)
- 10 role families with curated mask blends
- 8 temporal epochs (career lifecycle stages)
- 5-factor compatibility scoring (skill match, values alignment, growth fit, sustainability, compensation)
- Inverted Interview protocol (employer becomes interviewee)
- W3C Verifiable Credentials + DID resolution
- Hunter Protocol (autonomous job discovery)
- Tone analysis of employer responses
- JSON-LD semantic export

**Analogy:** LinkedIn Profile on steroids — but the candidate controls the narrative, not the platform. And the employer has to earn the right to see the full picture.

---

## How They Connect

```
CANDIDATE SIDE                          EMPLOYER SIDE

Application Pipeline                    in-midst-my-life
(outbound engine)                       (inbound engine)

┌──────────────────┐                    ┌──────────────────┐
│ Discover          │───── job found ──→│ Hunter Protocol   │
│ opportunity       │←── profile match ─│ matches candidate │
├──────────────────┤                    ├──────────────────┤
│ Score & qualify   │───── request ────→│ Select masks for  │
│ (9 dimensions)    │←── curated view ──│ this role family  │
├──────────────────┤                    ├──────────────────┤
│ Tailor materials  │───── identity ──→│ Generate narrative │
│ (resume, CL)      │←── masked CV ────│ blocks + weights  │
├──────────────────┤                    ├──────────────────┤
│ Submit via ATS    │                    │ Inverted Interview│
│ (Greenhouse,etc)  │                    │ (employer answers)│
├──────────────────┤                    ├──────────────────┤
│ Track & follow up │───── session ───→│ Compatibility      │
│ (outreach proto)  │←── 5-factor ─────│ score + analysis  │
├──────────────────┤                    ├──────────────────┤
│ Measure outcome   │───── result ────→│ Update identity   │
│ (conversion data) │←── VCs issued ───│ ledger + epochs   │
└──────────────────┘                    └──────────────────┘
```

**The bridge:** `config/identity.yaml` (pipeline) ↔ `/profiles/:id` (in-midst-my-life). Same person, same data, different representations. The pipeline uses a flat YAML config; in-midst stores the full identity graph in PostgreSQL. The API contract synchronizes them.

**Integration API calls:**
1. Pipeline discovers opportunity → calls in-midst `/profiles/:id/masks/select` with role family
2. In-midst returns masked profile → pipeline tailors resume/CL from masked view
3. Pipeline submits application → in-midst creates interview session
4. Employer hits in-midst link → Inverted Interview begins
5. Compatibility score flows back to pipeline → updates entry scoring
6. Outcome recorded in pipeline → in-midst updates identity ledger + issues VCs

---

## Revenue Model: Three Tiers × Two Sides

### Applicant Side (Application Pipeline)

| Tier | Price | Features |
|------|-------|----------|
| **Free (Open Core)** | $0 | CLI engine, state machine, basic scoring, manual submission. Self-hosted. |
| **Pro** | $29/mo | ATS integrations, outreach protocol, quality gates, analytics dashboard. Hosted. |
| **Team** | $99/mo | Multi-user (career coaches managing clients), batch operations, custom scoring rubrics. |

### Employer Side (in-midst-my-life)

| Tier | Price | Features |
|------|-------|----------|
| **Candidate Free** | $0 | Basic profile, 3 masks, manual export. Self-hosted. |
| **Candidate Pro** | $19/mo | Full 16 masks, Inverted Interview hosting, compatibility reports, VCs. |
| **Employer Seat** | $149/mo/seat | View candidate profiles, run Inverted Interviews, access compatibility scores, bulk search. |
| **Enterprise** | Custom | White-label, custom mask taxonomies, ATS plugin, SSO, dedicated instance. |

### Marketplace (Both Products)

| Feature | Revenue |
|---------|---------|
| **Candidate-Employer Match** | $X per successful match (performance fee) |
| **Featured Candidates** | Candidate pays to be surfaced to employers in their role family |
| **Verified Skills** | Employer pays for VC-verified candidate pools |
| **Interview Sessions** | Per-session fee for Inverted Interview hosting |

---

## Business Implementers

### Who buys this as infrastructure?

| Implementer | Uses Pipeline | Uses in-midst | Revenue Model |
|-------------|--------------|---------------|---------------|
| **Career services** (TopResume, ResumeGenius) | White-label pipeline for client management | Profile system for candidate presentation | SaaS license |
| **ATS vendors** (Greenhouse, Lever, Ashby) | — (they ARE the ATS) | Inverted Interview as plugin/integration | API partnership |
| **Staffing agencies** (Robert Half, Hays) | Pipeline for candidate tracking | in-midst for employer-facing presentations | Enterprise license |
| **University career centers** | Pipeline for student job tracking | in-midst for employer engagement events | Education license |
| **Outplacement firms** (Lee Hecht Harrison) | Pipeline for displaced worker campaigns | in-midst for identity reframing | Enterprise license |
| **Bootcamps** (General Assembly, Flatiron) | Pipeline for graduate placement tracking | in-midst for portfolio presentation | Education license |
| **AI recruiting startups** | Pipeline scoring engine | Hunter Protocol + compatibility scoring | API license |
| **Government employment offices** | Pipeline for constituent services | in-midst for skills-based matching | Government license |

### Integration patterns for implementers:

1. **Plugin model:** in-midst as Greenhouse/Lever plugin. Employer clicks "Run Inverted Interview" from their ATS. Compatibility score flows back as a custom field.

2. **White-label model:** Staffing agency deploys both products under their brand. Their consultants manage candidate pipelines; their clients see masked profiles.

3. **API-first model:** AI recruiting startup consumes both APIs. Pipeline for scoring/matching, in-midst for identity resolution and VC verification.

4. **Embedded model:** University career center embeds pipeline in their student portal. Students manage applications. Employers run Inverted Interviews during career fairs.

---

## The Applicant Journey (Both Products)

1. **Setup** — Applicant creates identity in in-midst (skills, experiences, values, career stage). Pipeline initializes with `config/identity.yaml` synced from in-midst API.

2. **Discover** — Pipeline's Hunter Protocol + sourcing scripts find opportunities. Scored across 9 dimensions. Top matches surfaced.

3. **Present** — For each application, in-midst selects optimal mask blend based on role family. Pipeline consumes the masked profile to generate tailored resume + cover letter.

4. **Apply** — Pipeline submits through ATS (Greenhouse/Lever/Ashby APIs). Portal answers auto-filled from identity config. Quality gates verify materials before submission.

5. **Engage** — Pipeline's outreach protocol sends connection requests + DMs. Employer clicks the in-midst link → Inverted Interview begins. Employer answers candidate's questions. Compatibility score computed.

6. **Convert** — Interview progresses. Pipeline tracks stage transitions. In-midst updates compatibility as more data arrives. VCs issued for verified claims.

7. **Outcome** — Pipeline records result. In-midst updates identity ledger (new experience, new epoch). Block-outcome correlation feeds back to improve future scoring.

---

## The Employer Journey (in-midst-my-life)

1. **Receive link** — Candidate shares their in-midst profile URL (from pipeline outreach DM).

2. **Answer questions** — Inverted Interview: employer describes their org, culture, role requirements, growth trajectory, non-negotiables. Tone analyzed in real time.

3. **See curated profile** — Based on employer answers, in-midst selects masks and generates a role-specific view. Not a generic resume — a contextually curated presentation.

4. **Review compatibility** — 5-factor score: skill match, values alignment, growth fit, sustainability, compensation. Green/red flags surfaced.

5. **Follow up** — in-midst generates context-aware follow-up questions based on the interview session. Employer can request deeper views (unlock additional masks).

6. **Verify** — Employer checks W3C Verifiable Credentials for claimed skills/experiences. Blockchain-anchored proof.

---

## Competitive Positioning

| Competitor | What they do | What we do differently |
|-----------|-------------|----------------------|
| **LinkedIn** | Passive profile, employer searches | Active identity management, employer answers YOUR questions |
| **Indeed/ZipRecruiter** | Volume matching, spray-and-pray | Precision matching, quality-gated applications |
| **Wellfound (AngelList)** | Startup job board | Full pipeline management + identity system |
| **Huntr/Teal** | Job tracking spreadsheet | State machine + scoring + ATS integration + quality gates |
| **Resume.io/Novoresume** | Resume builder | Identity operating system (16 masks, not 1 template) |
| **Greenhouse/Lever** | ATS (employer-side) | Both sides of the table + compatibility scoring |

**Defensible moat:** The identity ledger + mask system + Inverted Interview protocol are architecturally novel. No competitor combines applicant pipeline management with dynamic identity curation and employer-side interview inversion. The two products create a flywheel: more applicants → richer compatibility data → better employer experience → more employers → more opportunities → more applicants.

---

## First Revenue Path

1. **Dogfood** — Both products already running one production instance (personal). Prove the model.
2. **Open-source the engine** — Pipeline CLI + core library as Apache 2.0. Build community. Same play as Cvrsvs Honorvm.
3. **Launch Pro tier** — $29/mo for hosted pipeline with ATS integrations. $19/mo for in-midst Pro with full masks.
4. **Employer beta** — 10 companies trial Inverted Interview. Free during beta. Collect compatibility data.
5. **Marketplace** — Connect Pro applicants with beta employers. First matches. First revenue from match fees.
6. **Enterprise** — White-label to one staffing agency or career services company. Validate the B2B model.
