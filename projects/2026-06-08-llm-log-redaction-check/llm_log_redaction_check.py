#!/usr/bin/env python3
import re
import sys
from pathlib import Path


PATTERNS = [
    ("Bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._-]{12,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Email address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("IPv4 address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    (
        "Secret assignment",
        re.compile(r"(?i)\b(?:password|passwd|token|secret|api[_-]?key)\b\s*[:=]\s*\S+"),
    ),
]


def scan_text(text: str) -> list[str]:
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        labels = [label for label, pattern in PATTERNS if pattern.search(line)]
        if labels:
            joined = ", ".join(labels)
            findings.append(f"line {line_number}: {joined} -> {line.strip()}")
    return findings


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 llm_log_redaction_check.py <log-file>",
            file=sys.stderr,
        )
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

    findings = scan_text(text)
    if not findings:
        print("PASS: no obvious secrets or PII detected")
        return 0

    print(f"FLAGGED: {len(findings)} risky line(s)")
    for finding in findings:
        print(f"- {finding}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
