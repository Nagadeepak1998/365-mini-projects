import json
import subprocess
import sys
import unittest
from pathlib import Path

import prometheus_rule_sanity_check as checker


PROJECT_DIR = Path(__file__).resolve().parents[1]
RISKY_SAMPLE = PROJECT_DIR / "samples" / "risky_rules.json"
SAFE_SAMPLE = PROJECT_DIR / "samples" / "safe_rules.json"


class PrometheusRuleSanityCheckTests(unittest.TestCase):
    def test_risky_sample_findings(self) -> None:
        findings = checker.collect_findings(checker.load_snapshot(RISKY_SAMPLE))

        self.assertEqual(len(findings), 8)
        self.assertEqual(findings[0]["code"], "missing-for-window")
        self.assertTrue(
            any(finding["code"] == "missing-severity-label" for finding in findings)
        )
        self.assertTrue(
            any(finding["code"] == "missing-owner-label" for finding in findings)
        )

    def test_safe_sample_has_no_findings(self) -> None:
        findings = checker.collect_findings(checker.load_snapshot(SAFE_SAMPLE))

        self.assertEqual(findings, [])

    def test_cli_json_output(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_DIR / "prometheus_rule_sanity_check.py"),
                str(RISKY_SAMPLE),
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR,
        )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["findings"]), 8)


if __name__ == "__main__":
    unittest.main()
