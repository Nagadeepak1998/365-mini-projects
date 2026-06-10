from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass(frozen=True)
class SignalRule:
    name: str
    category: str
    severity: str
    patterns: tuple[str, ...]
    recommendation: str


@dataclass(frozen=True)
class Evidence:
    line_number: int
    line: str
    rule: str
    category: str
    severity: str


RULES: tuple[SignalRule, ...] = (
    SignalRule(
        name="kubernetes_restart_loop",
        category="kubernetes",
        severity="high",
        patterns=(r"\bCrashLoopBackOff\b", r"back-off restarting failed container"),
        recommendation="Check recent deploys, container command changes, and pod events with kubectl describe pod.",
    ),
    SignalRule(
        name="memory_pressure",
        category="resources",
        severity="high",
        patterns=(r"\bOOMKilled\b", r"out of memory", r"exit code 137", r"memory limit exceeded"),
        recommendation="Review memory limits, recent traffic, heap usage, and restart counts before scaling.",
    ),
    SignalRule(
        name="image_pull_failure",
        category="kubernetes",
        severity="high",
        patterns=(r"\bImagePullBackOff\b", r"\bErrImagePull\b", r"pull access denied", r"manifest unknown"),
        recommendation="Verify image name, tag, registry credentials, and imagePullSecrets.",
    ),
    SignalRule(
        name="probe_failure",
        category="kubernetes",
        severity="high",
        patterns=(r"readiness probe failed", r"liveness probe failed", r"progress deadline exceeded"),
        recommendation="Inspect health endpoint behavior, startup time, dependency availability, and rollout history.",
    ),
    SignalRule(
        name="tls_certificate_failure",
        category="network_tls",
        severity="high",
        patterns=(r"SSLHandshakeException", r"handshake_failure", r"certificate verify failed", r"x509:", r"\bTLS\b"),
        recommendation="Validate certificate chain, trust store, SNI, protocol versions, and load balancer TLS policy.",
    ),
    SignalRule(
        name="dns_or_network_timeout",
        category="network",
        severity="high",
        patterns=(r"no such host", r"temporary failure in name resolution", r"\bDNS\b", r"i/o timeout", r"timed out"),
        recommendation="Check DNS, service endpoints, firewall rules, network policies, and upstream health.",
    ),
    SignalRule(
        name="connection_refused",
        category="network",
        severity="high",
        patterns=(r"connection refused", r"\bECONNREFUSED\b", r"upstream connect error"),
        recommendation="Confirm the target service is running, listening on the expected port, and reachable from the caller.",
    ),
    SignalRule(
        name="authorization_failure",
        category="auth",
        severity="high",
        patterns=(r"\b401\b", r"\b403\b", r"unauthorized", r"forbidden", r"permission denied", r"\bRBAC\b"),
        recommendation="Check service account permissions, token freshness, Vault/Kubernetes auth role bindings, and IAM policy.",
    ),
    SignalRule(
        name="secret_exposure_risk",
        category="security",
        severity="critical",
        patterns=(r"BEGIN PRIVATE KEY", r"\bapi[_-]?key\s*=", r"\bpassword\s*=", r"\btoken\s*="),
        recommendation="Treat exposed credentials as compromised, rotate them, and remove secrets from logs.",
    ),
    SignalRule(
        name="database_failure",
        category="database",
        severity="high",
        patterns=(r"deadlock detected", r"connection pool exhausted", r"database.*unavailable", r"could not connect to .*database"),
        recommendation="Inspect database availability, connection pool limits, slow queries, locks, and failover events.",
    ),
    SignalRule(
        name="rate_limit",
        category="throttling",
        severity="medium",
        patterns=(r"\b429\b", r"rate limit", r"too many requests", r"throttl"),
        recommendation="Add retry with backoff, reduce request bursts, and verify upstream quota limits.",
    ),
    SignalRule(
        name="test_or_runtime_failure",
        category="application",
        severity="medium",
        patterns=(r"\bERROR\b", r"\bException\b", r"Traceback", r"AssertionError", r"failed test"),
        recommendation="Open the first failing stack trace or test assertion and compare with the last code/config change.",
    ),
)


def analyze_log(text: str, source: str = "stdin", max_evidence_per_rule: int = 3) -> dict:
    lines = _meaningful_lines(text)
    evidence = _collect_evidence(lines, max_evidence_per_rule)
    categories = _summarize_categories(evidence)
    severity = _classify_severity(evidence)

    return {
        "source": source,
        "line_count": len(lines),
        "time_window": _extract_time_window(lines),
        "severity": severity,
        "probable_cause": _probable_cause(categories),
        "categories": categories,
        "evidence": [item.__dict__ for item in evidence],
        "action_items": _action_items(categories),
    }


def format_markdown(report: dict) -> str:
    category_rows = _format_category_rows(report["categories"])
    evidence_rows = _format_evidence_rows(report["evidence"])
    action_rows = "\n".join(f"- {item}" for item in report["action_items"])

    return "\n".join(
        [
            f"# Incident Summary: {report['source']}",
            "",
            f"- Severity: **{report['severity'].upper()}**",
            f"- Lines analyzed: `{report['line_count']}`",
            f"- Time window: `{report['time_window']}`",
            f"- Probable cause: {report['probable_cause']}",
            "",
            "## Signals",
            "",
            category_rows,
            "",
            "## Evidence",
            "",
            evidence_rows,
            "",
            "## Recommended Actions",
            "",
            action_rows,
            "",
        ]
    )


def _meaningful_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def _collect_evidence(lines: Iterable[str], max_evidence_per_rule: int) -> list[Evidence]:
    evidence: list[Evidence] = []
    rule_counts: dict[str, int] = {}

    for line_number, line in enumerate(lines, start=1):
        for rule in RULES:
            if rule_counts.get(rule.name, 0) >= max_evidence_per_rule:
                continue
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in rule.patterns):
                evidence.append(
                    Evidence(
                        line_number=line_number,
                        line=line.strip(),
                        rule=rule.name,
                        category=rule.category,
                        severity=rule.severity,
                    )
                )
                rule_counts[rule.name] = rule_counts.get(rule.name, 0) + 1
                break

    return evidence


def _summarize_categories(evidence: list[Evidence]) -> list[dict]:
    by_category: dict[str, dict] = {}

    for item in evidence:
        current = by_category.setdefault(
            item.category,
            {"category": item.category, "count": 0, "severity": item.severity, "rules": set()},
        )
        current["count"] += 1
        current["rules"].add(item.rule)
        if SEVERITY_ORDER[item.severity] > SEVERITY_ORDER[current["severity"]]:
            current["severity"] = item.severity

    categories = []
    for item in by_category.values():
        categories.append(
            {
                "category": item["category"],
                "count": item["count"],
                "severity": item["severity"],
                "rules": sorted(item["rules"]),
            }
        )

    return sorted(categories, key=lambda item: (-SEVERITY_ORDER[item["severity"]], -item["count"], item["category"]))


def _classify_severity(evidence: list[Evidence]) -> str:
    if not evidence:
        return "low"

    max_rank = max(SEVERITY_ORDER[item.severity] for item in evidence)
    high_or_above = sum(1 for item in evidence if SEVERITY_ORDER[item.severity] >= SEVERITY_ORDER["high"])
    if max_rank >= SEVERITY_ORDER["critical"] or high_or_above >= 5:
        return "critical"
    if max_rank >= SEVERITY_ORDER["high"]:
        return "high"
    return "medium"


def _probable_cause(categories: list[dict]) -> str:
    if not categories:
        return "No high-confidence failure pattern was detected. Review recent deploys and upstream dependencies."

    top = categories[0]
    labels = {
        "kubernetes": "Kubernetes workload health or rollout failure",
        "resources": "resource pressure, likely memory-related",
        "network_tls": "TLS or certificate negotiation failure",
        "network": "network reachability, DNS, or upstream availability failure",
        "auth": "authorization or identity configuration failure",
        "security": "possible credential exposure in logs",
        "database": "database connectivity or contention failure",
        "throttling": "upstream rate limiting or quota pressure",
        "application": "application runtime or test failure",
    }
    return labels.get(top["category"], f"{top['category']} issue")


def _action_items(categories: list[dict]) -> list[str]:
    if not categories:
        return [
            "Compare the log timestamp with the latest deploy, config change, and dependency alerts.",
            "Re-run with a wider log window if the failure boundary is not visible.",
        ]

    actions: list[str] = []
    for category in categories:
        matching_rules = [rule for rule in RULES if rule.category == category["category"]]
        for rule in matching_rules:
            if rule.name in category["rules"] and rule.recommendation not in actions:
                actions.append(rule.recommendation)

    actions.append("Capture the exact failing command, pod name, commit SHA, or request ID before handing off.")
    return actions


def _extract_time_window(lines: list[str]) -> str:
    timestamps: list[str] = []
    timestamp_pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2}[T ][0-9:.]+Z?|\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
    )

    for line in lines:
        match = timestamp_pattern.search(line)
        if match:
            timestamps.append(match.group(1))

    if not timestamps:
        return "not detected"
    if timestamps[0] == timestamps[-1]:
        return timestamps[0]
    return f"{timestamps[0]} to {timestamps[-1]}"


def _format_category_rows(categories: list[dict]) -> str:
    if not categories:
        return "No failure signals detected."

    rows = ["| Category | Severity | Evidence Count | Rules |", "|---|---:|---:|---|"]
    for item in categories:
        rows.append(
            f"| {item['category']} | {item['severity']} | {item['count']} | {', '.join(item['rules'])} |"
        )
    return "\n".join(rows)


def _format_evidence_rows(evidence: list[dict]) -> str:
    if not evidence:
        return "No matching evidence lines were found."

    rows = ["| Line | Category | Evidence |", "|---:|---|---|"]
    for item in evidence:
        line = item["line"].replace("|", "\\|")
        rows.append(f"| {item['line_number']} | {item['category']} | `{line}` |")
    return "\n".join(rows)
