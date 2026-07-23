#!/usr/bin/env python3
"""Check saved AI responses against deterministic application contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MISSING = object()


def value_at(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def parse_output(output: Any, expected_type: str) -> tuple[Any, str, list[str]]:
    if expected_type == "json":
        if isinstance(output, (dict, list)):
            return output, json.dumps(output, sort_keys=True), []
        if not isinstance(output, str):
            return None, str(output), ["output must be a JSON object, array, or string"]
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as error:
            return None, output, [f"output is not valid JSON: {error.msg}"]
        return parsed, output, []

    if not isinstance(output, str):
        return output, json.dumps(output, sort_keys=True), ["output must be text"]
    return output, output, []


def evaluate_case(case: dict) -> dict:
    case_id = case.get("id")
    contract = case.get("contract")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("each case must have a non-empty string id")
    if "output" not in case:
        raise ValueError(f"{case_id}: missing output")
    if not isinstance(contract, dict):
        raise ValueError(f"{case_id}: contract must be an object")

    expected_type = contract.get("type", "text")
    if expected_type not in {"text", "json"}:
        raise ValueError(f"{case_id}: contract type must be text or json")

    parsed, searchable, parse_failures = parse_output(case["output"], expected_type)
    failures = list(parse_failures)
    searchable_lower = searchable.lower()

    required_terms = contract.get("required_terms", [])
    forbidden_terms = contract.get("forbidden_terms", [])
    if not isinstance(required_terms, list) or not all(isinstance(term, str) for term in required_terms):
        raise ValueError(f"{case_id}: required_terms must be a string array")
    if not isinstance(forbidden_terms, list) or not all(isinstance(term, str) for term in forbidden_terms):
        raise ValueError(f"{case_id}: forbidden_terms must be a string array")

    for term in required_terms:
        if term.lower() not in searchable_lower:
            failures.append(f"missing required term: {term}")
    for term in forbidden_terms:
        if term.lower() in searchable_lower:
            failures.append(f"contains forbidden term: {term}")

    required_keys = contract.get("required_keys", [])
    exact_values = contract.get("exact_values", {})
    if not isinstance(required_keys, list) or not all(isinstance(path, str) for path in required_keys):
        raise ValueError(f"{case_id}: required_keys must be a string array")
    if not isinstance(exact_values, dict):
        raise ValueError(f"{case_id}: exact_values must be an object")

    if expected_type == "json" and not parse_failures:
        for path in required_keys:
            if value_at(parsed, path) is MISSING:
                failures.append(f"missing required key: {path}")
        for path, expected in exact_values.items():
            actual = value_at(parsed, path)
            if actual is MISSING:
                failures.append(f"missing exact-value key: {path}")
            elif actual != expected:
                failures.append(f"{path} expected {expected!r}, got {actual!r}")

    check_limit(case, contract, "latency_ms", "max_latency_ms", failures)
    check_limit(case, contract, "cost_usd", "max_cost_usd", failures)
    return {"id": case_id, "passed": not failures, "failures": failures}


def check_limit(case: dict, contract: dict, metric: str, limit_name: str, failures: list[str]) -> None:
    if limit_name not in contract:
        return
    value = case.get(metric)
    limit = contract[limit_name]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        failures.append(f"{metric} is required and must be numeric")
    elif not isinstance(limit, (int, float)) or isinstance(limit, bool) or limit < 0:
        raise ValueError(f"{case['id']}: {limit_name} must be a non-negative number")
    elif value > limit:
        failures.append(f"{metric} {value} exceeds {limit_name} {limit}")


def evaluate(cases: list[dict]) -> dict:
    if not cases:
        raise ValueError("input must contain at least one case")
    if not all(isinstance(case, dict) for case in cases):
        raise ValueError("every case must be an object")
    results = [evaluate_case(case) for case in cases]
    passed = sum(result["passed"] for result in results)
    return {
        "passed": passed,
        "failed": len(results) - passed,
        "total": len(results),
        "results": results,
    }


def text_report(report: dict) -> str:
    lines = []
    for result in report["results"]:
        lines.append(f"{'PASS' if result['passed'] else 'FAIL'} {result['id']}")
        lines.extend(f"  - {failure}" for failure in result["failures"])
    lines.append(f"\nSummary: {report['passed']} passed, {report['failed']} failed")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    try:
        cases = json.loads(args.cases.read_text())
        if not isinstance(cases, list):
            raise ValueError("input must be a JSON array")
        report = evaluate(cases)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")

    print(json.dumps(report, indent=2) if args.format == "json" else text_report(report))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
