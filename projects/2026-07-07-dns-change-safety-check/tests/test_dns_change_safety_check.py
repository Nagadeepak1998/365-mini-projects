from pathlib import Path
import tempfile
import unittest

from dns_change_safety_check import load_change_plan, review_changes


class DnsChangeSafetyCheckTests(unittest.TestCase):
    def test_ready_change_plan_has_no_findings(self):
        changes = [
            {
                "name": "api.example.com",
                "type": "A",
                "action": "update",
                "environment": "prod",
                "zone_scope": "public",
                "owner": "platform-dns",
                "ticket": "CHG-2407",
                "ttl_seconds": 60,
                "existing_ttl_seconds": 300,
                "rollback": "Restore the previous alias target from the change ticket.",
                "validation_checks": [
                    {"name": "dns_resolution", "enabled": True},
                    {"name": "http_health", "enabled": True},
                    {"name": "rollback_verified", "enabled": True},
                ],
            },
            {
                "name": "internal-api.example.local",
                "type": "CNAME",
                "action": "update",
                "environment": "prod",
                "zone_scope": "private",
            },
        ]

        findings = review_changes(changes)

        self.assertEqual([], findings)

    def test_risky_change_plan_reports_expected_findings(self):
        changes = [
            {
                "name": "example.com",
                "type": "CNAME",
                "action": "update",
                "environment": "production",
                "zone_scope": "public",
                "owner": "",
                "ticket": "",
                "ttl_seconds": 3600,
                "existing_ttl_seconds": 7200,
                "rollback": "",
                "validation_checks": [
                    {"name": "dns_resolution", "enabled": True},
                ],
            },
            {
                "name": "*.example.com",
                "type": "A",
                "action": "delete",
                "environment": "prod",
                "zone_scope": "internet",
                "owner": "edge-platform",
                "ticket": "CHG-2408",
                "ttl_seconds": 60,
                "existing_ttl_seconds": 300,
                "rollback": "Recreate the wildcard record from the saved zone export.",
                "validation_checks": [
                    {"name": "dns_resolution", "enabled": True},
                    {"name": "http_health", "enabled": True},
                    {"name": "rollback_verified", "enabled": False},
                ],
            },
            {
                "name": "mail.example.com",
                "type": "MX",
                "action": "create",
                "environment": "prod",
                "zone_scope": "public",
                "owner": "messaging",
                "ticket": "CHG-2409",
                "priority": 0,
                "ttl_seconds": 600,
                "existing_ttl_seconds": 0,
                "rollback": "Remove the new MX record.",
                "validation_checks": [
                    {"name": "dns_resolution", "enabled": True},
                    {"name": "http_health", "enabled": True},
                    {"name": "rollback_verified", "enabled": True},
                ],
            },
            {
                "name": "dev.example.com",
                "type": "A",
                "action": "delete",
                "environment": "dev",
                "zone_scope": "public",
            },
        ]

        findings = review_changes(changes)
        messages = [finding.message for finding in findings]

        self.assertEqual(12, len(findings))
        self.assertIn("production public DNS change is missing an owner", messages)
        self.assertIn("change has no ticket or approval reference", messages)
        self.assertIn("cutover TTL is above 300 seconds", messages)
        self.assertIn("existing TTL is high enough to slow rollback", messages)
        self.assertIn("CNAME appears to target the zone apex", messages)
        self.assertIn("rollback plan is missing", messages)
        self.assertIn("missing validation check(s): http_health, rollback_verified", messages)
        self.assertIn("production public DNS delete needs an explicit migration plan", messages)
        self.assertIn("wildcard production record should be reviewed manually", messages)
        self.assertIn("missing validation check(s): rollback_verified", messages)
        self.assertIn("MX record is missing a positive priority", messages)

    def test_loader_rejects_duplicate_changes(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write(
                '{"changes": ['
                '{"name": "api.example.com", "type": "A", "action": "update"},'
                '{"name": "api.example.com", "type": "A", "action": "update"}'
                "]}"
            )
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate change"):
                load_change_plan(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
