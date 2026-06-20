import unittest

from container_image_drift_check import collect_findings, parse_image


class ContainerImageDriftCheckTests(unittest.TestCase):
    def test_parse_image_handles_registry_port_tag_and_digest(self):
        parsed = parse_image("registry.local:5000/payments/api:1.2.3@sha256:abc123")

        self.assertEqual(parsed["repository"], "registry.local:5000/payments/api")
        self.assertEqual(parsed["tag"], "1.2.3")
        self.assertEqual(parsed["digest"], "sha256:abc123")
        self.assertTrue(parsed["has_digest"])

    def test_risky_images_are_flagged(self):
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
                                        "image": "registry.example.com/payments/api:latest",
                                        "imagePullPolicy": "IfNotPresent",
                                    },
                                    {
                                        "name": "worker",
                                        "image": "registry.example.com/payments/worker",
                                    },
                                ]
                            }
                        }
                    },
                },
                {
                    "kind": "Deployment",
                    "metadata": {"namespace": "staging", "name": "payments-api"},
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "api",
                                        "image": "registry.example.com/payments/api:1.4.2",
                                    }
                                ]
                            }
                        }
                    },
                },
            ]
        }

        findings = collect_findings(snapshot)
        codes = {finding["code"] for finding in findings}

        self.assertEqual(len(findings), 8)
        self.assertIn("missing-image-digest", codes)
        self.assertIn("mutable-image-tag", codes)
        self.assertIn("mutable-tag-with-sticky-pull-policy", codes)
        self.assertIn("untagged-image", codes)
        self.assertIn("image-version-drift", codes)

    def test_digest_pinned_images_pass_when_policy_is_not_always(self):
        snapshot = {
            "items": [
                {
                    "kind": "StatefulSet",
                    "metadata": {"namespace": "prod", "name": "ledger-db-migrator"},
                    "spec": {
                        "template": {
                            "spec": {
                                "initContainers": [
                                    {
                                        "name": "migrate",
                                        "image": (
                                            "registry.example.com/ledger/migrate"
                                            "@sha256:1111222233334444"
                                        ),
                                        "imagePullPolicy": "IfNotPresent",
                                    }
                                ],
                                "containers": [
                                    {
                                        "name": "ledger",
                                        "image": (
                                            "registry.example.com/ledger/api"
                                            "@sha256:aaaabbbbccccdddd"
                                        ),
                                        "imagePullPolicy": "IfNotPresent",
                                    }
                                ],
                            }
                        }
                    },
                }
            ]
        }

        self.assertEqual(collect_findings(snapshot), [])

    def test_cronjob_pod_template_is_checked(self):
        snapshot = {
            "kind": "CronJob",
            "metadata": {"namespace": "ops", "name": "nightly-reconcile"},
            "spec": {
                "jobTemplate": {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "reconcile",
                                        "image": "registry.example.com/ops/reconcile:nightly",
                                    }
                                ]
                            }
                        }
                    }
                }
            },
        }

        codes = {finding["code"] for finding in collect_findings(snapshot)}

        self.assertIn("mutable-image-tag", codes)
        self.assertIn("missing-image-digest", codes)


if __name__ == "__main__":
    unittest.main()
