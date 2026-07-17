#!/usr/bin/env python3
"""Review release artifacts for software supply-chain provenance evidence."""

import argparse
import json
import sys
from pathlib import Path


def review_artifact(artifact):
    name = artifact.get("name") or "<unnamed>"
    findings = []

    def flag(code, message):
        findings.append({"artifact": name, "code": code, "message": message})

    if not artifact.get("owner"):
        flag("missing-owner", "release artifact has no owner")
    digest = artifact.get("digest", "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        flag("invalid-digest", "artifact must use a full sha256 digest")
    if not artifact.get("sbom", {}).get("present"):
        flag("missing-sbom", "artifact has no SBOM")
    elif artifact.get("sbom", {}).get("format") not in {"cyclonedx", "spdx"}:
        flag("unsupported-sbom", "SBOM format must be CycloneDX or SPDX")
    if not artifact.get("signature", {}).get("verified"):
        flag("unverified-signature", "artifact signature was not verified")

    provenance = artifact.get("provenance", {})
    if not provenance.get("verified"):
        flag("unverified-provenance", "build provenance was not verified")
    if not provenance.get("source_repository"):
        flag("missing-source", "provenance does not identify a source repository")
    if not provenance.get("source_revision"):
        flag("missing-revision", "provenance does not identify a source revision")
    if artifact.get("environment") == "production" and not artifact.get("promotion", {}).get("digest_matched"):
        flag("promotion-digest-mismatch", "production promotion lacks a verified digest match")

    return findings


def review_inventory(data):
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("inventory must contain a non-empty 'artifacts' list")
    return [finding for artifact in artifacts for finding in review_artifact(artifact)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path, help="JSON release artifact inventory")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()

    try:
        data = json.loads(args.inventory.read_text())
        findings = review_inventory(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"status": "flagged" if findings else "pass", "findings": findings}, indent=2))
    elif findings:
        print(f"FLAGGED: {len(findings)} release artifact provenance issue(s) detected")
        for finding in findings:
            print(f"- [{finding['code']}] {finding['artifact']}: {finding['message']}")
    else:
        print("PASS: release artifacts have verified provenance evidence")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
