# Prompt Regression Check

Small Python CLI that runs lightweight regression checks against saved LLM responses before you update a prompt, model, or system instruction.

## Real-world use case

Teams often tweak prompts and only notice quality regressions after shipping. This tool gives a cheap local gate for exact requirements like "must mention rollback" or "must not leak secrets" before a change lands in CI.

## What this project demonstrates

- Practical prompt evaluation without paid APIs
- Developer tooling for repeatable AI quality checks
- Simple rule-based guardrails that fit CI/CD workflows

## Usage

Run the passing sample:

```bash
python3 prompt_regression_check.py sample_cases_pass.json
```

Run the failing sample:

```bash
python3 prompt_regression_check.py sample_cases_fail.json
```

## Input format

Each JSON file contains an array of test cases:

```json
[
  {
    "name": "incident summary",
    "actual": "Investigate the error and roll back if needed.",
    "required_terms": ["error", "roll back"],
    "forbidden_terms": ["password"],
    "min_length": 20
  }
]
```

## Exit codes

- `0` when every case passes
- `1` when one or more cases fail
- `2` when the input file is missing or invalid

## Skill demonstrated

Prompt engineering evaluation, CI-friendly Python automation, and practical AI guardrail design.
