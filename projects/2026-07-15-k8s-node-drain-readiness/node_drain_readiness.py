#!/usr/bin/env python3
"""Decide whether a Kubernetes node is ready for a planned drain."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Blocker:
    code: str
    pod: str
    message: str


def review_snapshot(payload: Any) -> list[Blocker]:
    if not isinstance(payload, dict) or not isinstance(payload.get("pods"), list):
        raise ValueError("input must be an object containing a pods list")
    if not isinstance(payload.get("node"), str) or not payload["node"].strip():
        raise ValueError("node must be a non-empty string")

    blockers: list[Blocker] = []
    seen: set[tuple[str, str]] = set()

    for pod in payload["pods"]:
        if not isinstance(pod, dict):
            raise ValueError("each pods entry must be an object")
        namespace = pod.get("namespace")
        name = pod.get("name")
        if not isinstance(namespace, str) or not namespace.strip() or not isinstance(name, str) or not name.strip():
            raise ValueError("each pod must have non-empty namespace and name strings")
        identity = (namespace, name)
        if identity in seen:
            raise ValueError(f"duplicate pod: {namespace}/{name}")
        seen.add(identity)
        display = f"{namespace}/{name}"

        def add(code: str, message: str) -> None:
            blockers.append(Blocker(code, display, message))

        owner_kind = pod.get("owner_kind")
        if owner_kind in {"DaemonSet", "MirrorPod"}:
            continue
        if owner_kind in {None, ""}:
            add("unmanaged-pod", "pod has no controller to recreate it")
        if pod.get("safe_to_evict") is False:
            add("eviction-disabled", "pod is explicitly marked unsafe to evict")
        if pod.get("uses_local_storage") is True and pod.get("local_data_disposable") is not True:
            add("local-data-risk", "pod uses local storage without disposable-data confirmation")

        replicas = pod.get("controller_replicas")
        if owner_kind not in {None, "", "Job"}:
            if not isinstance(replicas, int) or isinstance(replicas, bool) or replicas < 1:
                raise ValueError(f"{display}.controller_replicas must be a positive integer")
            if replicas == 1:
                add("single-replica", "controller has no second replica during eviction")
            if replicas > 1 and pod.get("pdb_allows_eviction") is not True:
                add("pdb-blocks-eviction", "disruption budget does not currently allow eviction")
            ready_elsewhere = pod.get("ready_replicas_elsewhere")
            if not isinstance(ready_elsewhere, int) or isinstance(ready_elsewhere, bool) or ready_elsewhere < 0:
                raise ValueError(f"{display}.ready_replicas_elsewhere must be a non-negative integer")
            if ready_elsewhere < 1:
                add("no-ready-replacement", "no ready replica is running on another node")

    return sorted(blockers, key=lambda item: (item.pod, item.code))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="path to the node snapshot JSON file")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.snapshot.read_text(encoding="utf-8"))
        blockers = review_snapshot(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps({"ready": not blockers, "blocker_count": len(blockers), "blockers": [asdict(item) for item in blockers]}, indent=2))
    elif blockers:
        for blocker in blockers:
            print(f"[BLOCK] {blocker.pod} {blocker.code}: {blocker.message}")
        print(f"STOP: node drain has {len(blockers)} blocker(s)")
    else:
        print("READY: node can be drained with the reviewed workload state")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
