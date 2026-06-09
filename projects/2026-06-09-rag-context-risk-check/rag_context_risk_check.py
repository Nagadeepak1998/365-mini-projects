#!/usr/bin/env python3
import re
import sys
from pathlib import Path


PATTERNS = [
    (
        "Instruction override",
        re.compile(r"(?i)\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above)\b.{0,40}\b(instruction|rule|prompt)s?\b"),
    ),
    (
        "System prompt probe",
        re.compile(r"(?i)\b(reveal|show|print|display|leak)\b.{0,40}\b(system prompt|hidden prompt|developer message|secret instructions?)\b"),
    ),
    (
        "Credential exfiltration",
        re.compile(r"(?i)\b(api key|token|secret|password|credential|environment variable|env var)s?\b.{0,40}\b(output|print|share|expose|dump|reveal)\b"),
    ),
    (
        "Tool or browsing directive",
        re.compile(r"(?i)\b(use the browser|browse to|open https?://|call the tool|run this command|execute this)\b"),
    ),
]


def scan_text(text: str) -> list[str]:
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        labels = [label for label, pattern in PATTERNS if pattern.search(line)]
        if labels:
            findings.append(f"line {line_number}: {', '.join(labels)} -> {line.strip()}")
    return findings


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 rag_context_risk_check.py <context-file>", file=sys.stderr)
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
        print("PASS: no obvious prompt-injection cues detected")
        return 0

    print(f"FLAGGED: {len(findings)} risky line(s)")
    for finding in findings:
        print(f"- {finding}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
