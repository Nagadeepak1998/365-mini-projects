# Kubernetes Graceful Shutdown Check

## Problem

A pod can pass its deployment checks and still drop requests or duplicate work when Kubernetes terminates it. The termination grace period, endpoint removal delay, and longest in-flight operation need to fit together, and the application must react correctly to `SIGTERM`.

## What it does

This dependency-free Python CLI reviews a saved workload inventory and flags:

- missing ownership or `SIGTERM` handling
- applications that keep accepting work during shutdown
- a `preStop` delay shorter than endpoint removal propagation
- a termination grace period that cannot cover `preStop`, in-flight work, and a safety buffer
- production workloads with one replica or no PodDisruptionBudget
- retried in-flight work without idempotent processing

The timing model is deliberately conservative. It budgets the full `preStop` delay plus the longest in-flight operation and a safety buffer. It does not simulate traffic distribution or application-specific cancellation behavior.

## How to run

```bash
python3 graceful_shutdown_check.py samples/safe_inventory.json
python3 graceful_shutdown_check.py samples/risky_inventory.json
python3 graceful_shutdown_check.py samples/safe_inventory.json --json
```

`PASS` returns exit code `0`. `FLAGGED` returns exit code `1`, so the check can be used in a CI verification step.

## Example

```text
FLAGGED: 8 graceful-shutdown issue(s) detected
- order-worker [SIGTERM_NOT_HANDLED]: handle SIGTERM and begin graceful shutdown
- order-worker [GRACE_PERIOD_TOO_SHORT]: termination grace is 20s; budget at least 38s
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

The tests cover a safe workload, timing-budget failures, production availability checks, retry idempotency, and the CI-friendly report status.
