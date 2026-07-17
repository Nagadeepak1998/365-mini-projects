import unittest

from release_artifact_provenance_check import review_inventory


SAFE_ARTIFACT = {
    "name": "payments-api:2026.07.17",
    "owner": "payments-platform",
    "environment": "production",
    "digest": "sha256:" + "a" * 64,
    "sbom": {"present": True, "format": "cyclonedx"},
    "signature": {"verified": True},
    "provenance": {
        "verified": True,
        "source_repository": "github.com/example/payments-api",
        "source_revision": "7b81bbed",
    },
    "promotion": {"digest_matched": True},
}


class ProvenanceReviewTests(unittest.TestCase):
    def test_safe_artifact_passes(self):
        self.assertEqual(review_inventory({"artifacts": [SAFE_ARTIFACT]}), [])

    def test_risky_artifact_reports_expected_findings(self):
        findings = review_inventory({"artifacts": [{"name": "payments-api:latest", "environment": "production"}]})
        self.assertEqual(
            {finding["code"] for finding in findings},
            {"missing-owner", "invalid-digest", "missing-sbom", "unverified-signature",
             "unverified-provenance", "missing-source", "missing-revision", "promotion-digest-mismatch"},
        )

    def test_invalid_sbom_format_is_flagged(self):
        artifact = {**SAFE_ARTIFACT, "sbom": {"present": True, "format": "custom"}}
        self.assertEqual(review_inventory({"artifacts": [artifact]})[0]["code"], "unsupported-sbom")

    def test_empty_inventory_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            review_inventory({"artifacts": []})


if __name__ == "__main__":
    unittest.main()
