from pathlib import Path
import tempfile
import unittest

from k8s_namespace_quota_check import load_inventory, review_namespaces


class K8sNamespaceQuotaCheckTests(unittest.TestCase):
    def test_ready_inventory_has_no_findings(self):
        namespaces = [
            {
                "name": "orders-prod",
                "environment": "prod",
                "owner": "orders-platform",
                "resource_quota": {
                    "hard": {
                        "cpu": "20",
                        "memory": "64Gi",
                        "pods": "80",
                    }
                },
                "limit_range": {
                    "default_requests": {
                        "cpu": "100m",
                        "memory": "128Mi",
                    }
                },
                "default_deny_network_policy": True,
                "workloads": [
                    {
                        "name": "orders-api",
                        "containers": [
                            {
                                "name": "app",
                                "requests": {"cpu": "250m", "memory": "512Mi"},
                                "limits": {"cpu": "1", "memory": "1Gi"},
                            }
                        ],
                    }
                ],
            }
        ]

        findings = review_namespaces(namespaces)

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        namespaces = [
            {
                "name": "checkout-prod",
                "environment": "production",
                "owner": "",
                "resource_quota": {"hard": {"cpu": "12"}},
                "default_deny_network_policy": False,
                "workloads": [
                    {
                        "name": "checkout-api",
                        "containers": [
                            {
                                "name": "app",
                                "requests": {"cpu": "250m"},
                                "limits": {},
                            },
                            {
                                "name": "sidecar",
                                "requests": {},
                                "limits": {"memory": "256Mi"},
                            },
                        ],
                    }
                ],
            },
            {
                "name": "billing-prod",
                "environment": "prod",
                "owner": "billing-platform",
                "limit_range": {
                    "default_requests": {
                        "cpu": "100m",
                    }
                },
                "default_deny_network_policy": True,
                "workloads": [
                    {
                        "name": "billing-worker",
                        "containers": [
                            {
                                "name": "worker",
                                "requests": {"cpu": "500m", "memory": "1Gi"},
                                "limits": {"cpu": "1", "memory": "2Gi"},
                            }
                        ],
                    }
                ],
            },
        ]

        findings = review_namespaces(namespaces)
        messages = [finding.message for finding in findings]

        self.assertEqual(10, len(findings))
        self.assertIn("production namespace has no ResourceQuota", messages)
        self.assertIn("production namespace is missing an owner", messages)
        self.assertIn("resource quota missing hard limit(s): memory, pods", messages)
        self.assertIn("production namespace has no LimitRange", messages)
        self.assertIn("default-deny NetworkPolicy is not enabled", messages)
        self.assertIn("checkout-api/app missing request(s): memory", messages)
        self.assertIn("checkout-api/app missing limit(s): cpu, memory", messages)
        self.assertIn("checkout-api/sidecar missing request(s): cpu, memory", messages)
        self.assertIn("checkout-api/sidecar missing limit(s): cpu", messages)
        self.assertIn("LimitRange missing default request(s): memory", messages)

    def test_loader_rejects_duplicate_namespaces(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write('{"namespaces": [{"name": "apps"}, {"name": "apps"}]}')
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate namespace"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
