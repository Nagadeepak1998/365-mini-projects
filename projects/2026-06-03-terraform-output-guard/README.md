# Terraform Output Guard

Small Python CLI that checks Terraform `output` blocks for two common review misses: missing descriptions and secret-looking outputs that are not marked `sensitive`.

## Real-world use case

Teams often expose Terraform outputs for app URLs, IDs, and connection details. During fast delivery, outputs can ship without descriptions or accidentally print secret values into CI logs and deployment summaries. This tool gives a cheap local review step before opening a pull request.

## What this project demonstrates

- Practical IaC review automation
- Security-minded Terraform hygiene checks
- CI-friendly Python scripting for DevOps workflows

## Usage

Run the checker against the included sample:

```bash
python3 terraform_output_guard.py sample_outputs.tf
```

Run it against the corrected sample:

```bash
python3 terraform_output_guard.py sample_outputs_fixed.tf
```

## What it checks

- Every `output` block should include a `description`
- Outputs with names like `password`, `secret`, `token`, or `key` should include `sensitive = true`

## Exit codes

- `0` when no issues are found
- `1` when one or more issues are found
- `2` when the input file is missing or invalid

## Skill demonstrated

Terraform review automation, cloud security awareness, and lightweight developer tooling.
