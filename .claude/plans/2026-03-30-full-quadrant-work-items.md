# Full Quadrant Distribution — Work Item Specification

**Date:** 2026-03-30
**Board:** https://github.com/orgs/a-organvm/projects/1/views/1
**Tracks:** Product, Content, Distribution, Funding, Consulting
**Masks:** Narrator (Q1), Strategist (Q2), Architect (Q3), Integrator (Q4)

---

## TRACK 1: PRODUCT (Engine Extraction + Marketplace)

### P0 — This Week

#### PROD-001: Extract identity.yaml decoupling
**Organ:** III | **Priority:** P0 | **Sprint:** S39
**Description:** Replace all 22 hardcoded personal references across scripts with `load_identity()` calls. The 7 instance-coupled scripts (check_email, generate_project_blocks, materials_validator, prepare_submission, refresh_from_ecosystem, standards, check_email_constants) need configurable identity injection.
**Acceptance:** `grep -r "Anthony\|Padavano\|padavano.anthony\|561-602" scripts/*.py` returns 0 matches outside identity.yaml imports. All 3,266 tests pass.
**Files:** scripts/apply.py (22 refs), scripts/build_cover_letters.py (12), scripts/dm_composer.py (2), scripts/recruiter_filter.py (2), + 18 others
**Depends on:** config/identity.yaml (DONE), pipeline_lib.load_identity() (DONE)

#### PROD-002: Public README for open-source launch
**Organ:** III | **Priority:** P0 | **Sprint:** S39
**Description:** Write the README that IS the marketing. Structure: problem statement (2,000 apps → 0 interviews), solution (state machine + quality gates + precision), quick start, feature tour, architecture diagram, metrics (3,266 tests, 161 scripts, 127 commands). Include screenshots of CLI output.
**Acceptance:** README passes the stranger test — someone with zero context can install and run `python scripts/run.py standup` within 5 minutes.
**Depends on:** PROD-001 (identity decoupled)

#### PROD-003: Make repo PUBLIC
**Organ:** III | **Priority:** P0 | **Sprint:** S39
**Description:** Audit repo for secrets (.submit-config.yaml, .greenhouse-answers/, .env, .email-config.yaml). Verify .gitignore covers all sensitive files. Strip any leaked credentials from git history if needed. Flip visibility to public.
**Acceptance:** `gitleaks detect` returns 0 findings. Repo visible at github.com/4444J99/application-pipeline (or organvm-iii-ergon/).
**Depends on:** PROD-001, PROD-002

### P1 — This Month

#### PROD-004: Pipeline ↔ in-midst-my-life API bridge
**Organ:** III | **Priority:** P1 | **Sprint:** S40
**Description:** Build the integration between pipeline's config/identity.yaml and in-midst's /profiles/:id API. Sync identity data bidirectionally. When pipeline generates a tailored resume, it should optionally consume the masked profile from in-midst for the role family.
**Acceptance:** `python scripts/run.py sync-identity` pushes identity.yaml to in-midst API. `python scripts/run.py fetch-mask <role-family>` returns masked profile view.
**Depends on:** PROD-001, in-midst API deployed (DONE — inmidst-api.onrender.com)

#### PROD-005: Pro tier — hosted pipeline with ATS integrations
**Organ:** III | **Priority:** P1 | **Sprint:** S40-41
**Description:** Web dashboard wrapping the CLI. User creates account, uploads identity.yaml, manages pipeline through browser. ATS integrations (Greenhouse, Lever, Ashby) as premium feature. Stripe billing at $29/mo.
**Acceptance:** User can sign up, create entries, score opportunities, submit applications through hosted UI. Stripe processes payment.
**Depends on:** PROD-001, PROD-003

#### PROD-006: Employer seat — Inverted Interview hosting
**Organ:** III | **Priority:** P1 | **Sprint:** S41-42
**Description:** in-midst's Inverted Interview available as a paid feature. Employer creates account ($149/mo), runs interviews, sees compatibility scores, bulk-searches candidates.
**Acceptance:** Employer can create session, answer questions, see 5-factor compatibility score. Stripe processes payment.
**Depends on:** in-midst-my-life employer flow (partially built)

### P2 — Next Quarter

#### PROD-007: Greenhouse Partner Program integration
**Organ:** III | **Priority:** P2 | **Sprint:** S43+
**Description:** Package Inverted Interview as a Greenhouse plugin. Apply to Greenhouse Partner Program. When employer clicks "Run Inverted Interview" from Greenhouse, they hit in-midst.
**Depends on:** PROD-006

#### PROD-008: White-label SDK for staffing agencies
**Organ:** III | **Priority:** P2 | **Sprint:** S44+
**Description:** Multi-tenant deployment. Staffing agency brand, our engine. Custom mask taxonomies. Bulk candidate management.
**Depends on:** PROD-005, PROD-006

---

## TRACK 2: CONTENT (Application-as-Research → Publication)

### The Indictment Series (Narrator mask, Q1 — Individual Applicants)

#### CONT-001: "I Sent 2,000 Applications and Got Zero Interviews"
**Mask:** Narrator | **Quadrant:** Q1 | **Priority:** P0 | **Sprint:** S39
**Format:** LinkedIn Testament post (800-1600 chars) + Dev.to article expansion (1500 words)
**Data source:** Pipeline Era 1 data, conversion-log.yaml, closed/ entries
**Thesis:** Volume-based job searching is structurally broken. The system rewards precision targeting + warm paths. 2,000 cold apps = 0 interviews. 60 structured + 271 outreach = 6 responses (20% DM rate).
**Testament audit target:** 6/8 minimum
**Publish:** LinkedIn (Testament) + Dev.to (expanded) + cross-post to Hashnode

#### CONT-002: "16 Rejections, 13 Withdrawals, 11 Expirations"
**Mask:** Narrator | **Quadrant:** Q1 | **Priority:** P1 | **Sprint:** S39
**Format:** LinkedIn Testament post
**Data source:** pipeline/closed/ outcome analysis, 40 closed entries
**Thesis:** Closed pipeline data reveals more about the market than open pipeline data. Rejection patterns, withdrawal reasons, expiration rates are signals, not failures.

#### CONT-003: "1,510 Job Postings Sourced. 9 Were Worth Applying To."
**Mask:** Narrator | **Quadrant:** Q1 | **Priority:** P1 | **Sprint:** S40
**Format:** LinkedIn Testament + Dev.to
**Data source:** research_pool/ (1,512 entries), scoring data, qualification rates
**Thesis:** The ratio of opportunities to actionable opportunities is ~170:1. Most job postings are noise. The scoring rubric is the filter that makes the haystack navigable.

#### CONT-004: "The 20% DM Response Rate vs the 0% Cold Application Rate"
**Mask:** Narrator | **Quadrant:** Q1 | **Priority:** P0 | **Sprint:** S39
**Format:** LinkedIn Testament post
**Data source:** outreach-log.yaml (311 actions), contacts.yaml (210 contacts), conversion data
**Thesis:** Relationships > resumes. One warm DM outperforms a hundred cold applications. The data proves it.

### The Exposé Series (Strategist mask, Q2 — Individual Employers)

#### CONT-005: "Your Greenhouse Portal Has Hidden Questions That Filter Candidates"
**Mask:** Strategist | **Quadrant:** Q2 | **Priority:** P1 | **Sprint:** S40
**Format:** LinkedIn Testament + Dev.to
**Data source:** Greenhouse API field analysis from apply.py, portal-answers.md across 34 applications
**Thesis:** Portals ask questions the handbook doesn't mention. Demographic surveys, "optional" checkboxes, and hidden qualification gates filter candidates before a human reviews them. Employers: do you know what your portal is doing?

#### CONT-006: "Why Your AI Resume Screener Ships Truncated Sentences"
**Mask:** Strategist | **Quadrant:** Q2 | **Priority:** P1 | **Sprint:** S40
**Format:** Dev.to article
**Data source:** tailor_resume.py character limit analysis, sentence completeness validator data, batch-03 truncation audit
**Thesis:** AI tailoring tools hit character limits and cut sentences mid-phrase. "Manages." "And." "Across 8 GitHub." Every AI resume builder has this bug. Here's the validator that catches it.

#### CONT-007: "The Auto-Fill Bug: Career Tools Answer 'Yes' to Questions They Don't Understand"
**Mask:** Strategist | **Quadrant:** Q2 | **Priority:** P1 | **Sprint:** S41
**Format:** LinkedIn Testament
**Data source:** apply.py _answer_question() blanket "Yes" bug, portal-answers.md audit
**Thesis:** A single `return "Yes"` for every Yes/No question. "Have you interviewed here before?" → "Yes." Every auto-fill tool has a version of this. The fix: default unknown questions to blank, not affirmative.

#### CONT-008: "$405K for Package Management: The Credential Inflation Tax"
**Mask:** Strategist | **Quadrant:** Q2 | **Priority:** P2 | **Sprint:** S41
**Format:** LinkedIn Testament
**Data source:** Anthropic job description analysis, salary data, experience requirement analysis
**Thesis:** "10+ years experience in a full-time Software Engineer role" for a role that owns "build environments, package management, and dependency systems." The credential bar rises while the work stays the same.

### The Architecture Series (Architect mask, Q3 — Institutional Seekers)

#### CONT-009: "3,266 Tests for a Job Search"
**Mask:** Architect | **Quadrant:** Q3 | **Priority:** P0 | **Sprint:** S39
**Format:** Dev.to article (flagship technical piece) + HN "Show HN" post
**Data source:** Entire pipeline architecture — tests/, scripts/, pipeline_lib.py, quality gates
**Thesis:** The pipeline is a production system with production discipline. 161 scripts, 127 CLI commands, forward-only state machine, 9-dimension scoring rubric, quality gates that catch truncated sentences. Here's the architecture, open source.
**Timing:** Publish with PROD-003 (repo goes public)

#### CONT-010: "Forward-Only State Machines: Why Your Application Process Should Never Go Backward"
**Mask:** Architect | **Quadrant:** Q3 | **Priority:** P1 | **Sprint:** S40
**Format:** Dev.to article
**Data source:** pipeline_entry_state.py, advance.py, state transition validation
**Thesis:** The state machine enforces forward-only progression because backward transitions corrupt data integrity. The same principle governs database migrations, deployment pipelines, and career decisions. Here's the formal model.

#### CONT-011: "The Forced Revision Protocol"
**Mask:** Architect | **Quadrant:** Q3 | **Priority:** P1 | **Sprint:** S40
**Format:** Dev.to article
**Data source:** SOP-INST-001 from aerarium, apply.py vs. forced revision comparison
**Thesis:** One-pass cover letters are always wrong. The SOP requires 4 forced revisions across 3 media before submission. The quality difference is measurable. Here's the protocol, applicable to any writing process.

#### CONT-012: "1,030 Target Profiles: Building Competitive Intelligence at Scale"
**Mask:** Architect | **Quadrant:** Q3 | **Priority:** P2 | **Sprint:** S41
**Format:** Dev.to article
**Data source:** materials/targets/profiles/ (1,030 JSON profiles), scoring rubric
**Thesis:** Every opportunity the pipeline evaluates gets a structured profile: category, position, deadline, work samples, evidence highlights. At 1,030 profiles, you have a market intelligence database. Here's the schema and what it reveals.

### The Enterprise Series (Integrator mask, Q4 — Institutional Hirers)

#### CONT-013: "What If Every Application Was a Product Demo?"
**Mask:** Integrator | **Quadrant:** Q4 | **Priority:** P1 | **Sprint:** S40
**Format:** LinkedIn article (long-form) + email to enterprise contacts
**Data source:** Product strategy doc, marketplace thesis, integration architecture
**Thesis:** The hiring managers receiving your applications are potential customers for your product. The quality of the output IS the pitch. Every submission demonstrates the engine's capability to the people who might buy it. Here's the two-sided marketplace model.

#### CONT-014: "The Inverted Interview: Making Employers Earn the Right to See Your Full Profile"
**Mask:** Integrator | **Quadrant:** Q4 | **Priority:** P0 | **Sprint:** S39
**Format:** Product Hunt listing copy + Dev.to article + demo video script
**Data source:** in-midst-my-life architecture, Inverted Interview paradigm doc, compatibility scoring engine
**Thesis:** Stop sending resumes. Make the employer answer YOUR questions first. The 5-factor compatibility score replaces resume screening. Here's the product, it's live, try it.

#### CONT-015: "Why Staffing Agencies Should Stop Using Spreadsheets"
**Mask:** Integrator | **Quadrant:** Q4 | **Priority:** P2 | **Sprint:** S42
**Format:** White paper (gated content — email capture)
**Data source:** Pipeline architecture vs. spreadsheet workflow comparison, enterprise feature set
**Thesis:** Staffing agencies manage candidate pipelines in spreadsheets and CRMs that weren't designed for application lifecycle management. Here's a state machine with quality gates, scoring rubrics, and ATS integrations. White-label ready.

---

## TRACK 3: DISTRIBUTION (Channel Activation)

#### DIST-001: Publish 2 READY Testament posts to LinkedIn
**Priority:** P0 | **Sprint:** S39 (THIS WEEK)
**Content:** post-002-testament-revision (7/8) + post-004-ai-conductor (6/8)
**Action:** Paste to LinkedIn. Include portfolio + LinkedIn + GitHub links. Schedule: Mon + Thu.

#### DIST-002: Dev.to account setup + first article
**Priority:** P0 | **Sprint:** S39
**Action:** Create Dev.to account. Publish CONT-009 ("3,266 Tests for a Job Search") as flagship article. Cross-post to Hashnode.

#### DIST-003: Daily micro-content cadence
**Priority:** P0 | **Sprint:** S39 (starts NOW)
**Action:** Every day: screenshot pipeline output, quality gate catching an error, a metric, a CLI command. Post to LinkedIn with 1-2 sentence caption. The practice IS the content.

#### DIST-004: HN "Show HN" launch
**Priority:** P1 | **Sprint:** S40 (after repo public)
**Action:** "Show HN: I built a 3,266-test application pipeline because 2,000 cold apps got me 0 interviews." Tuesday morning, 9 AM ET. One shot.
**Depends on:** PROD-003 (repo public), PROD-002 (README), CONT-009 (article)

#### DIST-005: Product Hunt launch (both products)
**Priority:** P1 | **Sprint:** S41
**Action:** Launch in-midst-my-life + application-pipeline-engine as paired products. "The two-sided hiring platform." Inverted Interview is the hook.
**Depends on:** PROD-003, PROD-006

#### DIST-006: Send 30 overdue follow-up DMs
**Priority:** P0 | **Sprint:** S39 (THIS WEEK)
**Action:** Generate Protocol-validated DMs for all 24 submitted entries with overdue follow-ups. Include full profile links (portfolio + LinkedIn + GitHub). Every DM is distribution.

#### DIST-007: Activate 12 new connect requests (2026-03-28 batch)
**Priority:** P0 | **Sprint:** S39
**Action:** Monitor acceptances. Send Protocol-validated DMs on acceptance. Priority: hiring managers (Dylan Kozlowski, Spencer Judge, Roy Williams III, Tammer Galal).

#### DIST-008: 5-minute Inverted Interview demo video
**Priority:** P1 | **Sprint:** S40
**Action:** Screen-record an Inverted Interview flow. Employer fills out questions, sees compatibility score, sees masked profile. Upload to YouTube. Embed in Dev.to articles and LinkedIn posts.

#### DIST-009: Contact 3 bootcamp placement directors
**Priority:** P2 | **Sprint:** S41
**Action:** Research placement team leads at General Assembly, Flatiron, Springboard. Use pipeline to score, research contacts, send Protocol-validated outreach.

#### DIST-010: Contact 3 career center directors
**Priority:** P2 | **Sprint:** S41
**Action:** Research career center directors at universities with strong CS programs. Offer pilot: free pipeline for 1 semester. Publish case study.

---

## TRACK 4: FUNDING (Grants + Institutional — Aerarium)

#### FUND-001: Submit NLnet NGI0 Commons application
**Priority:** P0 | **Sprint:** S39 (DUE APRIL 1 — TOMORROW)
**Repo:** meta-organvm/aerarium--res-publica
**Action:** Paste draft.md fields into https://nlnet.nl/propose/ web form. All content is written. EUR 37,080, 11 milestones, 6 months.
**SOP phase:** Phase 6 (Submission — human-gated)

#### FUND-002: Creative Capital — DEFERRED
**Status:** DEFERRED (funder-fit gate failed)
**Reason:** CC funds sensory art, ORGANVM produces infrastructure. See GH#5, IRF-INST-002.
**Next action:** Monitor CC 2028 cycle. If they expand criteria to include infrastructure art / systems art, re-evaluate.

#### FUND-003: Sovereign Tech Fellowship research
**Priority:** P1 | **Sprint:** S40
**Repo:** meta-organvm/aerarium--res-publica
**Action:** Complete research at research/2026-03-30-sovereign-tech-research.md. Evaluate fit for Cvrsvs Honorvm extraction work. If funder-fit passes, begin SOP Phase 1 (Research).

#### FUND-004: ZKM Rauschenberg research
**Priority:** P2 | **Sprint:** S40
**Repo:** meta-organvm/aerarium--res-publica
**Action:** Complete research at research/2026-03-30-zkm-rauschenberg-research.md. Requires artistic evidence (Dimension II from Becoming the Thing roadmap). Blocked until video documentation of Alchemical Synthesizer exists.

#### FUND-005: Aspiration Tech fiscal sponsorship application
**Priority:** P1 | **Sprint:** S40
**Repo:** meta-organvm/aerarium--res-publica
**Action:** Complete research at research/2026-03-30-aspiration-tech-research.md. Fiscal sponsorship unlocks 501(c)(3) grant eligibility without forming a nonprofit. Gateway to Sloan, NSF POSE, foundation grants.

#### FUND-006: GitHub Sponsors activation
**Priority:** P1 | **Sprint:** S40
**Repo:** meta-organvm/aerarium--res-publica
**Action:** Set up GitHub Sponsors profile per entity-formation/ research. Tiers: $5 (individual supporter), $25 (pro user), $100 (organization), $500 (enterprise partner). Requires: payment account, profile description, tier descriptions.
**Depends on:** PROD-003 (repo public — sponsors need visible repos)

---

## TRACK 5: CONSULTING (Pillar 3 — Commerce)

#### CONS-001: Tony Carbone follow-up — scope MCA + Flyland workstreams
**Priority:** P0 | **Sprint:** S39
**Repo:** organvm-iii-ergon/commerce--meta
**Action:** Return to Tony with specific deliverables + timeline + pricing for MCA automation and Flyland.com healthcare SaaS. 5 workstreams identified from 40-min call. Needs SOW.

#### CONS-002: Scott Lefler — ship first build+sell product
**Priority:** P1 | **Sprint:** S39-40
**Repo:** organvm-iii-ergon (scrapper or new repo)
**Action:** Pick one product from the build+sell pipeline. Ship it. Prove the partnership model produces revenue. Content cannibalizer / audience builder is the cross-cutting need.

#### CONS-003: Dustin Dipaulo — spec music DSP alternative
**Priority:** P2 | **Sprint:** S40
**Action:** Run the ideas through the alchemical process (SOP-INST-001 adapted for product specs). Music DSP alternative (Cronus-Metabolus) has the clearest product-market signal.

#### CONS-004: Jessica Tenenbaum — activate behavioral blockchain
**Priority:** P2 | **Sprint:** S40
**Repo:** organvm-iii-ergon/peer-audited--behavioral-blockchain (EXISTS)
**Action:** 18K heartbreak audience + existing repo. Connect the audience to the product. Jessica provides domain + audience, you provide architecture.

#### CONS-005: Rob Bonavoglia — HokageChess iteration
**Priority:** P2 | **Sprint:** S41
**Repo:** Multiple existing iterations in meta-organvm/intake/
**Action:** Pick the best iteration, deploy, connect to Rob's YouTube channel + chess audience.

#### CONS-006: Maddie — water funnel infrastructure
**Priority:** P2 | **Sprint:** S41
**Action:** Awaiting her transcripts/voice notes. When received, run through alchemical process. She asked for "the bones" — system architecture for her existing water filtration business.

---

## EXECUTION PRIORITY (This Week — S39)

| # | Item | Track | Mask | Due |
|---|------|-------|------|-----|
| 1 | FUND-001: Submit NLnet | Funding | — | **TOMORROW** |
| 2 | DIST-001: Publish 2 Testament posts | Distribution | Narrator | Mon + Thu |
| 3 | DIST-006: Send 30 overdue follow-up DMs | Distribution | All | Mon-Fri |
| 4 | PROD-001: Identity.yaml decoupling | Product | — | Wed |
| 5 | CONT-001: "2,000 Apps → 0 Interviews" draft | Content | Narrator | Thu |
| 6 | CONT-004: "20% DM Response Rate" draft | Content | Narrator | Fri |
| 7 | DIST-003: Daily micro-content starts | Distribution | All | NOW |
| 8 | CONS-001: Tony Carbone SOW | Consulting | — | Wed |
| 9 | PROD-002: Public README draft | Product | — | Fri |

---

## METRICS (Monthly Review)

| Metric | Current | Month 1 Target | Month 3 Target |
|--------|---------|-----------------|-----------------|
| GitHub stars | 0 (private) | 50 | 500 |
| LinkedIn followers | 27 | 100 | 500 |
| Dev.to followers | 0 | 50 | 300 |
| Pro tier signups | 0 | 1 | 10 |
| Employer seats | 0 | 0 | 1 |
| MRR | $0 | $29 | $439 |
| Content pieces published | 6 (Testament posts) | 14 | 40 |
| Pipeline conversion rate | 0% | 4% (1/24) | 8% |
| Bootcamp/career center pilots | 0 | 0 | 1 |
| NLnet funding | pending | decision | EUR 37,080 (if awarded) |
| Consulting revenue | $0 | $2,000 (Tony) | $8,000 |
