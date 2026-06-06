# Log Anomaly Buckets

Small Python CLI that scans plain-text application logs and groups suspicious lines into quick triage buckets such as `server_error`, `slow_request`, `timeout`, and `connectivity`.

## Real-world use case

During an incident, engineers often have only raw logs from a failed deployment, background worker, or API path. Before opening a full observability tool, this script gives a fast local summary of what kind of failure pattern is showing up most often, which helps narrow the next debugging step.

## What this project demonstrates

- Practical incident-response automation
- Log analysis patterns useful in AI and cloud application support
- Lightweight Python tooling for developer productivity

## Usage

Run against the included sample log:

```bash
python3 log_anomaly_buckets.py sample_app.log
```

Use a stricter or looser slow-request threshold:

```bash
python3 log_anomaly_buckets.py sample_app.log 1500
```

## What it checks

- `status=5xx` as `server_error`
- `status=429` as `rate_limited`
- `latency_ms` above a configurable threshold as `slow_request`
- Timeout, connectivity, and generic application error phrases

## Exit codes

- `0` when no suspicious lines are found
- `1` when one or more suspicious lines are bucketed
- `2` when the input file is missing or invalid

## Skill demonstrated

Incident triage automation, cloud application troubleshooting, and practical Python scripting.
