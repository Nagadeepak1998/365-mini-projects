#!/usr/bin/env python3
"""Review API Gateway route inventory snapshots for production readiness gaps."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCTION_ENVS = {"prod", "production"}
SAFE_AUTH_TYPES = {"aws_iam", "jwt", "lambda", "cognito"}
REQUIRED_ALARMS = {"5XXError", "Latency"}
DEFAULT_MAX_TIMEOUT_SECONDS = 25


@dataclass(frozen=True)
class Finding:
    severity: str
    route: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.route}: {self.message}"


def has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalize_text(value: Any) -> str:
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

    routes = raw.get("routes") if isinstance(raw, dict) else None
    if not isinstance(routes, list):
        raise ValueError(f"{path}: expected top-level object with a routes list")

    seen: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, route in enumerate(routes, start=1):
        if not isinstance(route, dict):
            raise ValueError(f"{path}: routes[{index}] must be an object")
        route_key = route.get("route_key")
        if not has_text(route_key):
            raise ValueError(f"{path}: routes[{index}] must include a non-empty string route_key")
        if route_key in seen:
            raise ValueError(f"{path}: duplicate route_key {route_key!r}")
        seen.add(route_key)
        parsed.append(route)
    return parsed


def alarm_metric_names(route: dict[str, Any]) -> set[str]:
    alarms = route.get("alarms")
    if not isinstance(alarms, list):
        return set()
    return {str(alarm.get("metric_name", "")).strip() for alarm in alarms if isinstance(alarm, dict)}


def alarms_missing_runbooks(route: dict[str, Any]) -> bool:
    alarms = route.get("alarms")
    if not isinstance(alarms, list):
        return False
    return any(isinstance(alarm, dict) and not has_text(alarm.get("runbook")) for alarm in alarms)


def review_route(route: dict[str, Any], max_timeout_seconds: int) -> list[Finding]:
    findings: list[Finding] = []
    route_key = str(route["route_key"])
    env = normalize_text(route.get("environment"))
    production = env in PRODUCTION_ENVS
    public = bool(route.get("public"))
    critical = bool(route.get("critical"))

    integration = route.get("integration") if isinstance(route.get("integration"), dict) else {}
    throttling = route.get("throttling") if isinstance(route.get("throttling"), dict) else {}
    access_logs = route.get("access_logs") if isinstance(route.get("access_logs"), dict) else {}
    canary = route.get("canary") if isinstance(route.get("canary"), dict) else {}

    if production and not has_text(route.get("owner")):
        findings.append(Finding("HIGH", route_key, "production route is missing an owner"))

    auth_type = normalize_text(route.get("auth_type"))
    if production and public and auth_type not in SAFE_AUTH_TYPES:
        findings.append(Finding("HIGH", route_key, "public production route is missing strong auth"))

    if production and not throttling.get("enabled"):
        findings.append(Finding("HIGH", route_key, "production route is missing throttling"))
    if production and throttling.get("enabled"):
        rate_limit = parse_int(throttling.get("rate_limit_per_second"))
        burst_limit = parse_int(throttling.get("burst_limit"))
        if rate_limit <= 0 or burst_limit <= 0:
            findings.append(Finding("MEDIUM", route_key, "throttling is enabled without positive limits"))

    if production and not access_logs.get("enabled"):
        findings.append(Finding("MEDIUM", route_key, "access logs are not enabled"))
    if access_logs.get("enabled") and not has_text(access_logs.get("retention_days")):
        findings.append(Finding("MEDIUM", route_key, "access log retention is not documented"))

    timeout_seconds = parse_int(integration.get("timeout_seconds"))
    if production and timeout_seconds <= 0:
        findings.append(Finding("HIGH", route_key, "integration timeout is missing"))
    elif production and timeout_seconds > max_timeout_seconds:
        findings.append(
            Finding("MEDIUM", route_key, f"integration timeout is above {max_timeout_seconds} seconds")
        )

    if production and not has_text(integration.get("lambda_alias")):
        findings.append(Finding("MEDIUM", route_key, "Lambda integration is not pinned to an alias"))
    if production and not integration.get("request_validation"):
        findings.append(Finding("MEDIUM", route_key, "request validation is not enabled"))

    metrics = alarm_metric_names(route)
    missing_metrics = sorted(REQUIRED_ALARMS - metrics)
    if production and missing_metrics:
        findings.append(Finding("MEDIUM", route_key, f"missing alarm metric(s): {', '.join(missing_metrics)}"))
    if production and alarms_missing_runbooks(route):
        findings.append(Finding("MEDIUM", route_key, "one or more alarms are missing runbook links"))

    if (production or critical) and not has_text(route.get("rollback_note")):
        findings.append(Finding("MEDIUM", route_key, "rollback note is missing"))
    if production and critical and not canary.get("enabled"):
        findings.append(Finding("MEDIUM", route_key, "critical production route is missing a canary plan"))

    return findings


def review_routes(
    routes: list[dict[str, Any]], max_timeout_seconds: int = DEFAULT_MAX_TIMEOUT_SECONDS
) -> list[Finding]:
    findings: list[Finding] = []
    for route in sorted(routes, key=lambda item: str(item["route_key"])):
        findings.extend(review_route(route, max_timeout_seconds=max_timeout_seconds))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review API Gateway route inventory JSON for readiness gaps."
    )
    parser.add_argument("inventory", type=Path, help="API Gateway route inventory JSON")
    parser.add_argument(
        "--max-timeout-seconds",
        type=int,
        default=DEFAULT_MAX_TIMEOUT_SECONDS,
        help="Maximum acceptable Lambda integration timeout for production routes",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        routes = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_routes(routes, max_timeout_seconds=args.max_timeout_seconds)
    if not findings:
        print("PASS: API Gateway route readiness looks ready")
        return 0

    print(f"FLAGGED: {len(findings)} API Gateway route readiness issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
