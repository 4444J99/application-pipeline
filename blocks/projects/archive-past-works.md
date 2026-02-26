---
title: "Archival infrastructure for completed artworks with Dublin Core-inspired meta..."
category: projects
tags: [ai, ci-cd, creative-coding, database, generative-art, osc, python, supercollider, testing, typescript, websocket]
identity_positions: [community-practitioner, creative-technologist, systems-artist]
tracks: [grant, residency, fellowship]
tier: full
review_status: auto-generated
stats:
  languages: [markdown]
  ci: true
  public: true
  promotion_status: CANDIDATE
  relevance: HIGH
---

# Project: Archival infrastructure for completed artworks with Dublin Core-inspired meta...

## One-Line
Archival infrastructure for completed artworks with Dublin Core-inspired metadata, chronological index, and provenanc...

## Short (100 words)
Archival infrastructure for completed artworks with Dublin Core-inspired metadata, chronological index, and provenance tracking. Artistic Purpose | Conceptual Approach | Technical Overview | Installation | Quick Start | Working Examples | Theory Implemented | Portfolio & Exhibition | Related Work | Contributing | License | Author & Contact Part of ORGAN-II (Poiesis).

## Full
**Technical Overview:** ### Architecture The archive is structured as a flat-file repository with structured metadata, designed for long-term durability over runtime convenience. No database server is required — the archive is fully functional as a Git repository. ``` archive-past-works/ ├── works/ │ ├── 2020/ │ │ └── early-consensus-experiments/ │ │ ├── manifest.json # Extended Dublin Core metadata │ │ ├── provenance.json # Chain of custody / exhibition history │ │ ├── dependencies.json # Runtime environment snapshot │ │ ├── README.md # Human-readable description │ │ ├── source/ # Source code snapshot (tagged version) │ │ ├── documentation/ # Process photos, sketches, notes │ │ ├── outputs/ # Representative outputs (images, video, audio) │ │ └── migration/ # Format migration notes and scripts │ ├── 2021/ │ ├── 2022/ │ ├── 2023/ │ ├── 2024/ │ └── 2025/ ├── schemas/ │ ├── manifest-v1.json # JSON Schema for manifest records │ ├── manifest-v2.json # Current schema version │ ├── provenance-v1.json # Provenance record schema │ └── dependencies-v1.json # Dependency snapshot schema ├── indices/ │ ├── chronological.json # All works by date │ ├── by-medium.json # Grouped by medium │ ├── by-theme.json # Grouped by thematic concern │ ├── by-technology.json # Grouped by primary technology │ └── relationships.json # Work-to-work relationship graph ├── scripts/ │ ├── validate.ts # Schema validation for all records │ ├── index-rebuild.ts # Regenerate indices from manifests │ ├── migrate-schema.ts # Migrate records to new schema versions │ ├── export-dublin-core.ts # Dublin Core XML export │ ├── export-csv.ts # Spreadsheet export for grant apps │ └── check-integrity.ts # Verify file checksums and completeness ├── templates/ │ ├── manifest-template.json # Blank manifest for new works │ ├── provenance-template.json # Blank provenance record │ └── archival-checklist.md # Checklist for archiving a completed work └── package.json ``` ### Manifest Schema (Extended Dublin Core) ```json { "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "ORGAN-II Archival Manifest v2", "type": "object", "required": ["id", "title", "creator", "date", "format", "description", "medium", "status"], "properties": { "id": { "type": "string", "format": "uuid" }, "title": { "type": "string", "minLength": 1 }, "subtitle": { "type": "string" }, "creator": { "type": "string", "default": "Anthony Padavano" }, "date": {

## Links
- GitHub: https://github.com/organvm-ii-poiesis/archive-past-works
- Organ: ORGAN-II (Poiesis) — Art
