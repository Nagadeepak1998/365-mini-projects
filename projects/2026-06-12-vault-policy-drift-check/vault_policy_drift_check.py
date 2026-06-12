#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

PATH_BLOCK_RE = re.compile(
    r'path\s+"(?P<path>[^"]+)"\s*\{(?P<body>.*?)\}',
    re.DOTALL | re.IGNORECASE,
)
CAPABILITIES_RE = re.compile(
    r"capabilities\s*=\s*\[(?P<values>[^\]]*)\]",
    re.IGNORECASE,
)
QUOTED_VALUE_RE = re.compile(r'"([^"]+)"')
HIGH_RISK_CAPABILITIES = {"create", "update", "patch", "delete", "sudo"}


@dataclass(frozen=True)
class Rule:
    path_glob: str
    forbidden_capabilities: set[str]
    note: str


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Vault ACL policy drift against a baseline policy and guardrails."
    )
    parser.add_argument("candidate", help="Candidate Vault policy file to review.")
    parser.add_argument(
        "--baseline",
        required=True,
        help="Baseline Vault policy file that represents the currently approved access.",
    )
    parser.add_argument(
        "--rules",
        help="Optional JSON file with extra guardrail rules.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args()


def load_policy(path: Path) -> dict[str, set[str]]:
    text = path.read_text(encoding="utf-8")
    mapping: dict[str, set[str]] = {}

    for match in PATH_BLOCK_RE.finditer(text):
        raw_path = match.group("path").strip()
        body = match.group("body")
        capabilities_match = CAPABILITIES_RE.search(body)
        if not capabilities_match:
            continue
        capabilities = {
            value.strip().lower()
            for value in QUOTED_VALUE_RE.findall(capabilities_match.group("values"))
        }
        if capabilities:
            mapping[raw_path] = capabilities

    return mapping


def load_rules(path: Path | None) -> list[Rule]:
    default_rules = [
        Rule("sys/*", {"create", "update", "patch", "delete", "sudo"}, "system paths should not gain write-like access"),
        Rule("auth/*", {"create", "update", "patch", "delete", "sudo"}, "auth paths are sensitive and should stay tightly scoped"),
        Rule("identity/*", {"create", "update", "patch", "delete", "sudo"}, "identity paths should avoid broad mutation rights"),
        Rule("secret/data/prod/*", {"create", "update", "patch", "delete"}, "production secrets should not gain write/delete in app-reader policies"),
    ]
    if path is None:
        return default_rules

    payload = json.loads(path.read_text(encoding="utf-8"))
    rules = list(default_rules)
    for item in payload.get("forbidden_path_rules", []):
        rules.append(
            Rule(
                path_glob=item["path_glob"],
                forbidden_capabilities={cap.lower() for cap in item["forbidden_capabilities"]},
                note=item["note"],
            )
        )
    return rules


def find_matching_baseline(path: str, baseline_paths: set[str]) -> str | None:
    if path in baseline_paths:
        return path
    for baseline_path in sorted(baseline_paths):
        if "*" in baseline_path and fnmatchcase(path, baseline_path):
            return baseline_path
    return None


def analyze(
    baseline: dict[str, set[str]],
    candidate: dict[str, set[str]],
    rules: list[Rule],
) -> list[Finding]:
    findings: list[Finding] = []
    baseline_paths = set(baseline)

    for path, capabilities in sorted(candidate.items()):
        baseline_path = find_matching_baseline(path, baseline_paths)
        baseline_capabilities = baseline.get(baseline_path, set()) if baseline_path else set()

        added_capabilities = capabilities - baseline_capabilities
        if added_capabilities:
            findings.append(
                Finding(
                    "capability-expansion",
                    path,
                    f"candidate adds capabilities {sorted(added_capabilities)} compared with baseline path {baseline_path or 'none'}",
                )
            )

        if baseline_path is None and any(cap in HIGH_RISK_CAPABILITIES for cap in capabilities):
            findings.append(
                Finding(
                    "new-write-path",
                    path,
                    "candidate introduces a new path with write-like access that does not exist in baseline",
                )
            )

        if "*" in path and any(cap in HIGH_RISK_CAPABILITIES for cap in capabilities):
            findings.append(
                Finding(
                    "wildcard-write",
                    path,
                    "wildcard path grants write-like capabilities",
                )
            )

        for rule in rules:
            if fnmatchcase(path, rule.path_glob):
                blocked = sorted(capabilities & rule.forbidden_capabilities)
                if blocked:
                    findings.append(
                        Finding(
                            "forbidden-capability",
                            path,
                            f"{rule.note}; found {blocked}",
                        )
                    )

    for path, capabilities in sorted(baseline.items()):
        candidate_capabilities = candidate.get(path)
        if candidate_capabilities is None:
            findings.append(
                Finding(
                    "missing-baseline-path",
                    path,
                    "candidate removes a baseline path block; verify this is intentional",
                )
            )
            continue

        removed_capabilities = capabilities - candidate_capabilities
        if removed_capabilities:
            findings.append(
                Finding(
                    "capability-removal",
                    path,
                    f"candidate removes baseline capabilities {sorted(removed_capabilities)}",
                )
            )

    return findings


def as_json(candidate_path: Path, baseline_path: Path, findings: list[Finding]) -> str:
    payload = {
        "candidate": str(candidate_path),
        "baseline": str(baseline_path),
        "status": "flagged" if findings else "pass",
        "finding_count": len(findings),
        "findings": [
            {"code": finding.code, "path": finding.path, "detail": finding.detail}
            for finding in findings
        ],
    }
    return json.dumps(payload, indent=2)


def as_text(findings: list[Finding]) -> str:
    if not findings:
        return "PASS: no risky Vault policy drift detected"

    lines = [f"FLAGGED: {len(findings)} issue(s)"]
    for finding in findings:
        lines.append(f"- [{finding.code}] {finding.path}: {finding.detail}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    candidate_path = Path(args.candidate)
    baseline_path = Path(args.baseline)
    rules_path = Path(args.rules) if args.rules else None

    baseline = load_policy(baseline_path)
    candidate = load_policy(candidate_path)
    rules = load_rules(rules_path)
    findings = analyze(baseline, candidate, rules)

    if args.format == "json":
        print(as_json(candidate_path, baseline_path, findings))
    else:
        print(as_text(findings))

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
