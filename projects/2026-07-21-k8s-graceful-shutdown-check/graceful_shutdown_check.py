#!/usr/bin/env python3
"""Review Kubernetes workload shutdown settings using a saved JSON inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def review_workload(workload: dict[str, Any]) -> list[dict[str, str]]:
    name = str(workload.get("name") or "<unnamed>")
    findings: list[dict[str, str]] = []

    def add(code: str, message: str) -> None:
        findings.append({"workload": name, "code": code, "message": message})

    if not workload.get("owner"):
        add("MISSING_OWNER", "assign an owner for shutdown failures")
    if not workload.get("handles_sigterm", False):
        add("SIGTERM_NOT_HANDLED", "handle SIGTERM and begin graceful shutdown")
    if not workload.get("stops_accepting_work", False):
        add("ACCEPTS_NEW_WORK", "stop accepting new work during shutdown")

    pre_stop = workload.get("pre_stop_seconds")
    endpoint_removal = workload.get("endpoint_removal_seconds")
    max_inflight = workload.get("max_inflight_seconds")
    buffer_seconds = workload.get("shutdown_buffer_seconds", 5)
    grace = workload.get("termination_grace_period_seconds")

    numeric_values = (pre_stop, endpoint_removal, max_inflight, buffer_seconds, grace)
    if any(not isinstance(value, (int, float)) or value < 0 for value in numeric_values):
        add("INVALID_TIMING", "provide non-negative numeric shutdown timing values")
    else:
        if pre_stop < endpoint_removal:
            add(
                "ENDPOINT_DRAIN_GAP",
                f"preStop is {endpoint_removal - pre_stop:g}s shorter than endpoint removal",
            )
        required_grace = pre_stop + max_inflight + buffer_seconds
        if grace < required_grace:
            add(
                "GRACE_PERIOD_TOO_SHORT",
                f"termination grace is {grace:g}s; budget at least {required_grace:g}s",
            )

    if workload.get("environment") == "production":
        replicas = workload.get("replicas", 0)
        if not isinstance(replicas, int) or replicas < 2:
            add("SINGLE_REPLICA", "run at least two production replicas")
        if not workload.get("pod_disruption_budget", False):
            add("MISSING_PDB", "protect production availability with a PodDisruptionBudget")

    if workload.get("retries_inflight_work", False) and not workload.get(
        "idempotent_processing", False
    ):
        add("NON_IDEMPOTENT_RETRY", "make retried in-flight work idempotent")

    return findings


def review_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    workloads = inventory.get("workloads")
    if not isinstance(workloads, list):
        raise ValueError("inventory must contain a 'workloads' list")

    findings = [
        finding
        for workload in workloads
        if isinstance(workload, dict)
        for finding in review_workload(workload)
    ]
    return {
        "status": "PASS" if not findings else "FLAGGED",
        "workloads_reviewed": len(workloads),
        "finding_count": len(findings),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Kubernetes workloads for graceful-shutdown readiness."
    )
    parser.add_argument("inventory", type=Path, help="path to a JSON workload inventory")
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args()

    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        report = review_inventory(inventory)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["status"] == "PASS":
        print(f"PASS: {report['workloads_reviewed']} workload(s) are ready for graceful shutdown")
    else:
        print(f"FLAGGED: {report['finding_count']} graceful-shutdown issue(s) detected")
        for finding in report["findings"]:
            print(f"- {finding['workload']} [{finding['code']}]: {finding['message']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
