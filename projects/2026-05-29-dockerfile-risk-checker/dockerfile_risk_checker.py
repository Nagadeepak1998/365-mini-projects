#!/usr/bin/env python3
"""Minimal Dockerfile risk checker for common DevOps pitfalls."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SEVERITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def check_lines(lines: list[str]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    has_user = False

    for line_no, raw in enumerate(lines, start=1):
        line = raw.strip()
        upper = line.upper()

        if not line or line.startswith("#"):
            continue

        if upper.startswith("FROM"):
            if ":latest" in line.lower():
                findings.append(
                    (line_no, "HIGH", "Base image uses latest tag", "Pin an explicit image version or digest")
                )

        if upper.startswith("ADD "):
            findings.append(
                (line_no, "MEDIUM", "ADD used instead of COPY", "Use COPY unless ADD-specific behavior is required")
            )

        if upper.startswith("RUN") and "apt-get install" in line and "--no-install-recommends" not in line:
            findings.append(
                (
                    line_no,
                    "MEDIUM",
                    "apt-get install without --no-install-recommends",
                    "Add --no-install-recommends to reduce image bloat",
                )
            )

        if upper.startswith("USER"):
            has_user = True
            if re.search(r"^USER\s+root\s*$", line, re.IGNORECASE):
                findings.append((line_no, "HIGH", "Container runs as root", "Use a non-root USER for runtime"))

    if not has_user:
        findings.append((0, "MEDIUM", "No USER specified", "Set a non-root USER near the end of the Dockerfile"))

    findings.sort(key=lambda item: (SEVERITY_ORDER[item[1]], item[0]), reverse=True)
    return findings


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 dockerfile_risk_checker.py <Dockerfile-path>")
        return 1

    dockerfile_path = Path(sys.argv[1])
    if not dockerfile_path.exists():
        print(f"Error: file not found: {dockerfile_path}")
        return 1

    lines = dockerfile_path.read_text(encoding="utf-8").splitlines()
    findings = check_lines(lines)

    if not findings:
        print("No obvious risks found.")
        return 0

    print(f"Found {len(findings)} risk(s):")
    for line_no, severity, message, fix in findings:
        line_label = f"line {line_no}" if line_no > 0 else "file-level"
        print(f"- [{severity}] {line_label}: {message}. Fix: {fix}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
