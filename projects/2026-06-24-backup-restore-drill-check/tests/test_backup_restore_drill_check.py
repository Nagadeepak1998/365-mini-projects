from datetime import date
from pathlib import Path
import tempfile
import unittest

from backup_restore_drill_check import load_inventory, review_inventory


class BackupRestoreDrillCheckTests(unittest.TestCase):
    def test_safe_inventory_has_no_findings(self):
        services = [
            {
                "name": "payments-db",
                "tier": "critical",
                "owner": "payments-platform",
                "backup_status": "success",
                "latest_backup_at": "2026-06-24",
                "latest_restore_test_at": "2026-06-10",
                "restore_test_interval_days": 30,
                "rpo_hours": 24,
                "retention_days": 35,
                "encrypted": True,
                "cross_region": True,
            }
        ]

        findings = review_inventory(services, date(2026, 6, 24))

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        services = [
            {
                "name": "orders-db",
                "tier": "critical",
                "owner": "",
                "backup_status": "failed",
                "latest_backup_at": "2026-06-20",
                "latest_restore_test_at": "2026-01-10",
                "restore_test_interval_days": 60,
                "rpo_hours": 24,
                "retention_days": 7,
                "encrypted": False,
                "cross_region": False,
            }
        ]

        findings = review_inventory(services, date(2026, 6, 24))
        messages = [finding.message for finding in findings]

        self.assertEqual(7, len(findings))
        self.assertIn("missing owner for backup follow-up", messages)
        self.assertIn("latest backup is 96h old, above 24h RPO", messages)
        self.assertIn("latest backup status is failed", messages)
        self.assertIn("restore test is 165 days old, above 60 day target", messages)
        self.assertIn("retention is only 7 days", messages)
        self.assertIn("backup encryption is not confirmed", messages)
        self.assertIn("critical service has no confirmed cross-region backup", messages)

    def test_loader_rejects_duplicate_service_names(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write('{"services": [{"name": "api"}, {"name": "api"}]}')
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate service name"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
