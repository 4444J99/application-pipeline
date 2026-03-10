# Plan: Create GitHub Issues for Prix Ars Electronica Submission Gaps

## Context

Prix Ars Electronica deadline is **March 4, 2026 (8 days)**. We're submitting to two categories:
- **Interactive Art+** → AI Council Coliseum (`organvm-ii-poiesis/a-i-council--coliseum`)
- **Digital Humanity** → Nexus Babel Alexandria (`organvm-i-theoria/nexus--babel-alexandria`)

Pipeline YAML, project blocks, 2,000-char descriptions, and engineer handoff prompts are DONE. What remains is the actual engineering/production work to make both projects demo-ready for the required 3-minute video + images. We need GitHub issues to track every remaining task.

## What's Already Done (no issues needed)
- Pipeline entries: `prix-ars-electronica.yaml`, `prix-ars-digital-humanity.yaml` — both pass preflight
- Project blocks: `blocks/projects/ai-council-coliseum.md`, `blocks/projects/nexus-babel-alexandria.md`
- 2,000-char descriptions: `pipeline/drafts/prix-ars-interactive-art.md`, `pipeline/drafts/prix-ars-digital-humanity.md`
- Engineer handoff prompts: `pipeline/drafts/prix-ars-coliseum-engineer-prompt.md`, `pipeline/drafts/prix-ars-nba-engineer-prompt.md`
- Profile ID mapping in `pipeline_lib.py`

---

## Issues to Create

### Repo: `organvm-ii-poiesis/a-i-council--coliseum` (6 issues)

**Issue 1: Fix stale venv and verify backend starts**
- Labels: `bug`, `prix-ars-2026`
- `.venv/` has broken paths from repo move
- Recreate venv, install deps from `backend/requirements-test.txt`
- Set up `.env` from `.env.example` with real LLM API key and SQLite
- Verify `python -m pytest -q backend/tests` passes (22+ tests)
- AC: `uvicorn backend.main:app` starts without errors

**Issue 2: Create demo seed script with philosophical agents**
- Labels: `enhancement`, `prix-ars-2026`
- Create `backend/scripts/seed_demo.py`
- Seed 4 agents: Socrates (DEBATER, dialectical), Machiavelli (DEBATER, realist), Ada Lovelace (ANALYST, mathematical), The Moderator (MODERATOR, theatrical)
- Seed 1 initial debate event
- Creates DB tables via `Base.metadata.create_all`
- Runnable as `python -m backend.scripts.seed_demo`
- AC: After running, `GET /api/agents` returns 4 agents

**Issue 3: Wire autonomous demo loop for continuous debate + combat**
- Labels: `enhancement`, `prix-ars-2026`
- Reduce `AutonomousArenaWorker` interval from 120s to 15-20s
- Ensure it triggers `orchestrator.start_battle(topic)` with seeded event
- Verify orchestrator `_tick()` auto-progresses battle turns via `_run_battle_turns()`
- Verify combat events broadcast through WebSocket as `combat_update` messages
- AC: Backend runs continuously, debates start within 30 seconds, battles auto-progress

**Issue 4: Fix frontend WebSocket handling and wire BattleScene**
- Labels: `bug`, `prix-ars-2026`
- `page.tsx` only handles `agent_message` WS type — add `combat_update` handling
- Wire `BattleScene` component into main page layout (currently not rendered)
- Connect `isAttacking` prop in `Arena3D.tsx` to live combat data (hardcoded `false`)
- Add damage flash effect on defender avatar
- Fix missing font `/fonts/Geist-Black.ttf` in `public/` (or remove the reference)
- AC: Combat moves visible in BattleScene HP bars + combat log, 3D arena shows attack animations

**Issue 5: Visual polish for demo video recording**
- Labels: `enhancement`, `prix-ars-2026`
- Add pulsing border/glow during active combat
- Ensure EventTicker shows debate topic
- Verify ChatStream shows agent debate messages
- Agent avatars: improve from box geometry or add role-based visual distinction
- AC: 5-minute continuous demo loop looks visually compelling for screen recording

**Issue 6: Record 3-minute demo video and capture screenshots**
- Labels: `documentation`, `prix-ars-2026`
- Record: arena spin-up → agents appear → debate unfolds → combat starts → HP bars animate → battle concludes
- Capture screenshots: Arena3D, BattleScene mid-combat, VotingPanel, full layout
- Export video as MP4 for submission portal
- AC: 3-min video file and 3-4 screenshot PNGs ready for upload

### Repo: `organvm-i-theoria/nexus--babel-alexandria` (5 issues)

**Issue 7: Fix failing test and verify all suites pass**
- Labels: `bug`, `prix-ars-2026`
- Last known: 1 failing test (missing Jinja2 template `shell.html`)
- Check/create `src/nexus_babel/frontend/templates/shell.html`
- Verify all 3 suites: `test_mvp.py`, `test_wave2.py`, `test_arc4n.py`
- AC: `pytest -q` passes with 0 failures

**Issue 8: Create scripted demo sequence for video recording**
- Labels: `enhancement`, `prix-ars-2026`
- Create `scripts/demo_sequence.py` using httpx against running API
- Flow: authenticate → provision seed text (Odyssey) → show atomization breakdown → inspect glyph-seeds with rich metadata → run 9-layer analysis → governance evaluation → branch evolution → provision second text (Paradise Lost) → remix with glyph_collide strategy → compare branches
- Print each step with formatted headers and structured output
- AC: Script runs end-to-end in under 2 minutes, output is clear and visually readable in terminal

**Issue 9: Create atomization visualization for submission images**
- Labels: `enhancement`, `prix-ars-2026`
- Create `scripts/visualize_atoms.py`
- Produce matplotlib/networkx visualization: hierarchical tree (document → paragraphs → sentences → words → glyph-seeds) or glyph garden scatter plot colored by thematic tag
- Save as PNG files for submission images and video capture
- AC: At least 1 clean PNG showing atomization structure

**Issue 10: Generate architecture diagram for submission**
- Labels: `documentation`, `prix-ars-2026`
- Create a clean 9-layer plexus architecture diagram (Mermaid, draw.io, or Python `diagrams`)
- Show: ingestion → 9-layer plexus → remix engine, evolution → governance → hypergraph
- Export as PNG for submission portal
- AC: Clean architecture diagram PNG ready for upload

**Issue 11: Record 3-minute demo video**
- Labels: `documentation`, `prix-ars-2026`
- Record terminal: `uvicorn` startup → demo_sequence.py running → formatted output scrolling → matplotlib windows appearing
- Show FastAPI `/docs` to demonstrate API surface
- Show branch timeline + remix output as climax
- Export as MP4
- AC: 3-min video file ready for upload

### Repo: `4444J99/application-pipeline` (2 issues)

**Issue 12: Prepare portrait photo + bio for Prix Ars submission**
- Labels: `prix-ars-2026`
- Prix Ars requires portrait photo and artist bio
- Bio content exists in `targets/profiles/prix-ars.json` (short/medium/long)
- Need actual portrait photo file
- AC: Portrait JPG and bio text ready for portal

**Issue 13: Submit both Prix Ars categories and record in pipeline**
- Labels: `prix-ars-2026`
- Depends on: all Coliseum issues, all NBA issues, portrait/bio
- Submit Interactive Art+ (Coliseum) via portal
- Submit Digital Humanity (NBA) via portal
- Run `python scripts/submit.py --target prix-ars-electronica --record`
- Run `python scripts/submit.py --target prix-ars-digital-humanity --record`
- AC: Both entries status = `submitted`, conversion-log.yaml updated

---

## Execution

Use `gh issue create` for each issue. All issues get the `prix-ars-2026` label. Include the engineer handoff prompt content as body context where relevant. Cross-reference sister issues in the body.

### Verification
After creating all issues:
```bash
gh issue list --repo organvm-ii-poiesis/a-i-council--coliseum --label prix-ars-2026
gh issue list --repo organvm-i-theoria/nexus--babel-alexandria --label prix-ars-2026
gh issue list --repo 4444J99/application-pipeline --label prix-ars-2026
```
Should show 6 + 5 + 2 = 13 issues total.
