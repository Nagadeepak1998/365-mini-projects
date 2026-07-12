#!/usr/bin/env python3
"""Review a saved Kubernetes CronJob inventory for reliability risks."""

import argparse
import json
from datetime import date, datetime
from pathlib import Path


def days_since(value: str, today: date) -> int:
    return (today - datetime.fromisoformat(value.replace("Z", "+00:00")).date()).days


def check_cronjob(job: dict, today: date) -> list[str]:
    name = job.get("name", "<unnamed>")
    issues = []

    def flag(condition: bool, message: str) -> None:
        if condition:
            issues.append(f"{name}: {message}")

    flag(not job.get("owner"), "owner is missing")
    flag(job.get("suspend") is True, "schedule is suspended")
    flag(job.get("concurrency_policy") == "Allow", "concurrency policy allows overlapping runs")
    flag(not job.get("starting_deadline_seconds"), "starting deadline is not set")
    flag(job.get("backoff_limit", 6) > 3, "backoff limit permits more than 3 retries")
    flag(job.get("successful_jobs_history_limit", 3) < 1, "successful job history is disabled")
    flag(job.get("failed_jobs_history_limit", 1) < 1, "failed job history is disabled")
    flag(not job.get("active_deadline_seconds"), "active deadline is not set")
    flag(not job.get("resources_configured"), "CPU and memory controls are missing")

    last_success = job.get("last_successful_time")
    max_age = job.get("max_success_age_days")
    flag(not last_success, "last successful run is missing")
    if last_success and max_age is not None:
        flag(days_since(last_success, today) > max_age, "last successful run is stale")
    return issues


def review(data: dict, today: date) -> list[str]:
    return [issue for job in data.get("cronjobs", []) for issue in check_cronjob(job, today)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    issues = review(json.loads(args.inventory.read_text()), args.today)
    if issues:
        print(f"FLAGGED: {len(issues)} CronJob reliability issue(s) detected")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("PASS: Kubernetes CronJob inventory looks reliable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
