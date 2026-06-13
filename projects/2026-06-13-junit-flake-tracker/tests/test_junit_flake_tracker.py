from __future__ import annotations

import unittest
from pathlib import Path

from junit_flake_tracker import analyze, load_reports


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = PROJECT_ROOT / "samples"


class JunitFlakeTrackerTests(unittest.TestCase):
    def test_reports_produce_expected_findings(self) -> None:
        observations = load_reports([SAMPLES / "run_01.xml", SAMPLES / "run_02.xml"])

        findings = analyze(
            observations,
            slow_threshold=2.0,
            min_repeated_failures=2,
        )

        summary = {(finding.code, finding.test_id) for finding in findings}
        self.assertEqual(
            summary,
            {
                ("flaky-test", "tests.api.test_orders::test_checkout_retry"),
                ("repeated-failure", "tests.jobs.test_sync::test_backfill_job"),
                ("slow-test", "tests.ui.test_dashboard::test_homepage_render"),
            },
        )
        self.assertEqual(len(findings), 3)

    def test_single_clean_report_passes(self) -> None:
        observations = load_reports([SAMPLES / "stable_run.xml"])

        findings = analyze(
            observations,
            slow_threshold=2.0,
            min_repeated_failures=2,
        )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
