---
title: "Living portfolio aggregating all ORGAN-II generative art"
category: projects
tags: [ai, creative-coding, generative-art, portfolio, testing, typescript]
identity_positions: [community-practitioner, creative-technologist, systems-artist]
tracks: [grant, residency, fellowship]
tier: full
review_status: auto-generated
---

# Project: Living portfolio aggregating all ORGAN-II generative art

## One-Line
Living portfolio aggregating all ORGAN-II generative art, interactive installations, and AI-human collaborative works

## Short (100 words)
Living portfolio aggregating all ORGAN-II generative art, interactive installations, and AI-human collaborative works. Artistic Purpose | Conceptual Approach | Technical Overview | Installation | Quick Start | Working Examples | Theory Implemented | Portfolio & Exhibition | Related Work | Contributing | License | Author & Contact Part of ORGAN-II (Poiesis).

## Full
**Technical Overview:** ### Architecture The portfolio system is built as a static site generator with dynamic data sources. The core architecture separates content (artwork metadata, images, documentation) from presentation (templates, layouts, navigation logic) and from data (structured JSON records that drive both the site and API endpoints). ``` showcase-portfolio/ ├── content/ │ ├── works/ # Per-work directories │ │ ├── omni-dromenon-v1/ │ │ │ ├── metadata.json # Structured record │ │ │ ├── statement.md # Artist statement │ │ │ ├── process.md # Process documentation │ │ │ └── media/ # Images, video stills, audio │ │ └── ... │ ├── exhibitions/ # Exhibition records │ └── press/ # Press coverage links ├── src/ │ ├── generators/ # Site generation pipeline │ │ ├── gallery.ts # Visual gallery builder │ │ ├── chronology.ts # Timeline view │ │ ├── thematic.ts # Thematic grouping engine │ │ └── cv-export.ts # CV/grant format exporters │ ├── components/ # UI components │ │ ├── WorkCard.tsx # Individual work display │ │ ├── FilterBar.tsx # Medium/theme/year filters │ │ ├── GalleryGrid.tsx # Responsive grid layout │ │ └── ExhibitionTimeline.tsx │ ├── metadata/ │ │ ├── schema.ts # Zod schema for work records │ │ ├── dublin-core.ts # Dublin Core export │ │ └── cv-formatter.ts # Academic CV generator │ └── integrations/ │ ├── registry-sync.ts # Sync with registry-v2.json │ └── organ-bridge.ts # Cross-repo metadata pull ├── templates/ │ ├── grant-application.md # Grant-ready project list │ ├── exhibition-proposal.md # Venue proposal template │ └── academic-cv.md # Academic CV format ├── public/ # Static assets ├── tests/ └── package.json ``` ### Metadata Schema Each work record follows a structured schema validated with Zod: ```typescript import { z } from "zod"; const WorkRecord = z.object({ id: z.string().uuid(), title: z.string().min(1), subtitle: z.string().optional(), year: z.number().int().min(2018).max(2030), medium: z.enum([ "generative-visual", "interactive-installation", "real-time-performance", "ai-collaboration", "audio-synthesis", "motion-capture", "mixed-media", "net-art", "data-sculpture", ]), dimensions: z.string().optional(), duration: z.string().optional(), description: z.string().min(50), artistStatement: z.string().min(200), technicalMethod: z.string(), sourceRepo: z.string().url(), organ: z.literal("II"), relationships: z.array( z.object({ targetId: z.string().uuid(), type: z.enum(["predecessor", "variant", "component", "derivative", "response"]), }) ), exhibitions: z.array( z.object({ venue: z.string(), city: z.string(), country: z.string(), date: z.string(), type: z.enum(["solo", "group", "screening", "performance", "online"]),

## Links
- GitHub: https://github.com/organvm-ii-poiesis/showcase-portfolio
- Organ: ORGAN-II (Poiesis) — Art
