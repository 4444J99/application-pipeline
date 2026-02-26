---
title: "Structured case studies documenting creative methodology"
category: projects
tags: [ai, creative-coding, generative-art, osc, testing, typescript, websocket]
identity_positions: [community-practitioner, creative-technologist, systems-artist]
tracks: [grant, residency, fellowship]
tier: full
review_status: auto-generated
stats:
  languages: [markdown]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: CRITICAL
---

# Project: Structured case studies documenting creative methodology

## One-Line
Structured case studies documenting creative methodology — process documentation, comparative analysis, and grant-rea...

## Short (100 words)
Structured case studies documenting creative methodology — process documentation, comparative analysis, and grant-ready excerpts. Artistic Purpose | Conceptual Approach | Technical Overview | Installation | Quick Start | Working Examples | Theory Implemented | Portfolio & Exhibition | Related Work | Contributing | License | Author & Contact Part of ORGAN-II (Poiesis).

## Full
**Technical Overview:** ### Case Study Structure Each case study follows a consistent structure, implemented as a collection of Markdown files with structured frontmatter: ``` case-studies-methodology/ ├── studies/ │ ├── 001-omni-dromenon-genesis/ │ │ ├── metadata.yaml # Structured metadata │ │ ├── 01-concept.md # Artistic question and initial vision │ │ ├── 02-context.md # Field positioning and precedents │ │ ├── 03-methodology.md # Technical and artistic methods │ │ ├── 04-prototyping.md # Iteration history and key decisions │ │ ├── 05-exhibition.md # Deployment, audience response, documentation │ │ ├── 06-reflection.md # Assessment and future directions │ │ ├── 07-comparisons.md # Comparative methodology analysis │ │ ├── appendices/ │ │ │ ├── technical-specs.md # Detailed technical documentation │ │ │ ├── audience-data.md # Quantitative audience response data │ │ │ └── media/ # Process photos, diagrams, sketches │ │ └── exports/ │ │ ├── grant-excerpt.md # Pre-formatted for grant applications │ │ └── conference-paper.md # Pre-formatted for academic submission │ ├── 002-consensus-landscape/ │ │ └── ... │ └── 003-recursive-choir/ │ └── ... ├── templates/ │ ├── case-study-template/ # Complete scaffolding for new studies │ │ ├── metadata.yaml │ │ ├── 01-concept.md │ │ ├── 02-context.md │ │ ├── 03-methodology.md │ │ ├── 04-prototyping.md │ │ ├── 05-exhibition.md │ │ ├── 06-reflection.md │ │ └── 07-comparisons.md │ ├── grant-excerpt-template.md # Template for grant-ready excerpts │ └── conference-abstract.md # Template for academic abstracts ├── methodology-framework/ │ ├── core-principles.md # The practice's methodological commitments │ ├── vocabulary.md # Defined terms and their meanings │ └── evolution.md # How the methodology has changed over time ├── indices/ │ ├── by-work.json # Index of studies by associated artwork │ ├── by-theme.json # Studies grouped by methodological theme │ ├── by-technology.json # Studies grouped by primary technology │ └── by-comparison.json # Index of comparative references ├── scripts/ │ ├── validate.ts # Schema validation for metadata │ ├── export-grant.ts # Generate grant-ready excerpts │ ├── export-conference.ts # Generate conference paper format │ ├── word-count.ts # Word count verification per section │ └── build-index.ts # Regenerate indices from metadata └── package.json ``` ### Metadata Schema Each case study carries structured metadata in YAML

## Links
- GitHub: https://github.com/organvm-ii-poiesis/case-studies-methodology
- Organ: ORGAN-II (Poiesis) — Art
