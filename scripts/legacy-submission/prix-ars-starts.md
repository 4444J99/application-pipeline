# E5 Submission Script — Prix Ars Electronica + S+T+ARTS Prize 2026

**Created:** 2026-02-18
**Time to complete:** ~30 minutes
**Portal:** https://calls.ars.electronica.art/2026/prix/
**Deadline:** March 4, 2026
**Cost:** Free to submit
**Two-for-one:** Submitting to Prix Ars Electronica automatically qualifies you for S+T+ARTS Prize (EUR 20,000) consideration. One submission, two prizes.
**Combined potential:** EUR 10,000 (Prix Ars) + EUR 20,000 (S+T+ARTS) = EUR 30,000
**Benefits cliff:** International prize, lump-sum. SNAP-safe (excluded from countable income under BBCE).

---

> This is a step-by-step paste-and-submit guide. All answers are final. The submission portal is at calls.ars.electronica.art. You will need: project title, description, artist statement, URLs, and optionally images/video.

---

## Pre-flight (2 minutes)

- [ ] Open https://calls.ars.electronica.art/2026/prix/
- [ ] Create account or log in
- [ ] Choose category: **Digital Humanity** (primary recommendation) or **Interactive Art+** (secondary)
- [ ] Have portfolio URL and system hub URL ready

---

## Category Selection

**Recommended: Digital Humanity**

Why: This category explicitly seeks "artistic works that reflect the impact of digital technologies on society, culture, and our understanding of humanity." The eight-organ system is a living demonstration of how a single practitioner can build institutional-scale creative infrastructure using AI as a compositional instrument. The governance-as-art thesis IS a statement about digital humanity — what happens when technology, documentation, and creative practice converge.

**Alternative: Interactive Art+**

Why: If the portal defines Interactive Art+ as "artworks that involve the viewer/user in a dialogue," the public-process essay series and the open governance model create a participatory dimension — the system is built in public, documented transparently, and designed to be replicable.

---

## Project Title

```
The Eight-Organ Creative-Institutional System: Governance as Artistic Medium
```

---

## Short Description

**~100 words**

Copy everything between the lines:

---

The eight-organ system is a living creative infrastructure coordinating 100 repositories across 8 organizations through automated governance — treating the rules that coordinate creative production as an artistic medium in their own right. Built by a single practitioner using AI as a compositional instrument (the AI-conductor methodology), the system orchestrates theory, generative art, commercial products, governance, public process, community, and marketing under a unified architecture. 42 published essays document its construction in real time. The infrastructure IS the artwork: dependency validation, promotion state machines, and registry design are artistic decisions made visible through technology.

---

## Extended Description / Project Description

**~500 words**

Copy everything between the lines:

---

Over five years, I built a creative-institutional system that coordinates 100 code repositories across 8 GitHub organizations. Each organization represents an organ — a functional domain of creative practice: Theory (ORGAN-I), Art (ORGAN-II), Commerce (ORGAN-III), Governance (ORGAN-IV), Public Process (ORGAN-V), Community (ORGAN-VI), Marketing (ORGAN-VII), and Meta (ORGAN-VIII). The system is governed by a machine-readable registry that serves as single source of truth, automated dependency validation that enforces constitutional constraints (no circular dependencies, no back-edges in the flow from theory to art to commerce), a formal promotion state machine, and 11 GitHub Actions workflows that execute governance decisions autonomously.

This is not a software project documented as art. It is an argument — expressed through infrastructure — that governance and art are not separate categories. The choice of how work flows between organs is as much an artistic decision as any visual or sonic output the system produces. The dependency rule (theory feeds art, art feeds commerce, never the reverse) is a compositional constraint analogous to serialism or Eno's oblique strategies: it forces each organ to be genuinely self-sufficient, producing work that is stranger and more honest than anything generated when everything can depend on everything else.

The system was built using what I call the AI-conductor methodology: AI tools generate volume (code, prose, configurations), while the human practitioner directs strategy, ensures accuracy, and makes editorial decisions. This is analogous to Brian Wilson directing session musicians or Terrence Malick assembling The Tree of Life from hundreds of hours of footage. The creative intelligence lives in the architecture and the editorial judgment, not in any individual output. 42 published essays (~134,000 words) document this methodology transparently, treating the process of creation as a first-class deliverable.

The documentation corpus is not supplementary to the artwork — it IS the artwork. The 42 essays published via ORGAN-V (Public Process) constitute a real-time record of artistic decision-making at institutional scale: why certain governance rules were adopted, how the dependency architecture was designed, what failed, and what the failures revealed. This is building-in-public as artistic practice, where the opacity typically surrounding creative production is replaced by radical transparency.

The system operates autonomously: daily health checks monitor all repositories, automated audits generate monthly reports, essays are distributed via POSSE (Publish on Own Site, Syndicate Elsewhere) to Mastodon, Discord, and RSS. The system doesn't need constant human intervention to sustain itself — the governance rules hold because they are structural, not procedural.

Key metrics: 100 repositories, 8 organizations, 82+ CI/CD pipelines, 42 published essays, ~404,000 words of public documentation, 33 named development sprints, and a formal registry tracking every component's status, dependencies, and promotion state. All of this was built by a single practitioner.

---

## Artist Statement / Bio

**~200 words**

Copy everything between the lines:

---

I build environments for creative work to grow in. My practice treats governance — the rules, constraints, and architectures that coordinate creative production — as an artistic medium.

I applied to roughly 3,000 jobs before building this system. I lost every time to people who actually wanted those jobs. What I wanted was to build the thing that IS what I am: a documented creative infrastructure that makes its own logic visible. The eight-organ system is that infrastructure.

My reference points are Brian Eno (the studio as compositional instrument), Trent Reznor and Prince (solo production because collaboration at the required intensity was unavailable), Brian Wilson (the edit as the creative act), and Terrence Malick (the creature formed in the assembly). These describe a production method I recognize as my own: design the environment, generate the material, assemble in the edit.

MFA in Creative Writing (Florida Atlantic University, 2015–2018). 11 years teaching at 8+ institutions, 100+ courses, 2,000+ students. Currently building at the intersection of governance, generative art, and AI-augmented production. Based in New York City.

Portfolio: https://4444j99.github.io/portfolio/
System Hub: https://github.com/meta-organvm
Public Process: https://organvm-v-logos.github.io/public-process/

---

## Technical Description (if form asks)

**~150 words**

---

The system uses GitHub as its primary substrate — 8 GitHub organizations containing 100 repositories, each tracked by a machine-readable JSON registry (registry-v2.json). Governance is enforced by 11 GitHub Actions workflows: dependency validation on every push, monthly organ audits, automated content distribution (POSSE to Mastodon + Discord + RSS via GitHub Actions), and a promotion pipeline that manages repository state transitions. 82+ CI/CD pipelines run tests across the system. The essay series is published via Jekyll on GitHub Pages with Atom feed syndication.

The dependency architecture enforces a strict directed acyclic graph: I→II→III (theory→art→commerce). Cross-organ dependencies are validated automatically — no circular dependencies, no back-edges. The registry tracks implementation status, promotion tier, CI/CD status, and inter-repository dependencies for all 97 components.

All infrastructure is open-source and publicly accessible.

---

## Links to Submit

| Field | URL |
|-------|-----|
| Project URL / Portfolio | `https://4444j99.github.io/portfolio/` |
| Project Documentation | `https://github.com/meta-organvm` |
| Public Process (Essays) | `https://organvm-v-logos.github.io/public-process/` |
| Central Registry | `https://github.com/meta-organvm/organvm-corpvs-testamentvm` |
| Flagship: Generative Art | `https://github.com/organvm-ii-poiesis/metasystem-master` |
| Flagship: AI Orchestration | `https://github.com/organvm-iv-taxis/agentic-titan` |
| Video (if required) | Record a 2-minute screen walkthrough of the GitHub organizations + portfolio site |

---

## S+T+ARTS Prize — Additional Notes

If the portal has a separate S+T+ARTS section or asks about the science-technology-arts nexus:

**Angle:** The eight-organ system demonstrates that creative governance infrastructure IS science+technology+arts integration. The registry is a data structure (science), the automation is technology, and the governance rules are artistic decisions. The AI-conductor methodology contributes a reusable production model at the intersection of all three domains.

**One-liner for S+T+ARTS:** "A single-practitioner creative-institutional system that treats governance as an artistic medium, built with AI as a compositional instrument, demonstrating that infrastructure and art are not separate categories."

---

## Post-Submission Checklist

- [ ] Screenshot the confirmation page
- [ ] Record submission date in `docs/applications/04-application-tracker.md`
- [ ] Update `docs/operations/rolling-todo.md` — mark Prix Ars + S+T+ARTS as SUBMITTED
- [ ] Note: Prix Ars results announced at Ars Electronica Festival (typically September)

---

## If Something Goes Wrong

- **Word/character limits tighter than expected:** Cut the extended description from 500 to 300 words by removing the documentation-as-artwork paragraph (4th paragraph) and the autonomy paragraph (5th paragraph). The first three paragraphs carry the core argument.
- **Portal asks for video:** Record a 2-minute screen recording walking through: (1) meta-organvm GitHub org overview, (2) portfolio site with generative layer, (3) public-process essay index. Use QuickTime or OBS. Upload directly.
- **Portal asks for images:** Screenshot: (1) the portfolio site, (2) the GitHub org page showing all repos, (3) the registry file, (4) a CI/CD pipeline output. Four images cover the visual argument.
- **Category is unclear or has changed:** Choose whichever category mentions "digital society," "AI," or "systems." Avoid pure "Computer Animation" or "Sound Art" unless there's no better fit.
- **Form asks about collaboration:** Emphasize: single-practitioner system using AI as compositional instrument. Not a team project — the solo-production method IS the point.
