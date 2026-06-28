#!/usr/bin/env python3
"""Review ECS service inventory snapshots for deployment safety gaps."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCTION_ENVS = {"prod", "production"}
REQUIRED_PROD_ALARMS = {"CPUUtilization", "MemoryUtilization"}
DEFAULT_MIN_LOG_RETENTION_DAYS = 14


@dataclass(frozen=True)
class Finding:
    severity: str
    service: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.service}: {self.message}"


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

    services = raw.get("services") if isinstance(raw, dict) else None
    if not isinstance(services, list):
        raise ValueError(f"{path}: expected top-level object with a services list")

    names: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, service in enumerate(services, start=1):
        if not isinstance(service, dict):
            raise ValueError(f"{path}: services[{index}] must be an object")
        name = service.get("name")
        if not has_text(name):
            raise ValueError(f"{path}: services[{index}] must include a non-empty string name")
        if name in names:
            raise ValueError(f"{path}: duplicate service name {name!r}")
        names.add(name)
        parsed.append(service)
    return parsed


def alarm_metric_names(service: dict[str, Any]) -> set[str]:
    alarms = service.get("alarms")
    if not isinstance(alarms, list):
        return set()
    return {str(alarm.get("metric_name", "")).strip() for alarm in alarms if isinstance(alarm, dict)}


def alarms_missing_runbooks(service: dict[str, Any]) -> bool:
    alarms = service.get("alarms")
    if not isinstance(alarms, list):
        return False
    return any(isinstance(alarm, dict) and not has_text(alarm.get("runbook")) for alarm in alarms)


def image_is_mutable(image: Any) -> bool:
    if not has_text(image):
        return True
    image_text = str(image).strip()
    if "@sha256:" in image_text:
        return False
    if ":" not in image_text:
        return True
    return image_text.rsplit(":", 1)[1] in {"latest", "main", "stable"}


def review_service(service: dict[str, Any], min_log_retention_days: int) -> list[Finding]:
    findings: list[Finding] = []
    name = str(service["name"])
    env = normalize_env(service.get("environment"))
    production = env in PRODUCTION_ENVS
    critical = bool(service.get("critical"))
    desired_count = parse_int(service.get("desired_count"))
    public_endpoint = bool(service.get("public_endpoint"))

    deployment = service.get("deployment") if isinstance(service.get("deployment"), dict) else {}
    load_balancer = service.get("load_balancer") if isinstance(service.get("load_balancer"), dict) else {}
    task_definition = service.get("task_definition") if isinstance(service.get("task_definition"), dict) else {}

    if production and not has_text(service.get("owner")):
        findings.append(Finding("HIGH", name, "production service is missing an owner"))

    if (production or critical) and desired_count < 2:
        findings.append(Finding("HIGH", name, "production or critical service should run at least 2 tasks"))

    if production and not deployment.get("circuit_breaker_enabled"):
        findings.append(Finding("HIGH", name, "ECS deployment circuit breaker is not enabled"))
    if production and not deployment.get("rollback_enabled"):
        findings.append(Finding("HIGH", name, "ECS deployment rollback is not enabled"))

    minimum_healthy_percent = parse_int(deployment.get("minimum_healthy_percent"), default=100)
    maximum_percent = parse_int(deployment.get("maximum_percent"), default=200)
    if production and desired_count >= 2 and minimum_healthy_percent < 100:
        findings.append(Finding("MEDIUM", name, "minimum_healthy_percent below 100 can reduce capacity during deploys"))
    if production and maximum_percent <= 100:
        findings.append(Finding("HIGH", name, "maximum_percent leaves no room for replacement tasks"))
    elif production and maximum_percent > 200:
        findings.append(Finding("MEDIUM", name, "maximum_percent above 200 can create a large surge during deploys"))

    if public_endpoint and not load_balancer.get("enabled"):
        findings.append(Finding("HIGH", name, "public service is missing a load balancer health gate"))
    if load_balancer.get("enabled") and not has_text(load_balancer.get("health_check_path")):
        findings.append(Finding("MEDIUM", name, "load balancer is missing a health check path"))

    health_grace = parse_int(service.get("health_check_grace_period_seconds"))
    if production and health_grace < 30:
        findings.append(Finding("MEDIUM", name, "health_check_grace_period_seconds should be at least 30"))

    metrics = alarm_metric_names(service)
    missing_metrics = sorted(REQUIRED_PROD_ALARMS - metrics)
    if production and missing_metrics:
        findings.append(Finding("MEDIUM", name, f"missing alarm metric(s): {', '.join(missing_metrics)}"))
    if production and alarms_missing_runbooks(service):
        findings.append(Finding("MEDIUM", name, "one or more alarms are missing runbook links"))

    if image_is_mutable(task_definition.get("image")) and not has_text(task_definition.get("image_digest")):
        findings.append(Finding("MEDIUM", name, "task image is mutable or missing a digest pin"))

    log_retention_days = parse_int(task_definition.get("log_retention_days"))
    if production and log_retention_days < min_log_retention_days:
        findings.append(
            Finding("MEDIUM", name, f"log retention is below {min_log_retention_days} days")
        )

    return findings


def review_services(
    services: list[dict[str, Any]], min_log_retention_days: int = DEFAULT_MIN_LOG_RETENTION_DAYS
) -> list[Finding]:
    findings: list[Finding] = []
    for service in sorted(services, key=lambda item: str(item["name"])):
        findings.extend(review_service(service, min_log_retention_days))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review ECS service inventory JSON for deployment safety gaps."
    )
    parser.add_argument("inventory", type=Path, help="ECS service inventory JSON")
    parser.add_argument(
        "--min-log-retention-days",
        type=int,
        default=DEFAULT_MIN_LOG_RETENTION_DAYS,
        help="Minimum acceptable CloudWatch Logs retention for production services",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        services = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_services(services, min_log_retention_days=args.min_log_retention_days)
    if not findings:
        print("PASS: ECS service deployment safety looks ready")
        return 0

    print(f"FLAGGED: {len(findings)} ECS service safety issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
