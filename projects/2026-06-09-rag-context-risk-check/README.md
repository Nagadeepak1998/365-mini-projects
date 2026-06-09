# RAG Context Risk Check

Small Python CLI that scans retrieved text chunks for prompt-injection style instructions before sending that context into an LLM or agent workflow.

## Real-world use case

Teams often feed support articles, uploaded documents, or scraped web pages into RAG pipelines. Some of that content can contain adversarial instructions such as "ignore previous instructions" or requests to reveal hidden prompts. This script provides a quick local safety check before that context gets embedded in an app or copied into a debugging prompt.

## What this project demonstrates

- Practical AI guardrails for retrieval pipelines
- Lightweight prompt-injection detection without external dependencies
- Developer productivity tooling for LLM app debugging and review

## Usage

Run against the included suspicious sample:

```bash
python3 rag_context_risk_check.py sample_untrusted_context.txt
```

Run against the included clean sample:

```bash
python3 rag_context_risk_check.py sample_safe_context.txt
```

## What it checks

- Attempts to override prior instructions
- Requests to reveal system prompts or hidden rules
- Attempts to exfiltrate credentials or environment variables
- Instructions to call tools, browse URLs, or take external actions

## Exit codes

- `0` when no risky content is found
- `1` when one or more risky lines are reported
- `2` when the input file is missing or invalid

## Skill demonstrated

AI application safety, RAG pipeline hygiene, and practical Python automation.
