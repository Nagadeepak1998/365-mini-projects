# Workflow Concurrency Check

Small Python CLI that scans a GitHub Actions workflow for deploy-like jobs and flags workflows that do not declare a `concurrency` policy.

## Real-world use case

Teams often add production or staging deploy jobs to GitHub Actions without protecting them from overlapping runs. That can lead to two releases racing each other, clobbered environments, or noisy rollback incidents. This tool gives a cheap local review step before merging workflow changes.

## What this project demonstrates

- Practical GitHub Actions reliability automation
- CI/CD review thinking for safer deployments
- Lightweight Python tooling for developer productivity

## Usage

Run the checker against the included risky sample:

```bash
python3 workflow_concurrency_check.py sample_risky_workflow.yml
```

Run it against the corrected sample:

```bash
python3 workflow_concurrency_check.py sample_safe_workflow.yml
```

## What it checks

- Looks for job names or ids that suggest deployment work
- Requires a workflow-level `concurrency:` block when deploy-like jobs exist

## Exit codes

- `0` when no issues are found
- `1` when one or more issues are found
- `2` when the input file is missing or invalid

## Skill demonstrated

GitHub Actions review automation, CI/CD reliability awareness, and practical Python scripting.
