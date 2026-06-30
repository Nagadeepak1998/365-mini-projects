# RDS Failover Readiness Check

I built this small CLI to review an RDS inventory before a production database is treated as ready for failover. It checks the operational controls I would want to see around critical databases: ownership, Multi-AZ coverage, backups, alarms, recent failover drills, RTO/RPO notes, and pending changes.

## What It Does

The script reads a JSON inventory of RDS databases and flags:

- production databases without owners
- critical production databases without Multi-AZ
- missing deletion protection
- disabled automated backups
- backup retention shorter than seven days
- missing backup windows
- disabled storage autoscaling
- missing CPU, free storage, or connection alarms
- read replicas without replica lag alarms
- alarms without runbook links
- missing or stale failover drills
- missing failover runbooks
- missing RTO or RPO targets
- pending-reboot changes

It exits with `0` when the inventory is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 rds_failover_readiness_check.py samples/safe_inventory.json --today 2026-06-30
```

Expected output:

```text
PASS: RDS failover readiness looks ready
```

Risky sample:

```bash
python3 rds_failover_readiness_check.py samples/risky_inventory.json --today 2026-06-30
```

Expected output starts with:

```text
FLAGGED: 18 RDS failover readiness issue(s) detected
```

## Input Shape

```json
{
  "databases": [
    {
      "identifier": "orders-prod",
      "environment": "prod",
      "owner": "orders-platform",
      "critical": true,
      "multi_az": true,
      "deletion_protection": true,
      "read_replica": true,
      "backups": {
        "enabled": true,
        "retention_days": 14,
        "window": "07:00-08:00 UTC"
      },
      "storage": {
        "autoscaling": true
      },
      "alarms": [
        {
          "metric_name": "CPUUtilization",
          "runbook": "https://runbooks.example/db/orders"
        },
        {
          "metric_name": "FreeStorageSpace",
          "runbook": "https://runbooks.example/db/orders"
        },
        {
          "metric_name": "DatabaseConnections",
          "runbook": "https://runbooks.example/db/orders"
        },
        {
          "metric_name": "ReplicaLag",
          "runbook": "https://runbooks.example/db/orders"
        }
      ],
      "failover_drill": {
        "last_tested_at": "2026-05-15",
        "runbook": "https://runbooks.example/db/orders/failover"
      },
      "rto_minutes": 30,
      "rpo_minutes": 5,
      "pending_reboot": false
    }
  ]
}
```

## Tests

```bash
python3 -m py_compile rds_failover_readiness_check.py tests/test_rds_failover_readiness_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This is a static review tool for saved database inventory data. It does not call AWS and it is not a replacement for real failover testing, backup restore drills, or database monitoring. I kept it dependency-free so it can run quickly from a local checkout or CI job with a generated RDS snapshot.
