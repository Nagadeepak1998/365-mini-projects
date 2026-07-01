# Kubernetes Namespace Quota Check

I built this small CLI to review a Kubernetes namespace inventory before a production namespace is treated as ready for shared-cluster use. It focuses on guardrails I would want in place before teams rely on a namespace: ownership, quota coverage, default requests, network isolation, and workload resource settings.

## What It Does

The script reads a JSON inventory of Kubernetes namespaces and flags:

- production namespaces without owners
- production namespaces without a ResourceQuota
- quotas missing CPU, memory, or pod hard limits
- production namespaces without a LimitRange
- LimitRanges missing default CPU or memory requests
- missing default-deny NetworkPolicy coverage
- workloads with missing container CPU or memory requests
- workloads with missing container CPU or memory limits
- workloads with no container resource data

It exits with `0` when the inventory is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 k8s_namespace_quota_check.py samples/safe_inventory.json
```

Expected output:

```text
PASS: Kubernetes namespace guardrails look ready
```

Risky sample:

```bash
python3 k8s_namespace_quota_check.py samples/risky_inventory.json
```

Expected output starts with:

```text
FLAGGED: 10 Kubernetes namespace guardrail issue(s) detected
```

## Input Shape

```json
{
  "namespaces": [
    {
      "name": "orders-prod",
      "environment": "prod",
      "owner": "orders-platform",
      "resource_quota": {
        "hard": {
          "cpu": "20",
          "memory": "64Gi",
          "pods": "80"
        }
      },
      "limit_range": {
        "default_requests": {
          "cpu": "100m",
          "memory": "128Mi"
        }
      },
      "default_deny_network_policy": true,
      "workloads": [
        {
          "name": "orders-api",
          "containers": [
            {
              "name": "app",
              "requests": {
                "cpu": "250m",
                "memory": "512Mi"
              },
              "limits": {
                "cpu": "1",
                "memory": "1Gi"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

## Tests

```bash
python3 -m py_compile k8s_namespace_quota_check.py tests/test_k8s_namespace_quota_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This is a static review tool for saved namespace inventory data. It does not call the Kubernetes API and it is not a replacement for admission policies, live quota monitoring, or cluster-level security controls. I kept it dependency-free so it can run quickly from a local checkout or CI job with a generated namespace snapshot.
