#!/usr/bin/env python3
import re
import sys
from pathlib import Path


USES_LINE = re.compile(r"^\s*-\s*uses:\s*(['\"]?)([^'\"\s]+)\1\s*(?:#.*)?$")
RISKY_REFS = {"main", "master", "latest", "head"}


def find_risky_refs(text: str) -> list[str]:
    findings = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        match = USES_LINE.match(line)
        if not match:
            continue

        action_ref = match.group(2)
        if action_ref.startswith("docker://") or "@" not in action_ref:
            continue

        action_name, ref = action_ref.rsplit("@", 1)
        if ref.lower() in RISKY_REFS:
            findings.append(
                f"line {line_number}: '{action_name}' uses floating ref '@{ref}'"
            )

    return findings


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 github_action_pin_check.py <workflow.yml>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 2

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Failed to inspect workflow file: {exc}", file=sys.stderr)
        return 2

    findings = find_risky_refs(text)
    if findings:
        print(f"FAIL: {len(findings)} risky action ref(s) found")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("PASS: no risky floating action refs found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
