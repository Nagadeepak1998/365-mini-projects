#!/usr/bin/env python3
"""Review PrometheusRule JSON snapshots for alert metadata gaps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PAGE_SEVERITIES = {"critical", "page"}
OWNER_LABELS = ("team", "owner", "service")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review PrometheusRule JSON output for alert metadata gaps."
    )
    parser.add_argument(
        "snapshot",
        type=Path,
        help="Path to kubectl get prometheusrule -A -o json output",
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


def issue(
    severity: str,
    code: str,
    namespace: str,
    rule_resource: str,
    group: str,
    alert: str,
    message: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "namespace": namespace,
        "rule_resource": rule_resource,
        "group": group,
        "alert": alert,
        "message": message,
    }


def has_owner_label(labels: dict[str, Any]) -> bool:
    return any(str(labels.get(key, "")).strip() for key in OWNER_LABELS)


def check_alert_rule(
    namespace: str,
    rule_resource: str,
    group_name: str,
    rule: dict[str, Any],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    alert_name = str(rule.get("alert", "unnamed"))
    labels = rule.get("labels", {})
    annotations = rule.get("annotations", {})

    if not isinstance(labels, dict):
        labels = {}
    if not isinstance(annotations, dict):
        annotations = {}

    severity = str(labels.get("severity", "")).strip().lower()
    hold_for = str(rule.get("for", "")).strip()

    if not severity:
        findings.append(
            issue(
                "medium",
                "missing-severity-label",
                namespace,
                rule_resource,
                group_name,
                alert_name,
                "alert rule does not define a severity label",
            )
        )

    if severity in PAGE_SEVERITIES and not hold_for:
        findings.append(
            issue(
                "high",
                "missing-for-window",
                namespace,
                rule_resource,
                group_name,
                alert_name,
                "page-level alert does not define a for window to reduce flapping",
            )
        )

    if not str(annotations.get("runbook_url", "")).strip():
        findings.append(
            issue(
                "medium",
                "missing-runbook-url",
                namespace,
                rule_resource,
                group_name,
                alert_name,
                "alert rule is missing a runbook_url annotation",
            )
        )

    if not str(annotations.get("dashboard_url", "")).strip():
        findings.append(
            issue(
                "low",
                "missing-dashboard-url",
                namespace,
                rule_resource,
                group_name,
                alert_name,
                "alert rule is missing a dashboard_url annotation",
            )
        )

    if not str(annotations.get("summary", "")).strip():
        findings.append(
            issue(
                "low",
                "missing-summary",
                namespace,
                rule_resource,
                group_name,
                alert_name,
                "alert rule is missing a summary annotation",
            )
        )

    if not has_owner_label(labels):
        findings.append(
            issue(
                "medium",
                "missing-owner-label",
                namespace,
                rule_resource,
                group_name,
                alert_name,
                "alert rule is missing team, owner, or service ownership labels",
            )
        )

    return findings


def collect_findings(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    for item in normalize_items(snapshot):
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        if not isinstance(metadata, dict) or not isinstance(spec, dict):
            continue

        namespace = str(metadata.get("namespace", "default"))
        rule_resource = str(metadata.get("name", "unnamed-rule"))
        groups = spec.get("groups", [])
        if not isinstance(groups, list):
            continue

        for group in groups:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", "unnamed-group"))
            rules = group.get("rules", [])
            if not isinstance(rules, list):
                continue

            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                if "alert" not in rule:
                    continue
                findings.extend(
                    check_alert_rule(namespace, rule_resource, group_name, rule)
                )

    return findings


def render_text(findings: list[dict[str, str]]) -> str:
    if not findings:
        return "PASS: no Prometheus alert metadata gaps detected"

    lines = [f"FLAGGED: {len(findings)} Prometheus alert metadata issue(s)"]
    for finding in findings:
        lines.append(
            (
                f"- [{finding['severity']}] {finding['namespace']}/"
                f"{finding['rule_resource']} :: {finding['group']} :: "
                f"{finding['alert']} - {finding['message']}"
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    snapshot = load_snapshot(args.snapshot)
    findings = collect_findings(snapshot)

    if args.format == "json":
        print(json.dumps({"findings": findings}, indent=2))
    else:
        print(render_text(findings))

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
