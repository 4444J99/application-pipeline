# F1 + F2 Infrastructure Setup Guide — GitHub Sponsors + Fractured Atlas

**Created:** 2026-02-18
**Time to complete:** ~45 minutes total (15 min GitHub Sponsors + 30 min Fractured Atlas)
**Benefits cliff:** GitHub Sponsors income is taxable. Small amounts safe. Fractured Atlas is a pass-through fiscal sponsor — donations to your project are tax-deductible for donors and processed through FA's 501(c)(3).

---

## F1: Activate GitHub Sponsors (~15 minutes)

### Why This Matters

GitHub Sponsors monetizes the 100-repo system immediately. It adds a "Sponsor" button to every repo, signals to grant reviewers that the project accepts financial support, and provides passive income infrastructure with zero upfront cost.

### Steps

**1. Go to https://github.com/sponsors**

Click "Get sponsored" or navigate to your profile's sponsor dashboard.

**2. Choose account type**

Set up for your personal account (@4444J99) first — this covers all repos across all orgs. Organization-level sponsorship can be added later for meta-organvm.

**3. Complete your profile**

**Description (paste this):**

---

Building the eight-organ creative-institutional system — 100 repositories across 8 organizations, coordinating theory, generative art, commercial products, governance, public process, community, and marketing as a unified creative practice. 42 published essays, 404,000+ words, 82+ CI/CD pipelines, all built by a single practitioner using AI as a compositional instrument. Your sponsorship directly supports an independent systems artist maintaining open-source creative infrastructure.

---

**4. Create sponsorship tiers**

| Tier | Amount | Description |
|------|--------|-------------|
| Supporter | $3/month | Support the eight-organ system. Your name in the project's public acknowledgments. |
| Patron | $10/month | All previous + early access to essays before public distribution. |
| Sustainer | $25/month | All previous + monthly update on system development progress. |
| Champion | $50/month | All previous + direct input on feature priorities for ORGAN-III products. |
| Institutional | $100/month | All previous + consultation on creative-institutional governance for your own projects. |

Also create **one-time tiers:**

| Tier | Amount | Description |
|------|--------|-------------|
| Coffee | $5 | Buy the system a coffee. |
| Essay | $25 | Sponsor one essay in the public process series. |
| Sprint | $100 | Sponsor one development sprint. |

**5. Payment setup**

Connect a bank account (US) or use Stripe Connect. GitHub pays monthly.

**6. Tax form**

Complete the W-9 form (US individual). This is required before payouts activate.

**7. Add FUNDING.yml to repositories**

After setup, create `.github/FUNDING.yml` in the meta-organvm org's `.github` repo:

```yaml
github: 4444J99
```

This will add the Sponsor button to all repos in the meta-organvm org. Repeat for each org's `.github` repo, or add it to individual repo `.github/` directories.

### Post-Setup Checklist

- [ ] Profile description is compelling and accurate
- [ ] At least 3 monthly tiers and 2 one-time tiers created
- [ ] Bank account or Stripe connected
- [ ] W-9 completed
- [ ] FUNDING.yml committed to at least meta-organvm/.github/
- [ ] Verified: Sponsor button visible on organvm-corpvs-testamentvm repo page
- [ ] Update `docs/operations/rolling-todo.md` — mark F1 as COMPLETED

---

## F2: Apply for Fractured Atlas Fiscal Sponsorship (~30 minutes)

### Why This Matters

Fractured Atlas fiscal sponsorship:
1. Gives your project 501(c)(3) pass-through status — donors get tax deductions
2. Unlocks grants that require 501(c)(3) (NEA, state arts councils, many foundations)
3. Provides a professional fiscal infrastructure for the practice
4. Costs only $10/month (Professional membership) + 8% fee on donations received

### Steps

**1. Go to https://www.fracturedatlas.org/fiscal-sponsorship**

Click "Apply" or navigate to the fiscal sponsorship application.

**2. Create a Fractured Atlas account**

Choose **Professional membership** ($10/month). You need this before applying for fiscal sponsorship.

**3. Complete the application**

#### Project Name

```
The Eight-Organ Creative-Institutional System
```

#### Project Description / Mission

**Paste this (adjust to field limits):**

---

The Eight-Organ Creative-Institutional System is a documented creative infrastructure coordinating 100 open-source software repositories across 8 organizations, governing theory, generative art, commercial products, governance protocols, public documentation, community programming, and distribution as a unified artistic practice.

The project's mission is to demonstrate that governance structures, coordination protocols, and systems design are primary creative outputs — not supplementary to art, but constitutive of it. The system produces generative visual and sonic art, published nonfiction essays, community salon programming, and reusable creative technology tools, all coordinated through a machine-readable registry, automated dependency validation, and formal promotion state machines.

The project serves the public by: (1) publishing all governance documentation, audit reports, and process essays as open-source educational resources; (2) developing reusable tools other creative technologists can adapt; (3) hosting community programming (salons, reading groups, workshops) through ORGAN-VI; and (4) demonstrating a methodology for solo creative production at institutional scale that other independent artists can learn from.

42 published nonfiction essays (~134,000 words) document the system's construction in real time. The project's radical transparency — building in public as artistic practice — ensures that every creative decision, governance rule, and architectural choice is publicly visible and verifiable.

---

#### Activities (what you actually do)

---

1. Write and publish nonfiction essays documenting creative systems design (42 essays published, ~5 per month cadence)
2. Develop and maintain generative art software (p5.js, SuperCollider, Pure Data)
3. Design and implement governance protocols for multi-repository creative infrastructure
4. Host community programming: creative-technology salons, governance workshops, reading groups
5. Produce and distribute open-source tools for creative technologists
6. Develop live performance works translating software governance into choreographic scores

---

#### Audience / Public Benefit

---

The project serves: (1) independent artists and creative technologists seeking models for systematic creative practice; (2) the open-source community, which benefits from 97 publicly available repositories; (3) readers of the essay series, who follow the public construction process; (4) participants in community programming; and (5) scholars and practitioners interested in governance as creative medium, AI-augmented production methodology, and building-in-public as artistic practice.

---

#### Budget Estimate (if asked)

---

Annual projected budget: $15,000–$50,000
- Grant income (art-tech grants, residencies): $10,000–$40,000
- Individual donations (GitHub Sponsors, direct): $2,000–$5,000
- Workshop/consultation fees: $3,000–$5,000

Primary expenses:
- Equipment and hosting: $3,000/year
- Application fees and materials: $1,000/year
- Travel to residencies, conferences, events: $5,000/year
- Collaborator fees for performance works: $5,000–$10,000
- Community programming costs: $1,000–$3,000/year

---

#### Non-commercial nature

The project is not primarily commercial. While ORGAN-III includes commercial product development, the fiscal sponsorship covers the artistic, educational, and community components (Organs I, II, IV, V, VI, VII). No investors, no profit-sharing arrangements, no commercial distribution agreements.

#### Political activity

None.

#### Previous 501(c)(3) status

No — this is a first-time application. The project has never held 501(c)(3) status.

#### Geographic scope

Primarily NYC-based. Fundraising and spending in the United States.

### Post-Submission Checklist

- [ ] Fractured Atlas membership active ($10/month)
- [ ] Fiscal sponsorship application submitted
- [ ] Set calendar reminder: check status in 1-2 weeks (approval timeline)
- [ ] Once approved: update grant applications to reference fiscal sponsor status
- [ ] Update `docs/operations/rolling-todo.md` — mark F2 as SUBMITTED
- [ ] Future: add FA donation page link to FUNDING.yml alongside GitHub Sponsors

---

## After Both Are Active

Once GitHub Sponsors and Fractured Atlas are both active:

1. **Update portfolio site** — add Sponsor/Donate buttons
2. **Update README files** — add "Support This Project" section to key repos
3. **Update FUNDING.yml** — add both GitHub Sponsors and FA custom URL
4. **Update grant applications** — note "fiscal sponsorship available through Fractured Atlas" where applicable
5. **Revisit NEA GAP** — now eligible with fiscal sponsor (previously ineligible without 501(c)(3))
6. **Update `docs/operations/rolling-todo.md`** — mark F1 and F2 as COMPLETED
