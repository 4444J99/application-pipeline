---
title: "Architecture governance toolkit"
category: projects
tags: [ai, api, ci-cd, database, docker, formal-systems, governance, python, recursive, symbolic, testing, typescript]
identity_positions: [independent-engineer, systems-artist]
tracks: [grant, fellowship]
related_projects: [recursive-engine]
tier: full
review_status: auto-generated
stats:
  languages: [python]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Architecture governance toolkit

## One-Line
Architecture governance toolkit — 7-script Python pipeline for risk scoring, drift detection, ownership analysis, and...

## Short (100 words)
Architecture governance toolkit — 7-script Python pipeline for risk scoring, drift detection, ownership analysis, and SBOM generation across any codebase. Part of ORGAN-I (Theoria).

## Full
**Problem Statement:** Software architecture degrades through three invisible mechanisms: 1. **Knowledge concentration** — critical subsystems understood by one person, creating single points of failure that only surface during attrition or incident response. The git history contains this information, but nobody reads `git log` to assess organizational risk. 2. **Dependency drift** — the actual import graph and service boundaries diverge from the documented or intended architecture, introducing coupling that contradicts design decisions. This coupling is invisible until someone tries to extract a service or change a shared module and discovers unexpected consumers. 3. **Security surface expansion** — vulnerability density in specific modules grows unchecked because scanning tools produce raw findings without contextual prioritization. A critical CVE in a dead-code module and a critical CVE in the authentication middleware are treated identically, diluting the signal. Traditional approaches treat these as separate concerns: bus-factor analysis in one tool, dependency graphing in another, vulnerability scanning in a third. The result is three dashboards that nobody synthesizes. This toolkit unifies all three into a single pipeline that produces a weighted, composite risk score per service or module — so you can see which parts of your codebase are simultaneously poorly understood, architecturally drifting, and accumulating vulnerabilities. The output is a prioritized remediation backlog, not a dashboard. It is designed to feed into sprint planning, not sit in a monitoring tab.

**Technical Architecture:** The toolkit follows a staged pipeline architecture where each script reads from upstream outputs or external tool results and writes structured JSON or YAML for the next stage. There is no shared state, no database, and no runtime coordination — each script is a standalone CLI tool that communicates through the filesystem. ``` ┌─────────────────┐ │ Target Codebase │ └────────┬────────┘ │ ┌──────────────┼──────────────┐ ▼ ▼ ▼ ┌────────────┐ ┌────────────┐ ┌────────────┐ │ Trivy JSON │ │Semgrep JSON│ │ git log │ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ ▼ ▼ ▼ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │parse_trivy.py│ │parse_semgrep │ │ownership_diff│ │ │ │ .py │ │ .py │ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │ │ │ ▼ ▼ │ ┌──────────────────────────┐ │ │ Security Findings JSON │ │ └────────────┬─────────────┘ │ │ │ ┌────────────┼─────────┐ │ │ │ │ │ ▼ ▼

## Links
- GitHub: https://github.com/organvm-i-theoria/reverse-engine-recursive-run
- Organ: ORGAN-I (Theoria) — Theory
