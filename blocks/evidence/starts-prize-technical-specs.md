# Evidence: Technical Specifications (S+T+ARTS Prize)

## Software Stack by Organ

**ORGAN-I (Theoria):** Python 3.11+, Pydantic data models, custom DSL (RE:GE invocation syntax with 22 organ handlers), 1,254 automated tests at 85% coverage. CLI interface for symbolic computation.

**ORGAN-II (Poiesis):**
- *Omni-Dromenon Engine:* TypeScript pnpm monorepo — Express/Socket.io (WebSocket core), React 18 (performer + audience interfaces), OSC bridge to SuperCollider/Max/MSP, Docker Compose infrastructure. 60 tests, P95 latency <2ms, designed for 1,000+ concurrent audience connections.
- *Alchemical Synthesizer (Brahma Meta-Rack):* 66 SuperCollider files (~20K LOC), 33 web interface files (p5.js Visual Cortex), Pure Data canvas patches, 3-port OSC topology binding SC/PD/web into a real-time feedback loop.
- *MET4MORFOSES:* Next.js 16, React Three Fiber (3D node map), TypeScript, content pipeline from PDF sources, generative audio (GlitchSynth), 14 test files.
- *KRYPTO-VELAMEN:* 8 microservices (Next.js 14, FastAPI, Django, Neo4j), knowledge graph with 106 entities and 118 relations, AI agent swarm architecture, pseudonym management and risk-calibrated privacy.

**ORGAN-IV (Taxis):** Python + Redis + FastAPI (Agentic Titan: 2,000 tests, 9 topology patterns, 22 agent archetypes), TypeScript + Anthropic SDK (agent--claude-smith).

**META-ORGANVM:** FastAPI + HTMX (system dashboard with brutalist CMYK design), Python CLI (organvm-engine: 7 module groups — registry, governance, seed, metrics, dispatch, git management, promotion state machine).

## Exhibition Configuration

**Minimum (1 station):** Laptop + external monitor + internet connection. System dashboard with live GitHub queries, portfolio generative art, public process essays. Footprint: 1m x 1m table.

**Recommended (3-screen + audio):** Screen 1: Omni-Dromenon audience interface (interactive). Screen 2: Brahma Visual Cortex (p5.js organism visualization with live SuperCollider audio). Screen 3: System governance dashboard (registry browser, dependency graph, health metrics). Audio: SuperCollider generative synthesis. Footprint: 3m x 2m.

**Full installation (participatory):** 4m x 6m space. Three screens as above. Audio monitors for Brahma synthesis. Audience mobile devices for Omni-Dromenon participatory performance. Dedicated WiFi AP. Optional: projection of MET4MORFOSES 3D node map or KRYPTO-VELAMEN knowledge atlas as fourth visual layer.

## Hardware Requirements
- Screens: 1920x1080 minimum, 4K recommended for Retina-quality visualization
- Audio: Stereo monitors minimum, 4-channel recommended for Brahma spatialization
- Network: Dedicated WiFi AP for audience participation (802.11ac, 100+ concurrent clients)
- Compute: Apple Silicon or equivalent (M1+ for SuperCollider real-time synthesis)
