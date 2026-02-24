# AI Engineer Handoff: Nexus Babel Alexandria — Demo for Prix Ars Electronica Digital Humanity

**Repo:** `~/Workspace/organvm-i-theoria/nexus--babel-alexandria`
**Deadline:** March 4, 2026 (video must be recorded by March 2)
**Goal:** Get the API running with a visible demo: ingest a text, show atomization, show 9-layer analysis, show remix output, show branch evolution — all recordable as a 3-minute screen recording

---

## Current State (Ground Truth)

### What Works (This Repo Is Much Further Along)
- **Full FastAPI app** with `create_app()` factory pattern, 25+ API routes under `/api/v1/`, health/metrics endpoints, 4 UI shell views (`/app/corpus`, `/app/hypergraph`, `/app/timeline`, `/app/governance`)
- **Ingestion pipeline** is production-grade — multimodal (text, PDF, image, audio), SHA256 dedup, conflict marker detection, raw payload storage, cross-modal linking. `IngestionService.ingest_batch()` handles full lifecycle.
- **5-level atomization** works — `atomize_text_rich()` produces glyph-seeds (with phoneme, historic forms, visual mutations, thematic tags), syllabic clusters, words, sentences, paragraphs. The `_create_atoms()` method stores them in the DB with projection ledger tracking.
- **Remix engine** is fully implemented — 4 strategies (interleave, thematic_blend, temporal_layer, glyph_collide), deterministic via seeded RNG, creates branch events
- **Branch evolution** works — `evolve_branch()` creates new branches with events, `get_timeline()` returns event history, `replay_branch()` deterministically replays, `compare_branches()` diffs two branches
- **Governance evaluation** works — dual-mode (PUBLIC/RAW), policy hits, redactions, audit trail
- **Rhetorical analysis** exists — `RhetoricalAnalyzer.analyze()` endpoint
- **9-layer analysis** exists — `AnalysisService.analyze()` with layer selection, sync/async/shadow execution modes, plugin profiles, confidence bundles
- **Auth system** works — API key based, 4 roles (viewer/operator/researcher/admin), mode enforcement (PUBLIC/RAW)
- **Hypergraph** — `HypergraphProjector` with Neo4j adapter and `LocalGraphCache` fallback (no Neo4j required)
- **Job queue** — async jobs with retry/backoff, cancel, status tracking
- **Seed corpus** — Gutenberg provisioning for canonical texts (Homer, Dante, etc.)
- **Tests** — 3 test suites: `test_mvp.py` (ingestion, analysis, evolution, governance), `test_wave2.py` (async jobs, plugins, metrics), `test_arc4n.py` (glyph-seeds, remix, seed corpus). Uses `conftest.py` with isolated SQLite + tmp_path fixtures.
- **Config** — pydantic-settings with `NEXUS_` prefix, SQLite default, all bootstrap keys in `.env.example`

### What Needs Work for Demo
1. **Verify all tests pass** — Last known state is "1 failing test (missing template)". Need to confirm and fix.
2. **UI shells are empty** — The `/app/{view}` routes serve `shell.html` but the Jinja2 templates may be minimal or missing. The demo video needs something visual.
3. **No simple demo script** — Need a way to ingest a text, analyze it, evolve it, and remix it in a scripted sequence that produces visible API output for screen recording
4. **Hypergraph visualization** — The spec mentions a "Semiotic Garden" metaphor but there's no visualization. For the video, need even a simple matplotlib/networkx graph of the atomized text.
5. **The analysis output needs to be visually interpretable** — Raw JSON from the API is fine for the recording but needs to show the 9 layers clearly

### Key Files
- `src/nexus_babel/main.py` — App factory, service wiring, lifespan handler
- `src/nexus_babel/api/routes.py` — All 25+ API routes (ingest, analyze, evolve, remix, governance, hypergraph, corpus, jobs, branches, auth)
- `src/nexus_babel/services/ingestion.py` — Multimodal ingestion with atomization
- `src/nexus_babel/services/analysis.py` — 9-layer analysis engine
- `src/nexus_babel/services/evolution.py` — Branch evolution and timeline
- `src/nexus_babel/services/remix.py` — 4-strategy remix engine
- `src/nexus_babel/services/rhetoric.py` — Rhetorical analysis
- `src/nexus_babel/services/governance.py` — Dual-mode governance evaluation
- `src/nexus_babel/services/text_utils.py` — Atomization functions (`atomize_text_rich`)
- `src/nexus_babel/services/glyph_data.py` — Glyph-seed metadata (phonemes, historic forms)
- `src/nexus_babel/services/hypergraph.py` — Graph projection (Neo4j or local cache)
- `src/nexus_babel/services/seed_corpus.py` — Gutenberg seed text provisioning
- `src/nexus_babel/config.py` — Settings (pydantic-settings)
- `src/nexus_babel/models.py` — SQLAlchemy models (Document, Atom, Branch, BranchEvent, AnalysisRun, Job, etc.)
- `src/nexus_babel/schemas.py` — Pydantic request/response models
- `tests/conftest.py` — Test fixtures (isolated app, client, corpus, auth headers)
- `.env.example` — Environment template with all NEXUS_ vars
- `corpus/` — Corpus storage directory
- `specs/` — SDD specifications for feature domains

---

## Task: Get Demo Running for Screen Recording

The goal is NOT to build new features. The API already works. The goal is to get a scripted demo sequence that produces visually compelling output for a 3-minute screen recording.

### Step 1: Fix venv and verify tests pass
```bash
cd ~/Workspace/organvm-i-theoria/nexus--babel-alexandria
source .venv/bin/activate  # or recreate: python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```
- If the "missing template" test fails, check for a Jinja2 template at `src/nexus_babel/frontend/templates/shell.html` — create a minimal one if missing
- All 3 test suites should pass: `test_mvp.py`, `test_wave2.py`, `test_arc4n.py`
- Copy `.env.example` to `.env` (defaults are fine — SQLite, no Neo4j)

### Step 2: Create a demo script
Create `scripts/demo_sequence.py` that runs the full demo flow via the API using `httpx` or `requests`. The script should:

1. **Start the server** (or assume it's running on `:8000`)
2. **Authenticate** as operator: `GET /api/v1/auth/whoami` with `X-Nexus-API-Key` header
3. **Provision a seed text**: `POST /api/v1/corpus/seed` with `{"title": "The Odyssey"}` (or any Gutenberg title)
4. **List documents** to confirm ingestion: `GET /api/v1/documents`
5. **Show atomization** — query the ingested document and print/display the atom breakdown:
   - Total glyph-seeds, syllables, words, sentences, paragraphs
   - Print a few example glyph-seeds with their metadata (phoneme, historic forms, thematic tags)
6. **Run 9-layer analysis**: `POST /api/v1/analyze` with selected layers (e.g., `["token", "morphology", "syntax", "semantics", "rhetoric", "semiotic"]`)
   - Print the layer results in a formatted table or structured output
7. **Evaluate governance**: `POST /api/v1/governance/evaluate` with a sample text — show the allow/redact decision
8. **Create a branch evolution**: `POST /api/v1/evolve/branch` — show the diff summary
9. **Get the timeline**: `GET /api/v1/branches/{branch_id}/timeline` — show the event sequence
10. **Run a remix**: `POST /api/v1/remix` with `strategy: "interleave"` (or `"glyph_collide"` — that's the most visually interesting), using two documents
    - For the second document, provision another seed text first (e.g., "Paradise Lost")
    - Print the remixed output — this is a visual highlight
11. **Compare branches**: `GET /api/v1/branches/{id1}/compare/{id2}` — show the diff

The script should print each step with clear headers and formatted output, like:
```
═══════════════════════════════════════════════════════
  STEP 1: SEED TEXT PROVISIONING — Homer's Odyssey
═══════════════════════════════════════════════════════
Document ID: abc-123
Atoms created: 4,521 glyph-seeds, 1,203 syllables, ...

═══════════════════════════════════════════════════════
  STEP 2: GLYPH-SEED INSPECTION
═══════════════════════════════════════════════════════
Character: μ (mu)
  Phoneme: /m/
  Historic forms: Phoenician 𐤌, Proto-Sinaitic ∞
  Thematic tags: [water, origin, breath]
...
```

### Step 3: Create a simple visualization
Create `scripts/visualize_atoms.py` that:
1. Reads atomization output from the API
2. Generates a matplotlib or networkx visualization:
   - **Option A**: A hierarchical tree showing document → paragraphs → sentences → words → glyph-seeds (first few levels)
   - **Option B**: A network graph showing atom relationships (glyph-seeds connected to their words, words to sentences)
   - **Option C**: A "glyph garden" — scatter plot of glyph-seeds colored by thematic tag, sized by frequency
3. Saves as PNG(s) for the submission images AND for showing in the video

Also consider a simple visualization of a remix output — side-by-side or color-coded showing which source each piece came from.

### Step 4: Ensure the UI shells work
The `/app/corpus`, `/app/hypergraph`, `/app/timeline`, `/app/governance` views serve `shell.html` from Jinja2 templates. Check if this template exists at `src/nexus_babel/frontend/templates/shell.html`:
- If it exists and renders something, great
- If it's missing or empty, create a minimal one that shows the view name and links to the API docs (`/docs`)
- Even better: create a simple HTML page that embeds the demo script output or shows live API calls in an iframe

### Step 5: Record the demo
Terminal recording approach (more authentic than polished UI for an art prize):
1. Start the server: `make dev` (or `uvicorn nexus_babel.main:app --reload`)
2. In another terminal, run the demo script: `python scripts/demo_sequence.py`
3. Record the terminal with the formatted output scrolling past — showing each step
4. Capture the matplotlib visualization windows as they appear
5. Optionally show the FastAPI docs at `/docs` to demonstrate the full API surface
6. Show the branch timeline and remix output as the climax

### What NOT to Do
- Don't add Neo4j — the `LocalGraphCache` fallback is fine for demo
- Don't implement real NLP/ML models for the 9-layer analysis — whatever the existing `AnalysisService` and `RhetoricalAnalyzer` produce is sufficient
- Don't refactor the codebase
- Don't add new API endpoints
- Don't worry about the Gutenberg download failing — if it does, just ingest a local `.txt` file from `corpus/` or `seeds/`
- Don't build a full frontend — terminal output + matplotlib is more honest and more interesting for Prix Ars

### Success Criteria
- `pytest -q` passes all tests (0 failures)
- `uvicorn nexus_babel.main:app` starts without errors
- The demo script runs end-to-end: provision → ingest → atomize → analyze → evolve → remix
- Glyph-seed output shows rich metadata (phoneme, historic forms, thematic tags)
- The remix output is visible and interesting (two canonical texts merged)
- At least one visualization (matplotlib PNG) shows the atomization structure
- The whole sequence runs in under 2 minutes (so it fits in a 3-min video with intro/outro)

---

## Architecture Diagram (for submission images)

Generate a clean architecture diagram showing:
```
┌─────────────────────────────────────────────────────────┐
│                   NEXUS BABEL ALEXANDRIA                  │
│               ARC4N Living Digital Canon                  │
├──────────────┬──────────────────────────┬───────────────┤
│  INGESTION   │      9-LAYER PLEXUS      │   REMIX       │
│              │                          │   ENGINE      │
│ text/pdf/    │ token → morphology →     │               │
│ image/audio  │ syntax → semantics →     │ interleave    │
│              │ pragmatics → discourse → │ thematic_blend│
│ atomize:     │ sociolinguistics →       │ temporal_layer│
│ glyph-seed → │ rhetoric → semiotic     │ glyph_collide │
│ syllable →   │                          │               │
│ word →       │                          │               │
│ sentence →   │                          │               │
│ paragraph    │                          │               │
├──────────────┼──────────────────────────┼───────────────┤
│  EVOLUTION   │      GOVERNANCE          │  HYPERGRAPH   │
│              │                          │               │
│ branch       │ PUBLIC mode (filtered)   │ Neo4j or      │
│ timeline     │ RAW mode (research)      │ local cache   │
│ replay       │ audit trail              │ integrity     │
│ compare      │ policy decisions         │ verification  │
└──────────────┴──────────────────────────┴───────────────┘
```

Use a diagramming tool (Mermaid, draw.io, or programmatic — Python `diagrams` library) to produce a clean PNG for the submission.
