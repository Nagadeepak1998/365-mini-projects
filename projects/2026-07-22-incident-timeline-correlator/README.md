# Incident Timeline Correlator

## Problem

During an incident, deployment, alert, and log timestamps often live in different tools. I wanted a small way to turn exported events into one focused timeline before forming a root-cause hypothesis.

## What it does

This dependency-free Python CLI filters normalized JSON events by service and incident window, orders them deterministically, counts symptom events, and highlights the latest change before the incident anchor as the first trigger to investigate. It can produce Markdown for an incident note or JSON for another tool.

The highlighted change is correlation evidence, not proof of causation. The output is meant to guide investigation while keeping that distinction explicit.

## How to run

```bash
python3 incident_timeline.py samples/incident_events.json \
  --incident-time 2026-07-22T10:00:00Z \
  --service checkout
```

For machine-readable output:

```bash
python3 incident_timeline.py samples/incident_events.json \
  --incident-time 2026-07-22T10:00:00Z \
  --service checkout \
  --format json
```

The command exits `0` when matching events exist, `1` when the selected window is empty, and `2` for invalid input.

## Example

The sample produces a three-event checkout timeline: a deployment at 09:45, an error-rate alert at 09:58, and a timeout log at 10:03. The deployment is highlighted as the latest pre-incident change to investigate.

## Tests

```bash
python3 -m py_compile incident_timeline.py tests/test_incident_timeline.py
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Notes

The input format is intentionally normalized instead of integrating directly with vendor APIs. That keeps the project runnable without credentials and makes the sorting and correlation behavior easy to test. A production version would add adapters for deployment, observability, and ticketing systems while retaining the same normalized event contract.
