# LLM Log Redaction Check

Small Python CLI that scans logs or transcripts for common secrets and PII before sharing them with an LLM, ticket, or chat channel.

## Real-world use case

Engineers often paste incident logs into AI tools to summarize outages or explain failures. This script provides a fast local preflight check so obvious secrets or personal data do not get shared accidentally.

## What this project demonstrates

- Practical AI safety guardrails for day-to-day engineering work
- Regex-based log hygiene automation without external dependencies
- Developer productivity scripting around incident response workflows

## Usage

Run against the included sample log with unsafe content:

```bash
python3 llm_log_redaction_check.py sample_incident_log.txt
```

Run against the included clean sample:

```bash
python3 llm_log_redaction_check.py sample_clean_log.txt
```

## What it checks

- Bearer tokens and API key style prefixes
- AWS access key id patterns
- Slack token patterns
- Email addresses
- IPv4 addresses
- Generic secret assignments such as `password=...` or `token: ...`

## Exit codes

- `0` when no risky content is found
- `1` when one or more risky lines are reported
- `2` when the input file is missing or invalid

## Skill demonstrated

AI safety hygiene, incident response prep, and lightweight Python automation.
