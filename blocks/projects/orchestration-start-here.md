---
title: "Central orchestration hub: registry, governance rules, 5 workflows"
category: projects
tags: [agent, ai, ci-cd, governance, orchestration, python, testing]
identity_positions: [creative-technologist, independent-engineer]
tracks: [job, grant, fellowship]
related_projects: [organvm-system]
tier: full
review_status: auto-generated
---

# Project: Central orchestration hub: registry, governance rules, 5 workflows

## One-Line
Central orchestration hub: registry, governance rules, 5 workflows, 3 Python scripts.

## Short (100 words)
Central orchestration hub: registry, governance rules, 5 workflows, 3 Python scripts. The central nervous system of the eight-organ system. The central nervous system of an eight-organ creative-institutional architecture. This repository is the single coordination point for ~80 repositories distributed across 8 GitHub organizations, enforcing governance rules, validating cross-organ dependencies, running monthly system-wide health audits, and automating the promotion pipeline that moves work from theoretical research through artistic expression into commercial products. Everything in this system — every README deployed, every dependency validated, every essay published — flows through the data structures and automation pipelines defined here. Part of ORGAN-IV (Taxis).

## Full
**Architectural Overview:** The organvm system organizes creative and institutional work into eight organs — discrete functional domains, each with its own GitHub organization, repository constellation, and operational mandate. The architecture draws from biological systems: organs are specialized but interdependent, and the system's health depends on coordination between them rather than any single organ's output. **Why eight organs?** The division mirrors the lifecycle of ideas in creative-institutional practice. Theoretical research (ORGAN-I) generates conceptual frameworks. Artistic practice (ORGAN-II) transforms those frameworks into experiential work. Commerce (ORGAN-III) packages that work for economic sustainability. The remaining five organs handle orchestration, public documentation, community, marketing, and meta-coordination — the connective tissue that makes the system function as a coherent whole rather than a collection of disconnected projects. **Why parallel launch?** Traditional project launches are sequential: build, then document, then ship. This system launched all eight organs simultaneously to demonstrate integrated systems thinking. A grant reviewer or hiring manager seeing one organ can follow dependency links to discover the entire architecture. The parallel approach also prevents the common failure mode of launching a single polished project while the supporting infrastructure remains invisible. **How this hub coordinates everything.** `orchestration-start-here` is the only repository that has read/write awareness of the entire system. It holds the canonical registry of all repositories, the governance rules that constrain how work flows between organs, and the automation workflows that enforce those constraints. When a developer opens a pull request in any organ, the `validate-dependencies` workflow fetches the registry from this hub to check for violations. When the monthly audit runs, it reads the registry and governance rules from this hub to produce a system-wide health report. The hub is the source of truth; individual organs are the locus of work. ``` ┌──────────────────────────────┐ │ orchestration-start-here │ │ │ │ registry.json │ │ governance-rules.json │ │ 5 workflows · 3 scripts │ └──────────┬───────────────────┘ │ ┌────────────────────┼────────────────────┐ │ │ │ ┌────────▼──────┐ ┌─────────▼────────┐ ┌────────▼──────┐ │ ORGAN-I │ │ ORGAN-II │ │ ORGAN-III │ │ Theory │──▶ Art │──▶ Commerce │ │ 18 repos │ │ 22 repos │ │ 21 repos │ └───────────────┘ └──────────────────┘ └───────────────┘ │ │ │ ┌────────▼──────┐

## Links
- GitHub: https://github.com/organvm-iv-taxis/orchestration-start-here
- Organ: ORGAN-IV (Taxis) — Orchestration
