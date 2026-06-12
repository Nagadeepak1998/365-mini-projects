import json
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_DIR / "vault_policy_drift_check.py"
BASELINE = PROJECT_DIR / "baseline_policy.hcl"
SAFE = PROJECT_DIR / "sample_safe_policy.hcl"
RISKY = PROJECT_DIR / "sample_risky_policy.hcl"
RULES = PROJECT_DIR / "rules.json"


class VaultPolicyDriftCheckTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_safe_policy_passes(self) -> None:
        result = self.run_cli("--baseline", str(BASELINE), str(SAFE))
        self.assertEqual(result.returncode, 0)
        self.assertIn("PASS: no risky Vault policy drift detected", result.stdout)

    def test_risky_policy_is_flagged(self) -> None:
        result = self.run_cli(
            "--baseline",
            str(BASELINE),
            "--rules",
            str(RULES),
            str(RISKY),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FLAGGED:", result.stdout)
        self.assertIn("[forbidden-capability] sys/*", result.stdout)
        self.assertIn("[forbidden-capability] auth/token/create", result.stdout)
        self.assertIn("[wildcard-write] secret/data/prod/*", result.stdout)

    def test_json_output(self) -> None:
        result = self.run_cli(
            "--baseline",
            str(BASELINE),
            str(RISKY),
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "flagged")
        self.assertGreaterEqual(payload["finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
