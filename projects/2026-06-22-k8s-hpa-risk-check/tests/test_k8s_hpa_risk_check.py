import unittest

from k8s_hpa_risk_check import analyze_snapshot, render_text


class K8sHpaRiskCheckTests(unittest.TestCase):
    def test_risky_snapshot_flags_expected_issues(self) -> None:
        snapshot = {
            "items": [
                {
                    "kind": "Deployment",
                    "metadata": {"namespace": "prod", "name": "payments-api"},
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "api",
                                        "image": "example.com/payments:v1",
                                        "resources": {"requests": {"memory": "256Mi"}},
                                    }
                                ]
                            }
                        }
                    },
                },
                {
                    "kind": "HorizontalPodAutoscaler",
                    "metadata": {"namespace": "prod", "name": "payments-api"},
                    "spec": {
                        "minReplicas": 1,
                        "maxReplicas": 1,
                        "scaleTargetRef": {
                            "apiVersion": "apps/v1",
                            "kind": "Deployment",
                            "name": "payments-api",
                        },
                        "metrics": [
                            {
                                "type": "Resource",
                                "resource": {
                                    "name": "cpu",
                                    "target": {
                                        "type": "Utilization",
                                        "averageUtilization": 80,
                                    },
                                },
                            }
                        ],
                    },
                },
                {
                    "kind": "HorizontalPodAutoscaler",
                    "metadata": {"namespace": "prod", "name": "worker-missing-target"},
                    "spec": {
                        "minReplicas": 2,
                        "maxReplicas": 6,
                        "scaleTargetRef": {
                            "apiVersion": "apps/v1",
                            "kind": "Deployment",
                            "name": "worker",
                        },
                        "metrics": [
                            {
                                "type": "Resource",
                                "resource": {
                                    "name": "memory",
                                    "target": {
                                        "type": "Utilization",
                                        "averageUtilization": 75,
                                    },
                                },
                            }
                        ],
                        "behavior": {
                            "scaleDown": {"stabilizationWindowSeconds": 300}
                        },
                    },
                },
            ]
        }

        findings = analyze_snapshot(snapshot)

        self.assertEqual(
            {finding["code"] for finding in findings},
            {
                "low-min-replicas",
                "no-scale-out-room",
                "cpu-metric-without-cpu-request",
                "missing-scale-down-stabilization",
                "missing-scale-target",
            },
        )

    def test_safe_snapshot_passes(self) -> None:
        snapshot = {
            "items": [
                {
                    "kind": "Deployment",
                    "metadata": {"namespace": "prod", "name": "billing-api"},
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "api",
                                        "image": "example.com/billing:v3",
                                        "resources": {
                                            "requests": {
                                                "cpu": "250m",
                                                "memory": "256Mi",
                                            }
                                        },
                                    }
                                ]
                            }
                        }
                    },
                },
                {
                    "kind": "HorizontalPodAutoscaler",
                    "metadata": {"namespace": "prod", "name": "billing-api"},
                    "spec": {
                        "minReplicas": 3,
                        "maxReplicas": 10,
                        "scaleTargetRef": {
                            "apiVersion": "apps/v1",
                            "kind": "Deployment",
                            "name": "billing-api",
                        },
                        "metrics": [
                            {
                                "type": "Resource",
                                "resource": {
                                    "name": "cpu",
                                    "target": {
                                        "type": "Utilization",
                                        "averageUtilization": 65,
                                    },
                                },
                            }
                        ],
                        "behavior": {
                            "scaleDown": {"stabilizationWindowSeconds": 300}
                        },
                    },
                },
            ]
        }

        findings = analyze_snapshot(snapshot)

        self.assertEqual(findings, [])
        self.assertEqual(
            render_text(findings),
            "PASS: no configured Kubernetes HPA risks detected",
        )


if __name__ == "__main__":
    unittest.main()
