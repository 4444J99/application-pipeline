# Sovereign Systems — Full Build Roadmap

**Client:** Maddie
**Architect:** Anthony James Padavano / ORGANVM Studio
**Date:** 2026-03-25
**Status:** ALPHA

---

## The Vision

**Sovereign Systems** — a personal brand ecosystem with 4 pillars, connected by an interactive spiral navigation, deployed across 3 domains.

```
                    elevatealign.com
                   (SOVEREIGN SYSTEMS)
                    ┌──── SPIRAL ────┐
                    │                │
         stopdrinkingacid.com    eaucohub.com
            (WATER PILLAR)      (BUSINESS PILLAR)
                    │
              ┌─────┼─────┐
              │     │     │
            Gut  Fertility Athletic
              │     │     │
        Autoimmune Cancer Sustainability
```

**3 Domains:**
- **elevatealign.com** — hub. Interactive spiral. 4 pillars. The homebase.
- **stopdrinkingacid.com** — water pillar. Documentary-first funnel. Quiz. 6 branches. GHL backend.
- **eaucohub.com** — business/financial pillar. Ties into water site revenue.

---

## Build Order (Maddie's Own Prioritization)

> "focusing on the bones of structure/spiral and then making tiny one for water branch off & building that out first (and then plugging in business & finishing base/spiral down the line!)"

This roadmap follows her order exactly.

---

## ALPHA — Foundation

### A1. Repository + Tooling Setup
- [ ] Create project directory with clean structure
- [ ] Domain inventory: verify access to elevatealign.com, stopdrinkingacid.com, eaucohub.com
- [ ] Choose stack: static site (Astro/Next) for the spiral hub + GHL for the water funnel backend
- [ ] Set up deployment pipeline (Netlify or Vercel for static, GHL for forms/workflows)

### A2. Sovereign Systems Architecture Document
- [ ] Map all 4 pillars from Maddie's framework (she has these defined already)
- [ ] Define the spiral navigation data model: pillar → branches → pages
- [ ] Information architecture: what lives on which domain, what links where
- [ ] Content inventory: what exists (ChatGPT spec, current sites) vs what needs creation

---

## PHASE 1 — The Bones (elevatealign.com)

The spiral. The hub. The structure everything hangs on.

### 1.1 Spiral Navigation — Interactive UI
- [ ] Design the spiral component: center node + orbital pillar nodes
- [ ] Interaction model: hover reveals, click navigates, subtle motion (slow float)
- [ ] Responsive: works on mobile (collapses to list or simplified layout)
- [ ] Visual direction: soft neutrals + water tones, flowy lines, feminine but grounded, slight glow

### 1.2 Hub Landing Page
- [ ] Hero section: Maddie's identity statement + the spiral
- [ ] 4 pillar cards with icons/descriptions
- [ ] Each pillar clickable → routes to its domain or sub-page
- [ ] CTA: "Find where you want to start" or equivalent

### 1.3 Deploy elevatealign.com
- [ ] Static site deployed
- [ ] Spiral interactive and navigable
- [ ] Water pillar links to stopdrinkingacid.com
- [ ] Business pillar links to eaucohub.com (placeholder until Phase 3)

**Milestone: The spiral is live. Maddie can share elevatealign.com and people can navigate.**

---

## PHASE 2 — The Water Pillar (stopdrinkingacid.com)

The first spoke. This is where revenue lives.

### 2.1 Landing Page (Documentary-First)
- [ ] Hero: "Water changed everything for me." + subheadline
- [ ] Documentary embed (8-12 min, autoplay muted or click-to-play) — FRONT AND CENTER
- [ ] Post-video grounding section: "If you made it this far, you probably feel it too."
- [ ] Mini demo clip (1-2 min)
- [ ] Simple education: molecular hydrogen explainer
- [ ] Primary CTA → Quiz
- [ ] Secondary CTA → Spiral navigation (branch exploration)
- [ ] Final CTA: "If something in you is curious... follow that."

### 2.2 Quiz
- [ ] 5 questions (from ChatGPT spec — already written):
  1. What brought you here today? (6 options → primary routing)
  2. Have you heard of molecular hydrogen? (awareness level)
  3. What matters most to you? (motivation — choose up to 2)
  4. How ready are you? (intent level)
  5. Which feels most like you? (identity — optional)
- [ ] Results routing: Q1 answer → corresponding branch page
- [ ] Build in GHL or embed from GHL into the static site

### 2.3 Six Branch Pages
All follow identical structure (from ChatGPT spec):

**Structure per branch:**
1. Relatable hook (emotional entry)
2. Connection (what's happening in the body)
3. Where water fits (hydrogen benefits, grounded)
4. Relatable bridge (this doesn't have to be overwhelming)
5. Resources (videos/clips — expandable later)
6. CTA: "Start with your water" → product link

**The 6 branches:**
- [ ] Gut + Hormones (COPY DONE — from ChatGPT spec)
- [ ] Fertility (COPY DONE)
- [ ] Athletic Performance
- [ ] Inflammation / Autoimmune (COPY DONE)
- [ ] Cancer Support (special tone: soft, safe, non-invasive, no quiz digging)
- [ ] Sustainability / Savings (health + money + environment angle)

### 2.4 Mini Spiral for Water
- [ ] Smaller version of the elevatealign.com spiral
- [ ] Center = Water Hub
- [ ] 6 branches as orbital nodes
- [ ] Lives on stopdrinkingacid.com as an "Explore" section or dedicated page

### 2.5 GHL Backend
- [ ] **Tagging system:**
  - Primary tags (1 per person): Interest:Gut_Hormones, Interest:Fertility, etc.
  - Secondary tags: Level:Beginner/Aware/Ready, Goal:Heal_Symptoms/Energy/Longevity/Detox/Save_Money/Sustainability
  - Identity tags (optional): Type:Seeker/Optimizer/Overwhelmed
- [ ] **Workflow 1 — Quiz Router:**
  - Trigger: form submitted
  - Apply primary tag (Q1), secondary tags (Q3-Q5)
  - IF/ELSE branch → redirect to correct branch page
- [ ] **Workflow 2 — Follow-Up Sequence:**
  - Day 0: "Here's where I'd start based on you"
  - Day 2: Educational nugget (category-specific)
  - Day 4: Soft testimonial / story
  - Day 6: CTA → "If you feel called, here's the water I use"

### 2.6 Downline Duplication
- [ ] Document what changes per downline member (CTA links, optional intro video)
- [ ] Document what stays constant (quiz, tags, structure, branch pages)
- [ ] Template system: duplicate → swap links → deploy

**Milestone: stopdrinkingacid.com is a complete funnel. Documentary → Quiz → Branch → CTA. GHL tracks everything. Downline can duplicate.**

---

## PHASE 3 — Business Pillar (eaucohub.com)

### 3.1 Connect to Hub
- [ ] eaucohub.com links from elevatealign.com spiral
- [ ] Financial/business content lives here
- [ ] Ties into water site revenue reporting

### 3.2 Content Architecture
- [ ] Define what "financial pillar" means in Maddie's Sovereign Systems
- [ ] Business funnel structure (separate from water content funnel)
- [ ] Integration points with water site (revenue attribution, lead tracking)

**Milestone: All 3 domains connected. The hub-and-spoke is functional.**

---

## PHASE 4 — Polish + Expand

### 4.1 Remaining Branch Pages
- [ ] Athletic Performance (copy needed)
- [ ] Cancer Support (copy needed — special tone)
- [ ] Sustainability / Savings (copy needed)

### 4.2 Video Content
- [ ] Film documentary (8-12 min) — Maddie's story
- [ ] Film mini demo (1-2 min) — product demonstration
- [ ] Branch-specific video clips (can grow over time)
- [ ] Maddie mentioned: "can just film when/what it tells me"

### 4.3 Analytics + Tracking
- [ ] GHL reporting dashboard
- [ ] Quiz completion rates
- [ ] Branch page engagement
- [ ] Follow-up sequence conversion rates
- [ ] Downline performance tracking

### 4.4 Remaining Sovereign Systems Pillars
- [ ] Define pillars 3 and 4 (Maddie has these mapped)
- [ ] Add to elevatealign.com spiral as they're ready
- [ ] Each gets its own spoke when ready

---

## OMEGA — Completion Criteria

The system is complete when:

- [ ] elevatealign.com has a live interactive spiral with all 4 pillars navigable
- [ ] stopdrinkingacid.com converts visitors through documentary → quiz → branch → CTA
- [ ] eaucohub.com connects business/financial pillar to the hub
- [ ] GHL backend tags, routes, and follows up automatically
- [ ] At least 1 downline member has successfully duplicated the water funnel
- [ ] Maddie can add content (videos, branch pages) without developer intervention
- [ ] Analytics show conversion data from quiz to product

---

## There + Back Again

**There:** We build Maddie's Sovereign Systems from spec to deployed product.

**Back:** Every pattern discovered in this build feeds back into the studio:
- The spiral UI component becomes reusable (Rob's fitness hub, Dustin's music platform)
- The quiz → GHL routing pattern becomes a template
- The hub-and-spoke multi-domain architecture becomes a studio offering
- The downline duplication model maps to white-label SaaS

**Again:** The next client gets this faster because the tools exist.

---

## Tech Stack (Recommended)

| Layer | Tool | Why |
|-------|------|-----|
| Hub site (elevatealign.com) | Astro or Next.js | Static + interactive spiral component |
| Water funnel (stopdrinkingacid.com) | Same framework OR GHL pages | Depends on design control needed |
| Business funnel (eaucohub.com) | Same framework | Consistency |
| Backend / CRM | GHL (GoHighLevel) | She already uses it, has quiz + workflow infrastructure |
| Forms / Quiz | GHL embedded | Native integration with tags + routing |
| Hosting | Netlify or Vercel | Free tier, auto-deploy from git |
| Spiral component | p5.js, Three.js, or CSS/SVG animation | Interactive, floaty, glow aesthetic |
| Analytics | GHL + optional Plausible/PostHog | Privacy-respecting, funnel-aware |

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|-------------|
| Alpha (setup + architecture) | 2-3 days | Domain access confirmation |
| Phase 1 (spiral + hub) | 1 week | Maddie's 4 pillar definitions |
| Phase 2 (water funnel) | 1-2 weeks | Documentary video (can use placeholder) |
| Phase 3 (business pillar) | 3-5 days | Maddie's business content |
| Phase 4 (polish + expand) | Ongoing | Videos, remaining branch copy |

**MVP (Phases 1+2): 2-3 weeks to a live, functional system.**

---

## What Maddie Provided (Input Inventory)

- [x] ChatGPT "Novel Funnel Strategies" — full website architecture, quiz, GHL backend, copy
- [x] 3 complete branch page copy (gut, fertility, autoimmune)
- [x] Quiz questions + routing logic
- [x] GHL tagging + workflow spec
- [x] Landing page copy (ready to paste)
- [x] Downline duplication strategy
- [x] Sovereign Systems 4-pillar framework
- [x] 3 domains: elevatealign.com, stopdrinkingacid.com, eaucohub.com
- [x] Current site baseline (stopdrinkingacid.com)
- [x] Voice notes + conversation history
- [ ] Documentary video (to be filmed)
- [ ] Athletic, Cancer, Sustainability branch copy (to be written)
- [ ] Pillars 3-4 detailed definitions
