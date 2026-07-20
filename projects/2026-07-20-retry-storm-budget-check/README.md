# Retry Storm Budget Check

Retries can turn a small upstream slowdown into a much larger downstream load spike. I built this CLI to make that amplification visible before a retry policy reaches production.

## Problem

When several services retry the same request path, their retry counts multiply. Three attempts in an API and three attempts in its worker can create up to nine downstream attempts for one original request. Backoff helps with timing, but it does not remove that worst-case capacity demand.

## What it does

The checker reads a JSON description of a request path and:

- calculates worst-case retry amplification across service hops
- compares amplified traffic with a downstream request budget
- checks for exponential backoff and jitter
- flags retries of non-idempotent operations
- compares per-attempt timeouts with the retry deadline
- returns exit code `0` for `PASS` and `1` for `FLAGGED`

## How to run

```bash
python3 retry_storm_budget_check.py samples/safe.json
python3 retry_storm_budget_check.py samples/risky.json
python3 retry_storm_budget_check.py samples/risky.json --json
```

Example safe result:

```text
PASS: worst-case 150.00 req/s, amplification 3.00x, headroom 100.00 req/s
```

The risky sample models two layers with two retries each. At 100 incoming requests per second, the worst-case load becomes 900 requests per second against a 500 request-per-second budget.

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Notes

This is a conservative planning model, not a traffic simulator. It assumes every configured attempt can reach the next hop, so it is useful for setting an upper bound. Real traffic may be lower because requests can succeed early, circuit breakers can open, and retry budgets may be shared. The tradeoff is intentional: the output stays simple enough to review in CI while making cascading retry risk explicit.
