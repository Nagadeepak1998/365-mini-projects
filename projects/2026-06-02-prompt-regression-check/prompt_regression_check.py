#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("input must be a JSON array of test cases")
    return payload


def evaluate_case(case: dict) -> list[str]:
    name = case.get("name", "unnamed")
    actual = case.get("actual")
    required_terms = case.get("required_terms", [])
    forbidden_terms = case.get("forbidden_terms", [])
    min_length = case.get("min_length", 0)

    if not isinstance(actual, str):
        return [f"{name}: 'actual' must be a string"]

    if not isinstance(required_terms, list) or not all(isinstance(item, str) for item in required_terms):
        return [f"{name}: 'required_terms' must be a list of strings"]

    if not isinstance(forbidden_terms, list) or not all(isinstance(item, str) for item in forbidden_terms):
        return [f"{name}: 'forbidden_terms' must be a list of strings"]

    if not isinstance(min_length, int) or min_length < 0:
        return [f"{name}: 'min_length' must be a non-negative integer"]

    lowered = actual.lower()
    failures = []

    for term in required_terms:
        if term.lower() not in lowered:
            failures.append(f"{name}: missing required term '{term}'")

    for term in forbidden_terms:
        if term.lower() in lowered:
            failures.append(f"{name}: contains forbidden term '{term}'")

    if len(actual.strip()) < min_length:
        failures.append(f"{name}: response shorter than min_length {min_length}")

    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 prompt_regression_check.py <cases.json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 2

    try:
        cases = load_cases(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to load cases: {exc}", file=sys.stderr)
        return 2

    failures = []
    passed = 0

    for case in cases:
        case_failures = evaluate_case(case)
        if case_failures:
            failures.extend(case_failures)
            continue
        passed += 1

    if failures:
        print(f"FAIL: {len(failures)} issue(s) across {len(cases)} case(s)")
        for item in failures:
            print(f"- {item}")
        return 1

    print(f"PASS: {passed} case(s) passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
