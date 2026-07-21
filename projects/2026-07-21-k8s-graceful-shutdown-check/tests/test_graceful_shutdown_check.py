import unittest

from graceful_shutdown_check import review_inventory, review_workload


SAFE_WORKLOAD = {
    "name": "checkout-api",
    "owner": "payments-platform",
    "environment": "production",
    "replicas": 3,
    "pod_disruption_budget": True,
    "handles_sigterm": True,
    "stops_accepting_work": True,
    "pre_stop_seconds": 10,
    "endpoint_removal_seconds": 8,
    "max_inflight_seconds": 20,
    "shutdown_buffer_seconds": 5,
    "termination_grace_period_seconds": 35,
    "retries_inflight_work": True,
    "idempotent_processing": True,
}


class GracefulShutdownCheckTests(unittest.TestCase):
    def test_safe_workload_passes(self):
        self.assertEqual([], review_workload(SAFE_WORKLOAD))

    def test_timing_gaps_are_explained(self):
        workload = SAFE_WORKLOAD | {
            "pre_stop_seconds": 3,
            "endpoint_removal_seconds": 8,
            "termination_grace_period_seconds": 20,
        }
        findings = review_workload(workload)
        self.assertEqual(
            ["ENDPOINT_DRAIN_GAP", "GRACE_PERIOD_TOO_SHORT"],
            [finding["code"] for finding in findings],
        )
        self.assertIn("5s shorter", findings[0]["message"])
        self.assertIn("28s", findings[1]["message"])

    def test_production_and_retry_risks_are_flagged(self):
        workload = SAFE_WORKLOAD | {
            "replicas": 1,
            "pod_disruption_budget": False,
            "idempotent_processing": False,
        }
        codes = {finding["code"] for finding in review_workload(workload)}
        self.assertEqual({"SINGLE_REPLICA", "MISSING_PDB", "NON_IDEMPOTENT_RETRY"}, codes)

    def test_inventory_report_has_ci_friendly_status(self):
        report = review_inventory({"workloads": [SAFE_WORKLOAD]})
        self.assertEqual("PASS", report["status"])
        self.assertEqual(1, report["workloads_reviewed"])
        self.assertEqual(0, report["finding_count"])


if __name__ == "__main__":
    unittest.main()
