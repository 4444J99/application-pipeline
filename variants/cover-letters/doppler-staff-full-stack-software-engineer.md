# Cover Letter — Doppler Staff Full-Stack Software Engineer (Remote US)

---

Doppler's core insight is that config shouldn't live in .env files scattered across repos — it should be a governed, auditable, centrally managed contract. I've been building that same system from scratch for five years, just without the product.

113 repositories across 8 GitHub organizations. Every repo has a seed.yaml declaring its organ membership, tier, implementation status, produces/consumes edges, and event subscriptions. Those files are the config contract for the entire system. They're enforced by governance-rules.json, validated by CI (94 pipelines), and the registry-v2.json serves as single source of truth for all 113 repos. When I need to change a config value that affects downstream repos, I change it in one place and the validation gates catch every inconsistency before anything deploys. That's what Doppler does at enterprise scale.

I'm a full-stack engineer: Python and TypeScript, React 18, Express, CLI tooling, YAML schema validation, pytest and Vitest, Docker, GCP. 23,470 tests system-wide. Two testing strategies: live-data validation against the actual YAML contracts, and isolated unit tests with monkeypatching for reproducibility. I understand why both matter.

What draws me to Doppler specifically is that it's a developer tool, not just a product. The team is small and the problem is real. I've spent five years building for a user base of one (myself), which means I've shipped every single piece of this infrastructure to production, debugged it at 2am, and had to live with every architectural decision I made. That's a different kind of accountability than building for a product backlog.

Staff-level scope is where I operate: I'm not looking for a task to be assigned. I'm looking for a problem to own.

Anthony James Padavano
