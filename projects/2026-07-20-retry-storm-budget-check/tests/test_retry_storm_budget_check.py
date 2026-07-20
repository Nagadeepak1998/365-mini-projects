import unittest

from retry_storm_budget_check import format_text, review


class RetryStormBudgetCheckTests(unittest.TestCase):
    def test_safe_path_passes(self):
        result = review(
            {
                "request_rate_per_second": 50,
                "downstream_budget_per_second": 250,
                "services": [
                    {
                        "name": "inventory-api",
                        "max_retries": 2,
                        "timeout_ms": 200,
                        "retry_budget_ms": 700,
                        "exponential_backoff": True,
                        "jitter": True,
                        "idempotent": True,
                    }
                ],
            }
        )
        self.assertEqual("PASS", result["status"])
        self.assertEqual(3.0, result["retry_amplification"])
        self.assertEqual(100.0, result["headroom_per_second"])

    def test_retries_multiply_across_hops(self):
        result = review(
            {
                "request_rate_per_second": 100,
                "downstream_budget_per_second": 500,
                "services": [
                    {"name": "api", "max_retries": 2, "timeout_ms": 500, "retry_budget_ms": 1000},
                    {"name": "worker", "max_retries": 2, "timeout_ms": 400, "retry_budget_ms": 1000},
                ],
            }
        )
        self.assertEqual(9.0, result["retry_amplification"])
        self.assertEqual(900.0, result["worst_case_downstream_rate_per_second"])
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertIn("downstream_budget_exceeded", rules)
        self.assertIn("retry_deadline_exceeded", rules)

    def test_unsafe_policy_flags_guardrails(self):
        result = review(
            {
                "request_rate_per_second": 10,
                "downstream_budget_per_second": 100,
                "services": [
                    {"name": "payments", "max_retries": 1, "timeout_ms": 100, "retry_budget_ms": 300}
                ],
            }
        )
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertEqual("FLAGGED", result["status"])
        self.assertTrue({"missing_backoff", "missing_jitter", "non_idempotent_retry"}.issubset(rules))

    def test_text_summary_is_explainable(self):
        result = review({"request_rate_per_second": 1, "downstream_budget_per_second": 5, "services": []})
        output = format_text(result)
        self.assertIn("FLAGGED", output)
        self.assertIn("missing_services", output)


if __name__ == "__main__":
    unittest.main()
