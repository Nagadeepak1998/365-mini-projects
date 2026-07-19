# OpenTelemetry Sampling Budget Planner

## Problem

Trace sampling has two competing goals: preserve useful production evidence and keep collector volume affordable. A percentage that looks small can still overload the pipeline when traffic or trace width grows.

## What it does

This dependency-free Python CLI reviews a JSON sampling plan. It estimates spans per second for each service, compares the total with a shared collector budget, and checks that critical services retain useful baseline, error, and high-latency coverage.

The model intentionally estimates baseline head-sampling volume. Error and latency rates are coverage-policy checks because tail-sampling overlap depends on the collector configuration and should not be double-counted without real telemetry.

## How to run

```bash
python3 otel_sampling_budget_planner.py samples/safe_plan.json
python3 otel_sampling_budget_planner.py samples/risky_plan.json
python3 otel_sampling_budget_planner.py samples/safe_plan.json --json
```

A safe plan exits `0`. A plan with coverage gaps or excessive volume exits `1`, which makes the command useful as a CI policy check.

## Example

```text
PASS: estimated 800.00 spans/s, headroom 700.00 spans/s
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Notes

The estimate is a planning aid, not a replacement for collector metrics. Real systems should compare it with accepted, refused, and exported span metrics, then adjust policies as traffic changes.
