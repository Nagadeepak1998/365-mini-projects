# Feature Flag Risk Check

This is a small CLI for reviewing feature flag rollout changes before they go to production.

## Problem

Feature flags make releases safer, but they can also hide risky changes. A flag can jump from a small canary to 100%, lose its owner, keep debug behavior enabled, or stay partially rolled out after its cleanup date.

I wanted a simple check that can compare the current flag config with a proposed config and call out the changes I would want to review before a release.

## What it does

The checker reads two JSON files:

- current feature flag state
- proposed feature flag state

It flags:

- rollout increases greater than 50 percentage points
- full rollouts without a rollback note
- missing owners
- missing or expired cleanup dates
- debug behavior enabled in production
- active rollouts with no kill switch

The input format is intentionally small:

```json
{
  "flags": [
    {
      "name": "smart_retry",
      "environment": "prod",
      "rollout_percent": 10,
      "owner": "reliability",
      "expires_on": "2026-08-01",
      "kill_switch": true,
      "rollback": "Disable smart_retry in the flag console."
    }
  ]
}
```

## How to run

From this folder:

```bash
python3 feature_flag_risk_check.py samples/current_flags.json samples/proposed_safe_flags.json --today 2026-06-23
```

Expected output:

```text
PASS: no feature flag rollout risks detected
```

Risky sample:

```bash
python3 feature_flag_risk_check.py samples/current_flags.json samples/proposed_risky_flags.json --today 2026-06-23
```

Expected output:

```text
FLAGGED: 6 feature flag risk(s) detected
- [HIGH] smart_retry: rollout increases from 10% to 100% in one change
- [HIGH] smart_retry: reaches full rollout without a rollback note or runbook link
- [MEDIUM] smart_retry: missing owner for follow-up during incidents
- [MEDIUM] smart_retry: flag expired on 2026-01-15 but is still active
- [HIGH] smart_retry: debug behavior is enabled in prod
- [MEDIUM] smart_retry: rollout has no kill switch
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
python3 -m py_compile feature_flag_risk_check.py
```

## Notes

This is not trying to replace a feature flag platform. It is a lightweight release review check for config files, pull request examples, or exported flag snapshots.
