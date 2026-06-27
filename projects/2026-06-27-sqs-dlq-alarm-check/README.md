# SQS DLQ Alarm Check

Dead-letter queues are useful only if somebody can see them filling up. I built this small CLI to review an SQS inventory for the basics I would want before trusting an asynchronous service path: production queues need owners, important queues need DLQs, DLQs need visible-message alarms, and those alarms need thresholds and runbooks that are useful during support.

## What It Does

The script reads a JSON inventory of SQS queues and flags:

- production queues without owners
- production or critical queues without a dead-letter queue redrive policy
- redrive policies pointing at missing DLQs
- low `max_receive_count` values
- DLQs without `ApproximateNumberOfMessagesVisible` alarms
- DLQ alarms with high thresholds, long periods, or missing runbooks
- DLQs that already have visible messages or old messages

It exits with `0` when the inventory is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 sqs_dlq_alarm_check.py samples/safe_inventory.json
```

Expected output:

```text
PASS: SQS DLQ alarm coverage looks ready
```

Risky sample:

```bash
python3 sqs_dlq_alarm_check.py samples/risky_inventory.json
```

Expected output starts with:

```text
FLAGGED: 12 SQS DLQ alarm issue(s) detected
```

## Input Shape

```json
{
  "queues": [
    {
      "name": "payments-events",
      "environment": "prod",
      "owner": "payments-platform",
      "critical": true,
      "redrive_policy": {
        "dead_letter_queue": "payments-events-dlq",
        "max_receive_count": 5
      }
    },
    {
      "name": "payments-events-dlq",
      "environment": "prod",
      "owner": "payments-platform",
      "is_dead_letter_queue": true,
      "approximate_messages_visible": 0,
      "oldest_message_age_seconds": 0,
      "alarms": [
        {
          "metric_name": "ApproximateNumberOfMessagesVisible",
          "threshold": 1,
          "period_minutes": 5,
          "runbook": "https://runbooks.example/sqs/payments-events-dlq"
        }
      ]
    }
  ]
}
```

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
python3 -m py_compile sqs_dlq_alarm_check.py tests/test_sqs_dlq_alarm_check.py
```

## Notes

This is intentionally dependency-free and works from a static inventory export. The tradeoff is that it checks readiness signals in the inventory; it does not query AWS or prove that CloudWatch alarms are wired to the right paging route.
