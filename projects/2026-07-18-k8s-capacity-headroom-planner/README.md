# Kubernetes Capacity Headroom Planner

## Problem

An HPA ceiling can look reasonable until traffic grows or a node disappears. I wanted a small planning tool that turns those assumptions into an explainable replica recommendation before a load test or production event.

## What it does

The CLI reads a service snapshot and calculates:

- projected requests per second after expected growth
- replicas needed for traffic at a measured safe per-pod rate
- extra replicas reserved for losing the most heavily loaded node
- the gap against current replicas and the HPA maximum

It returns `READY`, `SCALE`, or `BLOCKED`. `BLOCKED` exits with status 1 so the command can be used as a planning gate in CI.

This is intentionally a planning model, not a replacement for load testing. The safe per-pod rate should come from a test that includes realistic latency and dependency behavior.

## How to run

Python 3.10 or newer is enough; there are no third-party dependencies.

```bash
python3 capacity_headroom_planner.py samples/scalable.json
python3 capacity_headroom_planner.py samples/blocked.json
python3 capacity_headroom_planner.py samples/scalable.json --json
```

## Example

```text
SCALE: checkout-api
Projected load: 900.0 RPS
Traffic replicas: 6
Node-loss reserve: 2
Recommended replicas: 8
Current / HPA max: 6 / 10
Action: scale by 2 replica(s); the existing HPA ceiling can support the plan
```

## Input fields

| Field | Meaning |
| --- | --- |
| `current_rps` | Current observed request rate |
| `growth_percent` | Expected traffic increase |
| `safe_rps_per_pod` | Tested sustainable request rate per pod |
| `current_replicas` | Replicas running now |
| `hpa_max_replicas` | Configured HPA ceiling |
| `largest_node_pod_count` | Service pods on the most heavily loaded node |

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

The tests cover the three decisions, replica math, node-loss reserve, and invalid input.

## Notes

The model assumes pods have similar capacity and traffic distributes evenly. Real planning should also review startup time, cluster autoscaler lag, zonal failure tolerance, downstream limits, and resource requests.
