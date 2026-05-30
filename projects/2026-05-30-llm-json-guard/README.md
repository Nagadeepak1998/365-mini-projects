# LLM JSON Guard

A tiny CLI to validate LLM-generated JSON against a required schema before downstream automation runs.

## Why this is useful

In AI workflows, malformed JSON is a common failure mode that breaks CI jobs, deployment scripts, or incident-response automations. This tool adds a fast validation gate so bad payloads fail early with clear errors.

## What this demonstrates

- Prompt/LLM output hardening for production workflows
- Lightweight Python tooling for CI/CD pipelines
- Practical schema validation with actionable failure messages

## Usage

```bash
python3 llm_json_guard.py --schema sample_schema.json --input sample_valid.json
python3 llm_json_guard.py --schema sample_schema.json --input sample_invalid.json
```

To use in CI, run the command against model output and fail the job when exit code is non-zero.

## Example CI step

```bash
python3 llm_json_guard.py --schema schema.json --input model_output.json
```

Exit codes:
- `0`: valid payload
- `1`: invalid payload or bad input
