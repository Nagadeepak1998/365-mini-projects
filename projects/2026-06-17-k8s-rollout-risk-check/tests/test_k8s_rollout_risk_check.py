import unittest

from k8s_rollout_risk_check import analyze_snapshot, render_text


class K8sRolloutRiskCheckTests(unittest.TestCase):
    def test_risky_snapshot_flags_expected_issues(self) -> None:
        snapshot = {
            "items": [
                {
                    "kind": "Deployment",
                    "metadata": {"namespace": "prod", "name": "payments-api"},
                    "spec": {
                        "replicas": 1,
                        "strategy": {
                            "type": "RollingUpdate",
                            "rollingUpdate": {"maxUnavailable": 1},
                        },
                        "template": {
                            "metadata": {"labels": {"app": "payments-api"}},
                            "spec": {
                                "containers": [
                                    {
                                        "name": "api",
                                        "image": "example.com/payments:v1",
                                    }
                                ]
                            },
                        },
                    },
                },
                {
                    "kind": "StatefulSet",
                    "metadata": {"namespace": "prod", "name": "orders-worker"},
                    "spec": {
                        "replicas": 3,
                        "updateStrategy": {
                            "type": "RollingUpdate",
                            "rollingUpdate": {"maxUnavailable": "100%"},
                        },
                        "template": {
                            "metadata": {"labels": {"app": "orders-worker"}},
                            "spec": {
                                "containers": [
                                    {
                                        "name": "worker",
                                        "image": "example.com/orders:v4",
                                        "readinessProbe": {"tcpSocket": {"port": 8080}},
                                    }
                                ]
                            },
                        },
                    },
                },
                {
                    "kind": "Deployment",
                    "metadata": {"namespace": "prod", "name": "catalog-api"},
                    "spec": {
                        "replicas": 2,
                        "strategy": {
                            "type": "RollingUpdate",
                            "rollingUpdate": {"maxUnavailable": 1},
                        },
                        "template": {
                            "metadata": {"labels": {"app": "catalog-api"}},
                            "spec": {
                                "containers": [
                                    {
                                        "name": "api",
                                        "image": "example.com/catalog:v2",
                                        "readinessProbe": {"httpGet": {"path": "/ready", "port": 8080}},
                                    }
                                ]
                            },
                        },
                    },
                },
                {
                    "kind": "PodDisruptionBudget",
                    "metadata": {"namespace": "prod", "name": "orders-worker-pdb"},
                    "spec": {
                        "maxUnavailable": 3,
                        "selector": {"matchLabels": {"app": "orders-worker"}},
                    },
                },
            ]
        }

        findings = analyze_snapshot(snapshot)

        self.assertEqual(len(findings), 5)
        self.assertEqual(
            {finding["code"] for finding in findings},
            {
                "single-replica-rollout",
                "missing-readiness-probe",
                "max-unavailable-all-replicas",
                "missing-pdb",
                "pdb-allows-total-disruption",
            },
        )

    def test_safe_snapshot_passes(self) -> None:
        snapshot = {
            "items": [
                {
                    "kind": "Deployment",
                    "metadata": {"namespace": "prod", "name": "billing-api"},
                    "spec": {
                        "replicas": 3,
                        "strategy": {
                            "type": "RollingUpdate",
                            "rollingUpdate": {"maxUnavailable": 1},
                        },
                        "template": {
                            "metadata": {"labels": {"app": "billing-api"}},
                            "spec": {
                                "containers": [
                                    {
                                        "name": "api",
                                        "image": "example.com/billing:v3",
                                        "readinessProbe": {"httpGet": {"path": "/ready", "port": 8080}},
                                    }
                                ]
                            },
                        },
                    },
                },
                {
                    "kind": "PodDisruptionBudget",
                    "metadata": {"namespace": "prod", "name": "billing-api-pdb"},
                    "spec": {
                        "minAvailable": 2,
                        "selector": {"matchLabels": {"app": "billing-api"}},
                    },
                },
            ]
        }

        findings = analyze_snapshot(snapshot)

        self.assertEqual(findings, [])
        self.assertEqual(
            render_text(findings),
            "PASS: no configured Kubernetes rollout risks detected",
        )


if __name__ == "__main__":
    unittest.main()
