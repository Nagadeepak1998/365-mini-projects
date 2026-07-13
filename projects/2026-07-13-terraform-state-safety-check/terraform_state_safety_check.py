#!/usr/bin/env python3
"""Review normalized Terraform backend inventories for state-safety risks."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    backend: str
    message: str


def parse_date(value: str, field: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD format") from exc


def review_backend(backend: dict[str, Any], today: date) -> list[Issue]:
    name = backend.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("each backend must have a non-empty string name")

    issues: list[Issue] = []

    def add(severity: str, code: str, message: str) -> None:
        issues.append(Issue(severity, code, name, message))

    environment = backend.get("environment")
    backend_type = backend.get("type")
    if not isinstance(environment, str) or not environment.strip():
        add("high", "missing-environment", "environment is not documented")
    if not isinstance(backend.get("owner"), str) or not backend["owner"].strip():
        add("high", "missing-owner", "an accountable owner is not documented")
    if backend_type not in {"local", "s3", "remote"}:
        add("high", "unknown-backend", f"backend type {backend_type!r} is not recognized")
        return issues

    if backend_type == "local":
        if environment == "production":
            add("critical", "local-production-state", "production state is stored locally")
        if backend.get("gitignored") is not True:
            add("critical", "state-not-gitignored", "local state is not confirmed as gitignored")
        if backend.get("backup_enabled") is not True:
            add("high", "missing-local-backup", "local state has no documented backup")

    if backend_type == "s3":
        required = ("bucket", "key", "region")
        missing = [field for field in required if not backend.get(field)]
        if missing:
            add("high", "incomplete-s3-backend", f"missing required setting(s): {', '.join(missing)}")
        if backend.get("encryption_enabled") is not True:
            add("critical", "unencrypted-state", "S3 state encryption is not enabled")
        if backend.get("versioning_enabled") is not True:
            add("high", "versioning-disabled", "S3 bucket versioning is not enabled")
        if backend.get("public_access_blocked") is not True:
            add("critical", "public-access-not-blocked", "S3 public access is not fully blocked")
        if backend.get("locking_enabled") is not True:
            add("critical", "locking-disabled", "concurrent Terraform runs are not protected by locking")

    if backend_type == "remote":
        missing = [field for field in ("organization", "workspace") if not backend.get(field)]
        if missing:
            add("high", "incomplete-remote-backend", f"missing required setting(s): {', '.join(missing)}")
        if backend.get("locking_enabled") is not True:
            add("critical", "locking-disabled", "remote state locking is not confirmed")

    drill_value = backend.get("last_recovery_drill")
    if not drill_value:
        add("medium", "missing-recovery-drill", "no state recovery drill is documented")
    else:
        drill_date = parse_date(drill_value, f"{name}.last_recovery_drill")
        age = (today - drill_date).days
        if age < 0:
            raise ValueError(f"{name}.last_recovery_drill cannot be in the future")
        if age > 90:
            add("medium", "stale-recovery-drill", f"last state recovery drill was {age} days ago")

    return issues


def review_inventory(payload: Any, today: date) -> list[Issue]:
    if not isinstance(payload, dict) or not isinstance(payload.get("backends"), list):
        raise ValueError("input must be an object containing a backends list")
    names: set[str] = set()
    issues: list[Issue] = []
    for backend in payload["backends"]:
        if not isinstance(backend, dict):
            raise ValueError("each backends entry must be an object")
        name = backend.get("name")
        if name in names:
            raise ValueError(f"duplicate backend name: {name}")
        if isinstance(name, str):
            names.add(name)
        issues.extend(review_backend(backend, today))
    return sorted(issues, key=lambda item: (item.backend, item.code))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path, help="path to the backend inventory JSON file")
    parser.add_argument("--today", default=date.today().isoformat(), help="review date in YYYY-MM-DD format")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(args.inventory.read_text(encoding="utf-8"))
        issues = review_inventory(payload, parse_date(args.today, "today"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps({"passed": not issues, "issue_count": len(issues), "issues": [asdict(issue) for issue in issues]}, indent=2))
    elif issues:
        for issue in issues:
            print(f"[{issue.severity.upper()}] {issue.backend} {issue.code}: {issue.message}")
        print(f"FLAGGED: {len(issues)} Terraform state safety issue(s) detected")
    else:
        print("PASS: Terraform backend inventory meets the state safety checks")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
