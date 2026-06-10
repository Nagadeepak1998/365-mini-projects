# Docker Compose Risk Check

Small Python CLI that scans a Docker Compose file for a few high-signal security and operability risks before you commit it.

## Real-world use case

Teams often use `compose.yml` for local development, demos, or internal tooling. Those files can quietly grow risky settings such as hardcoded secrets, privileged containers, mounted Docker sockets, or publicly exposed database ports. This script gives a fast local check you can run before pushing changes.

## What this project demonstrates

- Practical DevOps guardrails for container-based development
- Lightweight static analysis without external dependencies
- Python automation for secure developer workflows

## Usage

Run against the included risky sample:

```bash
python3 compose_risk_check.py sample_risky_compose.yml
```

Run against the included safer sample:

```bash
python3 compose_risk_check.py sample_safe_compose.yml
```

## What it checks

- Images pinned to `:latest`
- `privileged: true`
- Docker socket mounts such as `/var/run/docker.sock`
- Hardcoded secret-like environment variables
- Publicly exposed common database/cache ports

## Exit codes

- `0` when no risky settings are found
- `1` when one or more findings are reported
- `2` when the input file is missing or invalid

## Skill demonstrated

DevSecOps hygiene, container workflow review, and practical Python automation.
