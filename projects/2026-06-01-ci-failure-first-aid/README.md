# CI Failure First Aid

Small rule-based helper that scans a CI log and classifies the first likely failure category with a practical next troubleshooting step.

## Real-world use case

When GitHub Actions or any CI job fails, teams lose time jumping between random fixes. This tool gives a fast first response path for common issues like DNS outages, token permissions, dependency install breaks, and failing tests.

## Usage

```bash
python3 ci_failure_first_aid.py sample_ci_log.txt
```

Or point it at any CI log file:

```bash
python3 ci_failure_first_aid.py /path/to/failing.log
```

## Example output

```text
Category: Network/DNS
Recommended next step: Check runner egress/DNS health, retry once, then pin and mirror critical downloads.
```

## Skill demonstrated

- DevOps incident triage automation
- Pattern-based log analysis
- Practical reliability mindset for CI/CD operations
