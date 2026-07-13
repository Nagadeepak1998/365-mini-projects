import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from terraform_state_safety_check import review_inventory


PROJECT_DIR = Path(__file__).resolve().parents[1]
TODAY = date(2026, 7, 13)


class TerraformStateSafetyCheckTests(unittest.TestCase):
    def test_safe_inventory_has_no_issues(self):
        payload = json.loads((PROJECT_DIR / "samples/safe_inventory.json").read_text())
        self.assertEqual(review_inventory(payload, TODAY), [])

    def test_risky_inventory_finds_expected_controls(self):
        payload = json.loads((PROJECT_DIR / "samples/risky_inventory.json").read_text())
        issues = review_inventory(payload, TODAY)
        codes = {issue.code for issue in issues}
        self.assertEqual(len(issues), 11)
        self.assertTrue(
            {
                "local-production-state",
                "state-not-gitignored",
                "unencrypted-state",
                "versioning-disabled",
                "public-access-not-blocked",
                "locking-disabled",
                "stale-recovery-drill",
            }.issubset(codes)
        )

    def test_duplicate_names_are_rejected(self):
        payload = {"backends": [{"name": "shared", "type": "local"}, {"name": "shared", "type": "local"}]}
        with self.assertRaisesRegex(ValueError, "duplicate backend name"):
            review_inventory(payload, TODAY)

    def test_cli_uses_distinct_exit_codes(self):
        safe = subprocess.run(
            [sys.executable, str(PROJECT_DIR / "terraform_state_safety_check.py"), str(PROJECT_DIR / "samples/safe_inventory.json"), "--today", TODAY.isoformat()],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(safe.returncode, 0)
        self.assertIn("PASS:", safe.stdout)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as malformed:
            malformed.write("not-json")
            malformed.flush()
            bad = subprocess.run(
                [sys.executable, str(PROJECT_DIR / "terraform_state_safety_check.py"), malformed.name],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(bad.returncode, 2)
        self.assertIn("ERROR:", bad.stderr)


if __name__ == "__main__":
    unittest.main()
