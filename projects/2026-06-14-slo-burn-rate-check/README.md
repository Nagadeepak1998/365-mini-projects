# SLO Burn Rate Check

SLO Burn Rate Check is a small Python CLI I built to review a service error-budget snapshot and tell me whether the current error rate is burning through a 30-day budget too quickly.

I wanted a simple way to turn raw request and error counts into a signal I can use during incident triage or after a noisy deploy.

## Problem

When a service starts failing, the error rate by itself does not answer the question I usually care about: how fast am I consuming the error budget relative to the SLO? A 1% error rate might be minor for one service and a serious incident for another depending on the target.

## What It Does

- reads a JSON snapshot with request and error counts for one service across multiple windows
- calculates the allowed error rate from the SLO target
- computes burn rate per window
- flags windows that cross common fast-burn or slow-burn thresholds
- estimates how long a 30-day budget would last at the current rate
- returns text output for humans or JSON output for scripts

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for local verification

## Folder Structure

```text
.
|-- README.md
|-- POST_CAPTION.md
|-- samples
|   |-- healthy_snapshot.json
|   `-- risky_snapshot.json
|-- slo_burn_rate_check.py
`-- tests
    `-- test_slo_burn_rate_check.py
```

## Snapshot Format

```json
{
  "service": "checkout-api",
  "slo_target": 99.9,
  "windows": [
    {"name": "5m", "requests": 12000, "errors": 210},
    {"name": "1h", "requests": 120000, "errors": 1800},
    {"name": "6h", "requests": 720000, "errors": 1900}
  ]
}
```

Supported default thresholds:

- `5m` and `1h` alert at `14x`
- `30m` and `6h` alert at `6x`
- any other window falls back to `2x`

## How to Run

From this project folder:

```bash
python3 slo_burn_rate_check.py samples/risky_snapshot.json
```

Expected result:

```text
FLAGGED: 2 burn-rate alert(s)
```

Check a healthy sample:

```bash
python3 slo_burn_rate_check.py samples/healthy_snapshot.json
```

Expected result:

```text
PASS: no burn-rate alerts crossed the configured thresholds
```

Return JSON instead of plain text:

```bash
python3 slo_burn_rate_check.py samples/risky_snapshot.json --format json
```

## Example

In the bundled risky snapshot:

- the `5m` window is burning error budget at `17.50x`
- the `1h` window is also at `15.00x`
- the `6h` window is elevated but stays below the default `6x` threshold

That means the short-term incident signal is strong even though the longer window has not crossed its own alert threshold yet.

## Tests

```bash
python3 -m py_compile slo_burn_rate_check.py
python3 -m unittest discover -s tests
```

## Notes

- This tool does not replace Prometheus or an alert manager. It is a quick local check for saved metrics snapshots or incident notes.
- If I wanted to grow it further, I would add support for multiple services in one file and direct parsing of Prometheus query results.
