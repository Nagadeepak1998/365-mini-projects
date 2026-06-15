# Alert Noise Budget Check

Alert Noise Budget Check is a small Python CLI I built to review one week of paging history and flag alerts that are creating more noise than useful action.

I wanted something simple that could answer a practical on-call question: which alerts are burning attention without producing enough real incidents or actionable pages?

## Problem

It is easy for a paging setup to drift into a bad state where the same alert keeps firing, gets acknowledged inconsistently, and rarely turns into work that matters. That kind of alert trains people to ignore pages, which is the opposite of what I want from on-call signals.

## What It Does

- reads a JSON snapshot of alert history for one service
- focuses on `page` severity alerts
- flags low-actionability alerts once they cross a page-count threshold
- flags alerts that keep paging multiple times for the same incident
- flags alerts with poor acknowledgement rates
- returns text output for a quick terminal check or JSON for scripts

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for local verification

## Folder Structure

```text
.
|-- README.md
|-- POST_CAPTION.md
|-- alert_noise_budget_check.py
|-- samples
|   |-- healthy_alerts.json
|   `-- noisy_alerts.json
`-- tests
    `-- test_alert_noise_budget_check.py
```

## Snapshot Format

```json
{
  "service": "checkout-api",
  "window": "7d",
  "alerts": [
    {
      "name": "checkout-latency-high",
      "severity": "page",
      "pages": 8,
      "unique_incidents": 2,
      "acknowledged_pages": 6,
      "actionable_pages": 3
    }
  ]
}
```

Each alert entry uses:

- `pages`: how many times the alert paged during the review window
- `unique_incidents`: how many distinct incidents those pages represented
- `acknowledged_pages`: how many pages were acknowledged
- `actionable_pages`: how many pages led to real action instead of being noise

## How to Run

From this project folder:

```bash
python3 alert_noise_budget_check.py samples/noisy_alerts.json
```

Expected result:

```text
FLAGGED: 5 alert-noise issue(s)
```

Check a healthier sample:

```bash
python3 alert_noise_budget_check.py samples/healthy_alerts.json
```

Expected result:

```text
PASS: no page alerts crossed the configured noise thresholds
```

Return JSON instead of text:

```bash
python3 alert_noise_budget_check.py samples/healthy_alerts.json --format json
```

Tighten or relax the page threshold:

```bash
python3 alert_noise_budget_check.py samples/noisy_alerts.json --page-threshold 4
```

## Example

In the bundled noisy sample:

- `checkout-latency-high` paged 8 times for only 2 distinct incidents
- only 3 of those 8 pages were actionable
- the acknowledgement rate also dropped below 80%

That is a good sign the alert needs tuning, deduplication, or a different escalation path.

## Tests

```bash
python3 -m py_compile alert_noise_budget_check.py
python3 -m unittest discover -s tests
```

## Notes

- This tool is meant for local reviews of exported alert history, not as a replacement for PagerDuty, Opsgenie, or alert analytics platforms.
- If I extend it later, I would add CSV input and per-team noise budget summaries.
