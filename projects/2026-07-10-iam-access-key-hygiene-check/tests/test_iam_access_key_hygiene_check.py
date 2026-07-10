import unittest
from datetime import date
from pathlib import Path

from iam_access_key_hygiene_check import check_principal, review_inventory


PROJECT_DIR = Path(__file__).resolve().parents[1]


class IAMAccessKeyHygieneCheckTests(unittest.TestCase):
    def test_safe_inventory_has_no_findings(self):
        findings = review_inventory(PROJECT_DIR / "samples" / "safe_inventory.json", date(2026, 7, 10))
        self.assertEqual([], findings)

    def test_risky_inventory_flags_expected_gaps(self):
        findings = review_inventory(PROJECT_DIR / "samples" / "risky_inventory.json", date(2026, 7, 10))
        codes = {finding.code for finding in findings}
        self.assertTrue({"missing-owner", "human-static-key", "stale-active-key", "unused-active-key"} <= codes)
        self.assertTrue({"multiple-active-keys", "missing-rotation-runbook", "stale-inactive-key"} <= codes)

    def test_service_without_static_keys_is_valid(self):
        findings = check_principal(
            {"name": "deployment-role", "type": "service", "owner": "platform", "access_keys": []},
            date(2026, 7, 10),
        )
        self.assertEqual([], findings)

    def test_iam_api_use_is_flagged(self):
        findings = check_principal(
            {
                "name": "legacy-sync",
                "type": "service",
                "owner": "identity",
                "rotation_runbook": "runbooks/rotate-legacy-sync.md",
                "access_keys": [{
                    "id_suffix": "EXAMPLE1",
                    "status": "active",
                    "created_at": "2026-07-01",
                    "last_used_at": "2026-07-09",
                    "last_used_service": "iam",
                }],
            },
            date(2026, 7, 10),
        )
        self.assertEqual(["iam-api-key-use"], [finding.code for finding in findings])


if __name__ == "__main__":
    unittest.main()
