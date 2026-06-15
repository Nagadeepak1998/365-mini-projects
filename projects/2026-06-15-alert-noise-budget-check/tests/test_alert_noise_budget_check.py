from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from alert_noise_budget_check import (
    AlertSample,
    acknowledgement_rate,
    actionable_rate,
    analyze,
    build_summary,
    duplicate_ratio,
)


PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT_DIR / "alert_noise_budget_check.py"
NOISY_SAMPLE = PROJECT_DIR / "samples" / "noisy_alerts.json"
HEALTHY_SAMPLE = PROJECT_DIR / "samples" / "healthy_alerts.json"


class AlertNoiseBudgetCheckTests(unittest.TestCase):
    def test_rates(self) -> None:
        alert = AlertSample(
            name="checkout-latency-high",
            severity="page",
            pages=8,
            unique_incidents=2,
            acknowledged_pages=6,
            actionable_pages=3,
        )
        self.assertAlmostEqual(actionable_rate(alert), 0.375)
        self.assertAlmostEqual(duplicate_ratio(alert), 4.0)
        self.assertAlmostEqual(acknowledgement_rate(alert), 0.75)

    def test_analyze_flags_noisy_alert(self) -> None:
        findings = analyze(
            [
                AlertSample(
                    name="checkout-latency-high",
                    severity="page",
                    pages=8,
                    unique_incidents=2,
                    acknowledged_pages=6,
                    actionable_pages=3,
                )
            ],
            page_threshold=5,
            min_actionable_rate=0.5,
        )
        self.assertEqual({finding.code for finding in findings}, {"low-actionability", "repeat-pages", "poor-ack-rate"})

    def test_build_summary_marks_pass(self) -> None:
        snapshot = {"service": "checkout-api", "window": "7d"}
        alerts = [
            AlertSample(
                name="node-disk-low",
                severity="page",
                pages=2,
                unique_incidents=2,
                acknowledged_pages=2,
                actionable_pages=2,
            )
        ]
        summary = build_summary(snapshot, alerts, [])
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["total_pages"], 2)

    def test_cli_returns_non_zero_for_noisy_sample(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPT), str(NOISY_SAMPLE)],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FLAGGED", result.stdout)
        self.assertIn("checkout-latency-high", result.stdout)

    def test_cli_returns_zero_and_json_for_healthy_sample(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPT), str(HEALTHY_SAMPLE), "--format", "json"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")

    def test_cli_uses_custom_thresholds(self) -> None:
        payload = {
            "service": "billing-api",
            "window": "7d",
            "alerts": [
                {
                    "name": "billing-error-rate",
                    "severity": "page",
                    "pages": 4,
                    "unique_incidents": 1,
                    "acknowledged_pages": 2,
                    "actionable_pages": 1,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.json"
            snapshot_path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    str(snapshot_path),
                    "--page-threshold",
                    "4",
                ],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("billing-error-rate", result.stdout)


if __name__ == "__main__":
    unittest.main()
