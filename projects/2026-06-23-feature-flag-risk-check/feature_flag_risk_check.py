#!/usr/bin/env python3
"""Review proposed feature flag changes for rollout and ownership risk."""

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
    flag: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.flag}: {self.message}"


def load_flags(path: Path) -> dict[str, dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    flags = raw.get("flags") if isinstance(raw, dict) else None
    if not isinstance(flags, list):
        raise ValueError(f"{path}: expected top-level object with a flags list")

    indexed: dict[str, dict[str, Any]] = {}
    for index, flag in enumerate(flags, start=1):
        if not isinstance(flag, dict):
            raise ValueError(f"{path}: flags[{index}] must be an object")
        name = flag.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{path}: flags[{index}] must include a non-empty string name")
        if name in indexed:
            raise ValueError(f"{path}: duplicate flag name {name!r}")
        indexed[name] = flag
    return indexed


def percent(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and 0 <= value <= 100:
        return value
    return default


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return False


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def review_flag(name: str, before: dict[str, Any] | None, after: dict[str, Any], today: date) -> list[Finding]:
    findings: list[Finding] = []
    environment = str(after.get("environment", "")).lower()
    old_rollout = percent(before.get("rollout_percent") if before else 0)
    new_rollout = percent(after.get("rollout_percent"))
    rollout_delta = new_rollout - old_rollout

    owner = after.get("owner")
    expires_on = parse_date(after.get("expires_on"))
    rollback = after.get("rollback")

    if rollout_delta > 50:
        findings.append(
            Finding(
                "HIGH",
                name,
                f"rollout increases from {old_rollout}% to {new_rollout}% in one change",
            )
        )

    if old_rollout < 100 and new_rollout == 100 and (
        not isinstance(rollback, str) or not rollback.strip()
    ):
        findings.append(
            Finding(
                "HIGH",
                name,
                "reaches full rollout without a rollback note or runbook link",
            )
        )

    if not isinstance(owner, str) or not owner.strip():
        findings.append(Finding("MEDIUM", name, "missing owner for follow-up during incidents"))

    if expires_on is None:
        findings.append(Finding("MEDIUM", name, "missing valid expires_on date"))
    elif expires_on < today and new_rollout > 0:
        findings.append(
            Finding(
                "MEDIUM",
                name,
                f"flag expired on {expires_on.isoformat()} but is still active",
            )
        )

    if environment == "prod" and is_truthy(after.get("debug")):
        findings.append(Finding("HIGH", name, "debug behavior is enabled in prod"))

    if after.get("kill_switch") is False and new_rollout > 0:
        findings.append(Finding("MEDIUM", name, "rollout has no kill switch"))

    return findings


def review_flags(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]], today: date) -> list[Finding]:
    findings: list[Finding] = []
    for name in sorted(after):
        findings.extend(review_flag(name, before.get(name), after[name], today))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review proposed feature flag JSON for production rollout risk."
    )
    parser.add_argument("current", type=Path, help="Current feature flag JSON")
    parser.add_argument("proposed", type=Path, help="Proposed feature flag JSON")
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
        current = load_flags(args.current)
        proposed = load_flags(args.proposed)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_flags(current, proposed, today)
    if not findings:
        print("PASS: no feature flag rollout risks detected")
        return 0

    print(f"FLAGGED: {len(findings)} feature flag risk(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
