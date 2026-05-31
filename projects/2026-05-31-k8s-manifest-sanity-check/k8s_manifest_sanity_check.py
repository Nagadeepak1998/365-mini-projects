#!/usr/bin/env python3
"""Flag common Kubernetes manifest risks with zero dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    severity: str
    message: str


def check_manifest(text: str) -> list[Finding]:
    findings: list[Finding] = []

    if re.search(r"(?m)^\s*type:\s*NodePort\s*$", text):
        findings.append(Finding("MEDIUM", "Service uses NodePort; verify external exposure is intended."))

    if re.search(r"(?m)^\s*image:\s*[^\s]+:latest\s*$", text):
        findings.append(Finding("HIGH", "Container image uses :latest; pin to immutable version/tag."))

    if re.search(r"(?m)^\s*imagePullPolicy:\s*Always\s*$", text) and \
       not re.search(r"(?m)^\s*image:\s*[^\s]+:[^\s]+\s*$", text):
        findings.append(Finding("LOW", "imagePullPolicy is Always but image tag is unclear."))

    if re.search(r"(?m)^\s*kind:\s*Deployment\s*$", text):
        has_limits = re.search(r"(?m)^\s*limits:\s*$", text)
        has_requests = re.search(r"(?m)^\s*requests:\s*$", text)
        if not has_limits or not has_requests:
            findings.append(Finding("HIGH", "Deployment is missing resources.requests/limits."))

    if re.search(r"(?m)^\s*runAsNonRoot:\s*true\s*$", text) is None:
        findings.append(Finding("MEDIUM", "runAsNonRoot is not set to true."))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Kubernetes manifest for common risks.")
    parser.add_argument("manifest", type=Path, help="Path to YAML manifest file")
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"error: file not found: {args.manifest}", file=sys.stderr)
        return 2

    text = args.manifest.read_text(encoding="utf-8")
    findings = check_manifest(text)

    if not findings:
        print("PASS: no checks triggered")
        return 0

    print(f"FAIL: {len(findings)} finding(s)")
    for f in findings:
        print(f"- [{f.severity}] {f.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
