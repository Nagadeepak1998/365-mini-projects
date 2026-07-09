# Lambda Production Readiness Check

This is a small Python CLI for reviewing a saved AWS Lambda inventory before I treat a function as production-ready.

## Problem

Lambda functions can look simple until they become part of a production path. The common misses are usually operational: no owner, old runtime, `$LATEST` traffic, weak alarms, no async failure destination, inline secrets, or rollback drills that have gone stale.

## What it does

The checker reads a JSON inventory and flags practical readiness gaps:

- missing owner or runtime data
- unsupported runtimes
- production traffic pointed at `$LATEST` or no alias
- weak alarm coverage
- async functions without a DLQ or on-failure destination
- missing reserved concurrency on production functions
- missing structured logs or tracing
- long API/ALB timeouts
- invalid memory settings
- environment variables that look like inline secrets
- stale deploys or rollback drills

It is intentionally dependency-free so it can run in a clean Python environment.

## How to run

```bash
python3 lambda_production_readiness_check.py samples/safe_inventory.json --today 2026-07-09
python3 lambda_production_readiness_check.py samples/risky_inventory.json --today 2026-07-09
```

## Example

```text
PASS: Lambda production inventory looks ready
```

```text
FLAGGED: 19 Lambda production readiness issue(s) detected
- [HIGH] checkout-api-prod: missing-owner - production functions need an accountable owner
- [HIGH] checkout-api-prod: unsupported-runtime - runtime nodejs14.x is outside the supported runtime list
...
```

## Tests

```bash
python3 -m py_compile lambda_production_readiness_check.py tests/test_lambda_production_readiness_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This does not call AWS. It reviews exported inventory data so I can practice the operational thinking behind Lambda ownership, incident response, and deployment safety without needing cloud credentials.
