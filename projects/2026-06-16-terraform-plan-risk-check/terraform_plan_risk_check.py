#!/usr/bin/env python3
"""Review Terraform plan JSON for a few high-signal infrastructure risks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SENSITIVE_PORTS = {22, 3389, 5432, 6379, 9200}
RISKY_ACTIONS = {"create", "update", "delete"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review terraform show -json plan output for infrastructure risk."
    )
    parser.add_argument("plan", type=Path, help="Path to a Terraform plan JSON file")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    return parser


def load_plan(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def issue(severity: str, code: str, address: str, message: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "address": address,
        "message": message,
    }


def normalize_actions(change: dict[str, Any]) -> set[str]:
    actions = set(change.get("actions", []))
    if "create" in actions and "delete" in actions:
        actions.add("replace")
    return actions


def is_risky_change(actions: set[str]) -> bool:
    return bool(actions & RISKY_ACTIONS or "replace" in actions)


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def has_public_cidr(rule: dict[str, Any]) -> bool:
    cidr_blocks = {str(value) for value in as_list(rule.get("cidr_blocks"))}
    ipv6_blocks = {str(value) for value in as_list(rule.get("ipv6_cidr_blocks"))}
    return "0.0.0.0/0" in cidr_blocks or "::/0" in ipv6_blocks


def covers_sensitive_port(rule: dict[str, Any]) -> bool:
    from_port = int(rule.get("from_port", 0))
    to_port = int(rule.get("to_port", 0))
    protocol = str(rule.get("protocol", "tcp"))

    if protocol == "-1":
        return True
    if from_port == 0 and to_port == 0:
        return True
    return any(from_port <= port <= to_port for port in SENSITIVE_PORTS)


def check_security_group(address: str, after: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for index, rule in enumerate(as_list(after.get("ingress"))):
        if not isinstance(rule, dict):
            continue
        if has_public_cidr(rule) and covers_sensitive_port(rule):
            findings.append(
                issue(
                    "high",
                    "public-sensitive-ingress",
                    address,
                    (
                        "ingress rule opens a sensitive port range to the public internet "
                        f"(rule {index + 1})"
                    ),
                )
            )
    return findings


def check_security_group_rule(address: str, after: dict[str, Any]) -> list[dict[str, str]]:
    if str(after.get("type", "")).lower() != "ingress":
        return []
    if has_public_cidr(after) and covers_sensitive_port(after):
        return [
            issue(
                "high",
                "public-sensitive-ingress",
                address,
                "security group rule opens a sensitive port range to the public internet",
            )
        ]
    return []


def check_db_instance(address: str, after: dict[str, Any]) -> list[dict[str, str]]:
    if after.get("publicly_accessible") is True:
        return [
            issue(
                "high",
                "public-db-instance",
                address,
                "database instance is marked publicly accessible",
            )
        ]
    return []


def check_public_access_block(address: str, after: dict[str, Any]) -> list[dict[str, str]]:
    disabled = [
        name
        for name in (
            "block_public_acls",
            "block_public_policy",
            "ignore_public_acls",
            "restrict_public_buckets",
        )
        if after.get(name) is False
    ]
    if not disabled:
        return []
    return [
        issue(
            "medium",
            "s3-public-access-relaxed",
            address,
            "S3 public access protections are disabled for: " + ", ".join(sorted(disabled)),
        )
    ]


def extract_policy_document(after: dict[str, Any]) -> dict[str, Any] | None:
    raw_policy = after.get("policy")
    if not isinstance(raw_policy, str):
        return None
    try:
        decoded = json.loads(raw_policy)
    except json.JSONDecodeError:
        return None
    if isinstance(decoded, dict):
        return decoded
    return None


def as_string_list(value: Any) -> list[str]:
    return [str(item) for item in as_list(value)]


def statement_is_wildcard(statement: dict[str, Any]) -> bool:
    actions = as_string_list(statement.get("Action"))
    resources = as_string_list(statement.get("Resource"))
    has_wild_action = "*" in actions or any(action.endswith(":*") for action in actions)
    has_wild_resource = "*" in resources
    effect = str(statement.get("Effect", "Allow"))
    return effect.lower() == "allow" and has_wild_action and has_wild_resource


def check_iam_policy(address: str, after: dict[str, Any]) -> list[dict[str, str]]:
    document = extract_policy_document(after)
    if not document:
        return []
    statements = as_list(document.get("Statement"))
    findings: list[dict[str, str]] = []
    for index, statement in enumerate(statements):
        if isinstance(statement, dict) and statement_is_wildcard(statement):
            findings.append(
                issue(
                    "high",
                    "iam-wildcard-admin",
                    address,
                    f"IAM policy statement {index + 1} allows wildcard action and wildcard resource",
                )
            )
    return findings


def analyze_resource_change(resource_change: dict[str, Any]) -> list[dict[str, str]]:
    resource_type = str(resource_change.get("type", ""))
    address = str(resource_change.get("address", resource_type or "unknown"))
    change = resource_change.get("change", {})
    if not isinstance(change, dict):
        return []

    actions = normalize_actions(change)
    if not is_risky_change(actions):
        return []

    after = change.get("after")
    if not isinstance(after, dict):
        return []

    if resource_type == "aws_security_group":
        return check_security_group(address, after)
    if resource_type == "aws_security_group_rule":
        return check_security_group_rule(address, after)
    if resource_type in {"aws_db_instance", "aws_rds_cluster_instance"}:
        return check_db_instance(address, after)
    if resource_type == "aws_s3_bucket_public_access_block":
        return check_public_access_block(address, after)
    if resource_type in {"aws_iam_policy", "aws_iam_role_policy"}:
        return check_iam_policy(address, after)
    return []


def analyze_plan(plan: dict[str, Any]) -> list[dict[str, str]]:
    resource_changes = plan.get("resource_changes", [])
    findings: list[dict[str, str]] = []
    for resource_change in resource_changes:
        if isinstance(resource_change, dict):
            findings.extend(analyze_resource_change(resource_change))
    return sorted(findings, key=lambda item: (item["severity"], item["code"], item["address"]))


def summarize(findings: list[dict[str, str]]) -> dict[str, int]:
    summary = {"high": 0, "medium": 0, "low": 0}
    for finding in findings:
        summary[finding["severity"]] += 1
    return summary


def render_text(findings: list[dict[str, str]]) -> str:
    if not findings:
        return "PASS: no configured Terraform plan risks detected"

    summary = summarize(findings)
    lines = [
        f"FLAGGED: {len(findings)} Terraform plan risk issue(s)",
        f"Risk summary: high={summary['high']} medium={summary['medium']} low={summary['low']}",
    ]
    for finding in findings:
        lines.append(
            f"[{finding['severity'].upper()}] {finding['code']} {finding['address']} - {finding['message']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = load_plan(args.plan)
    findings = analyze_plan(plan)

    if args.format == "json":
        print(json.dumps({"findings": findings, "summary": summarize(findings)}, indent=2))
    else:
        print(render_text(findings))

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
