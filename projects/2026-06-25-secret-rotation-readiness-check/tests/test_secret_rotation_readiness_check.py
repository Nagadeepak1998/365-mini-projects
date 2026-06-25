from datetime import date
from pathlib import Path
import tempfile
import unittest

from secret_rotation_readiness_check import load_inventory, review_inventory


class SecretRotationReadinessCheckTests(unittest.TestCase):
    def test_safe_inventory_has_no_findings(self):
        secrets = [
            {
                "name": "payments-api-db-password",
                "owner": "payments-platform",
                "last_rotated_at": "2026-06-10",
                "next_rotation_due": "2026-07-10",
                "rotation_interval_days": 45,
                "used_by_critical_path": True,
                "dual_secret_supported": True,
                "rollback_plan": "Keep the previous password active until health checks pass.",
                "validation_status": "passed",
                "last_validation_at": "2026-06-24",
                "break_glass_access_reviewed_at": "2026-06-01",
            }
        ]

        findings = review_inventory(secrets, date(2026, 6, 25))

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        secrets = [
            {
                "name": "orders-api-token",
                "owner": "",
                "last_rotated_at": "2026-01-15",
                "next_rotation_due": "2026-05-30",
                "rotation_interval_days": 60,
                "used_by_critical_path": True,
                "dual_secret_supported": False,
                "rollback_plan": "",
                "validation_status": "failed",
                "last_validation_at": "2026-04-01",
                "break_glass_access_reviewed_at": "2026-01-01",
            }
        ]

        findings = review_inventory(secrets, date(2026, 6, 25))
        messages = [finding.message for finding in findings]

        self.assertEqual(8, len(findings))
        self.assertIn("missing owner for rotation follow-up", messages)
        self.assertIn("secret is 161 days old, above 60 day rotation target", messages)
        self.assertIn("rotation is 26 day(s) overdue", messages)
        self.assertIn("critical path secret cannot rotate with dual-secret overlap", messages)
        self.assertIn("missing rollback plan", messages)
        self.assertIn("latest validation status is failed", messages)
        self.assertIn("validation evidence is 85 days old", messages)
        self.assertIn("break-glass access review is 175 days old", messages)

    def test_loader_rejects_duplicate_secret_names(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write('{"secrets": [{"name": "api-key"}, {"name": "api-key"}]}')
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate secret name"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
