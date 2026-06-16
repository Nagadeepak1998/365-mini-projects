from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from terraform_plan_risk_check import analyze_plan


PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT_DIR / "terraform_plan_risk_check.py"
RISKY_SAMPLE = PROJECT_DIR / "samples" / "risky_plan.json"
SAFE_SAMPLE = PROJECT_DIR / "samples" / "safe_plan.json"


class TerraformPlanRiskCheckTests(unittest.TestCase):
    def test_analyze_plan_flags_expected_risks(self) -> None:
        findings = analyze_plan(json.loads(RISKY_SAMPLE.read_text(encoding="utf-8")))
        codes = {(finding["code"], finding["address"]) for finding in findings}
        self.assertIn(("public-sensitive-ingress", "aws_security_group.app"), codes)
        self.assertIn(("public-db-instance", "aws_db_instance.orders"), codes)
        self.assertIn(("s3-public-access-relaxed", "aws_s3_bucket_public_access_block.logs"), codes)
        self.assertIn(("iam-wildcard-admin", "aws_iam_policy.deploy"), codes)

    def test_analyze_plan_ignores_safe_sample(self) -> None:
        findings = analyze_plan(json.loads(SAFE_SAMPLE.read_text(encoding="utf-8")))
        self.assertEqual(findings, [])

    def test_cli_flags_risky_sample(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPT), str(RISKY_SAMPLE)],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FLAGGED", result.stdout)
        self.assertIn("aws_db_instance.orders", result.stdout)

    def test_cli_returns_json_for_safe_sample(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPT), str(SAFE_SAMPLE), "--format", "json"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["high"], 0)
        self.assertEqual(payload["findings"], [])

    def test_cli_handles_public_security_group_rule(self) -> None:
        payload = {
            "resource_changes": [
                {
                    "address": "aws_security_group_rule.redis",
                    "type": "aws_security_group_rule",
                    "change": {
                        "actions": ["create"],
                        "after": {
                            "type": "ingress",
                            "protocol": "tcp",
                            "from_port": 6379,
                            "to_port": 6379,
                            "cidr_blocks": ["0.0.0.0/0"],
                        },
                    },
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_path = Path(temp_dir) / "plan.json"
            sample_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(SCRIPT), str(sample_path)],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("aws_security_group_rule.redis", result.stdout)


if __name__ == "__main__":
    unittest.main()
