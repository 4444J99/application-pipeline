---
title: "Audit tool for cognitive systems and organizational coherence"
category: projects
tags: [ai, api, ci-cd, database, fastapi, formal-systems, knowledge-graph, python, recursive, symbolic, testing]
identity_positions: [independent-engineer, systems-artist]
tracks: [grant, fellowship]
related_projects: [recursive-engine]
tier: full
review_status: auto-generated
stats:
  languages: [python]
  ci: true
  public: false
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Audit tool for cognitive systems and organizational coherence

## One-Line
Audit tool for cognitive systems and organizational coherence

## Short (100 words)
Audit tool for cognitive systems and organizational coherence. A systematic excavation engine that audits every layer of a creator's digital footprint — archives, AI conversations, personal repositories, organisation repositories, and web bookmarks — and produces a unified inventory, a knowledge graph of relationships, and a prioritised triage report that transforms scattered creative history into an organised system foundation. Part of ORGAN-I (Theoria).

## Full
**Problem Statement:** Any sufficiently long creative practice accumulates entropy. Years of work produce scattered artefacts across incompatible systems: hundreds of AI conversation threads (ChatGPT, Claude, Gemini) containing architectural decisions that were never extracted; personal GitHub repositories that are really evaluation forks of external tools, not original work, but mixed indistinguishably with originals; cloud storage directories (iCloud, Dropbox, network drives) containing duplicated files across multiple locations with no canonical version; browser bookmark collections numbering in the thousands with no topical organisation; and organisation repositories that may be active, stale, or silently abandoned. The fundamental problem is not storage — storage is cheap. The problem is **epistemic**: you cannot govern what you cannot see. Before the eight-organ system could be designed, before repositories could be assigned to organisations, before any architectural decision could be made, someone had to answer the question: *what do we actually have?* Manual inventory is not viable at scale. A human scanning 85 repositories, thousands of archived files, and hundreds of AI conversations would take weeks and produce an incomplete, error-prone result. The Cognitive Archaeology Tribunal exists to answer this question programmatically, comprehensively, and repeatedly. It scans every layer of a creator's digital footprint — from local filesystem archives through GitHub API endpoints — and produces machine-readable outputs (JSON inventories, knowledge graphs, triage reports) that downstream tools and human reviewers can act on. This is not a backup tool or a file manager. It is a **pre-governance audit system** — the epistemological foundation that makes governance possible. Within ORGAN-I (Theoria), it embodies the principle that theory begins with accurate observation. You cannot theorise about a system you have not first measured. ---

**Core Concepts:** ### Multi-Layer Auditing The tribunal models a creator's digital footprint as four discrete layers, each with its own scanning module, data model, and triage logic: | Layer | Domain | Scanner Module | Key Metric | |-------|--------|---------------|------------| | **Layer 0** | Filesystem archives (iCloud, Dropbox, local/network drives) | `ArchiveScanner` | Files counted, duplicates found, space savings | | **Layer 1** | AI conversation history (ChatGPT, Claude, generic JSON) | `AIContextAggregator` | Conversations loaded, messages parsed, topics extracted |

## Links
- GitHub: https://github.com/organvm-i-theoria/cognitive-archaelogy-tribunal
- Organ: ORGAN-I (Theoria) — Theory
