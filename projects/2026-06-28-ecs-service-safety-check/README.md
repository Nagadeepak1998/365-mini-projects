# ECS Service Safety Check

I built this small CLI to review an ECS service inventory before trusting a production rollout. It checks the deployment settings I usually want to confirm before a service goes live: enough running tasks, circuit breaker rollback, sane deployment percentages, health checks, alarms, image pinning, log retention, and clear ownership.

## What It Does

The script reads a JSON inventory of ECS services and flags:

- production services without owners
- production or critical services running fewer than two tasks
- missing ECS deployment circuit breaker or rollback settings
- deployment percentages that reduce capacity or leave no replacement room
- public services without a load balancer health gate
- load balancers without health check paths
- short health check grace periods
- missing CPU or memory alarms
- alarms without runbook links
- mutable task images or images without digest pins
- short CloudWatch Logs retention

It exits with `0` when the inventory is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 ecs_service_safety_check.py samples/safe_inventory.json
```

Expected output:

```text
PASS: ECS service deployment safety looks ready
```

Risky sample:

```bash
python3 ecs_service_safety_check.py samples/risky_inventory.json
```

Expected output starts with:

```text
FLAGGED: 16 ECS service safety issue(s) detected
```

## Input Shape

```json
{
  "services": [
    {
      "name": "payments-api",
      "environment": "prod",
      "owner": "payments-platform",
      "critical": true,
      "desired_count": 3,
      "public_endpoint": true,
      "deployment": {
        "circuit_breaker_enabled": true,
        "rollback_enabled": true,
        "minimum_healthy_percent": 100,
        "maximum_percent": 200
      },
      "load_balancer": {
        "enabled": true,
        "health_check_path": "/health"
      },
      "health_check_grace_period_seconds": 60,
      "alarms": [
        {
          "metric_name": "CPUUtilization",
          "threshold": 80,
          "runbook": "https://runbooks.example/ecs/payments-api"
        },
        {
          "metric_name": "MemoryUtilization",
          "threshold": 85,
          "runbook": "https://runbooks.example/ecs/payments-api"
        }
      ],
      "task_definition": {
        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/payments-api:2026-06-28",
        "image_digest": "sha256:0123456789abcdef",
        "log_retention_days": 30
      }
    }
  ]
}
```

## Tests

```bash
python3 -m py_compile ecs_service_safety_check.py tests/test_ecs_service_safety_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This is a static review tool for saved inventory data, not a replacement for AWS Config, deployment alarms, or a real canary. I kept it dependency-free so it can run quickly from a local checkout or CI job with a generated ECS service snapshot.
