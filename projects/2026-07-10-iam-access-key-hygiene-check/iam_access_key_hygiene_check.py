#!/usr/bin/env python3
"""Review a saved IAM access-key inventory for common hygiene risks."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    principal: str
    severity: str
    code: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.principal}: {self.code} - {self.message}"


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def age_days(value: str | None, today: date) -> int | None:
    parsed = parse_date(value)
    return None if parsed is None else (today - parsed).days


def check_principal(principal: dict[str, Any], today: date) -> list[Finding]:
    findings: list[Finding] = []
    name = str(principal.get("name") or "<unnamed-principal>")
    principal_type = str(principal.get("type") or "").lower()
    keys = principal.get("access_keys") or []

    def add(severity: str, code: str, message: str) -> None:
        findings.append(Finding(name, severity, code, message))

    if not principal.get("owner"):
        add("HIGH", "missing-owner", "an accountable owner is not recorded")
    if principal_type not in {"human", "service"}:
        add("MEDIUM", "unknown-principal-type", "type must be human or service")
    if principal_type == "human" and keys:
        add("HIGH", "human-static-key", "human users should use temporary credentials instead of access keys")
    if len(keys) > 1:
        add("MEDIUM", "multiple-active-keys", "more than one access key increases credential exposure")

    for index, key in enumerate(keys, start=1):
        if not isinstance(key, dict):
            raise ValueError(f"access key {index} for {name} must be an object")
        label = str(key.get("id_suffix") or f"key-{index}")
        status = str(key.get("status") or "").lower()
        if status not in {"active", "inactive"}:
            add("HIGH", "invalid-key-status", f"{label} status must be active or inactive")
            continue

        created_age = age_days(key.get("created_at"), today)
        if created_age is None:
            add("HIGH", "missing-created-date", f"{label} has no created_at date")
        elif status == "active" and created_age > 90:
            add("HIGH", "stale-active-key", f"{label} is {created_age} days old")

        used_age = age_days(key.get("last_used_at"), today)
        if status == "active" and used_age is None:
            add("MEDIUM", "never-used-active-key", f"{label} has no recorded use")
        elif status == "active" and used_age is not None and used_age > 45:
            add("MEDIUM", "unused-active-key", f"{label} was last used {used_age} days ago")

        if status == "inactive":
            disabled_age = age_days(key.get("disabled_at"), today)
            if disabled_age is None:
                add("LOW", "missing-disabled-date", f"{label} is inactive without disabled_at")
            elif disabled_age > 30:
                add("MEDIUM", "stale-inactive-key", f"{label} has remained disabled for {disabled_age} days")

        if key.get("last_used_service") == "iam" and status == "active":
            add("MEDIUM", "iam-api-key-use", f"{label} was used against IAM and deserves privilege review")

    if principal_type == "service" and keys and not principal.get("rotation_runbook"):
        add("MEDIUM", "missing-rotation-runbook", "service credentials need a documented rotation path")

    return findings


def load_inventory(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    principals = payload.get("principals")
    if not isinstance(principals, list):
        raise ValueError("inventory must contain a top-level principals list")
    if not all(isinstance(item, dict) for item in principals):
        raise ValueError("each principal entry must be an object")
    return principals


def review_inventory(path: Path, today: date) -> list[Finding]:
    findings: list[Finding] = []
    for principal in load_inventory(path):
        findings.extend(check_principal(principal, today))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review an IAM access-key inventory for hygiene risks.")
    parser.add_argument("inventory", type=Path, help="Path to a JSON inventory file")
    parser.add_argument("--today", default=date.today().isoformat(), help="Review date in YYYY-MM-DD format")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        today = parse_date(args.today)
        if today is None:
            raise ValueError("--today must be in YYYY-MM-DD format")
        findings = review_inventory(args.inventory, today)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not findings:
        print("PASS: IAM access-key inventory meets the hygiene checks")
        return 0
    print(f"FLAGGED: {len(findings)} IAM access-key hygiene issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
