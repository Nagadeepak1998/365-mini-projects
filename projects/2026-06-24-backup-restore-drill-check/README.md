# Backup Restore Drill Check

This is a small CLI for reviewing whether service backups are ready for a real restore drill.

## Problem

Backups can look fine on paper while still being risky in practice. A job may be stale, a restore may not have been tested recently, retention may be too short, or nobody may own the follow-up when a restore fails.

I wanted a quick check I could run against a simple inventory export before a production-support review.

## What it does

The checker reads a JSON inventory of services and flags:

- backups older than the service RPO
- failed or missing latest backup status
- stale or missing restore drill dates
- missing owners
- short retention windows
- backups without confirmed encryption
- critical services without confirmed cross-region backups

The input format is intentionally small:

```json
{
  "services": [
    {
      "name": "payments-db",
      "tier": "critical",
      "owner": "payments-platform",
      "backup_status": "success",
      "latest_backup_at": "2026-06-24",
      "latest_restore_test_at": "2026-06-10",
      "restore_test_interval_days": 30,
      "rpo_hours": 24,
      "retention_days": 35,
      "encrypted": true,
      "cross_region": true
    }
  ]
}
```

## How to run

From this folder:

```bash
python3 backup_restore_drill_check.py samples/safe_inventory.json --today 2026-06-24
```

Expected output:

```text
PASS: backup restore drill inventory is ready
```

Risky sample:

```bash
python3 backup_restore_drill_check.py samples/risky_inventory.json --today 2026-06-24
```

Expected output:

```text
FLAGGED: 7 backup restore risk(s) detected
- [MEDIUM] orders-db: missing owner for backup follow-up
- [HIGH] orders-db: latest backup is 96h old, above 24h RPO
- [HIGH] orders-db: latest backup status is failed
- [HIGH] orders-db: restore test is 165 days old, above 60 day target
- [MEDIUM] orders-db: retention is only 7 days
- [HIGH] orders-db: backup encryption is not confirmed
- [MEDIUM] orders-db: critical service has no confirmed cross-region backup
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
python3 -m py_compile backup_restore_drill_check.py
```

## Notes

This is not a backup platform. It is a lightweight review step for service inventory exports, restore drill planning, and production-readiness checks.
