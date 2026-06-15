# 365 Mini Projects

I use this repo to build small, hands-on engineering projects around AI, DevOps, cloud, CI/CD, Kubernetes, Terraform, observability, and platform engineering.

Most folders are intentionally small. The goal is to practice one useful idea at a time, keep the code runnable, and document enough context so I can revisit the project later.

## Recent Builds

- [`2026-06-15-deployment-window-risk-check`](projects/2026-06-15-deployment-window-risk-check) - Deployment plan review CLI that flags risky release windows, weak rollback plans, missing monitoring links, and production rollout issues.
- [`2026-06-15-alert-noise-budget-check`](projects/2026-06-15-alert-noise-budget-check) - Alert history review CLI that flags noisy page-heavy alerts with low actionability, repeated pages, and poor acknowledgement rates.
- [`2026-06-14-slo-burn-rate-check`](projects/2026-06-14-slo-burn-rate-check) - SLO snapshot review CLI that calculates error-budget burn rate and flags fast-burn or slow-burn windows.
- [`2026-06-13-junit-flake-tracker`](projects/2026-06-13-junit-flake-tracker) - JUnit XML review CLI that highlights flaky tests, repeated failures, and slow tests across CI runs.
- [`2026-06-12-vault-policy-drift-check`](projects/2026-06-12-vault-policy-drift-check) - Vault ACL policy review CLI that flags risky capability drift, wildcard writes, and dangerous access expansion on sensitive paths.
- [`2026-06-12-llm-runbook-drift-check`](projects/2026-06-12-llm-runbook-drift-check) - Checks AI-generated incident runbooks against required evidence and safe response steps.
- [`2026-06-10-cinematic-streaming-hero`](projects/2026-06-10-cinematic-streaming-hero) - React/Tailwind streaming UI with a video hero, content sections, glass-style controls, and responsive navigation.
- [`2026-06-10-incident-log-summarizer`](projects/2026-06-10-incident-log-summarizer) - Python CLI that turns Kubernetes, CI, and application logs into a short incident summary with next steps.
- [`2026-06-10-compose-risk-check`](projects/2026-06-10-compose-risk-check) - Docker Compose risk checker for common production-readiness issues.
- [`2026-06-09-rag-context-risk-check`](projects/2026-06-09-rag-context-risk-check) - RAG context risk checker for prompt-injection style context issues.
- [`2026-06-07-workflow-permission-check`](projects/2026-06-07-workflow-permission-check) - GitHub Actions least-privilege permission checker.

## How I Use This Repo

Each project usually includes:

- a short README
- runnable source code
- sample input or demo commands
- tests or a deterministic verification command when it makes sense
- no secrets or private company data

## Repository Structure

```text
projects/
  YYYY-MM-DD-project-name/
    README.md
    source code, tests, examples, and supporting files
```
