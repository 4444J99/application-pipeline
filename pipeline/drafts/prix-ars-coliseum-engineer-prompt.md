# AI Engineer Handoff: AI Council Coliseum — Demo Loop for Prix Ars Electronica

**Repo:** `~/Workspace/organvm-ii-poiesis/a-i-council--coliseum`
**Deadline:** March 4, 2026 (video must be recorded by March 2)
**Goal:** Get a self-running demo loop that looks good on a 3-minute screen recording

---

## Current State (Ground Truth)

### What Works
- **Backend API** is real and runs — FastAPI with 6 routers (agents, events, voting, blockchain, achievements, users), health endpoint, WebSocket endpoint. 22 tests pass as of Feb 11.
- **Agent system** is real — `Agent` class with RAG memory (`KnowledgeBase.search`), NLP sentiment/topic analysis, LLM response generation via `NLPProcessor.generate()`. Agents have roles (DEBATER, MODERATOR, ANALYST, etc.) and distinct system prompts.
- **Combat engine** is fully implemented — `CombatEngine` with named moves (Strawman Strike, Ad Hominem, Data Dump, Gaslight Guard, Virtue Signal, CANCELLATION fatality), HP system, damage types (logic/emotional/reputation), hit rolls, fatality triggers at low HP. Battle state tracks turn order, rounds, logs.
- **Orchestrator** (`SystemOrchestrator`) ties everything together — `_run_battle_turns()` auto-progresses battles, `_run_autonomous_debates()` nudges agents with event prompts, `start_battle()` creates combat sessions, results broadcast via WebSocket.
- **Frontend** is scaffolded and built once (Next.js 14 with `.next/` present) — `Arena3D.tsx` renders a Three.js canvas with `@react-three/fiber`, box-geometry agent avatars with role-colored materials, orbit controls, arena floor. `BattleScene.tsx` has HP bars, fighter avatars, animated combat log overlay with Framer Motion. `VotingPanel`, `ChatStream`, `AgentGrid`, `EventTicker`, `WalletConnectCustom` components exist.
- **Event pipeline** is real — ingestion, classification, prioritization, routing, processing (sentiment/entities/summary/keywords enrichers), storage, notification system.
- **Voting engine** is real — sessions, stake-weighted votes, gamification (tiers, XP), achievements, leaderboard.

### What's Broken / Missing
1. **venv is stale** — `.venv/` has stale paths from a repo move. Needs fresh venv creation.
2. **No seeded agents** — No Socrates or Machiavelli agent configs exist in the database or as seed data. The orchestrator loads from DB at startup but there's no migration/seed script.
3. **LLM integration needs a real key** — `NLPProcessor.generate()` calls LiteLLM but `.env` has `your_openai_key_here` placeholder. Needs a real API key (OpenAI or Anthropic via LiteLLM).
4. **No autonomous demo trigger** — The `AutonomousArenaWorker` runs on a 120-second interval but there's no seeded event to kick off a debate. Need a way to inject a starter event and trigger a battle automatically.
5. **Frontend ↔ Backend WebSocket not tested end-to-end** — The WebSocket handler exists but the frontend's `onmessage` only handles `agent_message` type, not `combat_update` type that the orchestrator broadcasts.
6. **BattleScene not wired to the page** — `page.tsx` renders `Arena3D` but not `BattleScene`. The 2D battle view (HP bars, combat log) is a separate component not integrated into the main layout.
7. **Agent avatars are boxes** — `Arena3D` renders `boxGeometry` placeholders. No portrait textures exist. The `useLoader(THREE.TextureLoader, portraitUrl)` path exists but `portraitUrl` will be null.
8. **Blockchain write endpoints return 501** — Intentional; the Solana/Anchor code in `anchor/` exists but write paths are deferred. For demo purposes this is fine — just need read paths and voting to work without on-chain.
9. **No database persistence layer** — MVP report says "No persistent storage in this pass (in-memory only)." The models and async session machinery exist but migrations haven't been run. SQLite should be fine for demo.
10. **Frontend font path** — `Arena3D` references `/fonts/Geist-Black.ttf` which may not exist in `public/`.

### Key Files
- `backend/main.py` — App factory, lifespan (creates tables, starts orchestrator + arena worker + twitch listener)
- `backend/ai_agents/orchestrator.py` — Core loop: `_tick()` → `_run_battle_turns()` + `_run_autonomous_debates()`
- `backend/ai_agents/agent.py` — Agent class with `process_message()` → RAG → LLM → response
- `backend/ai_agents/nlp_module.py` — LiteLLM wrapper for generation, sentiment, topic classification
- `backend/combat/engine.py` — Battle state, moves, turns, fatalities
- `backend/event_pipeline/worker.py` — `AutonomousArenaWorker` background task
- `frontend/src/app/page.tsx` — Main layout (3-column: agents, arena+events+voting, chat)
- `frontend/src/components/Arena3D.tsx` — Three.js arena with agent avatars
- `frontend/src/components/BattleScene.tsx` — 2D battle view with HP bars + combat log
- `backend/.env.example` — Environment template
- `docker-compose.yml` — Postgres + Redis (can skip for demo, use SQLite + in-memory)

---

## Task: Get Demo Loop Running

The goal is NOT to build new features. The goal is to get what exists into a state where it runs as a continuous demo loop for 3 minutes of screen recording. Prioritize visual impact over correctness.

### Step 1: Fix the venv and verify backend starts
```bash
cd ~/Workspace/organvm-ii-poiesis/a-i-council--coliseum
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-test.txt
```
- Copy `.env.example` to `.env`
- Set a real `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) — the `NLPProcessor` uses LiteLLM which routes to either
- Set `DATABASE_URL=sqlite:///./coliseum_demo.db` (skip Postgres for demo)
- Verify: `python -m pytest -q backend/tests` — should get 22+ passing

### Step 2: Create a seed script for demo agents
Create `backend/scripts/seed_demo.py` that:
1. Creates the database tables (call `Base.metadata.create_all`)
2. Seeds 2-4 agents with pre-configured philosophical personalities:
   - **Socrates** — role: DEBATER, system_prompt: "You are Socrates. You question assumptions through dialectical reasoning. You never state positions directly — you ask questions that reveal contradictions. Your style is patient, ironic, and relentless."
   - **Machiavelli** — role: DEBATER, system_prompt: "You are Niccolò Machiavelli. You argue from political realism. Power is the only honest metric. Idealism is a luxury. Your style is blunt, strategic, and unflinching."
   - **Ada Lovelace** — role: ANALYST, system_prompt: "You are Ada Lovelace. You analyze arguments for logical structure and computational feasibility. You see patterns others miss. Your style is precise, visionary, and grounded in mathematics."
   - **The Moderator** — role: MODERATOR, system_prompt: "You are the Arena Moderator. You introduce topics, enforce debate rules, and summarize conclusions. You are neutral but theatrical — this is a show."
3. Seeds 1 initial event: a current trending topic (anything — "Should AI systems have constitutional rights?" works)
4. This script should be runnable as `python -m backend.scripts.seed_demo`

### Step 3: Wire the demo loop
The `AutonomousArenaWorker` in `backend/event_pipeline/worker.py` runs every 120 seconds. For the demo:
1. Reduce the interval to 15-20 seconds so things happen faster on screen
2. Ensure it triggers `orchestrator.start_battle(topic)` with the seeded event topic
3. Ensure the orchestrator's `_tick()` loop auto-progresses battle turns at a visible pace (the 1-second tick rate is fine)
4. Verify that battle events broadcast through WebSocket as `combat_update` messages

### Step 4: Fix frontend WebSocket handling
In `frontend/src/app/page.tsx`:
1. Add handling for `combat_update` message type (not just `agent_message`)
2. Wire `BattleScene` into the main page layout — either replace `Arena3D` or put it below the arena
3. In `BattleScene.tsx`, the `handleCombatUpdate` function is already structured to receive `data.log`, `data.is_fatality`, etc. — just verify the message shape matches what the orchestrator sends

In `frontend/src/components/Arena3D.tsx`:
1. Add attack animations — when a `combat_update` fires, flash the attacking agent's avatar (the `isAttacking` prop exists but is hardcoded `false`)
2. Add damage flash effect on the defender

### Step 5: Visual polish for video
- The arena floor grid is already there (red accent, dark metallic)
- The "GENERATIVE RENDER: ACTIVE" badge and uptime counter are there
- Add a pulsing red border or glow effect during active combat
- The `BattleScene` HP bars and animated combat log are the money shot — make sure they're visible
- The `EventTicker` should show the debate topic scrolling
- Hardcoded arena stats (2.4k viewers, 128 votes) are fine for demo — they look like a live system

### Step 6: Record the demo
Run both backend and frontend:
```bash
# Terminal 1
source .venv/bin/activate && python -m backend.scripts.seed_demo && uvicorn backend.main:app --reload

# Terminal 2
cd frontend && pnpm install && pnpm run dev
```
Open `http://localhost:3000`, wait for agents to load and debate to begin. Record 3 minutes of:
1. Arena spinning up, agents appearing
2. Debate unfolding (agent messages in ChatStream)
3. Combat starting (HP bars, combat moves, damage)
4. Voting panel activity (can seed a vote in the demo script)
5. Battle conclusion (fatality or KO)

### What NOT to Do
- Don't implement Solana/blockchain write paths
- Don't add auth/JWT
- Don't add database migrations (`.create_all()` is fine for demo)
- Don't refactor the agent architecture
- Don't add new features — just make what exists work and look good
- Don't worry about the Twitch listener (it'll fail silently without credentials, that's fine)

### Success Criteria
- `uvicorn backend.main:app` starts without errors
- Agents appear in the frontend's AgentGrid
- A debate begins autonomously within 30 seconds
- Combat moves appear in the BattleScene combat log with HP bars animating
- The 3D arena shows agents with attack animations during combat
- The whole loop runs continuously without crashing for 5+ minutes
