#!/usr/bin/env python3
"""Review saved Lambda function inventories for production readiness."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


SUPPORTED_RUNTIMES = {
    "nodejs20.x",
    "nodejs22.x",
    "python3.11",
    "python3.12",
    "python3.13",
    "java17",
    "java21",
    "dotnet8",
    "ruby3.3",
    "provided.al2023",
}

SECRET_WORDS = ("secret", "token", "password", "apikey", "api_key", "private_key")


@dataclass(frozen=True)
class Finding:
    function_name: str
    severity: str
    code: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.function_name}: {self.code} - {self.message}"


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def age_days(value: str | None, today: date) -> int | None:
    parsed = parse_date(value)
    if parsed is None:
        return None
    return (today - parsed).days


def has_truthy(value: Any) -> bool:
    return bool(value)


def environment_name(function: dict[str, Any]) -> str:
    return str(function.get("environment", "")).lower()


def is_production(function: dict[str, Any]) -> bool:
    env = environment_name(function)
    return env in {"prod", "production"} or bool(function.get("critical"))


def check_function(function: dict[str, Any], today: date) -> list[Finding]:
    findings: list[Finding] = []
    name = str(function.get("name") or "<unnamed-function>")
    production = is_production(function)

    def add(severity: str, code: str, message: str) -> None:
        findings.append(Finding(name, severity, code, message))

    if production and not function.get("owner"):
        add("HIGH", "missing-owner", "production functions need an accountable owner")

    runtime = str(function.get("runtime") or "")
    if runtime and runtime not in SUPPORTED_RUNTIMES:
        add("HIGH", "unsupported-runtime", f"runtime {runtime} is outside the supported runtime list")
    if not runtime:
        add("HIGH", "missing-runtime", "runtime is missing from the inventory")

    if production and str(function.get("alias") or "") in {"", "$LATEST"}:
        add("HIGH", "unpinned-alias", "production traffic should use a named alias or version")

    if production and not has_truthy(function.get("structured_logging")):
        add("MEDIUM", "missing-structured-logs", "structured logs make production incidents easier to triage")

    alarms = function.get("alarms") or []
    if production and len(alarms) < 2:
        add("HIGH", "weak-alarm-coverage", "production functions should at least alarm on errors and throttles")

    async_invoked = bool(function.get("async_invoked"))
    has_failure_path = has_truthy(function.get("dead_letter_queue")) or has_truthy(
        function.get("on_failure_destination")
    )
    if async_invoked and not has_failure_path:
        add("HIGH", "missing-async-failure-path", "async functions need a DLQ or on-failure destination")

    reserved_concurrency = function.get("reserved_concurrency")
    if production and reserved_concurrency in (None, 0):
        add("MEDIUM", "missing-reserved-concurrency", "reserve concurrency to contain blast radius")

    if production and not has_truthy(function.get("xray_tracing")):
        add("LOW", "missing-tracing", "X-Ray tracing is useful for latency and downstream dependency debugging")

    timeout_seconds = int(function.get("timeout_seconds") or 0)
    if timeout_seconds <= 0:
        add("HIGH", "missing-timeout", "timeout_seconds must be recorded")
    elif timeout_seconds > 60 and function.get("trigger") in {"api_gateway", "alb"}:
        add("MEDIUM", "long-sync-timeout", "synchronous request paths should fail fast enough for callers")

    memory_mb = int(function.get("memory_mb") or 0)
    if memory_mb < 128:
        add("MEDIUM", "invalid-memory", "memory_mb should be at least 128")

    env_vars = function.get("environment_variables") or {}
    for key, value in sorted(env_vars.items()):
        combined = f"{key}={value}".lower()
        if any(word in combined for word in SECRET_WORDS):
            add("HIGH", "possible-inline-secret", f"environment variable {key} looks like a secret")

    last_deployed_age = age_days(function.get("last_deployed_at"), today)
    if production and last_deployed_age is None:
        add("MEDIUM", "missing-deploy-date", "last_deployed_at is needed for stale-service review")
    elif production and last_deployed_age is not None and last_deployed_age > 180:
        add("MEDIUM", "stale-production-deploy", f"last deploy was {last_deployed_age} days ago")

    last_drill_age = age_days(function.get("rollback_drill_at"), today)
    if production and last_drill_age is None:
        add("MEDIUM", "missing-rollback-drill", "rollback_drill_at is missing")
    elif production and last_drill_age is not None and last_drill_age > 120:
        add("MEDIUM", "stale-rollback-drill", f"rollback drill was {last_drill_age} days ago")

    return findings


def load_inventory(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    functions = payload.get("functions")
    if not isinstance(functions, list):
        raise ValueError("inventory must contain a top-level functions list")
    return functions


def review_inventory(path: Path, today: date) -> list[Finding]:
    findings: list[Finding] = []
    for function in load_inventory(path):
        if not isinstance(function, dict):
            raise ValueError("each function entry must be an object")
        findings.extend(check_function(function, today))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review a saved AWS Lambda inventory for production readiness gaps."
    )
    parser.add_argument("inventory", type=Path, help="Path to a JSON inventory file")
    parser.add_argument("--today", default=date.today().isoformat(), help="Review date in YYYY-MM-DD format")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    today = parse_date(args.today)
    if today is None:
        print("ERROR: --today must be in YYYY-MM-DD format", file=sys.stderr)
        return 2

    try:
        findings = review_inventory(args.inventory, today)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not findings:
        print("PASS: Lambda production inventory looks ready")
        return 0

    print(f"FLAGGED: {len(findings)} Lambda production readiness issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
