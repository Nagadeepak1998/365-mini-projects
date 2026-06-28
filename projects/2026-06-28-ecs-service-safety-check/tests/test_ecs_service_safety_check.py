from pathlib import Path
import tempfile
import unittest

from ecs_service_safety_check import load_inventory, review_services


class EcsServiceSafetyCheckTests(unittest.TestCase):
    def test_ready_inventory_has_no_findings(self):
        services = [
            {
                "name": "payments-api",
                "environment": "prod",
                "owner": "payments-platform",
                "critical": True,
                "desired_count": 3,
                "public_endpoint": True,
                "deployment": {
                    "circuit_breaker_enabled": True,
                    "rollback_enabled": True,
                    "minimum_healthy_percent": 100,
                    "maximum_percent": 200,
                },
                "load_balancer": {"enabled": True, "health_check_path": "/health"},
                "health_check_grace_period_seconds": 60,
                "alarms": [
                    {
                        "metric_name": "CPUUtilization",
                        "threshold": 80,
                        "runbook": "https://runbooks.example/ecs/payments-api",
                    },
                    {
                        "metric_name": "MemoryUtilization",
                        "threshold": 85,
                        "runbook": "https://runbooks.example/ecs/payments-api",
                    },
                ],
                "task_definition": {
                    "image": "repo/payments-api:2026-06-28",
                    "image_digest": "sha256:0123456789abcdef",
                    "log_retention_days": 30,
                },
            }
        ]

        findings = review_services(services)

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        services = [
            {
                "name": "checkout-api",
                "environment": "prod",
                "owner": "",
                "critical": True,
                "desired_count": 1,
                "public_endpoint": True,
                "deployment": {
                    "circuit_breaker_enabled": False,
                    "rollback_enabled": False,
                    "minimum_healthy_percent": 50,
                    "maximum_percent": 100,
                },
                "load_balancer": {"enabled": False},
                "health_check_grace_period_seconds": 0,
                "alarms": [{"metric_name": "CPUUtilization", "threshold": 90}],
                "task_definition": {"image": "repo/checkout-api:latest", "log_retention_days": 7},
            },
            {
                "name": "worker",
                "environment": "production",
                "owner": "orders-platform",
                "critical": False,
                "desired_count": 2,
                "public_endpoint": False,
                "deployment": {
                    "circuit_breaker_enabled": True,
                    "rollback_enabled": True,
                    "minimum_healthy_percent": 100,
                    "maximum_percent": 250,
                },
                "load_balancer": {"enabled": True},
                "health_check_grace_period_seconds": 45,
                "alarms": [
                    {
                        "metric_name": "MemoryUtilization",
                        "threshold": 85,
                        "runbook": "https://runbooks.example/ecs/worker",
                    }
                ],
                "task_definition": {"image": "repo/worker:stable", "log_retention_days": 3},
            },
        ]

        findings = review_services(services)
        messages = [finding.message for finding in findings]

        self.assertEqual(16, len(findings))
        self.assertIn("production service is missing an owner", messages)
        self.assertIn("production or critical service should run at least 2 tasks", messages)
        self.assertIn("ECS deployment circuit breaker is not enabled", messages)
        self.assertIn("ECS deployment rollback is not enabled", messages)
        self.assertIn("maximum_percent leaves no room for replacement tasks", messages)
        self.assertIn("public service is missing a load balancer health gate", messages)
        self.assertIn("health_check_grace_period_seconds should be at least 30", messages)
        self.assertIn("missing alarm metric(s): MemoryUtilization", messages)
        self.assertIn("one or more alarms are missing runbook links", messages)
        self.assertIn("task image is mutable or missing a digest pin", messages)
        self.assertIn("log retention is below 14 days", messages)
        self.assertIn("maximum_percent above 200 can create a large surge during deploys", messages)
        self.assertIn("load balancer is missing a health check path", messages)
        self.assertIn("missing alarm metric(s): CPUUtilization", messages)

    def test_loader_rejects_duplicate_service_names(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write('{"services": [{"name": "api"}, {"name": "api"}]}')
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate service name"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
