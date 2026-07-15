# Kubernetes Node Drain Readiness

## Problem

A planned node drain can still cause downtime or data loss when workloads have no replacement replica, a disruption budget blocks eviction, or a pod depends on node-local data. I wanted a small preflight check that turns a saved workload snapshot into a clear proceed-or-stop decision.

## What it does

The CLI reviews a normalized JSON snapshot and blocks a drain when it finds:

- unmanaged pods that will not be recreated
- pods explicitly marked unsafe to evict
- local storage without confirmation that its data is disposable
- single-replica controllers
- disruption budgets that do not allow eviction
- no ready replica on another node

DaemonSet and mirror pods are ignored because drain tooling handles them separately. The input is normalized on purpose: this keeps the project dependency-free and lets the decision logic be tested without a live cluster.

## How to run

```bash
python3 node_drain_readiness.py samples/ready_node.json
python3 node_drain_readiness.py samples/blocked_node.json
python3 node_drain_readiness.py samples/blocked_node.json --format json
```

Exit code `0` means ready, `1` means blockers were found, and `2` means the input was invalid.

## Example

```text
[BLOCK] payments/api-4d2a no-ready-replacement: no ready replica is running on another node
[BLOCK] payments/api-4d2a single-replica: controller has no second replica during eviction
STOP: node drain has 7 blocker(s)
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

The tests cover a ready node, multiple operational blockers, duplicate pod validation, and the CLI exit-code contract.

## Notes

This is a decision layer, not a replacement for `kubectl drain --dry-run=server`. A production version could build the normalized snapshot from the Kubernetes API and then run the same checks before maintenance begins.
