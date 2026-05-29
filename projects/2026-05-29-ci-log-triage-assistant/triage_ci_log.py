#!/usr/bin/env python3
"""Small CI log triage helper for common pipeline failures."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str
    action: str
    severity: str


RULES = [
    Rule("ModuleNotFoundError", "dependency", "Install missing package and pin it in requirements/lockfile.", "high"),
    Rule("No module named", "dependency", "Install missing package and pin it in requirements/lockfile.", "high"),
    Rule("npm ERR!", "dependency", "Run clean install and verify package-lock consistency.", "high"),
    Rule("ENOSPC", "runner-disk", "Free runner disk/cache or use a larger runner.", "high"),
    Rule("No space left on device", "runner-disk", "Free runner disk/cache or use a larger runner.", "high"),
    Rule("timed out", "network-timeout", "Retry with backoff and increase timeout for external calls.", "medium"),
    Rule("SSL", "tls", "Verify certificate chain and runner trust store.", "medium"),
    Rule("permission denied", "permissions", "Check token/role scopes and file permissions.", "high"),
    Rule("exit code 137", "out-of-memory", "Raise memory limit or reduce parallelism.", "high"),
]


def triage(log_text: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    lower = log_text.lower()
    for rule in RULES:
        if rule.pattern.lower() in lower:
            findings.append(
                {
                    "category": rule.category,
                    "severity": rule.severity,
                    "pattern": rule.pattern,
                    "action": rule.action,
                }
            )
    if not findings:
        findings.append(
            {
                "category": "unknown",
                "severity": "low",
                "pattern": "none",
                "action": "No known pattern found. Inspect first failing step and stack trace manually.",
            }
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage CI log text for likely root-cause categories.")
    parser.add_argument("log_file", type=Path, help="Path to CI log text file")
    args = parser.parse_args()

    text = args.log_file.read_text(encoding="utf-8")
    findings = triage(text)

    print(f"Log file: {args.log_file}")
    print("Likely issues:")
    for index, finding in enumerate(findings, start=1):
        print(
            f"{index}. [{finding['severity']}] {finding['category']} - "
            f"matched '{finding['pattern']}' -> {finding['action']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
