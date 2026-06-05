#!/usr/bin/env python3
import re
import sys
from pathlib import Path


JOB_HEADER = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
JOB_NAME = re.compile(r"^\s{4}name:\s*(.+?)\s*$")
WORKFLOW_CONCURRENCY = re.compile(r"^concurrency:\s*.*$")
DEPLOY_HINTS = ("deploy", "release", "publish", "production", "staging")


def normalize(value: str) -> str:
    return value.strip().strip("'\"").lower()


def find_deploy_jobs(lines: list[str]) -> list[str]:
    deploy_jobs = []
    in_jobs = False
    current_job_id = None
    current_job_name = None

    for line in lines:
        if not in_jobs:
            if line.strip() == "jobs:":
                in_jobs = True
            continue

        header_match = JOB_HEADER.match(line)
        if header_match:
            if current_job_id and looks_like_deploy_job(current_job_id, current_job_name):
                deploy_jobs.append(current_job_id)

            current_job_id = header_match.group(1)
            current_job_name = None
            continue

        if current_job_id is None:
            continue

        name_match = JOB_NAME.match(line)
        if name_match:
            current_job_name = normalize(name_match.group(1))

    if current_job_id and looks_like_deploy_job(current_job_id, current_job_name):
        deploy_jobs.append(current_job_id)

    return deploy_jobs


def looks_like_deploy_job(job_id: str, job_name: str | None) -> bool:
    job_text = normalize(job_id)
    if any(hint in job_text for hint in DEPLOY_HINTS):
        return True

    if job_name and any(hint in job_name for hint in DEPLOY_HINTS):
        return True

    return False


def check_workflow(text: str) -> list[str]:
    lines = text.splitlines()
    deploy_jobs = find_deploy_jobs(lines)
    has_concurrency = any(WORKFLOW_CONCURRENCY.match(line) for line in lines)

    if not deploy_jobs or has_concurrency:
        return []

    job_list = ", ".join(deploy_jobs)
    return [f"deploy-like job(s) found without workflow concurrency: {job_list}"]


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 workflow_concurrency_check.py <workflow.yml>",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 2

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Failed to inspect workflow file: {exc}", file=sys.stderr)
        return 2

    findings = check_workflow(text)
    if findings:
        print(f"FAIL: {len(findings)} issue(s) found")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("PASS: workflow concurrency guard looks good")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
