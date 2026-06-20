#!/usr/bin/env python3
"""Review Kubernetes workload snapshots for container image drift risks."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


MUTABLE_TAGS = {"latest", "main", "master", "dev", "develop", "canary", "nightly"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review Kubernetes workload JSON for mutable or drifting images."
    )
    parser.add_argument(
        "snapshot",
        type=Path,
        help="Path to kubectl get deployment,statefulset,daemonset,cronjob -A -o json",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="Output format"
    )
    return parser


def load_snapshot(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def items_from(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    items = snapshot.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return [snapshot] if snapshot else []


def pod_spec_from(item: dict[str, Any]) -> dict[str, Any]:
    spec = item.get("spec", {})
    if not isinstance(spec, dict):
        return {}

    if item.get("kind") == "CronJob":
        spec = (
            spec.get("jobTemplate", {})
            .get("spec", {})
            .get("template", {})
            .get("spec", {})
        )
    else:
        spec = spec.get("template", {}).get("spec", {})

    return spec if isinstance(spec, dict) else {}


def parse_image(image: str) -> dict[str, str | bool]:
    name_part, _, digest = image.partition("@")
    last_segment = name_part.rsplit("/", 1)[-1]
    if ":" in last_segment:
        repository, tag = name_part.rsplit(":", 1)
    else:
        repository, tag = name_part, ""
    return {
        "repository": repository,
        "tag": tag,
        "digest": digest,
        "has_digest": bool(digest),
    }


def make_finding(
    severity: str,
    code: str,
    context: dict[str, str],
    image: str,
    message: str,
) -> dict[str, str]:
    return {
        **context,
        "severity": severity,
        "code": code,
        "image": image,
        "message": message,
    }


def container_findings(
    context: dict[str, str], container: dict[str, Any]
) -> list[dict[str, str]]:
    image = str(container.get("image", "")).strip()
    if not image:
        return [
            make_finding(
                "high",
                "missing-image",
                context,
                "",
                "container does not declare an image",
            )
        ]

    parsed = parse_image(image)
    tag = str(parsed["tag"]).lower()
    pull_policy = str(container.get("imagePullPolicy", "")).strip()
    findings: list[dict[str, str]] = []

    if not parsed["has_digest"]:
        findings.append(
            make_finding(
                "medium",
                "missing-image-digest",
                context,
                image,
                "image is not pinned by digest",
            )
        )

    if not tag and not parsed["has_digest"]:
        findings.append(
            make_finding(
                "high",
                "untagged-image",
                context,
                image,
                "image has no tag or digest",
            )
        )
    elif tag in MUTABLE_TAGS:
        findings.append(
            make_finding(
                "high",
                "mutable-image-tag",
                context,
                image,
                f"image uses mutable tag '{tag}'",
            )
        )

    if tag in MUTABLE_TAGS and pull_policy in {"IfNotPresent", "Never"}:
        findings.append(
            make_finding(
                "medium",
                "mutable-tag-with-sticky-pull-policy",
                context,
                image,
                f"mutable tag uses imagePullPolicy {pull_policy}",
            )
        )

    if parsed["has_digest"] and pull_policy == "Always":
        findings.append(
            make_finding(
                "low",
                "digest-with-always-pull",
                context,
                image,
                "digest-pinned image still uses imagePullPolicy Always",
            )
        )

    return findings


def container_entries(item: dict[str, Any]) -> list[tuple[dict[str, str], dict[str, Any]]]:
    metadata = item.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    base_context = {
        "namespace": str(metadata.get("namespace", "default")),
        "kind": str(item.get("kind", "Unknown")),
        "workload": str(metadata.get("name", "unnamed-workload")),
    }

    entries: list[tuple[dict[str, str], dict[str, Any]]] = []
    pod_spec = pod_spec_from(item)
    for field in ("initContainers", "containers"):
        values = pod_spec.get(field, [])
        if not isinstance(values, list):
            continue
        for container in values:
            if not isinstance(container, dict):
                continue
            context = {
                **base_context,
                "container": str(container.get("name", field)),
            }
            entries.append((context, container))
    return entries


def drift_findings(
    image_usage: dict[str, list[tuple[dict[str, str], str, str]]],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for repository, uses in sorted(image_usage.items()):
        versions = {version for _, _, version in uses if version}
        if len(versions) < 2:
            continue
        message = (
            f"{repository} is deployed with multiple tags or digests "
            f"across the snapshot: {', '.join(sorted(versions))}"
        )
        for context, image, _ in uses:
            findings.append(
                make_finding("medium", "image-version-drift", context, image, message)
            )
    return findings


def collect_findings(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    image_usage: dict[str, list[tuple[dict[str, str], str, str]]] = defaultdict(list)

    for item in items_from(snapshot):
        for context, container in container_entries(item):
            image = str(container.get("image", "")).strip()
            if image:
                parsed = parse_image(image)
                version = str(parsed["digest"] or parsed["tag"])
                image_usage[str(parsed["repository"])].append((context, image, version))
            findings.extend(container_findings(context, container))

    return findings + drift_findings(image_usage)


def render_text(findings: list[dict[str, str]]) -> str:
    if not findings:
        return "PASS: no container image drift risks detected"

    lines = [f"FLAGGED: {len(findings)} container image drift issue(s)"]
    for item in findings:
        lines.append(
            (
                f"- [{item['severity']}] {item['namespace']}/{item['kind']}/"
                f"{item['workload']} :: {item['container']} - "
                f"{item['code']}: {item['message']}"
            )
        )
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    findings = collect_findings(load_snapshot(args.snapshot))
    if args.format == "json":
        print(json.dumps({"findings": findings}, indent=2))
    else:
        print(render_text(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
