import json
import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from deployment_window_risk_check import exit_code, render_text, review_plan


class DeploymentWindowRiskCheckTests(unittest.TestCase):
    def load_sample(self, name):
        with (PROJECT_DIR / "samples" / name).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_risky_deployment_flags_release_blockers(self):
        issues = review_plan(self.load_sample("risky_deployment.json"))
        codes = {issue["code"] for issue in issues}

        self.assertIn("freeze-window-overlap", codes)
        self.assertIn("weak-rollback-plan", codes)
        self.assertIn("low-error-budget", codes)
        self.assertIn("risky-cutover-strategy", codes)
        self.assertGreaterEqual(len(issues), 8)

    def test_controlled_deployment_passes(self):
        plan = self.load_sample("controlled_deployment.json")
        issues = review_plan(plan)

        self.assertEqual([], issues)
        self.assertIn("PASS:", render_text(plan, issues))

    def test_fail_on_high_uses_nonzero_exit_for_high_risk(self):
        issues = review_plan(self.load_sample("risky_deployment.json"))

        self.assertEqual(2, exit_code(issues, "high"))
        self.assertEqual(0, exit_code([], "high"))


if __name__ == "__main__":
    unittest.main()
