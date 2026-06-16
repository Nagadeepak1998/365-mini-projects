# Terraform Plan Risk Check

Terraform Plan Risk Check is a small Python CLI I built to review `terraform show -json` output before an infrastructure change lands.

I already had a basic check for Terraform output blocks in this repo. This project goes one step deeper into the plan itself so I can catch risky infrastructure changes before apply time.

## Problem

Terraform plans can look busy enough that a few dangerous lines slip through review: a database becomes public, an IAM policy quietly expands to admin-level access, or a security group opens SSH to the internet.

I wanted a quick local check for a handful of high-signal cases that are easy to explain in a review or interview.

## What It Does

- reads Terraform plan JSON from `terraform show -json`
- flags public ingress on sensitive ports such as SSH, RDP, Postgres, Redis, and Elasticsearch
- flags RDS instances that are marked `publicly_accessible = true`
- flags S3 public access blocks that disable bucket protections
- flags IAM policies that allow wildcard action and wildcard resource
- returns readable terminal output or JSON output for scripts

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for verification

## Folder Structure

```text
.
|-- README.md
|-- terraform_plan_risk_check.py
|-- samples
|   |-- risky_plan.json
|   `-- safe_plan.json
`-- tests
    `-- test_terraform_plan_risk_check.py
```

## How to Run

From this project folder:

```bash
python3 terraform_plan_risk_check.py samples/risky_plan.json
```

Expected result:

```text
FLAGGED: 4 Terraform plan risk issue(s)
```

Check the safer sample:

```bash
python3 terraform_plan_risk_check.py samples/safe_plan.json
```

Expected result:

```text
PASS: no configured Terraform plan risks detected
```

Return JSON instead:

```bash
python3 terraform_plan_risk_check.py samples/risky_plan.json --format json
```

Use it with real Terraform output:

```bash
terraform show -json tfplan > tfplan.json
python3 terraform_plan_risk_check.py tfplan.json
```

## Example

The bundled risky sample includes four review problems:

- SSH is open to `0.0.0.0/0`
- the RDS instance is publicly accessible
- S3 public access protections are being relaxed
- an IAM policy grants `Action: "*"` on `Resource: "*"`

Those are the kinds of changes I would want to catch before an apply reaches production.

## Tests

```bash
python3 -m py_compile terraform_plan_risk_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

- This is intentionally a narrow review tool, not a full Terraform policy engine.
- If I extend it later, I would add workspace-aware rules, plan-file metadata, and custom allowlists for approved public services.
