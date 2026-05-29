# CI Log Triage Assistant

Small Python utility that scans CI log text and flags likely failure categories with a suggested next action.

## Why this is useful
When pipelines fail, teams often lose time manually identifying whether the issue is dependency drift, runner limits, network instability, or permissions. This script gives a fast first-pass triage to speed incident response.

## Real-world use case
Use it in post-failure workflow steps or local debugging to quickly classify a failed GitHub Actions/CI run before assigning ownership.

## Skill demonstrated
- DevOps troubleshooting automation
- Pattern-based incident triage
- Practical CLI tooling for developer productivity

## Files
- `triage_ci_log.py` - triage script
- `sample_ci_failure.log` - sample failing log input

## Usage
```bash
python3 triage_ci_log.py sample_ci_failure.log
```

## Example output
```text
Log file: sample_ci_failure.log
Likely issues:
1. [high] dependency - matched 'ModuleNotFoundError' -> Install missing package and pin it in requirements/lockfile.
2. [high] dependency - matched 'No module named' -> Install missing package and pin it in requirements/lockfile.
```
