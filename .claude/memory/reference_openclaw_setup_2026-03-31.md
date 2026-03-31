---
name: OpenClaw Gateway Setup
description: OpenClaw v2026.3.28 installed and configured — local Ollama gateway on port 18789, config at ~/.openclaw/
type: reference
---

OpenClaw v2026.3.28 installed at `~/.local/share/npm/bin/openclaw`.

**Config:** `~/.openclaw/openclaw.json`
**Gateway:** ws://127.0.0.1:18789 (loopback, token auth)
**LaunchAgent:** `ai.openclaw.gateway` (restart via `openclaw gateway restart`)
**Workspace:** `~/.openclaw/workspace/` (IDENTITY.md, SOUL.md, AGENTS.md, etc.)
**Logs:** `~/.openclaw/logs/gateway.log`, `gateway.err.log`, `config-health.json`

**Models (Ollama):**
- `glm-4.7-flash` — 19GB, 128K context, chat-capable (WARNING: swaps on 16GB RAM)
- `llama3.2:3b` — 2GB, 131K context, chat-capable (currently primary)
- `nomic-embed-text` — 0.3GB, embedding only (removed from config; was erroneously set as primary during onboard)

**Known gaps:**
- No cloud provider auth (Google OAuth failed with `loadCodeAssist: 400 Bad Request`)
- xAI auth not configured ("no config-backed key found" in logs)
- Anthropic/OpenAI not configured
- Web search/fetch now enabled but untested

**Session S43 fix (2026-03-31):** Changed primary model from `nomic-embed-text` (embedding, cannot chat) to `glm-4.7-flash`, added `ollama` to plugin allowlist. User subsequently switched primary to `llama3.2:3b` and enabled web tools.
