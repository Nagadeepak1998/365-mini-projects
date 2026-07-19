import unittest

from otel_sampling_budget_planner import review


class SamplingBudgetTests(unittest.TestCase):
    def test_safe_plan_passes_with_calculated_headroom(self):
        result = review({"collector_budget_spans_per_second": 1000, "services": [{
            "name": "checkout", "critical": True, "requests_per_second": 500,
            "average_spans_per_trace": 8, "baseline_sample_rate": 0.1,
            "error_sample_rate": 1, "high_latency_sample_rate": 1,
        }]})
        self.assertEqual("PASS", result["status"])
        self.assertEqual(400, result["estimated_spans_per_second"])
        self.assertEqual(600, result["headroom_spans_per_second"])

    def test_over_budget_plan_is_flagged(self):
        result = review({"collector_budget_spans_per_second": 100, "services": [{
            "name": "search", "requests_per_second": 1000, "average_spans_per_trace": 5,
            "baseline_sample_rate": 0.1, "error_sample_rate": 1,
            "high_latency_sample_rate": 0.5,
        }]})
        self.assertEqual("FLAGGED", result["status"])
        self.assertTrue(any("exceeds collector budget" in finding for finding in result["findings"]))

    def test_critical_coverage_gaps_are_explained(self):
        result = review({"collector_budget_spans_per_second": 1000, "services": [{
            "name": "payments", "critical": True, "requests_per_second": 100,
            "average_spans_per_trace": 4, "baseline_sample_rate": 0.01,
            "error_sample_rate": 0.5, "high_latency_sample_rate": 0.25,
        }]})
        self.assertEqual(3, len(result["findings"]))

    def test_empty_plan_is_flagged(self):
        result = review({"collector_budget_spans_per_second": 100, "services": []})
        self.assertIn("sampling plan has no services", result["findings"])


if __name__ == "__main__":
    unittest.main()
