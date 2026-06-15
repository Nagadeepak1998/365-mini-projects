#!/usr/bin/env python3
"""Review deployment plans for release-window risk."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}
SAFE_STRATEGIES = {"canary", "rolling", "blue_green", "blue-green"}
RISKY_STRATEGIES = {"all_at_once", "big_bang", "manual_full_cutover"}


def parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include a timezone: {value}")
    return parsed


def overlaps(start: datetime, end: datetime, window: dict[str, Any]) -> bool:
    window_start = parse_timestamp(str(window["start"]))
    window_end = parse_timestamp(str(window["end"]))
    return start < window_end and end > window_start


def issue(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def review_plan(plan: dict[str, Any]) -> list[dict[str, str]]:
    deployment = plan.get("deployment", {})
    service = str(plan.get("service", "unknown-service"))
    service_tier = str(plan.get("service_tier", "unknown")).lower()
    environment = str(deployment.get("environment", "unknown")).lower()
    strategy = str(deployment.get("strategy", "")).lower()
    change_type = str(deployment.get("change_type", "")).lower()
    duration = int(deployment.get("duration_minutes", 0))
    start = parse_timestamp(str(deployment["start_time"]))
    end = start + timedelta(minutes=duration)
    is_production = environment in {"prod", "production"}
    is_critical = service_tier in {"tier-0", "tier-1", "critical"}
    results: list[dict[str, str]] = []

    for window in plan.get("freeze_windows", []):
        if overlaps(start, end, window):
            results.append(
                issue(
                    "high",
                    "freeze-window-overlap",
                    f"{service} deployment overlaps freeze window: {window.get('name', 'unnamed')}",
                )
            )

    if is_production and is_critical and strategy in RISKY_STRATEGIES:
        results.append(
            issue(
                "high",
                "risky-cutover-strategy",
                "critical production service is using an all-at-once style deployment",
            )
        )

    if is_production and is_critical and strategy not in SAFE_STRATEGIES:
        results.append(
            issue(
                "medium",
                "missing-progressive-delivery",
                "critical production deployment does not use canary, rolling, or blue-green delivery",
            )
        )

    rollback_plan = str(deployment.get("rollback_plan", "")).strip()
    has_database_change = "database" in change_type or bool(deployment.get("database_migration"))
    if has_database_change and len(rollback_plan) < 20:
        results.append(
            issue(
                "high",
                "weak-rollback-plan",
                "database-impacting change needs a clear rollback or recovery plan",
            )
        )

    if has_database_change and not deployment.get("backup_verified"):
        results.append(
            issue(
                "medium",
                "backup-not-verified",
                "database-impacting change does not show a verified backup or restore path",
            )
        )

    error_budget = deployment.get("error_budget_remaining_pct")
    if error_budget is not None:
        budget_value = float(error_budget)
        if budget_value < 20:
            results.append(
                issue(
                    "high",
                    "low-error-budget",
                    f"error budget remaining is only {budget_value:g}%",
                )
            )
        elif budget_value < 40:
            results.append(
                issue(
                    "medium",
                    "thin-error-budget",
                    f"error budget remaining is {budget_value:g}%",
                )
            )

    recent_incidents = int(deployment.get("recent_incidents_14d", 0))
    if recent_incidents >= 2:
        results.append(
            issue(
                "medium",
                "recent-incident-pressure",
                f"service had {recent_incidents} incident(s) in the last 14 days",
            )
        )

    if is_production and not deployment.get("monitoring_links"):
        results.append(
            issue(
                "medium",
                "missing-monitoring-links",
                "production deployment should link dashboards or alert views for the rollout",
            )
        )

    approvers = deployment.get("approvers", [])
    if is_production and is_critical and len(approvers) < 2:
        results.append(
            issue(
                "medium",
                "insufficient-approvals",
                "critical production deployment should have at least two named approvers",
            )
        )

    if deployment.get("touches_shared_dependencies") and strategy not in SAFE_STRATEGIES:
        results.append(
            issue(
                "medium",
                "shared-dependency-risk",
                "shared dependency change should use a progressive rollout strategy",
            )
        )

    checkpoint_minutes = deployment.get("checkpoint_minutes")
    if is_production and duration > 120 and not checkpoint_minutes:
        results.append(
            issue(
                "medium",
                "long-window-without-checkpoints",
                "long production deployment should define checkpoint intervals",
            )
        )

    return sorted(
        results,
        key=lambda item: (-SEVERITY_ORDER[item["severity"]], item["code"]),
    )


def summarize(issues: list[dict[str, str]]) -> dict[str, int]:
    summary = {"high": 0, "medium": 0, "low": 0}
    for found in issues:
        summary[found["severity"]] += 1
    return summary


def render_text(plan: dict[str, Any], issues: list[dict[str, str]]) -> str:
    service = plan.get("service", "unknown-service")
    if not issues:
        return f"PASS: {service} deployment plan stays within configured risk thresholds"

    summary = summarize(issues)
    lines = [
        f"FLAGGED: {len(issues)} deployment risk issue(s)",
        f"Risk summary: high={summary['high']} medium={summary['medium']} low={summary['low']}",
    ]
    for found in issues:
        lines.append(
            f"[{found['severity'].upper()}] {found['code']} - {found['message']}"
        )
    return "\n".join(lines)


def load_plan(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def exit_code(issues: list[dict[str, str]], fail_on: str) -> int:
    if fail_on == "off":
        return 0
    threshold = SEVERITY_ORDER[fail_on]
    return 2 if any(SEVERITY_ORDER[item["severity"]] >= threshold for item in issues) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check a deployment plan for release-window risk."
    )
    parser.add_argument("plan", type=Path, help="Path to a deployment plan JSON file")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--fail-on",
        choices=("off", "medium", "high"),
        default="high",
        help="Exit with code 2 when a matching severity is present",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = load_plan(args.plan)
    issues = review_plan(plan)

    if args.format == "json":
        print(json.dumps({"issues": issues, "summary": summarize(issues)}, indent=2))
    else:
        print(render_text(plan, issues))

    return exit_code(issues, args.fail_on)


if __name__ == "__main__":
    sys.exit(main())
