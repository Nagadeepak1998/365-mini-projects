# Deployment Window Risk Check

Deployment Window Risk Check is a small Python CLI I built to review a deployment plan before a production release.

I wanted a quick terminal check for the release questions that usually matter most: does the deploy overlap a freeze window, does it touch a critical service, is the rollout progressive, is there a real rollback plan, and are monitoring links ready?

## Problem

Production deploys can look safe in a ticket while still hiding operational risk. A risky window, thin error budget, recent incidents, or weak rollback plan can turn a routine release into an avoidable incident.

This tool gives me a repeatable way to review those signals before the deploy starts.

## What It Does

- reads a JSON deployment plan
- checks whether the deploy overlaps configured freeze windows
- flags all-at-once deployments for critical production services
- checks database-impacting changes for rollback and backup evidence
- flags low remaining error budget
- checks for recent incident pressure
- verifies production plans include monitoring links and enough approvers
- returns text output for humans or JSON output for scripts

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for local verification

## Folder Structure

```text
.
|-- README.md
|-- POST_CAPTION.md
|-- deployment_window_risk_check.py
|-- samples
|   |-- controlled_deployment.json
|   `-- risky_deployment.json
`-- tests
    `-- test_deployment_window_risk_check.py
```

## Plan Format

```json
{
  "service": "payments-api",
  "service_tier": "critical",
  "deployment": {
    "environment": "production",
    "start_time": "2026-06-15T21:30:00-07:00",
    "duration_minutes": 150,
    "change_type": "database_migration",
    "strategy": "all_at_once",
    "rollback_plan": "manual restore",
    "backup_verified": false,
    "monitoring_links": [],
    "approvers": ["release-owner"],
    "recent_incidents_14d": 3,
    "touches_shared_dependencies": true,
    "error_budget_remaining_pct": 14
  },
  "freeze_windows": [
    {
      "name": "month-end payment close",
      "start": "2026-06-15T21:00:00-07:00",
      "end": "2026-06-16T02:00:00-07:00"
    }
  ]
}
```

Timestamps must include a timezone offset so the freeze-window comparison is unambiguous.

## How to Run

From this project folder:

```bash
python3 deployment_window_risk_check.py samples/risky_deployment.json
```

Expected result:

```text
FLAGGED: 11 deployment risk issue(s)
```

Check a safer plan:

```bash
python3 deployment_window_risk_check.py samples/controlled_deployment.json
```

Expected result:

```text
PASS: catalog-api deployment plan stays within configured risk thresholds
```

Return JSON for scripting:

```bash
python3 deployment_window_risk_check.py samples/risky_deployment.json --format json --fail-on off
```

Use the exit code as a release gate:

```bash
python3 deployment_window_risk_check.py samples/risky_deployment.json --fail-on high
```

That command exits with code `2` when any high-risk issue is present.

## Example

The bundled risky sample is intentionally bad:

- it deploys `payments-api` during a freeze window
- it uses an all-at-once strategy for a critical production service
- it includes a database migration with a weak rollback plan
- it has only 14% error budget remaining
- it has no monitoring links and only one approver

Those are the kinds of signals I would want to catch before a release meeting or change review.

## Tests

```bash
python3 -m py_compile deployment_window_risk_check.py
python3 -m unittest discover -s tests
```

## Notes

- This is a local review tool, not a replacement for a full change-management system.
- If I extend it later, I would add YAML input, service ownership metadata, and per-team policy profiles.
