---
title: "Ontological knowledge management system applying Dante's epistemological fram..."
category: projects
tags: [ai, database, docker, fastapi, formal-systems, knowledge-graph, microservices, nlp, python, recursive, symbolic, testing]
identity_positions: [independent-engineer, systems-artist]
tracks: [grant, fellowship]
tier: full
review_status: auto-generated
stats:
  languages: [python]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Ontological knowledge management system applying Dante's epistemological fram...

## One-Line
Ontological knowledge management system applying Dante's epistemological framework to narrative universe modeling.

## Short (100 words)
Ontological knowledge management system applying Dante's epistemological framework to narrative universe modeling. Graph DB + semantic search for complex fictional universes. Part of ORGAN-I (Theoria).

## Full
**2. Solution Overview:** The Scalable Lore Expert addresses a specific problem: fictional universes of sufficient complexity (One Piece's 1,100+ chapters, Final Fantasy's 16 mainline entries plus spinoffs, the Marvel Cinematic Universe's 30+ films) generate knowledge corpora that exceed any individual's ability to hold in memory. Existing solutions — fan wikis, episode guides, Reddit threads — are flat, unsearchable by meaning, and indifferent to spoiler boundaries. ### Three-Layer Capabilities **Layer 1 (Inferno) — Storage and Provenance:** - Ingest structured and unstructured narrative sources - Maintain per-fact provenance records with confidence scores - Support multiple canonical universes (mainline canon, extended canon, non-canon) with explicit hierarchy - Store raw text alongside structured extractions for auditability **Layer 2 (Purgatorio) — Transformation and Resolution:** - Entity resolution across aliases, titles, and naming conventions - Relationship extraction: character-to-character, character-to-event, event-to-location, artifact-to-theme - Temporal ordering with support for non-linear narratives (flashbacks, parallel timelines) - Spoiler classification at episode/volume/chapter granularity - Conflict resolution with source-priority rules (primary canon overrides secondary) **Layer 3 (Paradiso) — Semantic Understanding:** - Natural-language query interface ("What happened to Zoro between Thriller Bark and Sabaody?") - Thematic clustering and cross-arc pattern detection - Cross-narrative comparative analysis - Progressive disclosure with configurable spoiler boundaries - Confidence-weighted results with citation chains back to primary sources ### Multiverse Logic The system supports multiple canonical universes simultaneously. Each universe (Final Fantasy VII, One Piece, Elden Ring) is a self-contained graph with its own entity namespace, timeline, and spoiler boundaries. Universes can be linked through explicit cross-reference edges (`is_thematic_parallel_to`, `is_adaptation_of`, `shares_archetype_with`) without collapsing their internal consistency. Canon hierarchy within a single universe distinguishes primary sources (the manga itself) from secondary sources (databooks, interviews) from tertiary sources (fan translations, wiki summaries), and query results respect this hierarchy by default. ---

**3. Technical Architecture:** ### Microservices Overview ``` ┌─────────────────────────────────────────────────────────────────────────┐ │ API Gateway │ │ (FastAPI / auth / rate limiting / routing) │ ├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤ │ │ │ │ │ │ │ │ Data │ Graph │ Semantic │ Query │ Spoiler │ Citation │ │ Ingest │ Database │ Search │ Orchestr │ Filter │ Tracker │ │ Service │ Service │ Service │ Service │ Service

## Links
- GitHub: https://github.com/organvm-i-theoria/scalable-lore-expert
- Organ: ORGAN-I (Theoria) — Theory
