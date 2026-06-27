from pathlib import Path
import tempfile
import unittest

from sqs_dlq_alarm_check import load_inventory, review_queues


class SqsDlqAlarmCheckTests(unittest.TestCase):
    def test_ready_inventory_has_no_findings(self):
        queues = [
            {
                "name": "payments-events",
                "environment": "prod",
                "owner": "payments-platform",
                "critical": True,
                "redrive_policy": {
                    "dead_letter_queue": "payments-events-dlq",
                    "max_receive_count": 5,
                },
            },
            {
                "name": "payments-events-dlq",
                "environment": "prod",
                "owner": "payments-platform",
                "is_dead_letter_queue": True,
                "approximate_messages_visible": 0,
                "oldest_message_age_seconds": 0,
                "alarms": [
                    {
                        "metric_name": "ApproximateNumberOfMessagesVisible",
                        "threshold": 1,
                        "period_minutes": 5,
                        "runbook": "https://runbooks.example/sqs/payments-events-dlq",
                    }
                ],
            },
        ]

        findings = review_queues(queues)

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        queues = [
            {
                "name": "billing-events",
                "environment": "prod",
                "owner": "",
                "critical": True,
                "redrive_policy": {
                    "dead_letter_queue": "billing-events-missing-dlq",
                    "max_receive_count": 1,
                },
            },
            {
                "name": "support-notifications",
                "environment": "prod",
                "critical": False,
            },
            {
                "name": "orders-dlq",
                "environment": "production",
                "is_dead_letter_queue": True,
                "owner": "",
                "approximate_messages_visible": 7,
                "oldest_message_age_seconds": 7200,
                "alarms": [
                    {
                        "metric_name": "ApproximateNumberOfMessagesVisible",
                        "threshold": 25,
                        "period_minutes": 15,
                    }
                ],
            },
            {
                "name": "audit-dlq",
                "environment": "prod",
                "is_dead_letter_queue": True,
                "owner": "platform",
                "approximate_messages_visible": 0,
                "oldest_message_age_seconds": 0,
            },
        ]

        findings = review_queues(queues)
        messages = [finding.message for finding in findings]

        self.assertEqual(12, len(findings))
        self.assertIn("production queue is missing an owner", messages)
        self.assertIn("redrive policy points to unknown DLQ 'billing-events-missing-dlq'", messages)
        self.assertIn("max_receive_count should be at least 3 before sending to DLQ", messages)
        self.assertIn("missing dead-letter queue redrive policy", messages)
        self.assertIn("production DLQ is missing an owner", messages)
        self.assertIn("DLQ alarm threshold 25 is above 10", messages)
        self.assertIn("DLQ alarm period should be 5 minutes or less", messages)
        self.assertIn("DLQ alarm is missing a runbook link", messages)
        self.assertIn("DLQ currently has 7 visible message(s)", messages)
        self.assertIn("oldest DLQ message is older than 1 hour", messages)
        self.assertIn("missing DLQ visible-messages alarm", messages)

    def test_loader_rejects_duplicate_queue_names(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write('{"queues": [{"name": "jobs"}, {"name": "jobs"}]}')
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate queue name"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
