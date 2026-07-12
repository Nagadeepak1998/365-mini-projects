import unittest
from datetime import date

from cronjob_reliability_check import check_cronjob, review


SAFE_JOB = {
    "name": "billing-rollup",
    "owner": "data-platform",
    "suspend": False,
    "concurrency_policy": "Forbid",
    "starting_deadline_seconds": 300,
    "backoff_limit": 2,
    "successful_jobs_history_limit": 3,
    "failed_jobs_history_limit": 2,
    "active_deadline_seconds": 1800,
    "resources_configured": True,
    "last_successful_time": "2026-07-12T07:00:00Z",
    "max_success_age_days": 1
}


class CronJobReliabilityCheckTests(unittest.TestCase):
    def test_safe_job_has_no_issues(self):
        self.assertEqual(check_cronjob(SAFE_JOB, date(2026, 7, 12)), [])

    def test_risky_job_reports_each_control(self):
        risky = {
            "name": "cleanup",
            "suspend": True,
            "concurrency_policy": "Allow",
            "backoff_limit": 6,
            "successful_jobs_history_limit": 0,
            "failed_jobs_history_limit": 0,
            "resources_configured": False,
            "last_successful_time": "2026-06-01T00:00:00Z",
            "max_success_age_days": 2
        }
        issues = check_cronjob(risky, date(2026, 7, 12))
        self.assertEqual(len(issues), 10)
        self.assertTrue(any("overlapping" in issue for issue in issues))
        self.assertTrue(any("stale" in issue for issue in issues))

    def test_review_combines_jobs(self):
        risky = {**SAFE_JOB, "name": "report", "owner": ""}
        self.assertEqual(review({"cronjobs": [SAFE_JOB, risky]}, date(2026, 7, 12)), ["report: owner is missing"])


if __name__ == "__main__":
    unittest.main()
