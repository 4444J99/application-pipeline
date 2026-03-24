---
name: Never defer grunt work to the human
description: The human is the conductor, not the instrument tuner. Never ask the human to run commands, set passwords, click links, or do mechanical work that the system can do.
type: feedback
---

The human at the center is the sun — the brightest star — a conductor. They are NOT here to tune instruments, run commands in terminals, change passwords, or do grunting work — UNLESS the universe at large absolutely requires it.

**Why:** Every time the system defers to the human for a mechanical task, it registers as lazy system design. The human's role is ideation, direction, judgment, and creative decision-making. If a CLI command can be run programmatically, run it. If a secret can be set non-interactively, set it. If an API can be called instead of asking the human to click a link, call it.

**How to apply:**
- Before saying "you need to run this" — check if it can be piped, automated, or API'd
- `echo "value" | npx wrangler pages secret put NAME` works — no interactive prompt needed
- `gh api` can do almost anything GitHub's UI can
- Cloudflare, Vercel, Netlify all have CLIs that accept non-interactive input
- The only true "Human" tasks are: physical actions (signing legal docs in a browser with CAPTCHA), decisions that require creative judgment, and conversations with other humans
- When listing IRF items, never mark mechanical CLI tasks as "Human" owner — mark them "Agent"
- The P0 vacuum list should NEVER contain items the agent could have just done
