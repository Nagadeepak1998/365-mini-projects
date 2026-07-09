import unittest
from datetime import date
from pathlib import Path

from lambda_production_readiness_check import check_function, review_inventory


PROJECT_DIR = Path(__file__).resolve().parents[1]


class LambdaProductionReadinessCheckTests(unittest.TestCase):
    def test_safe_inventory_has_no_findings(self):
        findings = review_inventory(PROJECT_DIR / "samples" / "safe_inventory.json", date(2026, 7, 9))

        self.assertEqual([], findings)

    def test_risky_inventory_flags_expected_gaps(self):
        findings = review_inventory(PROJECT_DIR / "samples" / "risky_inventory.json", date(2026, 7, 9))
        codes = {finding.code for finding in findings}

        self.assertIn("missing-owner", codes)
        self.assertIn("unsupported-runtime", codes)
        self.assertIn("unpinned-alias", codes)
        self.assertIn("weak-alarm-coverage", codes)
        self.assertIn("missing-async-failure-path", codes)
        self.assertIn("possible-inline-secret", codes)
        self.assertIn("stale-production-deploy", codes)
        self.assertIn("missing-rollback-drill", codes)

    def test_non_production_function_can_be_small_and_unpinned(self):
        findings = check_function(
            {
                "name": "scratch-dev-worker",
                "environment": "dev",
                "runtime": "python3.12",
                "alias": "$LATEST",
                "timeout_seconds": 10,
                "memory_mb": 128,
                "environment_variables": {},
            },
            date(2026, 7, 9),
        )

        self.assertEqual([], findings)

    def test_api_secret_names_are_flagged(self):
        findings = check_function(
            {
                "name": "customer-sync-prod",
                "environment": "prod",
                "owner": "platform",
                "runtime": "python3.12",
                "alias": "live",
                "trigger": "eventbridge",
                "timeout_seconds": 20,
                "memory_mb": 256,
                "reserved_concurrency": 5,
                "structured_logging": True,
                "xray_tracing": True,
                "async_invoked": False,
                "alarms": ["errors-high", "throttles-high"],
                "environment_variables": {"CUSTOMER_API_KEY": "from-env"},
                "last_deployed_at": "2026-07-01",
                "rollback_drill_at": "2026-06-01",
            },
            date(2026, 7, 9),
        )

        self.assertEqual(["possible-inline-secret"], [finding.code for finding in findings])


if __name__ == "__main__":
    unittest.main()
