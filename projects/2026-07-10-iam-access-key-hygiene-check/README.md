# IAM Access Key Hygiene Check

Static IAM access keys are easy to forget after a migration or a one-time integration. I built this small CLI to review a saved inventory before those credentials become long-lived security debt.

## What it does

The checker reports:

- human users with static access keys
- active keys older than 90 days or unused for more than 45 days
- multiple active keys, missing owners, and unknown principal types
- inactive keys left around for more than 30 days
- service credentials without a rotation runbook
- active keys recently used against the IAM API

The sample values are fictional suffixes only. The inventory should never contain secret access-key material.

## How to run

```bash
python3 iam_access_key_hygiene_check.py samples/safe_inventory.json --today 2026-07-10
python3 iam_access_key_hygiene_check.py samples/risky_inventory.json --today 2026-07-10
```

The command exits with `0` when no issues are found, `1` when review findings exist, and `2` for invalid input.

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This is an offline policy check, not an AWS account scanner. In a real pipeline I would generate the input from IAM credential reports and last-used metadata, then keep account identifiers and credentials out of source control. The 90, 45, and 30 day thresholds are deliberately explicit; a production team should align them with its own credential policy.
