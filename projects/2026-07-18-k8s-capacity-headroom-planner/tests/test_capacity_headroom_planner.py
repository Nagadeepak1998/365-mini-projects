import unittest

from capacity_headroom_planner import build_plan


def snapshot(**overrides):
    data = {
        "name": "checkout-api",
        "current_rps": 600,
        "growth_percent": 50,
        "safe_rps_per_pod": 150,
        "current_replicas": 6,
        "hpa_max_replicas": 10,
        "largest_node_pod_count": 2,
    }
    data.update(overrides)
    return data


class BuildPlanTests(unittest.TestCase):
    def test_recommends_scale_with_node_loss_reserve(self):
        plan = build_plan(snapshot())

        self.assertEqual(plan["projected_rps"], 900.0)
        self.assertEqual(plan["traffic_replicas"], 6)
        self.assertEqual(plan["recommended_replicas"], 8)
        self.assertEqual(plan["status"], "SCALE")
        self.assertEqual(plan["current_gap"], 2)

    def test_ready_when_current_capacity_covers_plan(self):
        plan = build_plan(snapshot(current_replicas=8))

        self.assertEqual(plan["status"], "READY")
        self.assertEqual(plan["current_gap"], 0)

    def test_blocks_when_hpa_ceiling_is_too_low(self):
        plan = build_plan(snapshot(hpa_max_replicas=7))

        self.assertEqual(plan["status"], "BLOCKED")
        self.assertEqual(plan["hpa_gap"], 1)

    def test_rejects_missing_or_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "missing fields"):
            build_plan({"name": "api"})
        with self.assertRaisesRegex(ValueError, "safe_rps_per_pod"):
            build_plan(snapshot(safe_rps_per_pod=0))
        with self.assertRaisesRegex(ValueError, "non-negative integers"):
            build_plan(snapshot(largest_node_pod_count=1.5))


if __name__ == "__main__":
    unittest.main()
