# Terraform State Safety Check

## Problem

Terraform state can contain sensitive infrastructure details and is also the coordination point for every apply. A backend that lacks encryption, version history, locking, or recovery practice can turn a routine deployment into data exposure or state corruption.

I built this small CLI to review a normalized inventory of Terraform backends before relying on them for shared environments.

## What it does

The checker flags:

- production state stored on a local machine
- local state that is not confirmed as gitignored or backed up
- S3 backends missing bucket, key, or region details
- missing S3 encryption, versioning, or public-access blocking
- S3 and remote backends without confirmed state locking
- missing backend owners or environment labels
- missing or older-than-90-day state recovery drills

It returns `0` when the inventory passes, `1` when risks are found, and `2` for invalid input. That makes it usable as a local review or CI gate.

## How to run

Python 3.10 or newer is enough; there are no third-party dependencies.

```bash
python3 terraform_state_safety_check.py samples/safe_inventory.json --today 2026-07-13
python3 terraform_state_safety_check.py samples/risky_inventory.json --today 2026-07-13
python3 terraform_state_safety_check.py samples/risky_inventory.json --today 2026-07-13 --format json
```

## Example

The safe fixture prints:

```text
PASS: Terraform backend inventory meets the state safety checks
```

The risky fixture prints individual findings and finishes with:

```text
FLAGGED: 11 Terraform state safety issue(s) detected
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
python3 -m py_compile terraform_state_safety_check.py tests/test_terraform_state_safety_check.py
```

The tests cover a passing inventory, the expected risky controls, duplicate-name validation, and CLI exit-code behavior.

## Notes

The input is intentionally a normalized JSON inventory instead of raw Terraform configuration. That keeps the checker deterministic across backend configuration styles, but it means the inventory must come from a trusted discovery step. This tool verifies declared controls; it does not contact S3 or Terraform Cloud to prove their live settings.
