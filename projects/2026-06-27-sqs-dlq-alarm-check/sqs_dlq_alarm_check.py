#!/usr/bin/env python3
"""Review SQS queue inventories for dead-letter queue and alarm gaps."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCTION_ENVS = {"prod", "production"}
DEFAULT_MAX_DLQ_ALARM_THRESHOLD = 10


@dataclass(frozen=True)
class Finding:
    severity: str
    queue: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.queue}: {self.message}"


def has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalize_env(value: Any) -> str:
    return str(value or "").strip().lower()


def parse_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return default


def load_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    queues = raw.get("queues") if isinstance(raw, dict) else None
    if not isinstance(queues, list):
        raise ValueError(f"{path}: expected top-level object with a queues list")

    names: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, queue in enumerate(queues, start=1):
        if not isinstance(queue, dict):
            raise ValueError(f"{path}: queues[{index}] must be an object")
        name = queue.get("name")
        if not has_text(name):
            raise ValueError(f"{path}: queues[{index}] must include a non-empty string name")
        if name in names:
            raise ValueError(f"{path}: duplicate queue name {name!r}")
        names.add(name)
        parsed.append(queue)
    return parsed


def is_dlq(queue: dict[str, Any]) -> bool:
    if queue.get("is_dead_letter_queue") is True:
        return True
    name = str(queue.get("name", "")).lower()
    return name.endswith("-dlq") or name.endswith("_dlq") or name.endswith(".dlq")


def queue_alarm_names(queue: dict[str, Any]) -> set[str]:
    alarms = queue.get("alarms")
    if not isinstance(alarms, list):
        return set()
    return {str(alarm.get("metric_name", "")).strip() for alarm in alarms if isinstance(alarm, dict)}


def has_dlq_alarm(queue: dict[str, Any]) -> bool:
    return "ApproximateNumberOfMessagesVisible" in queue_alarm_names(queue)


def review_source_queue(queue: dict[str, Any], queue_names: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    name = str(queue["name"])
    env = normalize_env(queue.get("environment"))
    critical = bool(queue.get("critical"))
    redrive = queue.get("redrive_policy")

    if env in PRODUCTION_ENVS and not has_text(queue.get("owner")):
        findings.append(Finding("HIGH", name, "production queue is missing an owner"))

    if not isinstance(redrive, dict) or not has_text(redrive.get("dead_letter_queue")):
        if env in PRODUCTION_ENVS or critical:
            findings.append(Finding("HIGH", name, "missing dead-letter queue redrive policy"))
        return findings

    dlq_name = str(redrive["dead_letter_queue"])
    max_receive_count = parse_int(redrive.get("max_receive_count"))
    if dlq_name not in queue_names:
        findings.append(Finding("HIGH", name, f"redrive policy points to unknown DLQ {dlq_name!r}"))
    if max_receive_count < 3:
        findings.append(Finding("MEDIUM", name, "max_receive_count should be at least 3 before sending to DLQ"))

    return findings


def review_dlq(queue: dict[str, Any], max_threshold: int) -> list[Finding]:
    findings: list[Finding] = []
    name = str(queue["name"])
    env = normalize_env(queue.get("environment"))
    visible_messages = parse_int(queue.get("approximate_messages_visible"))
    oldest_message_age = parse_int(queue.get("oldest_message_age_seconds"))
    alarms = queue.get("alarms") if isinstance(queue.get("alarms"), list) else []

    if env in PRODUCTION_ENVS and not has_text(queue.get("owner")):
        findings.append(Finding("HIGH", name, "production DLQ is missing an owner"))

    if not has_dlq_alarm(queue):
        findings.append(Finding("HIGH", name, "missing DLQ visible-messages alarm"))
    else:
        for alarm in alarms:
            if not isinstance(alarm, dict):
                continue
            if alarm.get("metric_name") != "ApproximateNumberOfMessagesVisible":
                continue
            threshold = parse_int(alarm.get("threshold"))
            period_minutes = parse_int(alarm.get("period_minutes"))
            if threshold > max_threshold:
                findings.append(Finding("MEDIUM", name, f"DLQ alarm threshold {threshold} is above {max_threshold}"))
            if period_minutes > 5:
                findings.append(Finding("MEDIUM", name, "DLQ alarm period should be 5 minutes or less"))
            if not has_text(alarm.get("runbook")):
                findings.append(Finding("MEDIUM", name, "DLQ alarm is missing a runbook link"))

    if visible_messages > 0:
        findings.append(Finding("HIGH", name, f"DLQ currently has {visible_messages} visible message(s)"))
    if oldest_message_age > 3600:
        findings.append(Finding("MEDIUM", name, "oldest DLQ message is older than 1 hour"))

    return findings


def review_queues(queues: list[dict[str, Any]], max_threshold: int = DEFAULT_MAX_DLQ_ALARM_THRESHOLD) -> list[Finding]:
    queue_names = {str(queue["name"]) for queue in queues}
    findings: list[Finding] = []
    for queue in sorted(queues, key=lambda item: str(item["name"])):
        if is_dlq(queue):
            findings.extend(review_dlq(queue, max_threshold))
        else:
            findings.extend(review_source_queue(queue, queue_names))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review SQS queue inventory JSON for DLQ and alarm readiness."
    )
    parser.add_argument("inventory", type=Path, help="SQS inventory JSON")
    parser.add_argument(
        "--max-dlq-alarm-threshold",
        type=int,
        default=DEFAULT_MAX_DLQ_ALARM_THRESHOLD,
        help="Highest acceptable DLQ visible-message alarm threshold",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        queues = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_queues(queues, max_threshold=args.max_dlq_alarm_threshold)
    if not findings:
        print("PASS: SQS DLQ alarm coverage looks ready")
        return 0

    print(f"FLAGGED: {len(findings)} SQS DLQ alarm issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
