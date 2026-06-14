from __future__ import annotations

import unittest
from pathlib import Path

from slo_burn_rate_check import analyze, load_snapshot


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = PROJECT_ROOT / "samples"


class SloBurnRateCheckTests(unittest.TestCase):
    def test_risky_snapshot_flags_expected_windows(self) -> None:
        service, slo_target, observations = load_snapshot(SAMPLES / "risky_snapshot.json")

        summary = analyze(service, slo_target, observations, budget_days=30)

        flagged = {result.name for result in summary["results"] if result.status == "alert"}
        self.assertEqual(summary["status"], "flagged")
        self.assertEqual(summary["alert_count"], 2)
        self.assertEqual(flagged, {"5m", "1h"})

    def test_healthy_snapshot_passes(self) -> None:
        service, slo_target, observations = load_snapshot(SAMPLES / "healthy_snapshot.json")

        summary = analyze(service, slo_target, observations, budget_days=30)

        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["alert_count"], 0)
        self.assertTrue(all(result.status == "ok" for result in summary["results"]))


if __name__ == "__main__":
    unittest.main()
