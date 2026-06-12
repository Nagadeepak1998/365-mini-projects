#!/usr/bin/env python3
"""Check whether an AI-generated incident runbook stays grounded."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    category: str
    label: str
    detail: str


def load_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON policy: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Unable to read policy file: {exc}") from exc

    if not isinstance(policy, dict):
        raise ValueError("Policy must be a JSON object")
    return policy


def _contains_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def _matching_evidence_terms(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def _first_pattern_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(0).strip()
    return None


def scan_response(policy: dict[str, Any], response_text: str) -> list[Finding]:
    findings: list[Finding] = []

    for action in policy.get("required_actions", []):
        label = str(action.get("label", "Unnamed required action"))
        phrases = [str(item) for item in action.get("any", [])]
        if phrases and not _contains_any(response_text, phrases):
            findings.append(
                Finding(
                    "missing_required_action",
                    label,
                    "Expected one of: " + ", ".join(phrases),
                )
            )

    evidence_terms = [str(term) for term in policy.get("evidence_terms", [])]
    min_evidence_terms = int(policy.get("min_evidence_terms", 0))
    matched_terms = _matching_evidence_terms(response_text, evidence_terms)
    if min_evidence_terms and len(matched_terms) < min_evidence_terms:
        findings.append(
            Finding(
                "insufficient_evidence",
                "Too few incident-specific evidence terms",
                f"Found {len(matched_terms)} of required {min_evidence_terms}: "
                + (", ".join(matched_terms) if matched_terms else "none"),
            )
        )

    for claim in policy.get("forbidden_claims", []):
        label = str(claim.get("label", "Forbidden claim"))
        patterns = [str(item) for item in claim.get("patterns", [])]
        matched = _first_pattern_match(response_text, patterns)
        if matched:
            findings.append(Finding("unsupported_claim", label, f"Matched: {matched}"))

    for action in policy.get("risky_actions", []):
        label = str(action.get("label", "Risky action"))
        patterns = [str(item) for item in action.get("patterns", [])]
        matched = _first_pattern_match(response_text, patterns)
        if matched:
            findings.append(Finding("risky_action", label, f"Matched: {matched}"))

    return findings


def build_summary(policy: dict[str, Any], response_text: str, findings: list[Finding]) -> dict[str, Any]:
    evidence_terms = [str(term) for term in policy.get("evidence_terms", [])]
    matched_terms = _matching_evidence_terms(response_text, evidence_terms)
    return {
        "scenario": policy.get("scenario", "Unnamed scenario"),
        "passed": not findings,
        "finding_count": len(findings),
        "matched_evidence_terms": matched_terms,
        "findings": [asdict(finding) for finding in findings],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check an AI-generated incident runbook for missing actions, weak grounding, and risky claims."
    )
    parser.add_argument("response_file", type=Path, help="Markdown or text file containing the AI runbook response")
    parser.add_argument("--policy", required=True, type=Path, help="JSON policy with required actions and risk rules")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        policy = load_policy(args.policy)
        response_text = args.response_file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Unable to read response file: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    findings = scan_response(policy, response_text)
    summary = build_summary(policy, response_text, findings)

    if args.format == "json":
        print(json.dumps(summary, indent=2))
    elif findings:
        print(f"FLAGGED: {len(findings)} issue(s)")
        for finding in findings:
            print(f"- {finding.category}: {finding.label} - {finding.detail}")
    else:
        print("PASS: runbook response is grounded enough for review")
        terms = ", ".join(summary["matched_evidence_terms"]) or "none"
        print(f"Evidence terms found: {terms}")

    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
