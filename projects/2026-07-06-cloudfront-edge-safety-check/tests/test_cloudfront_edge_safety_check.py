from pathlib import Path
import tempfile
import unittest

from cloudfront_edge_safety_check import load_inventory, review_distributions


class CloudFrontEdgeSafetyCheckTests(unittest.TestCase):
    def test_ready_inventory_has_no_findings(self):
        distributions = [
            {
                "id": "orders-edge",
                "environment": "prod",
                "owner": "edge-platform",
                "critical": True,
                "web_acl_id": "arn:aws:wafv2:us-east-1:123456789012:global/webacl/orders",
                "minimum_protocol_version": "TLSv1.2_2021",
                "access_logging": {"enabled": True, "retention_days": 90},
                "origin_failover": {"enabled": True},
                "default_behavior": {
                    "viewer_protocol_policy": "redirect-to-https",
                    "response_headers_policy": "security-headers",
                },
                "cache_behaviors": [
                    {
                        "path_pattern": "/api/*",
                        "viewer_protocol_policy": "https-only",
                        "response_headers_policy": "api-security-headers",
                    }
                ],
                "alarms": [
                    {"name": "5xx_error_rate", "enabled": True},
                    {"name": "origin_latency", "enabled": True},
                    {"name": "waf_block_spike", "enabled": True},
                ],
            }
        ]

        findings = review_distributions(distributions)

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        distributions = [
            {
                "id": "checkout-edge",
                "environment": "production",
                "owner": "",
                "critical": True,
                "web_acl_id": "",
                "minimum_protocol_version": "TLSv1",
                "access_logging": {"enabled": False, "retention_days": 0},
                "origin_failover": {"enabled": False},
                "default_behavior": {
                    "viewer_protocol_policy": "allow-all",
                    "response_headers_policy": "",
                },
                "cache_behaviors": [
                    {
                        "path_pattern": "/api/*",
                        "viewer_protocol_policy": "allow-all",
                    }
                ],
                "alarms": [
                    {"name": "waf_block_spike", "enabled": True},
                ],
            },
            {
                "id": "media-edge",
                "environment": "prod",
                "owner": "media-platform",
                "critical": False,
                "web_acl_id": "arn:aws:wafv2:us-east-1:123456789012:global/webacl/media",
                "minimum_protocol_version": "TLSv1.2_2021",
                "access_logging": {"enabled": True, "retention_days": 7},
                "default_behavior": {
                    "viewer_protocol_policy": "redirect-to-https",
                    "response_headers_policy": "security-headers",
                },
                "cache_behaviors": [
                    {
                        "path_pattern": "/video/*",
                        "viewer_protocol_policy": "https-only",
                    }
                ],
                "alarms": [
                    {"name": "5xx_error_rate", "enabled": True},
                    {"name": "origin_latency", "enabled": True},
                ],
            },
            {
                "id": "sandbox-edge",
                "environment": "dev",
                "default_behavior": {"viewer_protocol_policy": "allow-all"},
            },
        ]

        findings = review_distributions(distributions)
        messages = [finding.message for finding in findings]

        self.assertEqual(13, len(findings))
        self.assertIn("production distribution is missing an owner", messages)
        self.assertIn("production distribution has no WAF web ACL", messages)
        self.assertIn("minimum TLS policy is not modern: TLSv1", messages)
        self.assertIn("access logging is not enabled", messages)
        self.assertIn("critical distribution has no origin failover", messages)
        self.assertIn("default behavior does not enforce HTTPS viewers", messages)
        self.assertIn("default behavior has no response headers policy", messages)
        self.assertIn("/api/* behavior does not enforce HTTPS viewers", messages)
        self.assertIn("/api/* behavior has no response headers policy", messages)
        self.assertIn("missing enabled alarm(s): 5xx_error_rate, origin_latency", messages)
        self.assertIn("access log retention is under 30 days", messages)
        self.assertIn("/video/* behavior has no response headers policy", messages)
        self.assertIn("missing enabled alarm(s): waf_block_spike", messages)

    def test_loader_rejects_duplicate_distribution_ids(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write('{"distributions": [{"id": "edge-a"}, {"id": "edge-a"}]}')
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate distribution id"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
