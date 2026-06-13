#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestObservation:
    report: str
    status: str
    duration_seconds: float
    detail: str | None


@dataclass(frozen=True)
class Finding:
    code: str
    test_id: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize flaky, repeated-failure, and slow-test signals from JUnit XML reports."
    )
    parser.add_argument("reports", nargs="+", help="JUnit XML report files to inspect.")
    parser.add_argument(
        "--slow-threshold",
        type=float,
        default=2.0,
        help="Flag tests whose maximum duration is at least this many seconds.",
    )
    parser.add_argument(
        "--min-repeated-failures",
        type=int,
        default=2,
        help="Flag tests that fail in this many or more reports.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args()


def testcase_status(testcase: ET.Element) -> tuple[str, str | None]:
    if testcase.find("failure") is not None:
        failure = testcase.find("failure")
        return "failed", failure.get("message") or (failure.text or "").strip() or None
    if testcase.find("error") is not None:
        error = testcase.find("error")
        return "error", error.get("message") or (error.text or "").strip() or None
    if testcase.find("skipped") is not None:
        skipped = testcase.find("skipped")
        return "skipped", skipped.get("message") or (skipped.text or "").strip() or None
    return "passed", None


def parse_report(path: Path) -> dict[str, TestObservation]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    observations: dict[str, TestObservation] = {}

    for testcase in root.iter("testcase"):
        classname = testcase.get("classname", "unknown")
        name = testcase.get("name", "unnamed")
        test_id = f"{classname}::{name}"
        status, detail = testcase_status(testcase)
        duration_seconds = float(testcase.get("time", "0") or "0")
        observations[test_id] = TestObservation(
            report=path.name,
            status=status,
            duration_seconds=duration_seconds,
            detail=detail,
        )

    return observations


def load_reports(paths: list[Path]) -> dict[str, list[TestObservation]]:
    combined: dict[str, list[TestObservation]] = {}
    for path in paths:
        for test_id, observation in parse_report(path).items():
            combined.setdefault(test_id, []).append(observation)
    return combined


def analyze(
    observations_by_test: dict[str, list[TestObservation]],
    slow_threshold: float,
    min_repeated_failures: int,
) -> list[Finding]:
    findings: list[Finding] = []

    for test_id, observations in sorted(observations_by_test.items()):
        statuses = {observation.status for observation in observations}
        failed_reports = [
            observation.report for observation in observations if observation.status in {"failed", "error"}
        ]
        max_duration = max(observation.duration_seconds for observation in observations)

        if "passed" in statuses and (statuses & {"failed", "error"}):
            findings.append(
                Finding(
                    code="flaky-test",
                    test_id=test_id,
                    detail=(
                        "test both passed and failed across reports: "
                        + ", ".join(
                            f"{observation.report}={observation.status}" for observation in observations
                        )
                    ),
                )
            )

        if len(failed_reports) >= min_repeated_failures:
            findings.append(
                Finding(
                    code="repeated-failure",
                    test_id=test_id,
                    detail=(
                        f"test failed in {len(failed_reports)} reports: "
                        + ", ".join(failed_reports)
                    ),
                )
            )

        if max_duration >= slow_threshold:
            findings.append(
                Finding(
                    code="slow-test",
                    test_id=test_id,
                    detail=f"slowest run took {max_duration:.2f}s which meets or exceeds the {slow_threshold:.2f}s threshold",
                )
            )

    return findings


def as_text(findings: list[Finding]) -> str:
    if not findings:
        return "PASS: no obvious flaky, repeated-failure, or slow-test signals detected"

    lines = [f"FLAGGED: {len(findings)} issue(s)"]
    for finding in findings:
        lines.append(f"- [{finding.code}] {finding.test_id}: {finding.detail}")
    return "\n".join(lines)


def as_json(paths: list[Path], findings: list[Finding]) -> str:
    payload = {
        "reports": [str(path) for path in paths],
        "status": "flagged" if findings else "pass",
        "finding_count": len(findings),
        "findings": [
            {"code": finding.code, "test_id": finding.test_id, "detail": finding.detail}
            for finding in findings
        ],
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    args = parse_args()
    paths = [Path(report) for report in args.reports]
    observations_by_test = load_reports(paths)
    findings = analyze(
        observations_by_test,
        slow_threshold=args.slow_threshold,
        min_repeated_failures=args.min_repeated_failures,
    )

    if args.format == "json":
        print(as_json(paths, findings))
    else:
        print(as_text(findings))

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
