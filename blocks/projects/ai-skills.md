---
title: "Public repository of AI agent skills: specialized capabilities and workflows ..."
category: projects
tags: [agent, ai, blockchain, ci-cd, governance, knowledge-graph, orchestration, p5js, python, testing, three-js]
identity_positions: [creative-technologist, independent-engineer]
tracks: [job, fellowship]
related_projects: [agent-claude-smith]
tier: full
review_status: auto-generated
---

# Project: Public repository of AI agent skills: specialized capabilities and workflows ...

## One-Line
Public repository of AI agent skills: specialized capabilities and workflows across 12 categories

## Short (100 words)
Public repository of AI agent skills: specialized capabilities and workflows across 12 categories. A composable skill framework for AI agent orchestration -- 101 production-ready skill modules spanning creative, technical, enterprise, and governance domains, organized into a federated registry with multi-agent runtime support. Part of ORGAN-IV (Taxis).

## Full
**Product Overview:** `a-i--skills` is a structured repository of 101 AI agent skills -- self-contained instruction modules that teach large language models how to perform specialized tasks in a repeatable, composable way. Each skill is a directory containing a `SKILL.md` file with YAML frontmatter (metadata for discovery and activation) and Markdown content (the actual instructions an agent follows). The repository serves three distinct functions: 1. **Skill Library** -- A browsable catalog of 101 skills across 12 categories, from algorithmic art generation to security threat modeling, each with standardized metadata, optional helper scripts, reference documentation, and asset templates. 2. **Orchestration Infrastructure** -- Python tooling for skill validation, registry generation, health checking, and multi-agent bundle distribution. A built-in MCP (Model Context Protocol) server enables runtime skill discovery and planning. 3. **Federation Specification** -- A published protocol that allows third-party skill repositories to be discovered, validated, and consumed by any compatible agent, enabling a decentralized ecosystem of interoperable skill providers. The skills themselves range from beginner-level single-file instructions to advanced multi-file modules with executable scripts, OOXML schema references, and comprehensive troubleshooting guides. Four document-processing skills (DOCX, PDF, PPTX, XLSX) demonstrate production-grade complexity -- these are the same skills that power Claude's native document creation capabilities. ### Key Metrics | Dimension | Value | |-----------|-------| | Total skills | 101 (97 example + 4 document) | | Skill categories | 12 | | Multi-agent runtimes supported | 4 (Claude Code, Codex, Gemini CLI, Claude API) | | Total files | ~3,745 | | Repository size | ~5.2 MB | | Federation schema version | 1.1 (stable) | | Skill spec version | Current | ---

**Technical Architecture:** ### Directory Structure ``` a-i--skills/ ├── skills/ # 97 example skills, organized by category │ ├── creative/ # 13 skills (art, music, design, narrative) │ ├── data/ # 6 skills (pipelines, ML, analytics) │ ├── development/ # 26 skills (code quality, testing, infra) │ ├── documentation/ # 4 skills (READMEs, profiles, standards) │ ├── education/ # 4 skills (tutoring, curriculum, feedback) │ ├── integrations/ # 9 skills (MCP, OAuth, webhooks, SpecStory) │ ├── knowledge/ # 6 skills (graphs, architecture, research) │ ├──

## Links
- GitHub: https://github.com/organvm-iv-taxis/a-i--skills
- Organ: ORGAN-IV (Taxis) — Orchestration
