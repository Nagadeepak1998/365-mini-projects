import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "llm_runbook_drift_check.py"
SPEC = importlib.util.spec_from_file_location("llm_runbook_drift_check", MODULE_PATH)
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["llm_runbook_drift_check"] = checker
SPEC.loader.exec_module(checker)


def load_sample_policy():
    return checker.load_policy(PROJECT_DIR / "sample_policy.json")


class RunbookDriftCheckTests(unittest.TestCase):
    def test_safe_runbook_passes(self):
        policy = load_sample_policy()
        response = (PROJECT_DIR / "sample_safe_runbook.md").read_text(encoding="utf-8")

        findings = checker.scan_response(policy, response)

        self.assertEqual(findings, [])

    def test_risky_runbook_flags_unsupported_and_destructive_guidance(self):
        policy = load_sample_policy()
        response = (PROJECT_DIR / "sample_risky_runbook.md").read_text(encoding="utf-8")

        findings = checker.scan_response(policy, response)
        categories = {finding.category for finding in findings}
        labels = {finding.label for finding in findings}

        self.assertIn("missing_required_action", categories)
        self.assertIn("insufficient_evidence", categories)
        self.assertIn("unsupported_claim", categories)
        self.assertIn("risky_action", categories)
        self.assertIn("Unsupported database root cause certainty", labels)
        self.assertIn("Destructive Kubernetes mitigation", labels)


if __name__ == "__main__":
    unittest.main()
