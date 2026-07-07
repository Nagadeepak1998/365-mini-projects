#!/usr/bin/env python3
"""Review DNS change plans for risky production cutover gaps."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCTION_ENVS = {"prod", "production"}
PUBLIC_ZONES = {"public", "internet"}
DESTRUCTIVE_ACTIONS = {"delete", "remove"}
REQUIRED_CHECKS = {"dns_resolution", "http_health", "rollback_verified"}
MAX_CUTOVER_TTL_SECONDS = 300


@dataclass(frozen=True)
class Finding:
    severity: str
    record: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.record}: {self.message}"


def has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def load_change_plan(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    changes = raw.get("changes") if isinstance(raw, dict) else None
    if not isinstance(changes, list):
        raise ValueError(f"{path}: expected top-level object with a changes list")

    parsed: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, change in enumerate(changes, start=1):
        if not isinstance(change, dict):
            raise ValueError(f"{path}: changes[{index}] must be an object")

        name = change.get("name")
        record_type = change.get("type")
        action = change.get("action")
        if not has_text(name):
            raise ValueError(f"{path}: changes[{index}] must include a non-empty string name")
        if not has_text(record_type):
            raise ValueError(f"{path}: changes[{index}] must include a non-empty string type")
        if not has_text(action):
            raise ValueError(f"{path}: changes[{index}] must include a non-empty string action")

        key = (str(name).strip(), str(record_type).strip().upper(), normalize_text(action))
        if key in seen:
            raise ValueError(f"{path}: duplicate change for {key[0]} {key[1]} {key[2]}")
        seen.add(key)
        parsed.append(change)
    return parsed


def enabled_check_names(change: dict[str, Any]) -> set[str]:
    checks = change.get("validation_checks")
    if not isinstance(checks, list):
        return set()
    return {normalize_text(check.get("name")) for check in checks if isinstance(check, dict) and check.get("enabled") is True}


def integer_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def record_label(change: dict[str, Any]) -> str:
    return f"{change['name']} {str(change['type']).upper()}"


def review_change(change: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    label = record_label(change)
    production = normalize_text(change.get("environment")) in PRODUCTION_ENVS
    public_zone = normalize_text(change.get("zone_scope")) in PUBLIC_ZONES

    if not production or not public_zone:
        return findings

    action = normalize_text(change.get("action"))
    record_type = normalize_text(change.get("type")).upper()
    name = str(change["name"]).strip()

    if not has_text(change.get("owner")):
        findings.append(Finding("HIGH", label, "production public DNS change is missing an owner"))

    if not has_text(change.get("ticket")):
        findings.append(Finding("MEDIUM", label, "change has no ticket or approval reference"))

    if action in DESTRUCTIVE_ACTIONS:
        findings.append(Finding("HIGH", label, "production public DNS delete needs an explicit migration plan"))

    ttl = integer_value(change.get("ttl_seconds"))
    existing_ttl = integer_value(change.get("existing_ttl_seconds"))
    if action in {"create", "update", "upsert"} and ttl > MAX_CUTOVER_TTL_SECONDS:
        findings.append(Finding("MEDIUM", label, f"cutover TTL is above {MAX_CUTOVER_TTL_SECONDS} seconds"))
    if action in {"update", "upsert"} and existing_ttl > 1800:
        findings.append(Finding("LOW", label, "existing TTL is high enough to slow rollback"))

    if record_type == "CNAME" and name.count(".") <= 1:
        findings.append(Finding("HIGH", label, "CNAME appears to target the zone apex"))

    if name.startswith("*."):
        findings.append(Finding("MEDIUM", label, "wildcard production record should be reviewed manually"))

    if record_type == "MX" and integer_value(change.get("priority")) <= 0:
        findings.append(Finding("HIGH", label, "MX record is missing a positive priority"))

    if not has_text(change.get("rollback")):
        findings.append(Finding("HIGH", label, "rollback plan is missing"))

    missing_checks = sorted(REQUIRED_CHECKS - enabled_check_names(change))
    if missing_checks:
        findings.append(Finding("MEDIUM", label, f"missing validation check(s): {', '.join(missing_checks)}"))

    return findings


def review_changes(changes: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for change in sorted(changes, key=lambda item: (str(item["name"]), str(item["type"]))):
        findings.extend(review_change(change))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review DNS change plans for production cutover safety gaps.")
    parser.add_argument("change_plan", type=Path, help="DNS change plan JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        changes = load_change_plan(args.change_plan)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_changes(changes)
    if not findings:
        print("PASS: DNS change plan looks ready")
        return 0

    print(f"FLAGGED: {len(findings)} DNS change safety issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
