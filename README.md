# 365 Mini Projects

I use this repo to build small, hands-on engineering projects around AI, DevOps, cloud, CI/CD, Kubernetes, Terraform, observability, and platform engineering.

Most folders are intentionally small. The goal is to practice one useful idea at a time, keep the code runnable, and document enough context so I can revisit the project later.

## Recent Builds

- [`2026-06-24-backup-restore-drill-check`](projects/2026-06-24-backup-restore-drill-check) - Backup restore drill review CLI that flags stale backups, failed backup jobs, old restore tests, short retention, missing owners, missing encryption, and weak critical-service coverage.
- [`2026-06-23-feature-flag-risk-check`](projects/2026-06-23-feature-flag-risk-check) - Feature flag rollout review CLI that flags large rollout jumps, missing owners, stale cleanup dates, prod debug flags, missing rollback notes, and missing kill switches.
- [`2026-06-22-k8s-hpa-risk-check`](projects/2026-06-22-k8s-hpa-risk-check) - Kubernetes HPA review CLI that flags low minimum replicas, missing scale targets, no scale-out room, CPU metric/request mismatches, and weak scale-down stabilization.
- [`2026-06-21-openapi-contract-diff-check`](projects/2026-06-21-openapi-contract-diff-check) - OpenAPI contract comparison CLI that flags removed endpoints, stricter parameters, removed fields, and missing success responses before an API release.
- [`2026-06-20-container-image-drift-check`](projects/2026-06-20-container-image-drift-check) - Kubernetes workload image review CLI that flags mutable tags, missing digests, sticky pull-policy risks, and cross-namespace image version drift.
- [`2026-06-19-postgres-migration-risk-check`](projects/2026-06-19-postgres-migration-risk-check) - PostgreSQL migration review CLI that flags destructive DDL, explicit locks, blocking index builds, and risky `NOT NULL` changes.
- [`2026-06-18-prometheus-rule-sanity-check`](projects/2026-06-18-prometheus-rule-sanity-check) - PrometheusRule snapshot review CLI that flags missing severity labels, page alerts without `for`, and missing runbook, dashboard, summary, or ownership metadata.
- [`2026-06-17-k8s-rollout-risk-check`](projects/2026-06-17-k8s-rollout-risk-check) - Kubernetes rollout review CLI that flags single-replica workloads, missing readiness probes, risky rolling updates, and weak PodDisruptionBudget coverage.
- [`2026-06-16-terraform-plan-risk-check`](projects/2026-06-16-terraform-plan-risk-check) - Terraform plan JSON review CLI that flags public ingress, public database exposure, relaxed S3 bucket protections, and wildcard IAM policy expansion.
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
