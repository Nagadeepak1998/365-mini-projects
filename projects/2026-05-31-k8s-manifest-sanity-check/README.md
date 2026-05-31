# Kubernetes Manifest Sanity Check (No Dependencies)

Small Python CLI that performs fast static checks on Kubernetes YAML to catch common deployment risks before opening a PR.

## Real-world use case
Use this in local pre-commit hooks or CI to quickly fail risky manifest changes before they reach clusters.

## What this project demonstrates
- Practical DevOps guardrail design
- Lightweight automation with Python
- Shift-left Kubernetes hygiene checks without external tooling

## Checks included
- `Service` with `type: NodePort`
- Container image pinned to `:latest`
- Missing `resources.requests`/`resources.limits` in `Deployment`
- `runAsNonRoot: true` not set

## Usage
```bash
python3 k8s_manifest_sanity_check.py sample-risky-deployment.yaml
```

Exit code behavior:
- `0` when no findings are triggered
- `1` when at least one finding is reported
- `2` when the input file is missing
