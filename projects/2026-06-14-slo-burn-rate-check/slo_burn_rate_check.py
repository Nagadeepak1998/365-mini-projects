#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_THRESHOLDS = {
    "5m": 14.0,
    "30m": 6.0,
    "1h": 14.0,
    "6h": 6.0,
}
DEFAULT_BUDGET_DAYS = 30


@dataclass(frozen=True)
class WindowObservation:
    name: str
    requests: int
    errors: int
    burn_rate_threshold: float

    @property
    def error_rate(self) -> float:
        return 0.0 if self.requests == 0 else self.errors / self.requests


@dataclass(frozen=True)
class WindowResult:
    name: str
    requests: int
    errors: int
    error_rate: float
    allowed_error_rate: float
    burn_rate: float
    burn_rate_threshold: float
    budget_exhaustion_days: float | None
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check SLO error-budget burn rate from a JSON snapshot."
    )
    parser.add_argument("snapshot", help="Path to the SLO snapshot JSON file.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--budget-days",
        type=int,
        default=DEFAULT_BUDGET_DAYS,
        help="Error-budget period in days. Default: 30.",
    )
    return parser.parse_args()


def load_snapshot(path: Path) -> tuple[str, float, list[WindowObservation]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    service = payload["service"]
    slo_target = float(payload["slo_target"])
    thresholds = payload.get("thresholds", {})
    observations: list[WindowObservation] = []

    for window in payload["windows"]:
        name = window["name"]
        threshold = float(thresholds.get(name, DEFAULT_THRESHOLDS.get(name, 2.0)))
        observations.append(
            WindowObservation(
                name=name,
                requests=int(window["requests"]),
                errors=int(window["errors"]),
                burn_rate_threshold=threshold,
            )
        )

    return service, slo_target, observations


def analyze(
    service: str,
    slo_target: float,
    observations: list[WindowObservation],
    budget_days: int,
) -> dict[str, object]:
    allowed_error_rate = 1 - (slo_target / 100)
    results: list[WindowResult] = []

    for observation in observations:
        burn_rate = 0.0 if allowed_error_rate <= 0 else observation.error_rate / allowed_error_rate
        if burn_rate <= 0:
            budget_exhaustion_days = None
        else:
            budget_exhaustion_days = budget_days / burn_rate

        status = "alert" if burn_rate >= observation.burn_rate_threshold else "ok"
        results.append(
            WindowResult(
                name=observation.name,
                requests=observation.requests,
                errors=observation.errors,
                error_rate=observation.error_rate,
                allowed_error_rate=allowed_error_rate,
                burn_rate=burn_rate,
                burn_rate_threshold=observation.burn_rate_threshold,
                budget_exhaustion_days=budget_exhaustion_days,
                status=status,
            )
        )

    alert_count = sum(1 for result in results if result.status == "alert")
    return {
        "service": service,
        "slo_target": slo_target,
        "allowed_error_rate": allowed_error_rate,
        "budget_days": budget_days,
        "status": "flagged" if alert_count else "pass",
        "alert_count": alert_count,
        "results": results,
    }


def format_days(value: float | None) -> str:
    if value is None or math.isinf(value):
        return "never at current rate"
    return f"{value:.2f} day(s)"


def as_text(summary: dict[str, object]) -> str:
    if summary["status"] == "pass":
        header = "PASS: no burn-rate alerts crossed the configured thresholds"
    else:
        header = f"FLAGGED: {summary['alert_count']} burn-rate alert(s)"

    lines = [
        header,
        (
            f"Service: {summary['service']} | SLO: {float(summary['slo_target']):.3f}% | "
            f"Allowed error rate: {float(summary['allowed_error_rate']) * 100:.3f}%"
        ),
    ]
    budget_days = int(summary["budget_days"])

    for result in summary["results"]:
        window_result = result
        lines.append(
            (
                f"- [{window_result.status}] {window_result.name}: "
                f"errors={window_result.errors}/{window_result.requests} "
                f"({window_result.error_rate * 100:.3f}%), "
                f"burn rate={window_result.burn_rate:.2f}x "
                f"(threshold {window_result.burn_rate_threshold:.2f}x), "
                f"{budget_days}-day budget exhausts in {format_days(window_result.budget_exhaustion_days)}"
            )
        )

    return "\n".join(lines)


def as_json(summary: dict[str, object]) -> str:
    payload = {
        "service": summary["service"],
        "slo_target": summary["slo_target"],
        "allowed_error_rate": summary["allowed_error_rate"],
        "budget_days": summary["budget_days"],
        "status": summary["status"],
        "alert_count": summary["alert_count"],
        "results": [
            {
                "name": result.name,
                "requests": result.requests,
                "errors": result.errors,
                "error_rate": round(result.error_rate, 6),
                "burn_rate": round(result.burn_rate, 4),
                "burn_rate_threshold": result.burn_rate_threshold,
                "budget_exhaustion_days": (
                    None
                    if result.budget_exhaustion_days is None
                    else round(result.budget_exhaustion_days, 4)
                ),
                "status": result.status,
            }
            for result in summary["results"]
        ],
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    args = parse_args()
    service, slo_target, observations = load_snapshot(Path(args.snapshot))
    summary = analyze(service, slo_target, observations, budget_days=args.budget_days)

    if args.format == "json":
        print(as_json(summary))
    else:
        print(as_text(summary))

    return 1 if summary["status"] == "flagged" else 0


if __name__ == "__main__":
    sys.exit(main())
