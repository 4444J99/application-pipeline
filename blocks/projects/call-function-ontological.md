---
title: "Ontological function-calling framework"
category: projects
tags: [ai, ci-cd, formal-systems, nlp, python, react, recursive, symbolic, testing, typescript]
identity_positions: [independent-engineer, systems-artist]
tracks: [grant, fellowship]
related_projects: [organon-noumenon]
tier: full
review_status: auto-generated
---

# Project: Ontological function-calling framework

## One-Line
Ontological function-calling framework — 12-concept philosophical architecture for grounded AI tool use via Heidegger...

## Short (100 words)
Ontological function-calling framework — 12-concept philosophical architecture for grounded AI tool use via Heideggerian Dasein, Aristotelian four causes, and Peircean semiotics. A universal, self-documenting naming convention for files across codebases, media archives, and knowledge systems. Every file follows a single canonical pattern: {Layer}.{Role}.{Domain}.{Extension}. Four layers — core, interface, logic, application — map to symbolic categories that make filenames autological: a file's name tells you what it is, where it lives in the architecture, and why it exists. This is not a style guide. It is an ontological claim: naming is architecture.

## Full
**Technical Architecture:** The repository contains 82 files (~60KB) organized into six functional areas: ``` call-function--ontological/ ├── standards/ │ ├── FUNCTIONcalled_Spec_v1.0.md # Formal specification (9 sections) │ ├── FUNCTIONcalled_Metadata_Sidecar.v1.1.schema.json # JSON Schema (Draft 2020-12) │ ├── registry.schema.json # Registry output schema │ └── registry.example.json # Example registry structure ├── tools/ │ ├── validate_naming.py # Regex-based filename validator │ ├── validate_meta.py # JSON Schema metadata validator │ ├── registry-builder.py # Registry builder (SHA256 hashes) │ ├── llm-prompt.md # LLM integration templates │ ├── semgrep/functioncalled.yaml # 4 semgrep rules for header comments │ ├── test_validate_naming.py # 60+ naming validation tests │ └── test_validate_meta.py # 25+ metadata validation tests ├── core/ # Layer templates: C, C++, Rust, Go │ ├── template.{c,cpp,rs,go} │ └── template.{c,cpp,rs,go}.meta.json ├── interface/ # Layer templates: HTML, CSS, JS, PHP │ ├── template.{html,css,js,php} │ └── template.{html,css,js,php}.meta.json ├── logic/ # Layer templates: Python, Lua, Ruby │ ├── template.{py,lua,rb} │ └── template.{py,lua,rb}.meta.json ├── application/ # Layer templates: Java, Obj-C, Swift │ ├── template.{java,m,swift} │ └── template.{java,m,swift}.meta.json ├── examples/ # Fully annotated reference examples │ ├── interface.portal.entry.html # HTML portal with sidecar │ ├── interface.icon.brand.svg # SVG asset with sidecar │ ├── logic.agent.analysis.py # Python agent with sidecar │ └── logic.audio.notification.txt # Audio reference with sidecar ├── registry/ │ └── registry.json # 18 tracked resources with SHA256 hashes ├── docs/ │ ├── quickstart.md # 5-minute onboarding │ ├── layers.md # Layer taxonomy + Mermaid diagrams │ ├── rosetta-codex.md # 14 file types x 4 worldviews │ ├── migration.md # 3 adoption strategies │ ├── comparison.md # vs BEM, Atomic, Clean, DDD │ └── case-study.md # Applied naming walkthrough ├── .github/workflows/validate.yml # CI pipeline (push + PR) ├── Makefile # 7 make targets for validation ├── CHANGELOG.md # Semantic versioning history ├── CONTRIBUTING.md # Contribution guidelines └── CODE_OF_CONDUCT.md # Community standards ``` Each of the four layer directories contains starter template files with header comments describing the role for that language, paired with `.meta.json` sidecar files that provide machine-readable metadata. The `examples/` directory contains fully annotated reference implementations showing the convention applied to real file types — an HTML portal, an SVG brand icon, a Python analysis

## Links
- GitHub: https://github.com/organvm-i-theoria/call-function--ontological
- Organ: ORGAN-I (Theoria) — Theory
