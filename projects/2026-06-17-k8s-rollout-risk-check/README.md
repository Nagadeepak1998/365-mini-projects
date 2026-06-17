# Kubernetes Rollout Risk Check

Kubernetes Rollout Risk Check is a small Python CLI I built to review `kubectl` JSON snapshots for rollout and disruption problems before they turn into production downtime.

I already had a basic manifest checker in this repo. This project is narrower and more operational: it focuses on whether a workload can roll safely, stay ready, and survive voluntary disruption.

## Problem

Kubernetes YAML can look valid while still carrying rollout risk. A single-replica deployment, a missing readiness probe, or a loose PodDisruptionBudget can turn a routine update into an outage.

I wanted a quick local check I could run against cluster snapshots during reviews.

## What It Does

- reads `kubectl get deployment,statefulset,pdb -A -o json` output
- flags single-replica workloads that have no rollout redundancy
- flags containers without readiness probes
- flags rolling updates that can take every replica offline
- flags multi-replica workloads without a matching PodDisruptionBudget
- flags PodDisruptionBudgets that still allow total disruption

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for verification

## Folder Structure

```text
.
|-- README.md
|-- k8s_rollout_risk_check.py
|-- samples
|   |-- risky_cluster.json
|   `-- safe_cluster.json
`-- tests
    `-- test_k8s_rollout_risk_check.py
```

## How to Run

From this project folder:

```bash
python3 k8s_rollout_risk_check.py samples/risky_cluster.json
```

Expected result:

```text
FLAGGED: 5 Kubernetes rollout risk issue(s)
```

Check the safer sample:

```bash
python3 k8s_rollout_risk_check.py samples/safe_cluster.json
```

Expected result:

```text
PASS: no configured Kubernetes rollout risks detected
```

Return JSON instead:

```bash
python3 k8s_rollout_risk_check.py samples/risky_cluster.json --format json
```

Use it with a real cluster snapshot:

```bash
kubectl get deployment,statefulset,pdb -A -o json > cluster-snapshot.json
python3 k8s_rollout_risk_check.py cluster-snapshot.json
```

## Example

The bundled risky sample includes these review problems:

- a single-replica `payments-api` deployment
- no readiness probe on the `payments-api` container
- a rollout strategy that can take all replicas offline
- a multi-replica workload with no matching PodDisruptionBudget
- a PodDisruptionBudget that still allows total disruption

Those are the kinds of issues I want to catch before a rollout window starts.

## Tests

```bash
python3 -m py_compile k8s_rollout_risk_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

- This is intentionally a narrow static review tool, not a full Kubernetes policy engine.
- It expects JSON input so it can stay dependency-free and easy to run in CI or from a local shell.
