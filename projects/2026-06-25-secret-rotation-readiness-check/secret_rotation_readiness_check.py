#!/usr/bin/env python3
"""Review service secrets before a rotation window."""

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
    secret: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.secret}: {self.message}"


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


def has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    secrets = raw.get("secrets") if isinstance(raw, dict) else None
    if not isinstance(secrets, list):
        raise ValueError(f"{path}: expected top-level object with a secrets list")

    names: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, secret in enumerate(secrets, start=1):
        if not isinstance(secret, dict):
            raise ValueError(f"{path}: secrets[{index}] must be an object")
        name = secret.get("name")
        if not has_text(name):
            raise ValueError(f"{path}: secrets[{index}] must include a non-empty string name")
        if name in names:
            raise ValueError(f"{path}: duplicate secret name {name!r}")
        names.add(name)
        parsed.append(secret)
    return parsed


def review_secret(secret: dict[str, Any], today: date) -> list[Finding]:
    name = str(secret["name"])
    findings: list[Finding] = []

    owner = secret.get("owner")
    last_rotated_at = parse_date(secret.get("last_rotated_at"))
    next_rotation_due = parse_date(secret.get("next_rotation_due"))
    last_validation_at = parse_date(secret.get("last_validation_at"))
    rotation_interval_days = positive_int(secret.get("rotation_interval_days"), 90)
    validation_status = str(secret.get("validation_status", "")).strip().lower()
    critical = secret.get("used_by_critical_path") is True
    dual_secret_supported = secret.get("dual_secret_supported")
    break_glass_reviewed_at = parse_date(secret.get("break_glass_access_reviewed_at"))

    if not has_text(owner):
        findings.append(Finding("MEDIUM", name, "missing owner for rotation follow-up"))

    if last_rotated_at is None:
        findings.append(Finding("HIGH", name, "missing valid last_rotated_at date"))
    else:
        secret_age_days = (today - last_rotated_at).days
        if secret_age_days > rotation_interval_days:
            findings.append(
                Finding(
                    "HIGH",
                    name,
                    f"secret is {secret_age_days} days old, above {rotation_interval_days} day rotation target",
                )
            )

    if next_rotation_due is None:
        findings.append(Finding("MEDIUM", name, "missing valid next_rotation_due date"))
    elif next_rotation_due < today:
        days_overdue = (today - next_rotation_due).days
        findings.append(Finding("HIGH", name, f"rotation is {days_overdue} day(s) overdue"))

    if critical and dual_secret_supported is not True:
        findings.append(Finding("HIGH", name, "critical path secret cannot rotate with dual-secret overlap"))

    if not has_text(secret.get("rollback_plan")):
        findings.append(Finding("MEDIUM", name, "missing rollback plan"))

    if validation_status not in {"passed", "pass", "ok"}:
        findings.append(Finding("HIGH", name, f"latest validation status is {validation_status or 'missing'}"))

    if last_validation_at is None:
        findings.append(Finding("MEDIUM", name, "missing valid last_validation_at date"))
    else:
        validation_age_days = (today - last_validation_at).days
        if validation_age_days > 30:
            findings.append(
                Finding("MEDIUM", name, f"validation evidence is {validation_age_days} days old")
            )

    if critical:
        if break_glass_reviewed_at is None:
            findings.append(Finding("MEDIUM", name, "missing break-glass access review date"))
        else:
            break_glass_age_days = (today - break_glass_reviewed_at).days
            if break_glass_age_days > 90:
                findings.append(
                    Finding(
                        "MEDIUM",
                        name,
                        f"break-glass access review is {break_glass_age_days} days old",
                    )
                )

    return findings


def review_inventory(secrets: list[dict[str, Any]], today: date) -> list[Finding]:
    findings: list[Finding] = []
    for secret in sorted(secrets, key=lambda item: str(item["name"])):
        findings.extend(review_secret(secret, today))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review service secret inventory JSON for rotation readiness."
    )
    parser.add_argument("inventory", type=Path, help="Secret inventory JSON")
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
        secrets = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_inventory(secrets, today)
    if not findings:
        print("PASS: secret rotation inventory is ready")
        return 0

    print(f"FLAGGED: {len(findings)} secret rotation risk(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
