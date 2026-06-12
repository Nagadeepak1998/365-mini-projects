# 365 Mini Projects

Small, practical engineering projects focused on AI/ML, DevOps automation, cloud, CI/CD, Kubernetes, Terraform, observability, and platform engineering.

The goal is not fake GitHub activity. Each project should be explainable in an interview, include a clear README, and demonstrate a real engineering skill in a small scope.

## Featured Portfolio Projects

- [`2026-06-12-llm-runbook-drift-check`](projects/2026-06-12-llm-runbook-drift-check) - AI/DevOps CLI that checks LLM-generated incident runbooks for missing actions, weak grounding, unsupported claims, and risky mitigation advice.
- [`2026-06-10-cinematic-streaming-hero`](projects/2026-06-10-cinematic-streaming-hero) - React/Tailwind streaming homepage with cinematic video hero, movie/series/review sections, liquid-glass controls, responsive navigation, and visible `Built By Nagadeepak` credit.
- [`2026-06-10-incident-log-summarizer`](projects/2026-06-10-incident-log-summarizer) - Python CLI that summarizes Kubernetes, CI, and application logs into severity, evidence, probable cause, and runbook-style next actions.
- [`2026-06-10-compose-risk-check`](projects/2026-06-10-compose-risk-check) - Docker Compose risk checker for common production-readiness issues.
- [`2026-06-09-rag-context-risk-check`](projects/2026-06-09-rag-context-risk-check) - RAG context risk checker for prompt-injection style context issues.
- [`2026-06-08-llm-log-redaction-check`](projects/2026-06-08-llm-log-redaction-check) - Log redaction utility for secrets and PII before sending logs to LLM tools.
- [`2026-06-07-workflow-permission-check`](projects/2026-06-07-workflow-permission-check) - GitHub Actions least-privilege permission checker.

## Project Standards

Professional projects should include:

- problem statement and real-world use case
- setup and run instructions
- tests or deterministic verification where possible
- GitHub Actions workflow when useful
- Dockerfile when useful
- no hardcoded secrets
- a short demo or usage example

## Repository Structure

```text
projects/
  YYYY-MM-DD-project-name/
    README.md
    source code, tests, examples, and supporting files
```
