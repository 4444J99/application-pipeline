# Doppler — Staff Full-Stack Software Engineer — Portal Answers

## Will you now or in the future require sponsorship?
No

## Preferred Pronouns
He/Him

## Where did you hear about us?
Job board (sourced via Ashby API)

## Why would you like to work at Doppler?

Doppler solves the exact problem I have been building infrastructure for over the past five years: making configuration a governed, auditable, centrally managed contract rather than scattered .env files. Every one of my 113 repositories has a seed.yaml declaring its membership, tier, dependencies, and event subscriptions — validated by CI on every push, with registry-v2.json as single source of truth. I built the config governance layer because I needed it at scale (82,000 files, 12 organizations), and Doppler is the productized version of that same insight. I want to work on the productized version.

## What is the tech stack you are most comfortable with?

Python (2,650 files, 14,500 pytest tests) and TypeScript (1,955 files, 8,900 vitest/jest tests). React 18, Express, FastAPI, Typer CLI framework. YAML/JSON schema validation. Docker, GCP/Terraform, GitHub Actions (104 CI/CD pipelines). PostgreSQL (Neon), Redis. Full-stack in the real sense — I own backend, frontend, infrastructure, CI, documentation, and deployment across a 113-repository system.

## What problems or opportunities do you think there still are within the secrets management space?

The gap between config management and documentation management. Doppler manages secrets and env vars, but the documentation that describes how those secrets are used — which service needs which key, what the rotation policy is, what breaks if a secret changes — is still scattered across READMEs and wikis that go stale. I built a system where documentation is auto-generated from config contracts (Jinja2 templates bound to live registry data), so the docs never drift from the actual config state. That architectural pattern — config-as-source-of-truth for both runtime and documentation — is the next layer Doppler could own.

## Explain a difficult feature or system you designed recently. What challenges did you face and how did you solve them?

The promotion state machine governing 113 repositories across 8 GitHub organizations. The challenge: how do you enforce maturity gates (LOCAL → CANDIDATE → PUBLIC_PROCESS → GRADUATED → ARCHIVED) across independently-managed repos without creating a centralized bottleneck? The solution: every repo carries a seed.yaml contract declaring its current state. A registry (registry-v2.json, 2,240 lines) aggregates all contracts into a single source of truth. Automated validation runs weekly, checking 50 dependency edges for violations — no circular dependencies, no back-edges across organ boundaries. The difficulty was not the validation logic — it was designing contracts that are expressive enough to capture real architectural constraints but simple enough that every repo can maintain them independently. The current system has zero violations across all 50 edges since inception.

## Tell us about a time you weren't able to implement something exactly as it was planned. What happened and how did you handle it?

The scoring rubric for my application pipeline was originally set at a 9.0 minimum threshold — designed for "precision over volume" after 60 cold applications produced zero interviews. When I added a network_proximity dimension at 0.20 weight, I discovered through mathematical analysis that 9.0 was impossible to achieve: even with perfect 10s on all other dimensions, the maximum achievable score for a cold application was 8.2. The threshold was mathematically unattainable under the system's own weight structure. I recalibrated to 7.0 based on the actual weight distribution, documented the derivation, and added engagement-based recalibration (N=26 outcome data showing deadline_feasibility and network_proximity as the strongest predictors). The plan assumed the scoring model was correct; the data showed it was internally inconsistent. I changed the plan.
