# Kubernetes HPA Risk Check

Small Python CLI for reviewing Kubernetes HorizontalPodAutoscaler settings before a production release or support handoff.

## Problem

An HPA can look configured but still fail during real traffic or disruption. A few common examples are CPU-based scaling without CPU requests, a `maxReplicas` value that leaves no scale-out room, or a missing scale-down stabilization window that lets pods churn during recovery.

## What it does

The script reads a `kubectl` JSON snapshot and flags:

- HPAs with `minReplicas` below 2
- HPAs where `maxReplicas` is not greater than `minReplicas`
- HPAs whose `scaleTargetRef` is missing from the snapshot
- CPU-based HPAs where the target workload does not define a container CPU request
- HPAs without at least a 300 second scale-down stabilization window

## How to run

From this folder:

```bash
python3 k8s_hpa_risk_check.py samples/risky_cluster.json
python3 k8s_hpa_risk_check.py samples/safe_cluster.json
python3 k8s_hpa_risk_check.py --format json samples/risky_cluster.json
```

For a real cluster snapshot:

```bash
kubectl get hpa,deployment,statefulset -A -o json > cluster-scaling.json
python3 k8s_hpa_risk_check.py cluster-scaling.json
```

## Example

```text
Kubernetes HPA risk findings:
- medium prod/payments-api [low-min-replicas]: minReplicas is below 2, so scale-down can leave no spare pod for disruption
- high prod/payments-api [no-scale-out-room]: maxReplicas is not greater than minReplicas, so the HPA cannot add capacity
- high prod/payments-api [cpu-metric-without-cpu-request]: HPA uses CPU metrics but the target workload has no container CPU request
- medium prod/payments-api [missing-scale-down-stabilization]: scaleDown stabilizationWindowSeconds is missing or below 300 seconds
- high prod/worker-missing-target [missing-scale-target]: scaleTargetRef does not match a workload in this snapshot
```

## Tests

```bash
python3 -m unittest discover -s tests
```

## Notes

This is a static check, not a replacement for load testing or cluster metrics. I kept it focused on settings that are easy to miss during review and easy to explain during an incident handoff.
