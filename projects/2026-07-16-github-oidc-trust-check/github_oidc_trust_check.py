#!/usr/bin/env python3
"""Review normalized GitHub Actions OIDC trust bindings."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    binding: str
    severity: str
    code: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.binding}: {self.code} - {self.message}"


def check_binding(binding: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    name = str(binding.get("name") or "<unnamed-binding>")
    subjects = binding.get("subjects") or []

    def add(severity: str, code: str, message: str) -> None:
        findings.append(Finding(name, severity, code, message))

    if not binding.get("owner"):
        add("HIGH", "missing-owner", "an accountable owner is not recorded")
    if binding.get("issuer") != "https://token.actions.githubusercontent.com":
        add("HIGH", "invalid-issuer", "issuer must be GitHub Actions' token service")
    if binding.get("audience") != "sts.amazonaws.com":
        add("HIGH", "invalid-audience", "audience must be restricted to AWS STS")
    if not isinstance(subjects, list) or not subjects:
        add("HIGH", "missing-subject", "at least one GitHub subject restriction is required")
        return findings

    environment = str(binding.get("environment") or "").lower()
    for subject in subjects:
        if not isinstance(subject, str):
            raise ValueError(f"subject entries for {name} must be strings")
        if "*" in subject:
            add("CRITICAL", "wildcard-subject", f"wildcard trust is too broad: {subject}")
        if not subject.startswith("repo:") or subject.count(":") < 2:
            add("HIGH", "invalid-subject", f"subject is not repository-scoped: {subject}")
        if ":pull_request" in subject:
            add("HIGH", "pull-request-trust", "pull request workflows must not receive this cloud role")

    if environment == "production" and not any(":environment:production" in subject for subject in subjects):
        add("HIGH", "production-not-environment-bound", "production trust must use the production environment subject")
    if environment == "production" and not binding.get("approval_required"):
        add("HIGH", "missing-production-approval", "production environment approval is not recorded")
    if binding.get("id_token_permission") != "write":
        add("MEDIUM", "invalid-id-token-permission", "workflow id-token permission must be explicitly set to write")
    if binding.get("contents_permission") != "read":
        add("MEDIUM", "broad-contents-permission", "workflow contents permission should be read-only")
    return findings


def load_bindings(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    bindings = payload.get("trust_bindings")
    if not isinstance(bindings, list):
        raise ValueError("input must contain a top-level trust_bindings list")
    if not all(isinstance(item, dict) for item in bindings):
        raise ValueError("each trust binding must be an object")
    return bindings


def review(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for binding in load_bindings(path):
        findings.extend(check_binding(binding))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review GitHub Actions OIDC trust bindings.")
    parser.add_argument("input", type=Path, help="Path to a normalized JSON trust inventory")
    args = parser.parse_args(argv)
    try:
        findings = review(args.input)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not findings:
        print("PASS: GitHub Actions OIDC trust is narrowly scoped")
        return 0
    print(f"FLAGGED: {len(findings)} GitHub Actions OIDC trust issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
