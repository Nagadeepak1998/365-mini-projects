# GitHub Action Pin Check

Small Python CLI that scans a GitHub Actions workflow for `uses:` entries pinned to risky floating refs like `@main`, `@master`, `@latest`, or `@HEAD`.

## Real-world use case

Teams often copy workflow snippets from examples or older repositories. That can leave production CI depending on moving branch refs for third-party actions, which makes builds less predictable and increases supply-chain risk. This tool provides a cheap pre-review check before merging workflow changes.

## What this project demonstrates

- Practical GitHub Actions hygiene automation
- DevSecOps review thinking for CI/CD pipelines
- Lightweight Python tooling for repository checks

## Usage

Run the checker against the included risky sample:

```bash
python3 github_action_pin_check.py sample_risky_workflow.yml
```

Run it against the corrected sample:

```bash
python3 github_action_pin_check.py sample_safe_workflow.yml
```

## What it checks

- Flags `uses:` references pinned to `@main`
- Flags `uses:` references pinned to `@master`
- Flags `uses:` references pinned to `@latest`
- Flags `uses:` references pinned to `@HEAD`

## Exit codes

- `0` when no risky refs are found
- `1` when one or more risky refs are found
- `2` when the input file is missing or invalid

## Skill demonstrated

GitHub Actions review automation, CI/CD security awareness, and practical Python scripting.
