# dbt Labs -- Staff Software Engineer, Quality and Release Platform -- Portal Answers

## Country

United States

## LinkedIn Profile

https://www.linkedin.com/in/anthonyjamespadavano

## Website

https://4444j99.github.io/portfolio/

## How did you hear about this job?

Job board

## Are you legally authorized to work in the United States?

Yes

## Will you now or in the future require sponsorship?

No

## What is your current location? (City, State)

New York, NY

## Are you open to relocating?

Yes -- based in New York City, open to relocation

## I consent to have my personal information retained

I agree

## Describe your experience building or improving CI/CD platforms, release engineering systems, or developer tooling at scale

I designed and operate the CI/CD platform for a 113-repository, 8-organization system: 128 GitHub Actions workflows, 18 reusable workflow templates, and 104 CI/CD pipelines. The release engineering layer includes a promotion state machine with five states (LOCAL, CANDIDATE, PUBLIC_PROCESS, GRADUATED, ARCHIVED) enforced by automated gates -- no state skipping allowed. Every push triggers schema validation, linting, test execution, and a verification matrix that enforces module-to-test coverage at 117/117 modules. The quality ratchet system commits policy JSONs to the repo and CI validates that code meets or exceeds the ratcheted thresholds on every PR.

The infrastructure uses GitHub Actions for orchestration, Helm charts for Kubernetes deployments, Terraform for infrastructure-as-code, and Python/TypeScript for all automation tooling. I built self-service pipeline templates that teams adopt without platform team intervention -- reusable workflows handle build, test, lint, deploy, and release flows with standardized interfaces. The system processes 23,470 tests across 82K files, and the entire platform is maintained and extended by a single operator, which forces every component to be self-healing, observable, and documented.

## How would you approach defining and driving technical strategy for code quality across an engineering organization?

My approach starts with measurement, not mandates. I built a nine-dimension scoring rubric that evaluates code quality objectively -- including evidence match, track record fit, and portal friction -- and a multi-model inter-rater agreement facility that uses four AI raters with distinct personas to evaluate system quality, computing ICC, Cohen's kappa, and Fleiss kappa to detect scoring drift. That same measurement-first philosophy applies to code quality platforms: instrument what exists, establish baselines, then build tooling that raises the floor without blocking velocity.

Concretely, I would start by auditing dbt Labs' existing quality signals (test coverage, lint pass rates, build times, deploy frequency, rollback rates) and identifying the highest-leverage gaps. Then I would build the platform layer: standardized CI checks that run fast and provide actionable feedback, static analysis integrated into the developer workflow rather than bolted on after the fact, and a quality dashboard that makes trends visible to engineering leadership. The AI-assisted development strategy fits directly here -- I built an AI-conductor methodology where LLMs generate code volume while human-authored quality gates validate output. That pattern translates directly to evaluating and guardrailing AI coding tools across an engineering org: define the acceptance criteria first, then let AI accelerate everything that meets the bar.

## Describe your experience with Helm, ArgoCD, Terraform, GitHub Actions, or Kubernetes

GitHub Actions is my primary CI/CD orchestration layer: 128 workflows, 18 reusable templates, matrix builds, conditional deployments, and artifact management across 113 repositories. I use Terraform for infrastructure-as-code provisioning and have built templated deployment configurations using Helm chart patterns for Kubernetes workloads. My deployment architecture follows progressive delivery principles -- staged rollouts with automated health checks and rollback triggers, similar to ArgoCD's sync-and-verify model. The entire system is Python and TypeScript on the tooling side, with shell scripts for LaunchAgent-based scheduling and self-healing automation on macOS. I am comfortable operating at the Kubernetes layer and have designed cell-based deployment patterns that map directly to dbt Cloud's multi-cloud architecture requirements.
