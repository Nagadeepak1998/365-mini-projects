import unittest
from pathlib import Path

from github_oidc_trust_check import check_binding, review


PROJECT_DIR = Path(__file__).resolve().parents[1]


class GitHubOIDCTrustCheckTests(unittest.TestCase):
    def test_safe_inventory_passes(self):
        self.assertEqual([], review(PROJECT_DIR / "samples" / "safe.json"))

    def test_risky_inventory_exposes_expected_controls(self):
        codes = {finding.code for finding in review(PROJECT_DIR / "samples" / "risky.json")}
        self.assertTrue({"missing-owner", "invalid-audience", "wildcard-subject", "pull-request-trust"} <= codes)
        self.assertTrue({"production-not-environment-bound", "missing-production-approval", "broad-contents-permission"} <= codes)

    def test_missing_subject_stops_subject_specific_checks(self):
        findings = check_binding({
            "name": "empty",
            "owner": "platform",
            "issuer": "https://token.actions.githubusercontent.com",
            "audience": "sts.amazonaws.com",
            "id_token_permission": "write",
            "contents_permission": "read",
        })
        self.assertEqual(["missing-subject"], [finding.code for finding in findings])

    def test_invalid_subject_type_is_rejected(self):
        with self.assertRaises(ValueError):
            check_binding({"name": "bad", "subjects": [42]})


if __name__ == "__main__":
    unittest.main()
