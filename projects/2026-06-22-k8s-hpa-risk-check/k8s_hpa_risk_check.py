#!/usr/bin/env python3
"""Review Kubernetes HPA JSON snapshots for scaling risks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


WORKLOAD_KINDS = {"Deployment", "StatefulSet"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review kubectl JSON output for HPA and workload scaling risks."
    )
    parser.add_argument(
        "snapshot",
        type=Path,
        help="Path to kubectl get hpa,deployment,statefulset -A -o json output",
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


def normalize_items(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    items = snapshot.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    if snapshot:
        return [snapshot]
    return []


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
    hpa: str,
    message: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "namespace": namespace,
        "hpa": hpa,
        "message": message,
    }


def resource_name(item: dict[str, Any]) -> tuple[str, str, str]:
    metadata = item.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return (
        str(item.get("kind", "Unknown")),
        str(metadata.get("namespace", "default")),
        str(metadata.get("name", "unknown")),
    )


def workload_key(kind: str, namespace: str, name: str) -> str:
    return f"{kind}/{namespace}/{name}"


def collect_workloads(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    workloads: dict[str, dict[str, Any]] = {}
    for item in items:
        kind, namespace, name = resource_name(item)
        if kind not in WORKLOAD_KINDS:
            continue
        workloads[workload_key(kind, namespace, name)] = item
    return workloads


def collect_hpas(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if resource_name(item)[0] == "HorizontalPodAutoscaler"]


def target_key(hpa: dict[str, Any], namespace: str) -> str | None:
    spec = hpa.get("spec", {})
    if not isinstance(spec, dict):
        return None

    target = spec.get("scaleTargetRef", {})
    if not isinstance(target, dict):
        return None

    kind = str(target.get("kind", ""))
    name = str(target.get("name", ""))
    if not kind or not name:
        return None
    return workload_key(kind, namespace, name)


def has_cpu_request(workload: dict[str, Any]) -> bool:
    spec = workload.get("spec", {})
    if not isinstance(spec, dict):
        return False

    template = spec.get("template", {})
    pod_spec = template.get("spec", {}) if isinstance(template, dict) else {}
    containers = pod_spec.get("containers", []) if isinstance(pod_spec, dict) else []
    if not isinstance(containers, list) or not containers:
        return False

    for container in containers:
        if not isinstance(container, dict):
            continue
        resources = container.get("resources", {})
        requests = resources.get("requests", {}) if isinstance(resources, dict) else {}
        if isinstance(requests, dict) and requests.get("cpu"):
            return True
    return False


def has_resource_metric(hpa: dict[str, Any], resource_name_value: str) -> bool:
    spec = hpa.get("spec", {})
    metrics = spec.get("metrics", []) if isinstance(spec, dict) else []
    if not isinstance(metrics, list):
        return False

    for metric in metrics:
        if not isinstance(metric, dict) or metric.get("type") != "Resource":
            continue
        resource = metric.get("resource", {})
        if isinstance(resource, dict) and resource.get("name") == resource_name_value:
            return True
    return False


def has_scale_down_stabilization(hpa: dict[str, Any], minimum_seconds: int = 300) -> bool:
    spec = hpa.get("spec", {})
    behavior = spec.get("behavior", {}) if isinstance(spec, dict) else {}
    scale_down = behavior.get("scaleDown", {}) if isinstance(behavior, dict) else {}
    seconds = scale_down.get("stabilizationWindowSeconds") if isinstance(scale_down, dict) else None
    return as_int(seconds, 0) >= minimum_seconds


def check_hpa(
    hpa: dict[str, Any],
    workloads: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    _, namespace, name = resource_name(hpa)
    spec = hpa.get("spec", {})
    if not isinstance(spec, dict):
        return [
            issue("high", "invalid-hpa-spec", namespace, name, "HPA has no readable spec")
        ]

    findings: list[dict[str, str]] = []
    min_replicas = as_int(spec.get("minReplicas"), 1)
    max_replicas = as_int(spec.get("maxReplicas"), 0)

    if min_replicas < 2:
        findings.append(
            issue(
                "medium",
                "low-min-replicas",
                namespace,
                name,
                "minReplicas is below 2, so scale-down can leave no spare pod for disruption",
            )
        )

    if max_replicas <= min_replicas:
        findings.append(
            issue(
                "high",
                "no-scale-out-room",
                namespace,
                name,
                "maxReplicas is not greater than minReplicas, so the HPA cannot add capacity",
            )
        )

    key = target_key(hpa, namespace)
    workload = workloads.get(key or "")
    if key is None or workload is None:
        findings.append(
            issue(
                "high",
                "missing-scale-target",
                namespace,
                name,
                "scaleTargetRef does not match a workload in this snapshot",
            )
        )
    elif has_resource_metric(hpa, "cpu") and not has_cpu_request(workload):
        findings.append(
            issue(
                "high",
                "cpu-metric-without-cpu-request",
                namespace,
                name,
                "HPA uses CPU metrics but the target workload has no container CPU request",
            )
        )

    if not has_scale_down_stabilization(hpa):
        findings.append(
            issue(
                "medium",
                "missing-scale-down-stabilization",
                namespace,
                name,
                "scaleDown stabilizationWindowSeconds is missing or below 300 seconds",
            )
        )

    return findings


def analyze_snapshot(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    items = normalize_items(snapshot)
    workloads = collect_workloads(items)
    findings: list[dict[str, str]] = []
    for hpa in collect_hpas(items):
        findings.extend(check_hpa(hpa, workloads))
    return findings


def render_text(findings: list[dict[str, str]]) -> str:
    if not findings:
        return "PASS: no configured Kubernetes HPA risks detected"

    lines = ["Kubernetes HPA risk findings:"]
    for finding in findings:
        lines.append(
            "- {severity} {namespace}/{hpa} [{code}]: {message}".format(**finding)
        )
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    findings = analyze_snapshot(load_snapshot(args.snapshot))
    if args.format == "json":
        print(json.dumps({"findings": findings}, indent=2))
    else:
        print(render_text(findings))
    return 1 if any(finding["severity"] == "high" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
