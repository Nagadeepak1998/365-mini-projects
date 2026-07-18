#!/usr/bin/env python3
"""Calculate Kubernetes replica headroom for a projected traffic level."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def build_plan(service: dict[str, Any]) -> dict[str, Any]:
    required = {
        "name",
        "current_rps",
        "growth_percent",
        "safe_rps_per_pod",
        "current_replicas",
        "hpa_max_replicas",
        "largest_node_pod_count",
    }
    missing = sorted(required - service.keys())
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    name = service["name"]
    current_rps = service["current_rps"]
    growth_percent = service["growth_percent"]
    safe_rps_per_pod = service["safe_rps_per_pod"]
    current_replicas = service["current_replicas"]
    hpa_max_replicas = service["hpa_max_replicas"]
    node_reserve = service["largest_node_pod_count"]

    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    numeric_values = {
        "current_rps": current_rps,
        "growth_percent": growth_percent,
        "safe_rps_per_pod": safe_rps_per_pod,
    }
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in numeric_values.values()):
        raise ValueError("traffic values must be numbers")
    if current_rps < 0 or growth_percent < 0 or safe_rps_per_pod <= 0:
        raise ValueError("traffic values must be non-negative and safe_rps_per_pod must be positive")
    replica_values = {
        "current_replicas": current_replicas,
        "hpa_max_replicas": hpa_max_replicas,
        "largest_node_pod_count": node_reserve,
    }
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in replica_values.values()):
        raise ValueError("replica values must be non-negative integers")
    if current_replicas == 0 or hpa_max_replicas == 0:
        raise ValueError("current_replicas and hpa_max_replicas must be positive")

    projected_rps = current_rps * (1 + growth_percent / 100)
    traffic_replicas = max(1, math.ceil(projected_rps / safe_rps_per_pod))
    recommended_replicas = traffic_replicas + node_reserve
    current_gap = max(0, recommended_replicas - current_replicas)
    hpa_gap = max(0, recommended_replicas - hpa_max_replicas)

    if hpa_gap:
        status = "BLOCKED"
        action = f"raise HPA max by at least {hpa_gap} replica(s) or reduce the traffic assumption"
    elif current_gap:
        status = "SCALE"
        action = f"scale by {current_gap} replica(s); the existing HPA ceiling can support the plan"
    else:
        status = "READY"
        action = "current replicas and the HPA ceiling cover the projected load and node-loss reserve"

    return {
        "service": name,
        "status": status,
        "projected_rps": round(projected_rps, 2),
        "traffic_replicas": traffic_replicas,
        "node_loss_reserve": node_reserve,
        "recommended_replicas": recommended_replicas,
        "current_replicas": current_replicas,
        "hpa_max_replicas": hpa_max_replicas,
        "current_gap": current_gap,
        "hpa_gap": hpa_gap,
        "action": action,
    }


def render_text(plan: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"{plan['status']}: {plan['service']}",
            f"Projected load: {plan['projected_rps']} RPS",
            f"Traffic replicas: {plan['traffic_replicas']}",
            f"Node-loss reserve: {plan['node_loss_reserve']}",
            f"Recommended replicas: {plan['recommended_replicas']}",
            f"Current / HPA max: {plan['current_replicas']} / {plan['hpa_max_replicas']}",
            f"Action: {plan['action']}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON file containing one service capacity snapshot")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    try:
        service = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(service, dict):
            raise ValueError("input must be a JSON object")
        plan = build_plan(service)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(plan, indent=2, sort_keys=True) if args.json else render_text(plan))
    return 1 if plan["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
