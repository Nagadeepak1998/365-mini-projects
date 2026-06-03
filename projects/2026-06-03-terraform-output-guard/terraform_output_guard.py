#!/usr/bin/env python3
import re
import sys
from pathlib import Path


OUTPUT_HEADER = re.compile(r'^\s*output\s+"([^"]+)"\s*\{')
DESCRIPTION = re.compile(r"^\s*description\s*=")
SENSITIVE_TRUE = re.compile(r"^\s*sensitive\s*=\s*true\b", re.IGNORECASE)
SECRET_NAME = re.compile(r"(password|secret|token|key)", re.IGNORECASE)


def read_output_blocks(text: str) -> list[tuple[str, int, list[str]]]:
    blocks = []
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        match = OUTPUT_HEADER.match(lines[index])
        if not match:
            index += 1
            continue

        name = match.group(1)
        start_line = index + 1
        depth = lines[index].count("{") - lines[index].count("}")
        body = []
        index += 1

        while index < len(lines) and depth > 0:
            line = lines[index]
            depth += line.count("{") - line.count("}")
            if depth > 0:
                body.append(line)
            index += 1

        if depth != 0:
            raise ValueError(f"Unclosed output block '{name}' starting on line {start_line}")

        blocks.append((name, start_line, body))

    return blocks


def evaluate_block(name: str, start_line: int, body: list[str]) -> list[str]:
    issues = []
    has_description = any(DESCRIPTION.search(line) for line in body)
    has_sensitive_true = any(SENSITIVE_TRUE.search(line) for line in body)

    if not has_description:
        issues.append(f"line {start_line}: output '{name}' is missing description")

    if SECRET_NAME.search(name) and not has_sensitive_true:
        issues.append(f"line {start_line}: output '{name}' looks secret but is not marked sensitive = true")

    return issues


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 terraform_output_guard.py <file.tf>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 2

    try:
        text = path.read_text(encoding="utf-8")
        blocks = read_output_blocks(text)
    except (OSError, ValueError) as exc:
        print(f"Failed to inspect Terraform file: {exc}", file=sys.stderr)
        return 2

    if not blocks:
        print("No output blocks found")
        return 0

    issues = []
    for name, start_line, body in blocks:
        issues.extend(evaluate_block(name, start_line, body))

    if issues:
        print(f"FAIL: {len(issues)} issue(s) found across {len(blocks)} output block(s)")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print(f"PASS: {len(blocks)} output block(s) passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
