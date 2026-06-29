Today I added a small API Gateway route readiness checker.

The idea is simple: before a public route goes live, I want a quick way to confirm the basics are not missing. The CLI reviews saved route inventory JSON for ownership, auth, throttling, access logs, Lambda timeout settings, alias pinning, request validation, 5XX/latency alarms, runbook links, rollback notes, and canary coverage.

It is intentionally dependency-free and uses safe/risky sample inventories with unit tests, so I can run it locally or wire it into a lightweight CI check later.
