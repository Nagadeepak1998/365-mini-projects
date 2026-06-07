# Workflow Permission Check

Small Python CLI that scans GitHub Actions workflow files for overly broad `permissions` settings and missing explicit permission blocks.

## Real-world use case

CI pipelines often start with copied workflow templates that keep more GitHub token access than they need. This script gives a fast local check for obvious least-privilege issues before a workflow lands in a shared repository.

## What this project demonstrates

- Practical GitHub Actions security review
- DevSecOps automation with a lightweight local CLI
- Static analysis of YAML-like configuration without paid tools

## Usage

Run against the included risky sample:

```bash
python3 workflow_permission_check.py sample_risky_workflow.yml
```

Run against the included safer sample:

```bash
python3 workflow_permission_check.py sample_safe_workflow.yml
```

## What it checks

- Top-level `permissions: write-all`
- Job-level `permissions: write-all`
- Sensitive scopes set to `write`, such as `contents`, `actions`, `packages`, or `pull-requests`
- Missing explicit top-level and job-level `permissions` blocks, which makes review harder

## Exit codes

- `0` when no risky write permissions are found
- `1` when one or more findings are reported
- `2` when the input file is missing or invalid

## Skill demonstrated

GitHub Actions hardening, developer productivity scripting, and practical DevSecOps review.
