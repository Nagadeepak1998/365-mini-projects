#!/usr/bin/env python3
import re
import sys
from pathlib import Path


SENSITIVE_WRITE_SCOPES = {
    "actions",
    "checks",
    "contents",
    "deployments",
    "issues",
    "packages",
    "pull-requests",
    "repository-projects",
    "security-events",
    "statuses",
}

JOB_HEADER_PATTERN = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def collect_permission_block(lines: list[str], start_index: int) -> tuple[dict[str, str], int]:
    line = lines[start_index]
    indent = indentation(line)
    stripped = line.strip()

    inline_value = stripped.split(":", 1)[1].strip()
    if inline_value:
        return {"__inline__": inline_value}, start_index + 1

    entries: dict[str, str] = {}
    index = start_index + 1
    while index < len(lines):
        current = lines[index]
        if not current.strip() or current.lstrip().startswith("#"):
            index += 1
            continue

        current_indent = indentation(current)
        if current_indent <= indent:
            break

        stripped_current = current.strip()
        if ":" in stripped_current:
            key, value = stripped_current.split(":", 1)
            entries[key.strip()] = value.strip()

        index += 1

    return entries, index


def analyze_workflow(text: str) -> list[str]:
    lines = text.splitlines()
    findings: list[str] = []
    top_level_permissions_found = False
    jobs_seen: list[str] = []
    job_permissions_found: dict[str, bool] = {}
    in_jobs = False
    current_job: str | None = None
    current_job_indent: int | None = None

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        if stripped == "jobs:":
            in_jobs = True
            current_job = None
            current_job_indent = indentation(line)
            index += 1
            continue

        if in_jobs and indentation(line) <= (current_job_indent or 0) and not line.startswith(" "):
            in_jobs = False
            current_job = None

        if not in_jobs and stripped.startswith("permissions:"):
            top_level_permissions_found = True
            block, next_index = collect_permission_block(lines, index)
            inline_value = block.get("__inline__")
            if inline_value == "write-all":
                findings.append("FAIL: top-level permissions use write-all")
            for scope, value in block.items():
                if scope in SENSITIVE_WRITE_SCOPES and value == "write":
                    findings.append(
                        f"FAIL: top-level permissions grant {scope}: write"
                    )
            index = next_index
            continue

        if in_jobs:
            header_match = JOB_HEADER_PATTERN.match(line)
            if header_match:
                current_job = header_match.group(1)
                jobs_seen.append(current_job)
                job_permissions_found[current_job] = False
                index += 1
                continue

            if current_job and stripped.startswith("permissions:") and indentation(line) >= 4:
                job_permissions_found[current_job] = True
                block, next_index = collect_permission_block(lines, index)
                inline_value = block.get("__inline__")
                if inline_value == "write-all":
                    findings.append(
                        f"FAIL: job '{current_job}' permissions use write-all"
                    )
                for scope, value in block.items():
                    if scope in SENSITIVE_WRITE_SCOPES and value == "write":
                        findings.append(
                            f"FAIL: job '{current_job}' grants {scope}: write"
                        )
                index = next_index
                continue

        index += 1

    if not top_level_permissions_found:
        findings.append("WARN: workflow has no explicit top-level permissions block")

    for job in jobs_seen:
        if not job_permissions_found.get(job):
            findings.append(f"WARN: job '{job}' has no explicit permissions block")

    return findings


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 workflow_permission_check.py <workflow.yml>",
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
        print(f"Failed to read workflow file: {exc}", file=sys.stderr)
        return 2

    findings = analyze_workflow(text)
    if not findings:
        print("PASS: workflow permissions look narrowly scoped")
        return 0

    print(f"FLAGGED: {len(findings)} finding(s)")
    for finding in findings:
        print(f"- {finding}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
