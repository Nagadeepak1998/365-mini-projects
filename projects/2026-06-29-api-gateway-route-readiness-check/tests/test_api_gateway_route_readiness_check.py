from pathlib import Path
import tempfile
import unittest

from api_gateway_route_readiness_check import load_inventory, review_routes


class ApiGatewayRouteReadinessCheckTests(unittest.TestCase):
    def test_ready_inventory_has_no_findings(self):
        routes = [
            {
                "route_key": "GET /payments/{paymentId}",
                "environment": "prod",
                "owner": "payments-platform",
                "public": True,
                "critical": True,
                "auth_type": "jwt",
                "throttling": {
                    "enabled": True,
                    "rate_limit_per_second": 200,
                    "burst_limit": 400,
                },
                "access_logs": {"enabled": True, "retention_days": "30"},
                "integration": {
                    "type": "lambda",
                    "timeout_seconds": 15,
                    "lambda_alias": "live",
                    "request_validation": True,
                },
                "alarms": [
                    {
                        "metric_name": "5XXError",
                        "threshold": 5,
                        "runbook": "https://runbooks.example/api/payments",
                    },
                    {
                        "metric_name": "Latency",
                        "threshold": 1000,
                        "runbook": "https://runbooks.example/api/payments",
                    },
                ],
                "rollback_note": "Shift the alias back to the previous version.",
                "canary": {"enabled": True, "percent": 10},
            }
        ]

        findings = review_routes(routes)

        self.assertEqual([], findings)

    def test_risky_inventory_reports_expected_findings(self):
        routes = [
            {
                "route_key": "POST /checkout",
                "environment": "prod",
                "owner": "",
                "public": True,
                "critical": True,
                "auth_type": "none",
                "throttling": {"enabled": False},
                "access_logs": {"enabled": False},
                "integration": {
                    "type": "lambda",
                    "timeout_seconds": 30,
                    "lambda_alias": "",
                    "request_validation": False,
                },
                "alarms": [{"metric_name": "5XXError", "threshold": 10}],
                "rollback_note": "",
                "canary": {"enabled": False},
            },
            {
                "route_key": "GET /orders",
                "environment": "production",
                "owner": "orders-platform",
                "public": False,
                "critical": False,
                "auth_type": "aws_iam",
                "throttling": {"enabled": True, "rate_limit_per_second": 0, "burst_limit": 0},
                "access_logs": {"enabled": True, "retention_days": ""},
                "integration": {
                    "type": "lambda",
                    "timeout_seconds": 0,
                    "lambda_alias": "live",
                    "request_validation": True,
                },
                "alarms": [
                    {
                        "metric_name": "Latency",
                        "threshold": 1500,
                        "runbook": "https://runbooks.example/api/orders",
                    }
                ],
                "rollback_note": "Disable the route mapping during rollback.",
                "canary": {"enabled": False},
            },
        ]

        findings = review_routes(routes)
        messages = [finding.message for finding in findings]

        self.assertEqual(15, len(findings))
        self.assertIn("production route is missing an owner", messages)
        self.assertIn("public production route is missing strong auth", messages)
        self.assertIn("production route is missing throttling", messages)
        self.assertIn("access logs are not enabled", messages)
        self.assertIn("integration timeout is above 25 seconds", messages)
        self.assertIn("Lambda integration is not pinned to an alias", messages)
        self.assertIn("request validation is not enabled", messages)
        self.assertIn("missing alarm metric(s): Latency", messages)
        self.assertIn("missing alarm metric(s): 5XXError", messages)
        self.assertIn("one or more alarms are missing runbook links", messages)
        self.assertIn("rollback note is missing", messages)
        self.assertIn("critical production route is missing a canary plan", messages)
        self.assertIn("throttling is enabled without positive limits", messages)
        self.assertIn("access log retention is not documented", messages)
        self.assertIn("integration timeout is missing", messages)

    def test_loader_rejects_duplicate_route_keys(self):
        fixture = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        try:
            fixture.write('{"routes": [{"route_key": "GET /a"}, {"route_key": "GET /a"}]}')
            fixture.flush()

            with self.assertRaisesRegex(ValueError, "duplicate route_key"):
                load_inventory(Path(fixture.name))
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
