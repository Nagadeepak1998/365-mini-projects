from datetime import date
from pathlib import Path
import tempfile
import unittest

from tls_certificate_readiness_check import load_inventory, review_certificates


class TlsCertificateReadinessCheckTests(unittest.TestCase):
    def test_ready_inventory_has_no_findings(self):
        certificates = [
            {
                "common_name": "api.example.com",
                "environment": "prod",
                "exposure": "public",
                "owner": "platform-edge",
                "expires_at": "2026-10-30",
                "auto_renew": True,
                "hostname_match_validated": True,
                "certificate_chain_validated": True,
                "renewal_runbook": "docs/runbooks/tls-renewal.md",
                "monitoring_alarm": "tls-expiry-api-example-com",
                "key_size_bits": 2048,
                "signature_algorithm": "sha256WithRSAEncryption",
                "last_rotation_drill_at": "2026-03-15",
            },
            {
                "common_name": "internal-api.example.local",
                "environment": "prod",
                "exposure": "private",
                "expires_at": "2026-07-20",
            },
        ]

        findings = review_certificates(certificates, date(2026, 7, 8))

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        certificates = [
            {
                "common_name": "checkout.example.com",
                "environment": "production",
                "exposure": "internet",
                "owner": "",
                "expires_at": "2026-07-18",
                "auto_renew": False,
                "hostname_match_validated": False,
                "certificate_chain_validated": False,
                "renewal_runbook": "",
                "monitoring_alarm": "",
                "key_size_bits": 1024,
                "signature_algorithm": "sha1WithRSAEncryption",
                "last_rotation_drill_at": "2024-05-01",
            },
            {
                "common_name": "www.example.com",
                "environment": "prod",
                "exposure": "public",
                "owner": "web-platform",
                "expires_at": "2026-08-20",
                "auto_renew": True,
                "hostname_match_validated": True,
                "certificate_chain_validated": True,
                "renewal_runbook": "docs/runbooks/tls-renewal.md",
                "monitoring_alarm": "tls-expiry-www-example-com",
                "key_size_bits": 2048,
                "signature_algorithm": "sha256WithRSAEncryption",
                "last_rotation_drill_at": "",
            },
            {
                "common_name": "internal-api.example.local",
                "environment": "prod",
                "exposure": "private",
                "expires_at": "2026-07-12",
            },
        ]

        findings = review_certificates(certificates, date(2026, 7, 8))
        messages = [finding.message for finding in findings]

        self.assertEqual(12, len(findings))
        self.assertIn("public production certificate is missing an owner", messages)
        self.assertIn("certificate expires in 10 day(s)", messages)
        self.assertIn("certificate is near expiry without auto-renewal enabled", messages)
        self.assertIn("hostname/SAN match has not been validated", messages)
        self.assertIn("certificate chain validation is missing", messages)
        self.assertIn("renewal runbook is missing", messages)
        self.assertIn("expiry monitoring alarm is missing", messages)
        self.assertIn("key size is below 2048 bits", messages)
        self.assertIn("signature algorithm uses SHA-1", messages)
        self.assertIn("rotation drill is older than one year", messages)
        self.assertIn("certificate expires in 43 day(s)", messages)
        self.assertIn("rotation drill date is missing", messages)

    def test_loader_rejects_duplicate_common_names(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write(
                '{"certificates": ['
                '{"common_name": "api.example.com", "expires_at": "2026-08-01"},'
                '{"common_name": "api.example.com", "expires_at": "2026-08-01"}'
                "]}"
            )
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate certificate"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
