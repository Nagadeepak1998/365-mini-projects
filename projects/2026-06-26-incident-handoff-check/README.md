# Incident Handoff Check

When an incident crosses a shift boundary, the next owner needs more than a short status line. I built this small CLI to check whether a handoff note has the operational context I would want before taking over: timeline, impact, owner, next action, mitigation, evidence, customer comms state, and rollback or follow-up notes.

## What It Does

The script reads an incident handoff JSON file and flags missing or inconsistent fields:

- invalid or incomplete incident timeline
- missing owner, next action, impact summary, or mitigation
- missing affected services or evidence links
- open incidents without a next update time or rollback plan
- high-severity incidents without customer communication status
- closed incidents without a follow-up note

It exits with `0` when the handoff is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 incident_handoff_check.py samples/safe_handoff.json
```

Expected output:

```text
PASS: incident handoff is ready for the next owner
```

Risky sample:

```bash
python3 incident_handoff_check.py samples/risky_handoff.json
```

Expected output starts with:

```text
FLAGGED: 11 incident handoff issue(s) detected
```

## Input Shape

```json
{
  "incidents": [
    {
      "id": "INC-1042",
      "severity": "sev2",
      "status": "monitoring",
      "owner": "payments-platform",
      "started_at": "2026-06-26T08:10:00-07:00",
      "detected_at": "2026-06-26T08:14:00-07:00",
      "next_update_at": "2026-06-26T10:30:00-07:00",
      "impact_summary": "Checkout latency increased for a small set of card payments.",
      "affected_services": ["checkout-api"],
      "mitigation": "Shifted traffic away from the degraded processor route.",
      "next_action": "Watch error rate before restoring normal routing.",
      "rollback_plan": "Keep alternate route active if errors rise again.",
      "customer_comms_status": "sent",
      "evidence_links": ["https://dashboards.example/incidents/INC-1042"],
      "timeline_events": [
        {"at": "2026-06-26T08:14:00-07:00", "note": "Alert fired."},
        {"at": "2026-06-26T08:28:00-07:00", "note": "Traffic shifted."}
      ]
    }
  ]
}
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
python3 -m py_compile incident_handoff_check.py tests/test_incident_handoff_check.py
```

## Notes

This is intentionally dependency-free so it can run during an on-call handoff without setting up a larger toolchain. The tradeoff is that the checks are schema and completeness checks, not a replacement for reviewing the actual incident details.
