# Secret Rotation Readiness Check

This is a small CLI for reviewing whether service secrets are ready for a planned rotation.

## Problem

Secret rotation often fails for operational reasons, not because the secret manager cannot rotate a value. The risky parts are usually ownership, stale credentials, missing validation, no rollback path, or a critical service that cannot tolerate overlap between old and new credentials.

I wanted a quick check I could run against a simple inventory before a rotation window.

## What it does

The checker reads a JSON inventory of secrets and flags:

- secrets older than their rotation target
- overdue or missing next rotation dates
- missing owners
- critical-path secrets without dual-secret overlap support
- missing rollback plans
- failed or missing validation status
- stale validation evidence
- stale or missing break-glass access review dates for critical secrets

The input format is intentionally small:

```json
{
  "secrets": [
    {
      "name": "payments-api-db-password",
      "owner": "payments-platform",
      "last_rotated_at": "2026-06-10",
      "next_rotation_due": "2026-07-10",
      "rotation_interval_days": 45,
      "used_by_critical_path": true,
      "dual_secret_supported": true,
      "rollback_plan": "Keep the previous password active until health checks pass.",
      "validation_status": "passed",
      "last_validation_at": "2026-06-24",
      "break_glass_access_reviewed_at": "2026-06-01"
    }
  ]
}
```

## How to run

From this folder:

```bash
python3 secret_rotation_readiness_check.py samples/safe_inventory.json --today 2026-06-25
```

Expected output:

```text
PASS: secret rotation inventory is ready
```

Risky sample:

```bash
python3 secret_rotation_readiness_check.py samples/risky_inventory.json --today 2026-06-25
```

Expected output:

```text
FLAGGED: 8 secret rotation risk(s) detected
- [MEDIUM] orders-api-token: missing owner for rotation follow-up
- [HIGH] orders-api-token: secret is 161 days old, above 60 day rotation target
- [HIGH] orders-api-token: rotation is 26 day(s) overdue
- [HIGH] orders-api-token: critical path secret cannot rotate with dual-secret overlap
- [MEDIUM] orders-api-token: missing rollback plan
- [HIGH] orders-api-token: latest validation status is failed
- [MEDIUM] orders-api-token: validation evidence is 85 days old
- [MEDIUM] orders-api-token: break-glass access review is 175 days old
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
python3 -m py_compile secret_rotation_readiness_check.py
```

## Notes

This is not a secret manager. It is a lightweight review step for rotation planning, production-readiness checks, and release windows where credentials are part of the change.
