#!/usr/bin/env python3
"""Review Kubernetes namespace inventory for quota and guardrail gaps."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCTION_ENVS = {"prod", "production"}
REQUIRED_QUOTA_KEYS = {"cpu", "memory", "pods"}
REQUIRED_DEFAULT_REQUESTS = {"cpu", "memory"}


@dataclass(frozen=True)
class Finding:
    severity: str
    namespace: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.namespace}: {self.message}"


def has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def load_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    namespaces = raw.get("namespaces") if isinstance(raw, dict) else None
    if not isinstance(namespaces, list):
        raise ValueError(f"{path}: expected top-level object with a namespaces list")

    seen: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, namespace in enumerate(namespaces, start=1):
        if not isinstance(namespace, dict):
            raise ValueError(f"{path}: namespaces[{index}] must be an object")
        name = namespace.get("name")
        if not has_text(name):
            raise ValueError(f"{path}: namespaces[{index}] must include a non-empty string name")
        if name in seen:
            raise ValueError(f"{path}: duplicate namespace {name!r}")
        seen.add(name)
        parsed.append(namespace)
    return parsed


def quota_hard_keys(namespace: dict[str, Any]) -> set[str]:
    quota = namespace.get("resource_quota")
    if not isinstance(quota, dict):
        return set()
    hard = quota.get("hard")
    if not isinstance(hard, dict):
        return set()
    return {str(key).strip() for key, value in hard.items() if has_text(value)}


def limit_range_default_request_keys(namespace: dict[str, Any]) -> set[str]:
    limit_range = namespace.get("limit_range")
    if not isinstance(limit_range, dict):
        return set()
    defaults = limit_range.get("default_requests")
    if not isinstance(defaults, dict):
        return set()
    return {str(key).strip() for key, value in defaults.items() if has_text(value)}


def workload_container_findings(namespace_name: str, workloads: Any) -> list[Finding]:
    if not isinstance(workloads, list):
        return []

    findings: list[Finding] = []
    for workload in workloads:
        if not isinstance(workload, dict):
            continue
        workload_name = str(workload.get("name") or "unknown-workload")
        containers = workload.get("containers")
        if not isinstance(containers, list):
            findings.append(Finding("MEDIUM", namespace_name, f"{workload_name} has no container resource data"))
            continue

        for container in containers:
            if not isinstance(container, dict):
                continue
            container_name = str(container.get("name") or "unknown-container")
            requests = container.get("requests") if isinstance(container.get("requests"), dict) else {}
            limits = container.get("limits") if isinstance(container.get("limits"), dict) else {}
            missing_requests = sorted(REQUIRED_DEFAULT_REQUESTS - {key for key, value in requests.items() if has_text(value)})
            missing_limits = sorted(REQUIRED_DEFAULT_REQUESTS - {key for key, value in limits.items() if has_text(value)})
            label = f"{workload_name}/{container_name}"
            if missing_requests:
                findings.append(
                    Finding("MEDIUM", namespace_name, f"{label} missing request(s): {', '.join(missing_requests)}")
                )
            if missing_limits:
                findings.append(Finding("LOW", namespace_name, f"{label} missing limit(s): {', '.join(missing_limits)}"))
    return findings


def review_namespace(namespace: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    name = str(namespace["name"])
    production = normalize_text(namespace.get("environment")) in PRODUCTION_ENVS

    if production and not has_text(namespace.get("owner")):
        findings.append(Finding("HIGH", name, "production namespace is missing an owner"))

    if production and not isinstance(namespace.get("resource_quota"), dict):
        findings.append(Finding("HIGH", name, "production namespace has no ResourceQuota"))
    elif production:
        missing_quota = sorted(REQUIRED_QUOTA_KEYS - quota_hard_keys(namespace))
        if missing_quota:
            findings.append(Finding("MEDIUM", name, f"resource quota missing hard limit(s): {', '.join(missing_quota)}"))

    if production and not isinstance(namespace.get("limit_range"), dict):
        findings.append(Finding("MEDIUM", name, "production namespace has no LimitRange"))
    elif production:
        missing_defaults = sorted(REQUIRED_DEFAULT_REQUESTS - limit_range_default_request_keys(namespace))
        if missing_defaults:
            findings.append(Finding("LOW", name, f"LimitRange missing default request(s): {', '.join(missing_defaults)}"))

    if production and namespace.get("default_deny_network_policy") is not True:
        findings.append(Finding("MEDIUM", name, "default-deny NetworkPolicy is not enabled"))

    if production:
        findings.extend(workload_container_findings(name, namespace.get("workloads")))

    return findings


def review_namespaces(namespaces: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for namespace in sorted(namespaces, key=lambda item: str(item["name"])):
        findings.extend(review_namespace(namespace))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review Kubernetes namespaces for quota and guardrail gaps.")
    parser.add_argument("inventory", type=Path, help="Kubernetes namespace inventory JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        namespaces = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_namespaces(namespaces)
    if not findings:
        print("PASS: Kubernetes namespace guardrails look ready")
        return 0

    print(f"FLAGGED: {len(findings)} Kubernetes namespace guardrail issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
