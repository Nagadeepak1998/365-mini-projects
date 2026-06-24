#!/usr/bin/env python3
"""Review backup inventories for restore drill readiness."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    severity: str
    service: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.service}: {self.message}"


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def positive_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
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
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{path}: services[{index}] must include a non-empty string name")
        if name in names:
            raise ValueError(f"{path}: duplicate service name {name!r}")
        names.add(name)
        parsed.append(service)
    return parsed


def review_service(service: dict[str, Any], today: date) -> list[Finding]:
    name = str(service["name"])
    findings: list[Finding] = []

    latest_backup_at = parse_date(service.get("latest_backup_at"))
    latest_restore_test_at = parse_date(service.get("latest_restore_test_at"))
    rpo_hours = positive_int(service.get("rpo_hours"))
    retention_days = positive_int(service.get("retention_days"))
    restore_test_interval_days = positive_int(service.get("restore_test_interval_days"), 90)
    owner = service.get("owner")
    backup_status = str(service.get("backup_status", "")).strip().lower()
    encrypted = service.get("encrypted")
    cross_region = service.get("cross_region")
    tier = str(service.get("tier", "")).strip().lower()

    if not isinstance(owner, str) or not owner.strip():
        findings.append(Finding("MEDIUM", name, "missing owner for backup follow-up"))

    if latest_backup_at is None:
        findings.append(Finding("HIGH", name, "missing valid latest_backup_at date"))
    else:
        backup_age_hours = (today - latest_backup_at).days * 24
        if rpo_hours and backup_age_hours > rpo_hours:
            findings.append(
                Finding(
                    "HIGH",
                    name,
                    f"latest backup is {backup_age_hours}h old, above {rpo_hours}h RPO",
                )
            )

    if backup_status not in {"success", "ok", "completed"}:
        findings.append(Finding("HIGH", name, f"latest backup status is {backup_status or 'missing'}"))

    if latest_restore_test_at is None:
        findings.append(Finding("HIGH", name, "missing valid latest_restore_test_at date"))
    else:
        restore_age_days = (today - latest_restore_test_at).days
        if restore_age_days > restore_test_interval_days:
            findings.append(
                Finding(
                    "HIGH",
                    name,
                    f"restore test is {restore_age_days} days old, above {restore_test_interval_days} day target",
                )
            )

    if retention_days and retention_days < 14:
        findings.append(Finding("MEDIUM", name, f"retention is only {retention_days} days"))

    if encrypted is not True:
        findings.append(Finding("HIGH", name, "backup encryption is not confirmed"))

    if tier in {"critical", "tier1", "tier-1"} and cross_region is not True:
        findings.append(Finding("MEDIUM", name, "critical service has no confirmed cross-region backup"))

    return findings


def review_inventory(services: list[dict[str, Any]], today: date) -> list[Finding]:
    findings: list[Finding] = []
    for service in sorted(services, key=lambda item: str(item["name"])):
        findings.extend(review_service(service, today))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review backup inventory JSON for restore drill readiness."
    )
    parser.add_argument("inventory", type=Path, help="Backup inventory JSON")
    parser.add_argument(
        "--today",
        default=date.today().isoformat(),
        help="Review date in YYYY-MM-DD format, mainly for deterministic tests",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    today = parse_date(args.today)
    if today is None:
        parser.error("--today must use YYYY-MM-DD")

    try:
        services = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_inventory(services, today)
    if not findings:
        print("PASS: backup restore drill inventory is ready")
        return 0

    print(f"FLAGGED: {len(findings)} backup restore risk(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
