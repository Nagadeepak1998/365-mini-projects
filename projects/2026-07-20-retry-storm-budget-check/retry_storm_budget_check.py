#!/usr/bin/env python3
"""Estimate retry amplification and flag unsafe retry policies."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    service: str
    rule: str
    message: str


def review(config: dict[str, Any]) -> dict[str, Any]:
    request_rate = float(config["request_rate_per_second"])
    budget = float(config["downstream_budget_per_second"])
    services = config.get("services", [])
    multiplier = 1.0
    findings: list[Finding] = []

    if not services:
        findings.append(Finding("configuration", "missing_services", "add at least one service hop"))

    for service in services:
        name = str(service.get("name", "unnamed"))
        retries = int(service.get("max_retries", 0))
        if retries < 0:
            findings.append(Finding(name, "invalid_retries", "max_retries cannot be negative"))
            retries = 0
        multiplier *= retries + 1

        if retries > 0 and not service.get("exponential_backoff", False):
            findings.append(Finding(name, "missing_backoff", "retries need exponential backoff"))
        if retries > 0 and not service.get("jitter", False):
            findings.append(Finding(name, "missing_jitter", "retries need jitter to avoid synchronized bursts"))
        if retries > 0 and not service.get("idempotent", False):
            findings.append(Finding(name, "non_idempotent_retry", "retrying this operation can duplicate side effects"))

        timeout_ms = int(service.get("timeout_ms", 0))
        retry_budget_ms = int(service.get("retry_budget_ms", 0))
        worst_case_ms = timeout_ms * (retries + 1)
        if timeout_ms <= 0:
            findings.append(Finding(name, "missing_timeout", "set a positive per-attempt timeout"))
        if retry_budget_ms <= 0 or worst_case_ms > retry_budget_ms:
            findings.append(
                Finding(
                    name,
                    "retry_deadline_exceeded",
                    f"worst-case attempts take {worst_case_ms} ms against a {retry_budget_ms} ms retry budget",
                )
            )

    amplified_rate = request_rate * multiplier
    if amplified_rate > budget:
        findings.append(
            Finding(
                "request_path",
                "downstream_budget_exceeded",
                f"worst-case load is {amplified_rate:.2f} req/s against a {budget:.2f} req/s budget",
            )
        )

    return {
        "status": "PASS" if not findings else "FLAGGED",
        "request_rate_per_second": request_rate,
        "retry_amplification": multiplier,
        "worst_case_downstream_rate_per_second": amplified_rate,
        "downstream_budget_per_second": budget,
        "headroom_per_second": budget - amplified_rate,
        "findings": [asdict(finding) for finding in findings],
    }


def format_text(result: dict[str, Any]) -> str:
    summary = (
        f"{result['status']}: worst-case {result['worst_case_downstream_rate_per_second']:.2f} req/s, "
        f"amplification {result['retry_amplification']:.2f}x, "
        f"headroom {result['headroom_per_second']:.2f} req/s"
    )
    details = [
        f"- {item['service']} [{item['rule']}]: {item['message']}"
        for item in result["findings"]
    ]
    return "\n".join([summary, *details])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="JSON retry-path configuration")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()

    result = review(json.loads(args.config.read_text()))
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else format_text(result))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
