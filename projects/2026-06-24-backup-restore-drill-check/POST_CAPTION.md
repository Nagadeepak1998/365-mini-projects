Built a small backup restore drill checker today.

The idea is simple: backups are only useful if someone can restore them within the target window. This CLI reviews a JSON inventory and flags stale backups, old restore tests, failed jobs, short retention, missing owners, missing encryption, and critical systems without cross-region coverage.

It is dependency-free Python with sample safe/risky inputs and unit tests:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
python3 backup_restore_drill_check.py samples/risky_inventory.json --today 2026-06-24
```

Small project, but it matches a real production-support habit: do not wait for an outage to discover the restore plan was not actually ready.
