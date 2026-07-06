#!/usr/bin/env python3
"""Review CloudFront distribution inventory for production edge safety gaps."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCTION_ENVS = {"prod", "production"}
MODERN_TLS_POLICIES = {"TLSv1.2_2021", "TLSv1.3_2025"}
SAFE_VIEWER_PROTOCOL_POLICIES = {"redirect-to-https", "https-only"}
REQUIRED_ALARMS = {"5xx_error_rate", "origin_latency", "waf_block_spike"}


@dataclass(frozen=True)
class Finding:
    severity: str
    distribution: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.distribution}: {self.message}"


def has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def load_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    distributions = raw.get("distributions") if isinstance(raw, dict) else None
    if not isinstance(distributions, list):
        raise ValueError(f"{path}: expected top-level object with a distributions list")

    seen: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, distribution in enumerate(distributions, start=1):
        if not isinstance(distribution, dict):
            raise ValueError(f"{path}: distributions[{index}] must be an object")
        distribution_id = distribution.get("id")
        if not has_text(distribution_id):
            raise ValueError(f"{path}: distributions[{index}] must include a non-empty string id")
        if distribution_id in seen:
            raise ValueError(f"{path}: duplicate distribution id {distribution_id!r}")
        seen.add(distribution_id)
        parsed.append(distribution)
    return parsed


def behavior_findings(distribution_id: str, distribution: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    behaviors = [("default", distribution.get("default_behavior"))]
    extra_behaviors = distribution.get("cache_behaviors")
    if isinstance(extra_behaviors, list):
        for index, behavior in enumerate(extra_behaviors, start=1):
            label = behavior.get("path_pattern") if isinstance(behavior, dict) else None
            behaviors.append((str(label or f"cache_behavior[{index}]"), behavior))

    for label, behavior in behaviors:
        if not isinstance(behavior, dict):
            findings.append(Finding("HIGH", distribution_id, f"{label} behavior is missing"))
            continue

        protocol_policy = normalize_text(behavior.get("viewer_protocol_policy"))
        if protocol_policy not in SAFE_VIEWER_PROTOCOL_POLICIES:
            findings.append(Finding("HIGH", distribution_id, f"{label} behavior does not enforce HTTPS viewers"))

        if not has_text(behavior.get("response_headers_policy")):
            findings.append(Finding("MEDIUM", distribution_id, f"{label} behavior has no response headers policy"))

    return findings


def configured_alarm_names(distribution: dict[str, Any]) -> set[str]:
    alarms = distribution.get("alarms")
    if not isinstance(alarms, list):
        return set()
    return {normalize_text(alarm.get("name")) for alarm in alarms if isinstance(alarm, dict) and alarm.get("enabled") is True}


def review_distribution(distribution: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    distribution_id = str(distribution["id"])
    production = normalize_text(distribution.get("environment")) in PRODUCTION_ENVS

    if not production:
        return findings

    if not has_text(distribution.get("owner")):
        findings.append(Finding("HIGH", distribution_id, "production distribution is missing an owner"))

    if not has_text(distribution.get("web_acl_id")):
        findings.append(Finding("HIGH", distribution_id, "production distribution has no WAF web ACL"))

    tls_policy = str(distribution.get("minimum_protocol_version") or "").strip()
    if tls_policy not in MODERN_TLS_POLICIES:
        findings.append(Finding("MEDIUM", distribution_id, f"minimum TLS policy is not modern: {tls_policy or 'missing'}"))

    logging = distribution.get("access_logging")
    if not isinstance(logging, dict) or logging.get("enabled") is not True:
        findings.append(Finding("MEDIUM", distribution_id, "access logging is not enabled"))
    elif int(logging.get("retention_days") or 0) < 30:
        findings.append(Finding("LOW", distribution_id, "access log retention is under 30 days"))

    if distribution.get("critical") is True:
        failover = distribution.get("origin_failover")
        if not isinstance(failover, dict) or failover.get("enabled") is not True:
            findings.append(Finding("HIGH", distribution_id, "critical distribution has no origin failover"))

    findings.extend(behavior_findings(distribution_id, distribution))

    missing_alarms = sorted(REQUIRED_ALARMS - configured_alarm_names(distribution))
    if missing_alarms:
        findings.append(Finding("MEDIUM", distribution_id, f"missing enabled alarm(s): {', '.join(missing_alarms)}"))

    return findings


def review_distributions(distributions: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for distribution in sorted(distributions, key=lambda item: str(item["id"])):
        findings.extend(review_distribution(distribution))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review CloudFront distributions for production edge safety gaps.")
    parser.add_argument("inventory", type=Path, help="CloudFront distribution inventory JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        distributions = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_distributions(distributions)
    if not findings:
        print("PASS: CloudFront edge safety looks ready")
        return 0

    print(f"FLAGGED: {len(findings)} CloudFront edge safety issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
