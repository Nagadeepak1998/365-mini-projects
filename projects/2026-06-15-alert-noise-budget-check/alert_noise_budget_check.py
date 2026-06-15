#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AlertSample:
    name: str
    severity: str
    pages: int
    unique_incidents: int
    acknowledged_pages: int
    actionable_pages: int


@dataclass(frozen=True)
class Finding:
    code: str
    alert_name: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review alert history and flag noisy alerts that page too often without enough action."
    )
    parser.add_argument("snapshot", help="Path to the JSON alert history snapshot.")
    parser.add_argument(
        "--page-threshold",
        type=int,
        default=5,
        help="Minimum page count before an alert is considered for noise checks.",
    )
    parser.add_argument(
        "--min-actionable-rate",
        type=float,
        default=0.5,
        help="Minimum actionable-page rate required once an alert crosses the page threshold.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args()


def load_snapshot(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_alert(entry: dict[str, object]) -> AlertSample:
    return AlertSample(
        name=str(entry["name"]),
        severity=str(entry.get("severity", "page")),
        pages=int(entry["pages"]),
        unique_incidents=int(entry["unique_incidents"]),
        acknowledged_pages=int(entry["acknowledged_pages"]),
        actionable_pages=int(entry["actionable_pages"]),
    )


def actionable_rate(alert: AlertSample) -> float:
    if alert.pages == 0:
        return 0.0
    return alert.actionable_pages / alert.pages


def duplicate_ratio(alert: AlertSample) -> float:
    if alert.unique_incidents == 0:
        return float(alert.pages) if alert.pages else 0.0
    return alert.pages / alert.unique_incidents


def acknowledgement_rate(alert: AlertSample) -> float:
    if alert.pages == 0:
        return 0.0
    return alert.acknowledged_pages / alert.pages


def analyze(
    alerts: list[AlertSample],
    page_threshold: int,
    min_actionable_rate: float,
) -> list[Finding]:
    findings: list[Finding] = []

    for alert in sorted(alerts, key=lambda item: item.name):
        if alert.severity != "page":
            continue

        rate = actionable_rate(alert)
        duplicates = duplicate_ratio(alert)
        ack_rate = acknowledgement_rate(alert)

        if alert.pages >= page_threshold and rate < min_actionable_rate:
            findings.append(
                Finding(
                    code="low-actionability",
                    alert_name=alert.name,
                    detail=(
                        f"{alert.pages} pages but only {alert.actionable_pages} actionable "
                        f"({rate:.0%} actionable rate)"
                    ),
                )
            )

        if alert.pages >= page_threshold and duplicates > 2.0:
            findings.append(
                Finding(
                    code="repeat-pages",
                    alert_name=alert.name,
                    detail=(
                        f"{alert.pages} pages mapped to {alert.unique_incidents} incident(s) "
                        f"({duplicates:.2f} pages per incident)"
                    ),
                )
            )

        if alert.pages >= page_threshold and ack_rate < 0.8:
            findings.append(
                Finding(
                    code="poor-ack-rate",
                    alert_name=alert.name,
                    detail=(
                        f"{alert.acknowledged_pages} of {alert.pages} pages were acknowledged "
                        f"({ack_rate:.0%} acknowledgement rate)"
                    ),
                )
            )

    return findings


def build_summary(snapshot: dict[str, object], alerts: list[AlertSample], findings: list[Finding]) -> dict[str, object]:
    page_alerts = [alert for alert in alerts if alert.severity == "page"]
    total_pages = sum(alert.pages for alert in page_alerts)
    total_actionable = sum(alert.actionable_pages for alert in page_alerts)
    total_incidents = sum(alert.unique_incidents for alert in page_alerts)

    return {
        "service": snapshot.get("service", "unknown"),
        "window": snapshot.get("window", "unknown"),
        "status": "flagged" if findings else "pass",
        "page_alerts": len(page_alerts),
        "total_pages": total_pages,
        "total_actionable_pages": total_actionable,
        "total_unique_incidents": total_incidents,
        "findings": [
            {"code": finding.code, "alert_name": finding.alert_name, "detail": finding.detail}
            for finding in findings
        ],
    }


def as_text(summary: dict[str, object]) -> str:
    if summary["status"] == "pass":
        return (
            "PASS: no page alerts crossed the configured noise thresholds\n"
            f"Service: {summary['service']} | Window: {summary['window']} | "
            f"Pages: {summary['total_pages']} | Actionable pages: {summary['total_actionable_pages']}"
        )

    lines = [
        f"FLAGGED: {len(summary['findings'])} alert-noise issue(s)",
        f"Service: {summary['service']} | Window: {summary['window']}",
    ]
    for finding in summary["findings"]:
        lines.append(f"- [{finding['code']}] {finding['alert_name']}: {finding['detail']}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    snapshot = load_snapshot(Path(args.snapshot))
    alerts = [parse_alert(entry) for entry in snapshot.get("alerts", [])]
    findings = analyze(
        alerts,
        page_threshold=args.page_threshold,
        min_actionable_rate=args.min_actionable_rate,
    )
    summary = build_summary(snapshot, alerts, findings)

    if args.format == "json":
        print(json.dumps(summary, indent=2))
    else:
        print(as_text(summary))

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
