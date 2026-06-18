# Prometheus Rule Sanity Check

Prometheus Rule Sanity Check is a small Python CLI I built to review `PrometheusRule` snapshots for alert metadata gaps that usually slow down incident response.

The last few projects in this repo focused on rollout and infrastructure risk. This one is narrower: it checks whether alert rules carry the ownership and response context I would want when a page fires.

## Problem

An alert can be technically valid and still be hard to work with in production. Missing severity labels, no runbook link, no dashboard link, or no ownership label all add friction when someone is trying to respond quickly.

I wanted a lightweight check I could run against a cluster snapshot before merging alert changes.

## What It Does

- reads `kubectl get prometheusrule -A -o json` output
- flags alert rules that do not define a severity label
- flags page-level alerts without a `for` window
- flags alert rules that are missing `runbook_url`
- flags alert rules that are missing `dashboard_url`
- flags alert rules that are missing a `summary`
- flags alert rules without a `team`, `owner`, or `service` label

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for verification

## Folder Structure

```text
.
|-- README.md
|-- prometheus_rule_sanity_check.py
|-- samples
|   |-- risky_rules.json
|   `-- safe_rules.json
`-- tests
    `-- test_prometheus_rule_sanity_check.py
```

## How to Run

From this project folder:

```bash
python3 prometheus_rule_sanity_check.py samples/risky_rules.json
```

Expected result:

```text
FLAGGED: 8 Prometheus alert metadata issue(s)
```

Check the safer sample:

```bash
python3 prometheus_rule_sanity_check.py samples/safe_rules.json
```

Expected result:

```text
PASS: no Prometheus alert metadata gaps detected
```

Return JSON instead:

```bash
python3 prometheus_rule_sanity_check.py samples/risky_rules.json --format json
```

Use it with a real cluster snapshot:

```bash
kubectl get prometheusrule -A -o json > prometheus-rules.json
python3 prometheus_rule_sanity_check.py prometheus-rules.json
```

## Example

The bundled risky sample includes:

- a critical alert with no `for` window
- alerts with no runbook or dashboard link
- a warning alert with no severity label
- alerts with no clear ownership label
- an alert with no summary annotation

Those are the kinds of gaps I want to catch before an alert lands in a real on-call rotation.

## Tests

```bash
python3 -m py_compile prometheus_rule_sanity_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

- This is intentionally a narrow metadata check, not a full Prometheus rule validator.
- It expects JSON input so it can stay dependency-free and easy to run in CI or from a local shell.
