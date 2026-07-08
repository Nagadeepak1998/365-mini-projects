#!/usr/bin/env python3
"""Review TLS certificate inventory for expiry and renewal readiness gaps."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


PRODUCTION_ENVS = {"prod", "production"}
PUBLIC_EXPOSURE = {"public", "internet", "external"}
EXPIRY_HIGH_DAYS = 14
EXPIRY_MEDIUM_DAYS = 30
EXPIRY_LOW_DAYS = 60
STALE_DRILL_DAYS = 365


@dataclass(frozen=True)
class Finding:
    severity: str
    certificate: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.certificate}: {self.message}"


def has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def parse_date(value: Any, field: str, certificate: str) -> date:
    if not has_text(value):
        raise ValueError(f"{certificate}: {field} must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"{certificate}: {field} must be a YYYY-MM-DD string") from exc


def load_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    certificates = raw.get("certificates") if isinstance(raw, dict) else None
    if not isinstance(certificates, list):
        raise ValueError(f"{path}: expected top-level object with a certificates list")

    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, certificate in enumerate(certificates, start=1):
        if not isinstance(certificate, dict):
            raise ValueError(f"{path}: certificates[{index}] must be an object")

        name = certificate.get("common_name")
        if not has_text(name):
            raise ValueError(f"{path}: certificates[{index}] must include a non-empty string common_name")
        label = str(name).strip()
        if label in seen:
            raise ValueError(f"{path}: duplicate certificate common_name {label}")
        seen.add(label)

        parse_date(certificate.get("expires_at"), "expires_at", label)
        parsed.append(certificate)
    return parsed


def optional_date(value: Any) -> date | None:
    if not has_text(value):
        return None
    return date.fromisoformat(str(value).strip())


def integer_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def certificate_label(certificate: dict[str, Any]) -> str:
    return str(certificate["common_name"]).strip()


def is_public_production(certificate: dict[str, Any]) -> bool:
    return (
        normalize_text(certificate.get("environment")) in PRODUCTION_ENVS
        and normalize_text(certificate.get("exposure")) in PUBLIC_EXPOSURE
    )


def review_certificate(certificate: dict[str, Any], today: date) -> list[Finding]:
    findings: list[Finding] = []
    label = certificate_label(certificate)
    if not is_public_production(certificate):
        return findings

    expires_at = parse_date(certificate.get("expires_at"), "expires_at", label)
    days_remaining = (expires_at - today).days

    if not has_text(certificate.get("owner")):
        findings.append(Finding("HIGH", label, "public production certificate is missing an owner"))

    if days_remaining < 0:
        findings.append(Finding("HIGH", label, f"certificate expired {-days_remaining} day(s) ago"))
    elif days_remaining <= EXPIRY_HIGH_DAYS:
        findings.append(Finding("HIGH", label, f"certificate expires in {days_remaining} day(s)"))
    elif days_remaining <= EXPIRY_MEDIUM_DAYS:
        findings.append(Finding("MEDIUM", label, f"certificate expires in {days_remaining} day(s)"))
    elif days_remaining <= EXPIRY_LOW_DAYS:
        findings.append(Finding("LOW", label, f"certificate expires in {days_remaining} day(s)"))

    if days_remaining <= EXPIRY_LOW_DAYS and certificate.get("auto_renew") is not True:
        findings.append(Finding("MEDIUM", label, "certificate is near expiry without auto-renewal enabled"))

    if certificate.get("hostname_match_validated") is not True:
        findings.append(Finding("HIGH", label, "hostname/SAN match has not been validated"))

    if certificate.get("certificate_chain_validated") is not True:
        findings.append(Finding("HIGH", label, "certificate chain validation is missing"))

    if not has_text(certificate.get("renewal_runbook")):
        findings.append(Finding("MEDIUM", label, "renewal runbook is missing"))

    if not has_text(certificate.get("monitoring_alarm")):
        findings.append(Finding("MEDIUM", label, "expiry monitoring alarm is missing"))

    if integer_value(certificate.get("key_size_bits")) < 2048:
        findings.append(Finding("HIGH", label, "key size is below 2048 bits"))

    if "sha1" in normalize_text(certificate.get("signature_algorithm")):
        findings.append(Finding("MEDIUM", label, "signature algorithm uses SHA-1"))

    last_drill = optional_date(certificate.get("last_rotation_drill_at"))
    if last_drill is None:
        findings.append(Finding("LOW", label, "rotation drill date is missing"))
    elif (today - last_drill).days > STALE_DRILL_DAYS:
        findings.append(Finding("LOW", label, "rotation drill is older than one year"))

    return findings


def review_certificates(certificates: list[dict[str, Any]], today: date) -> list[Finding]:
    findings: list[Finding] = []
    for certificate in sorted(certificates, key=certificate_label):
        findings.extend(review_certificate(certificate, today))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review TLS certificate inventory for renewal readiness gaps.")
    parser.add_argument("inventory", type=Path, help="TLS certificate inventory JSON")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(), help="Review date in YYYY-MM-DD")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        certificates = load_inventory(args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = review_certificates(certificates, args.today)
    if not findings:
        print("PASS: TLS certificate inventory looks ready")
        return 0

    print(f"FLAGGED: {len(findings)} TLS certificate readiness issue(s) detected")
    for finding in findings:
        print(f"- {finding.render()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
