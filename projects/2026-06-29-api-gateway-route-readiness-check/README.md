# API Gateway Route Readiness Check

I built this small CLI to review an API Gateway route inventory before moving a route into production. It checks the controls I usually want around public endpoints: ownership, auth, throttling, access logs, Lambda integration settings, alarms, rollback notes, and canary coverage.

## What It Does

The script reads a JSON inventory of API Gateway routes and flags:

- production routes without owners
- public production routes without strong auth
- missing throttling or throttling without positive limits
- missing access logs or undocumented log retention
- missing or long Lambda integration timeouts
- Lambda integrations that are not pinned to an alias
- missing request validation
- missing 5XX or latency alarms
- alarms without runbook links
- missing rollback notes
- critical production routes without a canary plan

It exits with `0` when the inventory is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 api_gateway_route_readiness_check.py samples/safe_inventory.json
```

Expected output:

```text
PASS: API Gateway route readiness looks ready
```

Risky sample:

```bash
python3 api_gateway_route_readiness_check.py samples/risky_inventory.json
```

Expected output starts with:

```text
FLAGGED: 15 API Gateway route readiness issue(s) detected
```

## Input Shape

```json
{
  "routes": [
    {
      "route_key": "GET /payments/{paymentId}",
      "environment": "prod",
      "owner": "payments-platform",
      "public": true,
      "critical": true,
      "auth_type": "jwt",
      "throttling": {
        "enabled": true,
        "rate_limit_per_second": 200,
        "burst_limit": 400
      },
      "access_logs": {
        "enabled": true,
        "retention_days": "30"
      },
      "integration": {
        "type": "lambda",
        "timeout_seconds": 15,
        "lambda_alias": "live",
        "request_validation": true
      },
      "alarms": [
        {
          "metric_name": "5XXError",
          "threshold": 5,
          "runbook": "https://runbooks.example/api/payments"
        },
        {
          "metric_name": "Latency",
          "threshold": 1000,
          "runbook": "https://runbooks.example/api/payments"
        }
      ],
      "rollback_note": "Shift the Lambda alias back to the previous version.",
      "canary": {
        "enabled": true,
        "percent": 10
      }
    }
  ]
}
```

## Tests

```bash
python3 -m py_compile api_gateway_route_readiness_check.py tests/test_api_gateway_route_readiness_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This is a static review tool for saved route inventory data. It does not call AWS and it is not a replacement for deployment alarms, WAF rules, or real traffic canaries. I kept it dependency-free so it can run quickly from a local checkout or CI job with a generated API Gateway snapshot.
