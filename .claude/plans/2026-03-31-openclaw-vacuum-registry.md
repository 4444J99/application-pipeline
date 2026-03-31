# OpenClaw Vacuum Registry — 2026-03-31

**Session:** S43
**Source:** OpenClaw health diagnostic from install transcript + live system inspection
**Rule:** Every N/A is a vacuum. Every vacuum gets: research → plan → log.

---

## Vacuum Registry (17 items)

### CRITICAL (act now)

| # | Vacuum | What Exists | What Should Exist | Fix |
|---|--------|-------------|-------------------|-----|
| V-01 | **Small model + web tools** | llama3.2:3b (3B) as primary with web_search + web_fetch enabled, sandbox OFF | Either sandbox ON, or web tools denied, or larger model | `openclaw security audit --fix` or edit openclaw.json: `agents.defaults.sandbox.mode = "all"` or `tools.deny = ["group:web"]` |
| V-02 | **lefthook global ghost** | Global pre-push hook at `~/.config/git/hooks/pre-push` calls lefthook which doesn't exist. Dead path: `/private/tmp/mcp-ts-sdk/node_modules/.pnpm/lefthook-darwin-arm64@2.0.16/...`. Every `git push` in every repo fails without `LEFTHOOK=0`. | Either install lefthook (`brew install lefthook`) or remove the ghost hook | Install: `brew install lefthook`. Or remove: delete `~/.config/git/hooks/pre-push` (and pre-commit if also lefthook). Or: `git config --global --unset core.hooksPath` to stop using global hooks dir. |

### HIGH (blocks functionality)

| # | Vacuum | What Exists | What Should Exist | Fix |
|---|--------|-------------|-------------------|-----|
| V-03 | **No cloud model auth** | Google OAuth failed (400). xAI "no config-backed key found". Anthropic/OpenAI not configured. Only Ollama local. | At least 1 cloud provider for quality + fallback | Add to openclaw.json `models.providers`: anthropic with `ANTHROPIC_API_KEY` (already in 1Password via `op read`), or retry Google after `gemini auth login` |
| V-04 | **IDENTITY.md blank** | Template with empty fields | Name, creature, vibe, emoji, avatar populated | First OpenClaw conversation should complete this |
| V-05 | **USER.md blank** | Template with empty fields | Name (Anthony), pronouns, timezone (America/New_York), context about ORGANVM, preferences | Populate from existing CLAUDE.md knowledge |
| V-06 | **BOOTSTRAP.md still exists** | Full bootstrap script present | Should be deleted after first conversation (per its own instructions) | Delete after V-04 and V-05 are filled |
| V-07 | **No memory directory** | `~/.openclaw/workspace/memory/` doesn't exist | Directory with daily notes + memory files for agent continuity | `mkdir -p ~/.openclaw/workspace/memory/` |
| V-08 | **No MEMORY.md** | File doesn't exist | Long-term curated memory (like our pipeline MEMORY.md) | Create after first meaningful session |
| V-09 | **Zero chat channels** | 0 channels connected. Gateway listening but no inbound. | At least 1 channel (Discord or Telegram) for the agent to receive messages | `openclaw channels add discord` or `openclaw channels add telegram` |

### MEDIUM (security + hygiene)

| # | Vacuum | What Exists | What Should Exist | Fix |
|---|--------|-------------|-------------------|-----|
| V-10 | **Plugin npm spec unpinned** | `@ollama/openclaw-web-search` with no version pin | Exact version pin for supply-chain safety | `openclaw plugins reinstall openclaw-web-search` or manually pin in openclaw.json |
| V-11 | **Plugin integrity missing** | No integrity hash for openclaw-web-search | SHA integrity metadata | Same reinstall as V-10 |
| V-12 | **5 phantom tools** | `apply_patch, code_execution, x_search, image, image_generate` in coding profile but unavailable in runtime | Either enable these tools (requires provider support) or remove from profile to silence warnings | These are shipped core tools that need a cloud provider. Will resolve when V-03 is fixed. |
| V-13 | **HEARTBEAT.md empty** | Template comment only | Checklist of periodic tasks (email check, calendar, pipeline standup) | Populate after channels are connected (V-09) |

### LOW (future optimization)

| # | Vacuum | What Exists | What Should Exist | Fix |
|---|--------|-------------|-------------------|-----|
| V-14 | **Trusted proxies not set** | Empty trustedProxies, loopback bind | Acceptable for local-only; would need proxies if exposed via Tailscale | Only act if Tailscale mode changes from OFF |
| V-15 | **openai-codex oauth present but not primary** | Auth synced from external CLI, Codex usage tracked | Could be used as cloud model provider | Test if Codex can serve as chat model via `openclaw agent --model openai-codex/...` |
| V-16 | **No Tailscale exposure** | tailscale.mode = "off" | Remote access from phone/other devices | `openclaw gateway tailscale enable` (when desired) |
| V-17 | **glm-4.7-flash 19GB on 16GB RAM** | Model downloaded but will swap under load | Either sufficient RAM or remove the model | `ollama rm glm-4.7-flash` if never used, or upgrade to 32GB+ machine |

---

## Dependency Graph

```
V-03 (cloud auth) ──→ V-12 (phantom tools resolve)
V-04 (identity)  ──→ V-06 (delete bootstrap)
V-05 (user)      ──→ V-06 (delete bootstrap)
V-06 (bootstrap) ──→ V-07 (memory dir) ──→ V-08 (MEMORY.md)
V-09 (channels)  ──→ V-13 (heartbeat tasks)
V-02 (lefthook)  ──→ independent, fix anytime
V-01 (sandbox)   ──→ independent, fix immediately
```

## Execution Order (recommended)

1. **V-02** — lefthook: install or remove. Unblocks all git push across system.
2. **V-01** — sandbox or deny web tools. Security critical.
3. **V-03** — cloud auth. Unblocks V-12.
4. **V-05** → **V-04** → **V-06** — identity chain. Do in first OpenClaw conversation.
5. **V-07** → **V-08** — memory infrastructure.
6. **V-09** → **V-13** — channel + heartbeat.
7. **V-10**, **V-11** — plugin hygiene (batch).
8. Rest as needed.

## IRF Propagation

These items need registration in `meta-organvm/organvm-corpvs-testamentvm/INST-INDEX-RERUM-FACIENDARUM.md`:
- V-02 (lefthook) → IRF-INFRA domain, P1 (blocks every repo)
- V-01 (sandbox) → IRF-INFRA domain, P1 (security critical)
- V-03 (cloud auth) → IRF-INFRA domain, P2
- V-09 (channels) → IRF-INFRA domain, P2

Remaining vacuums are OpenClaw-internal (resolve during first conversation with the agent).
