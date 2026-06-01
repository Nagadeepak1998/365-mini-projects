#!/usr/bin/env python3
"""Classify common CI failure logs and suggest first response steps."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Rule:
    name: str
    patterns: tuple[str, ...]
    next_step: str


RULES: tuple[Rule, ...] = (
    Rule(
        name="Network/DNS",
        patterns=(r"Could not resolve host", r"Temporary failure in name resolution", r"Connection timed out"),
        next_step="Check runner egress/DNS health, retry once, then pin and mirror critical downloads.",
    ),
    Rule(
        name="Auth/Permission",
        patterns=(r"Permission denied", r"403 Forbidden", r"Authentication failed", r"not authorized"),
        next_step="Verify token scope/secrets mapping and principal permissions for this environment.",
    ),
    Rule(
        name="Dependency install",
        patterns=(r"No matching distribution found", r"npm ERR!", r"Unable to locate package", r"ModuleNotFoundError"),
        next_step="Lock dependency versions and reproduce install with the same runtime image locally.",
    ),
    Rule(
        name="Test failure",
        patterns=(r"AssertionError", r"FAILED ", r"expected .* got", r"test(s)? failed"),
        next_step="Open the first failing test, reproduce locally, and inspect recent logic/config changes.",
    ),
    Rule(
        name="Disk space",
        patterns=(r"No space left on device", r"ENOSPC"),
        next_step="Free runner workspace/cache and reduce artifact/cache size in CI steps.",
    ),
)


def classify(log_text: str) -> tuple[str, str]:
    for rule in RULES:
        if any(re.search(pattern, log_text, re.IGNORECASE) for pattern in rule.patterns):
            return rule.name, rule.next_step
    return (
        "Unknown",
        "Capture full failing step logs, identify first hard error, and add a targeted rule to this tool.",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 ci_failure_first_aid.py <ci-log-file>")
        return 2

    log_path = Path(sys.argv[1])
    if not log_path.exists():
        print(f"Error: file not found: {log_path}")
        return 2

    log_text = log_path.read_text(encoding="utf-8", errors="ignore")
    category, next_step = classify(log_text)

    print(f"Category: {category}")
    print(f"Recommended next step: {next_step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
