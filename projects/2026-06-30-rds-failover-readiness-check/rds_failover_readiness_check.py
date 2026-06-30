#!/usr/bin/env python3
"""Review RDS inventory snapshots for failover readiness gaps."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


PRODUCTION_ENVS = {"prod", "production"}
REQUIRED_ALARMS = {"CPUUtilization", "FreeStorageSpace", "DatabaseConnections"}
STALE_DRILL_DAYS = 180
MIN_BACKUP_RETENTION_DAYS = 7


@dataclass(frozen=True)
class Finding:
    severity: str
    database: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.database}: {self.message}"


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


def parse_date(value: Any) -> date | None:
    if not has_text(value):
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def load_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    databases = raw.get("databases") if isinstance(raw, dict) else None
    if not isinstance(databases, list):
        raise ValueError(f"{path}: expected top-level object with a databases list")

    seen: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, database in enumerate(databases, start=1):
        if not isinstance(database, dict):
            raise ValueError(f"{path}: databases[{index}] must be an object")
        identifier = database.get("identifier")
        if not has_text(identifier):
            raise ValueError(f"{path}: databases[{index}] must include a non-empty string identifier")
        if identifier in seen:
            raise ValueError(f"{path}: duplicate identifier {identifier!r}")
        seen.add(identifier)
        parsed.append(database)
    return parsed


def alarm_metric_names(database: dict[str, Any]) -> set[str]:
    alarms = database.get("alarms")
    if not isinstance(alarms, list):
        return set()
    return {str(alarm.get("metric_name", "")).strip() for alarm in alarms if isinstance(alarm, dict)}


def alarms_missing_runbooks(database: dict[str, Any]) -> bool:
    alarms = database.get("alarms")
    if not isinstance(alarms, list):
        return False
    return any(isinstance(alarm, dict) and not has_text(alarm.get("runbook")) for alarm in alarms)


def review_database(database: dict[str, Any], today: date) -> list[Finding]:
    findings: list[Finding] = []
    identifier = str(database["identifier"])
    production = normalize_text(database.get("environment")) in PRODUCTION_ENVS
    critical = bool(database.get("critical"))
    backups = database.get("backups") if isinstance(database.get("backups"), dict) else {}
    failover_drill = database.get("failover_drill") if isinstance(database.get("failover_drill"), dict) else {}
    storage = database.get("storage") if isinstance(database.get("storage"), dict) else {}

    if production and not has_text(database.get("owner")):
        findings.append(Finding("HIGH", identifier, "production database is missing an owner"))

    if production and critical and not database.get("multi_az"):
        findings.append(Finding("HIGH", identifier, "critical production database is not Multi-AZ"))

    if production and not database.get("deletion_protection"):
        findings.append(Finding("MEDIUM", identifier, "deletion protection is not enabled"))

    if production and not backups.get("enabled"):
        findings.append(Finding("HIGH", identifier, "automated backups are not enabled"))
    if production and backups.get("enabled"):
        retention_days = parse_int(backups.get("retention_days"))
        if retention_days < MIN_BACKUP_RETENTION_DAYS:
            findings.append(
                Finding("MEDIUM", identifier, f"backup retention is below {MIN_BACKUP_RETENTION_DAYS} days")
            )
        if not has_text(backups.get("window")):
            findings.append(Finding("LOW", identifier, "backup window is not documented"))

    if production and storage.get("autoscaling") is False:
        findings.append(Finding("MEDIUM", identifier, "storage autoscaling is disabled"))

    metrics = alarm_metric_names(database)
    missing_metrics = sorted(REQUIRED_ALARMS - metrics)
    if production and missing_metrics:
        findings.append(Finding("MEDIUM", identifier, f"missing alarm metric(s): {', '.join(missing_metrics)}"))
    if production and database.get("read_replica") and "ReplicaLag" not in metrics:
        findings.append(Finding("MEDIUM", identifier, "read replica is missing a ReplicaLag alarm"))
    if production and alarms_missing_runbooks(database):
        findings.append(Finding("MEDIUM", identifier, "one or more alarms are missing runbook links"))

    last_tested = parse_date(failover_drill.get("last_tested_at"))
    if production and critical and last_tested is None:
        findings.append(Finding("HIGH", identifier, "critical database has no recorded failover drill"))
    elif production and critical and (today - last_tested).days > STALE_DRILL_DAYS:
        findings.append(Finding("MEDIUM", identifier, "failover drill is older than 180 days"))

    if production and critical and not has_text(failover_drill.get("runbook")):
        findings.append(Finding("MEDIUM", identifier, "failover drill runbook is missing"))

    rto_minutes = parse_int(database.get("rto_minutes"), default=-1)
    rpo_minutes = parse_int(database.get("rpo_minutes"), default=-1)
    if production and critical and rto_minutes < 0:
        findings.append(Finding("MEDIUM", identifier, "RTO target is not documented"))
    if production and critical and rpo_minutes < 0:
        findings.append(Finding("MEDIUM", identifier, "RPO target is not documented"))

    if production and database.get("pending_reboot"):
        findings.append(Finding("LOW", identifier, "database has pending-reboot changes"))

    return findings


def review_databases(databases: list[dict[str, Any]], today: date | None = None) -> list[Finding]:
    review_date = today or date.today()
    findings: list[Finding] = []
    for database in sorted(databases, key=lambda item: str(item["identifier"])):
        findings.extend(review_database(database, today=review_date))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review RDS inventory JSON for failover readiness gaps.")
    parser.add_argument("inventory", type=Path, help="RDS inventory JSON")
    parser.add_argument(
        "--today",
        type=str,
        default=None,
        help="Override today's date for deterministic review, formatted YYYY-MM-DD",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    today = date.today()
    if args.today:
        parsed_today = parse_date(args.today)
        if parsed_today is None:
            print("ERROR: --today must use YYYY-MM-DD", file=sys.stderr)
            return 2
        today = parsed_today

    try:
        databases = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_databases(databases, today=today)
    if not findings:
        print("PASS: RDS failover readiness looks ready")
        return 0

    print(f"FLAGGED: {len(findings)} RDS failover readiness issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
