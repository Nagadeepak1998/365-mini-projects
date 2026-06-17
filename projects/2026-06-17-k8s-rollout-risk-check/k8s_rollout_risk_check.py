#!/usr/bin/env python3
"""Review Kubernetes workload JSON for rollout and disruption risks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


WORKLOAD_KINDS = {"Deployment", "StatefulSet"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review kubectl JSON output for rollout and disruption risks."
    )
    parser.add_argument(
        "snapshot",
        type=Path,
        help="Path to kubectl get deployment,statefulset,pdb -A -o json output",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    return parser


def load_snapshot(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return default


def issue(
    severity: str,
    code: str,
    namespace: str,
    workload: str,
    message: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "namespace": namespace,
        "workload": workload,
        "message": message,
    }


def normalize_items(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    items = snapshot.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    if snapshot:
        return [snapshot]
    return []


def parse_count(value: Any, replicas: int) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        if stripped.endswith("%") and stripped[:-1].isdigit():
            percent = int(stripped[:-1])
            return (replicas * percent) // 100
    return None


def labels_match(selector: dict[str, Any], labels: dict[str, Any]) -> bool:
    if not selector:
        return False
    for key, value in selector.items():
        if labels.get(key) != value:
            return False
    return True


def workload_key(namespace: str, name: str) -> str:
    return f"{namespace}/{name}"


def collect_pdb_selectors(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selectors: list[dict[str, Any]] = []
    for item in items:
        if item.get("kind") != "PodDisruptionBudget":
            continue
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        if not isinstance(metadata, dict) or not isinstance(spec, dict):
            continue
        selector = spec.get("selector", {})
        match_labels = selector.get("matchLabels", {}) if isinstance(selector, dict) else {}
        if not isinstance(match_labels, dict):
            continue
        selectors.append(
            {
                "namespace": str(metadata.get("namespace", "default")),
                "name": str(metadata.get("name", "unknown")),
                "match_labels": {str(key): value for key, value in match_labels.items()},
                "max_unavailable": spec.get("maxUnavailable"),
                "min_available": spec.get("minAvailable"),
            }
        )
    return selectors


def find_matching_pdb(
    namespace: str,
    pod_labels: dict[str, Any],
    pdbs: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for pdb in pdbs:
        if pdb["namespace"] != namespace:
            continue
        if labels_match(pdb["match_labels"], pod_labels):
            return pdb
    return None


def check_single_replica(namespace: str, name: str, replicas: int) -> list[dict[str, str]]:
    if replicas == 1:
        return [
            issue(
                "high",
                "single-replica-rollout",
                namespace,
                name,
                "workload has only one replica, so rollout or node disruption can cause downtime",
            )
        ]
    return []


def check_readiness_probes(
    namespace: str,
    name: str,
    containers: list[dict[str, Any]],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for container in containers:
        container_name = str(container.get("name", "unnamed"))
        if "readinessProbe" not in container:
            findings.append(
                issue(
                    "medium",
                    "missing-readiness-probe",
                    namespace,
                    name,
                    f"container {container_name} does not define a readiness probe",
                )
            )
    return findings


def check_rolling_update(
    kind: str,
    namespace: str,
    name: str,
    replicas: int,
    spec: dict[str, Any],
) -> list[dict[str, str]]:
    if replicas <= 1:
        return []

    if kind == "Deployment":
        strategy = spec.get("strategy", {})
    else:
        strategy = spec.get("updateStrategy", {})
    if not isinstance(strategy, dict):
        return []

    strategy_type = str(strategy.get("type", "RollingUpdate"))
    if strategy_type != "RollingUpdate":
        return []

    rolling_update = strategy.get("rollingUpdate", {})
    if not isinstance(rolling_update, dict):
        return []

    max_unavailable = parse_count(rolling_update.get("maxUnavailable"), replicas)
    if max_unavailable is None:
        return []

    if max_unavailable >= replicas and replicas > 0:
        return [
            issue(
                "high",
                "max-unavailable-all-replicas",
                namespace,
                name,
                "rolling update allows all replicas to become unavailable during rollout",
            )
        ]
    return []


def check_pdb(
    namespace: str,
    name: str,
    replicas: int,
    pod_labels: dict[str, Any],
    pdbs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    if replicas < 2:
        return []

    match = find_matching_pdb(namespace, pod_labels, pdbs)
    if match is None:
        return [
            issue(
                "medium",
                "missing-pdb",
                namespace,
                name,
                "workload has multiple replicas but no matching PodDisruptionBudget",
            )
        ]

    max_unavailable = parse_count(match.get("max_unavailable"), replicas)
    if max_unavailable is not None and max_unavailable >= replicas:
        return [
            issue(
                "high",
                "pdb-allows-total-disruption",
                namespace,
                name,
                f"matching PodDisruptionBudget {match['name']} allows all replicas to be disrupted",
            )
        ]

    min_available = parse_count(match.get("min_available"), replicas)
    if min_available is not None and min_available <= 0:
        return [
            issue(
                "high",
                "pdb-min-available-zero",
                namespace,
                name,
                f"matching PodDisruptionBudget {match['name']} sets minAvailable to zero",
            )
        ]

    return []


def analyze_workload(item: dict[str, Any], pdbs: list[dict[str, Any]]) -> list[dict[str, str]]:
    kind = str(item.get("kind", ""))
    if kind not in WORKLOAD_KINDS:
        return []

    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    if not isinstance(metadata, dict) or not isinstance(spec, dict):
        return []

    namespace = str(metadata.get("namespace", "default"))
    name = workload_key(namespace, str(metadata.get("name", "unknown")))
    replicas = as_int(spec.get("replicas"), default=1)

    template = spec.get("template", {})
    template_spec = template.get("spec", {}) if isinstance(template, dict) else {}
    template_metadata = template.get("metadata", {}) if isinstance(template, dict) else {}
    containers = template_spec.get("containers", []) if isinstance(template_spec, dict) else []
    pod_labels = template_metadata.get("labels", {}) if isinstance(template_metadata, dict) else {}
    if not isinstance(containers, list):
        containers = []
    if not isinstance(pod_labels, dict):
        pod_labels = {}

    findings: list[dict[str, str]] = []
    findings.extend(check_single_replica(namespace, name, replicas))
    findings.extend(check_readiness_probes(namespace, name, containers))
    findings.extend(check_rolling_update(kind, namespace, name, replicas, spec))
    findings.extend(check_pdb(namespace, name, replicas, pod_labels, pdbs))
    return findings


def analyze_snapshot(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    items = normalize_items(snapshot)
    pdbs = collect_pdb_selectors(items)
    findings: list[dict[str, str]] = []
    for item in items:
        findings.extend(analyze_workload(item, pdbs))
    return sorted(findings, key=lambda item: (item["severity"], item["code"], item["workload"]))


def summarize(findings: list[dict[str, str]]) -> dict[str, int]:
    summary = {"high": 0, "medium": 0, "low": 0}
    for finding in findings:
        summary[finding["severity"]] += 1
    return summary


def render_text(findings: list[dict[str, str]]) -> str:
    if not findings:
        return "PASS: no configured Kubernetes rollout risks detected"

    summary = summarize(findings)
    lines = [
        f"FLAGGED: {len(findings)} Kubernetes rollout risk issue(s)",
        f"Risk summary: high={summary['high']} medium={summary['medium']} low={summary['low']}",
    ]
    for finding in findings:
        lines.append(
            f"[{finding['severity'].upper()}] {finding['code']} {finding['workload']} - {finding['message']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    snapshot = load_snapshot(args.snapshot)
    findings = analyze_snapshot(snapshot)

    if args.format == "json":
        print(json.dumps({"findings": findings, "summary": summarize(findings)}, indent=2))
    else:
        print(render_text(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
