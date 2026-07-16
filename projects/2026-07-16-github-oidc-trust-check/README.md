# GitHub Actions OIDC Trust Check

Long-lived cloud keys in CI are difficult to rotate and easy to expose. GitHub Actions OIDC removes those stored credentials, but an overly broad cloud trust policy can still let the wrong workflow request a powerful role.

## What it does

I built this offline CLI to review a normalized inventory of GitHub Actions OIDC trust bindings. It flags:

- missing owners, incorrect token issuers, and unexpected audiences
- wildcard or malformed repository subjects
- pull request workflows trusted with a cloud role
- production roles that are not bound to a protected production environment
- missing production approvals
- missing `id-token: write` or overly broad repository contents access

## How to run

```bash
python3 github_oidc_trust_check.py samples/safe.json
python3 github_oidc_trust_check.py samples/risky.json
```

The command exits with `0` when the inventory passes, `1` when findings need review, and `2` for invalid input.

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Notes

The input is intentionally normalized instead of tied to one cloud provider's policy document. The sample uses AWS STS as the audience and models the GitHub `sub` claim directly. A production integration could translate AWS IAM, Azure federated credentials, or Google Workload Identity bindings into the same review shape.
