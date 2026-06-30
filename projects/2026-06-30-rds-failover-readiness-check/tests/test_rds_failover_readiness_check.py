from datetime import date
from pathlib import Path
import tempfile
import unittest

from rds_failover_readiness_check import load_inventory, review_databases


class RdsFailoverReadinessCheckTests(unittest.TestCase):
    def test_ready_inventory_has_no_findings(self):
        databases = [
            {
                "identifier": "orders-prod",
                "environment": "prod",
                "owner": "orders-platform",
                "critical": True,
                "multi_az": True,
                "deletion_protection": True,
                "read_replica": True,
                "backups": {
                    "enabled": True,
                    "retention_days": 14,
                    "window": "07:00-08:00 UTC",
                },
                "storage": {"autoscaling": True},
                "alarms": [
                    {
                        "metric_name": "CPUUtilization",
                        "runbook": "https://runbooks.example/db/orders",
                    },
                    {
                        "metric_name": "FreeStorageSpace",
                        "runbook": "https://runbooks.example/db/orders",
                    },
                    {
                        "metric_name": "DatabaseConnections",
                        "runbook": "https://runbooks.example/db/orders",
                    },
                    {
                        "metric_name": "ReplicaLag",
                        "runbook": "https://runbooks.example/db/orders",
                    },
                ],
                "failover_drill": {
                    "last_tested_at": "2026-05-15",
                    "runbook": "https://runbooks.example/db/orders/failover",
                },
                "rto_minutes": 30,
                "rpo_minutes": 5,
                "pending_reboot": False,
            }
        ]

        findings = review_databases(databases, today=date(2026, 6, 30))

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        databases = [
            {
                "identifier": "checkout-prod",
                "environment": "production",
                "owner": "",
                "critical": True,
                "multi_az": False,
                "deletion_protection": False,
                "read_replica": True,
                "backups": {
                    "enabled": True,
                    "retention_days": 3,
                    "window": "",
                },
                "storage": {"autoscaling": False},
                "alarms": [
                    {
                        "metric_name": "CPUUtilization",
                        "runbook": "",
                    }
                ],
                "failover_drill": {
                    "last_tested_at": "2025-11-01",
                    "runbook": "",
                },
                "pending_reboot": True,
            },
            {
                "identifier": "analytics-prod",
                "environment": "prod",
                "owner": "data-platform",
                "critical": True,
                "multi_az": True,
                "deletion_protection": True,
                "read_replica": False,
                "backups": {"enabled": False},
                "storage": {"autoscaling": True},
                "alarms": [
                    {
                        "metric_name": "FreeStorageSpace",
                        "runbook": "https://runbooks.example/db/analytics",
                    }
                ],
                "failover_drill": {},
                "rto_minutes": 60,
                "rpo_minutes": 15,
                "pending_reboot": False,
            },
        ]

        findings = review_databases(databases, today=date(2026, 6, 30))
        messages = [finding.message for finding in findings]

        self.assertEqual(18, len(findings))
        self.assertIn("production database is missing an owner", messages)
        self.assertIn("critical production database is not Multi-AZ", messages)
        self.assertIn("deletion protection is not enabled", messages)
        self.assertIn("backup retention is below 7 days", messages)
        self.assertIn("backup window is not documented", messages)
        self.assertIn("storage autoscaling is disabled", messages)
        self.assertIn("missing alarm metric(s): DatabaseConnections, FreeStorageSpace", messages)
        self.assertIn("read replica is missing a ReplicaLag alarm", messages)
        self.assertIn("one or more alarms are missing runbook links", messages)
        self.assertIn("failover drill is older than 180 days", messages)
        self.assertIn("failover drill runbook is missing", messages)
        self.assertIn("RTO target is not documented", messages)
        self.assertIn("RPO target is not documented", messages)
        self.assertIn("database has pending-reboot changes", messages)
        self.assertIn("automated backups are not enabled", messages)
        self.assertIn("missing alarm metric(s): CPUUtilization, DatabaseConnections", messages)
        self.assertIn("critical database has no recorded failover drill", messages)

    def test_loader_rejects_duplicate_identifiers(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write('{"databases": [{"identifier": "db-a"}, {"identifier": "db-a"}]}')
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate identifier"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
