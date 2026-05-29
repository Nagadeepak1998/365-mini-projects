# Dockerfile Risk Checker

A tiny developer-productivity script that scans a Dockerfile for a few high-signal risks often seen in CI/CD and production builds.

## Real-world use case

Before opening a PR, run this check to quickly catch common container hardening and reproducibility issues (for example `latest` tags, running as root, or missing pinned installs).

## What this demonstrates

- Practical DevOps automation with Python
- Lightweight static checks for container build hygiene
- CI-friendly CLI output for fast triage

## Files

- `dockerfile_risk_checker.py` - scanner script
- `sample.Dockerfile` - sample input with intentional issues

## Usage

```bash
python3 dockerfile_risk_checker.py sample.Dockerfile
```

You can also scan any Dockerfile path:

```bash
python3 dockerfile_risk_checker.py /path/to/Dockerfile
```

## Expected outcome

The script reports risk findings with line numbers, severity, and a short remediation tip.
