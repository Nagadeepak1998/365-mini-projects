#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


DATABASE_PORTS = {"5432", "3306", "6379", "27017", "9200", "5672"}
PLACEHOLDER_VALUES = {"changeme", "example", "your-value", "replace-me", "placeholder"}
SECRET_KEY_PATTERN = re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key)")
LATEST_IMAGE_PATTERN = re.compile(r"^\s*image:\s*[^\s#]+:latest\s*$")
PORT_PATTERN = re.compile(r'^\s*-\s*["\']?(?:0\.0\.0\.0:)?(\d+):(\d+)(?:/\w+)?["\']?\s*$')
SECRET_ENV_PATTERN = re.compile(r"^\s*-\s*([A-Z0-9_]+)=(.+?)\s*$")


@dataclass
class Finding:
    severity: str
    line_number: int
    message: str


def is_placeholder_secret(value: str) -> bool:
    cleaned = value.strip().strip("'\"")
    lowered = cleaned.lower()
    return (
        lowered in PLACEHOLDER_VALUES
        or cleaned.startswith("${")
        or cleaned.startswith("<")
        or cleaned.endswith(">")
    )


def scan_compose(text: str) -> list[Finding]:
    findings: list[Finding] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        if LATEST_IMAGE_PATTERN.match(line):
            findings.append(Finding("MEDIUM", line_number, "Image uses :latest; pin to a specific version or digest."))

        if re.match(r"^\s*privileged:\s*true\s*$", line):
            findings.append(Finding("HIGH", line_number, "Container runs with privileged=true."))

        if "/var/run/docker.sock" in stripped:
            findings.append(Finding("HIGH", line_number, "Docker socket is mounted into the container."))

        env_match = SECRET_ENV_PATTERN.match(line)
        if env_match:
            key, value = env_match.groups()
            if SECRET_KEY_PATTERN.search(key) and not is_placeholder_secret(value):
                findings.append(Finding("HIGH", line_number, f"Environment variable {key} contains an inline secret value."))

        port_match = PORT_PATTERN.match(line)
        if port_match:
            host_port, container_port = port_match.groups()
            if host_port == container_port and container_port in DATABASE_PORTS:
                findings.append(
                    Finding(
                        "MEDIUM",
                        line_number,
                        f"Common data-service port {container_port} is published on the host; verify external exposure is intended.",
                    )
                )

    return findings


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 compose_risk_check.py <compose-file>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 2

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Failed to read input file: {exc}", file=sys.stderr)
        return 2

    findings = scan_compose(text)
    if not findings:
        print("PASS: no obvious Docker Compose risks detected")
        return 0

    print(f"FLAGGED: {len(findings)} finding(s)")
    for finding in findings:
        print(f"- line {finding.line_number} [{finding.severity}] {finding.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
