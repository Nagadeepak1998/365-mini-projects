# AI Response Contract Check

## Problem

Prompt and model changes can produce answers that look reasonable while quietly breaking the contract an application depends on. I wanted a small evaluation tool that checks saved model responses without requiring an API key or a specific AI provider.

## What it does

This dependency-free Python CLI evaluates JSON test cases against explicit response contracts. A case can require valid JSON, nested keys, exact values, required phrases, forbidden phrases, and latency or cost limits.

The report shows every failed rule instead of stopping at the first one, so it is useful in a local prompt-development loop or a CI job. It exits `1` when any case fails.

## How to run

```bash
python3 response_contract_check.py samples/passing_cases.json
python3 response_contract_check.py samples/regression_cases.json
```

For machine-readable output:

```bash
python3 response_contract_check.py samples/regression_cases.json --format json
```

The command exits `0` when all contracts pass, `1` when a response violates a contract, and `2` for invalid input.

## Input contract

Each test case contains an `id`, an `output`, and a `contract`. JSON output may be stored as an object or as a string, which makes the tool work with both parsed fixtures and raw provider responses.

```json
{
  "id": "support-triage",
  "output": "{\"category\":\"billing\",\"escalate\":true}",
  "latency_ms": 420,
  "cost_usd": 0.0012,
  "contract": {
    "type": "json",
    "required_keys": ["category", "escalate"],
    "exact_values": {"escalate": true},
    "forbidden_terms": ["password"],
    "max_latency_ms": 800,
    "max_cost_usd": 0.002
  }
}
```

Nested JSON fields use dot paths such as `customer.priority`.

## Tests

```bash
python3 -m py_compile response_contract_check.py tests/test_response_contract_check.py
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Notes

This is a deterministic contract check, not a judge of answer quality or factual correctness. The deliberate tradeoff is repeatability: semantic scoring still belongs in a separate evaluation layer with reviewed datasets and human calibration.
