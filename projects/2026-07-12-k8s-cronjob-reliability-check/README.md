# Kubernetes CronJob Reliability Check

I built this small CLI to review scheduled Kubernetes workloads before relying on them for production housekeeping, reports, or batch processing.

## Problem

CronJobs can quietly stop running, overlap an earlier execution, retry for too long, or leave too little history to diagnose a failure. Those settings are easy to miss when several scheduled workloads are reviewed together.

## What it does

The checker reads a saved JSON inventory and flags:

- missing ownership or suspended schedules
- overlapping runs allowed by `concurrencyPolicy`
- missing start and execution deadlines
- excessive retries
- disabled successful or failed job history
- missing CPU and memory controls
- missing or stale successful-run evidence

It is dependency-free and returns exit code `0` for a clean inventory or `1` when it finds risks.

## How to run

```bash
python3 cronjob_reliability_check.py samples/safe_inventory.json --today 2026-07-12
python3 cronjob_reliability_check.py samples/risky_inventory.json --today 2026-07-12
```

The `--today` option makes stale-run checks deterministic in tests and saved examples.

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This project works with a small normalized inventory instead of parsing Kubernetes YAML directly. That keeps the review logic easy to test, but a real cluster integration would need an adapter that maps CronJob API fields and recent Job status into this format.
