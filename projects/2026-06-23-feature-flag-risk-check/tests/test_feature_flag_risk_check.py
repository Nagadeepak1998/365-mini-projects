from datetime import date
from pathlib import Path
import tempfile
import unittest

from feature_flag_risk_check import load_flags, review_flags


class FeatureFlagRiskCheckTests(unittest.TestCase):
    def test_safe_gradual_rollout_has_no_findings(self):
        current = {
            "checkout_redesign": {
                "name": "checkout_redesign",
                "environment": "prod",
                "rollout_percent": 20,
                "owner": "payments-platform",
                "expires_on": "2026-08-01",
                "kill_switch": True,
                "rollback": "Disable checkout_redesign in the flag console.",
            }
        }
        proposed = {
            "checkout_redesign": {
                "name": "checkout_redesign",
                "environment": "prod",
                "rollout_percent": 35,
                "owner": "payments-platform",
                "expires_on": "2026-08-01",
                "kill_switch": True,
                "rollback": "Disable checkout_redesign in the flag console.",
            }
        }

        findings = review_flags(current, proposed, date(2026, 6, 23))

        self.assertEqual([], findings)

    def test_risky_rollout_reports_expected_findings(self):
        current = {
            "smart_retry": {
                "name": "smart_retry",
                "environment": "prod",
                "rollout_percent": 10,
                "owner": "reliability",
                "expires_on": "2026-08-01",
                "kill_switch": True,
            }
        }
        proposed = {
            "smart_retry": {
                "name": "smart_retry",
                "environment": "prod",
                "rollout_percent": 100,
                "owner": "",
                "expires_on": "2026-01-15",
                "rollback": " ",
                "debug": True,
                "kill_switch": False,
            }
        }

        findings = review_flags(current, proposed, date(2026, 6, 23))
        messages = [finding.message for finding in findings]

        self.assertEqual(6, len(findings))
        self.assertIn("rollout increases from 10% to 100% in one change", messages)
        self.assertIn("reaches full rollout without a rollback note or runbook link", messages)
        self.assertIn("missing owner for follow-up during incidents", messages)
        self.assertIn("flag expired on 2026-01-15 but is still active", messages)
        self.assertIn("debug behavior is enabled in prod", messages)
        self.assertIn("rollout has no kill switch", messages)

    def test_loader_rejects_duplicate_names(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write(
                '{"flags": [{"name": "same", "rollout_percent": 1}, {"name": "same", "rollout_percent": 2}]}'
            )
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate flag name"):
                load_flags(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
