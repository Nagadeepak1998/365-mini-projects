#!/usr/bin/env python3
"""Review OpenTelemetry trace sampling plans against coverage and volume budgets."""

import argparse
import json
import sys
from pathlib import Path


def review(plan):
    budget = plan.get("collector_budget_spans_per_second", 0)
    findings = []
    services = []
    total = 0.0

    if not isinstance(budget, (int, float)) or budget <= 0:
        findings.append("collector_budget_spans_per_second must be greater than zero")
        budget = 0

    for item in plan.get("services", []):
        name = item.get("name", "<unnamed>")
        rps = item.get("requests_per_second", 0)
        spans = item.get("average_spans_per_trace", 0)
        baseline = item.get("baseline_sample_rate", 0)
        error_rate = item.get("error_sample_rate", 0)
        latency_rate = item.get("high_latency_sample_rate", 0)
        critical = item.get("critical", False)

        if not name or name == "<unnamed>":
            findings.append("a service is missing its name")
        if rps < 0 or spans <= 0:
            findings.append(f"{name}: requests_per_second must be non-negative and average_spans_per_trace positive")
            estimated = 0.0
        else:
            estimated = rps * spans * baseline
            total += estimated
        for field, rate in (("baseline_sample_rate", baseline), ("error_sample_rate", error_rate), ("high_latency_sample_rate", latency_rate)):
            if not isinstance(rate, (int, float)) or not 0 <= rate <= 1:
                findings.append(f"{name}: {field} must be between 0 and 1")
        if critical and baseline < 0.05:
            findings.append(f"{name}: critical service baseline sampling is below 5%")
        if error_rate < 1:
            findings.append(f"{name}: error traces are not sampled at 100%")
        if critical and latency_rate < 1:
            findings.append(f"{name}: critical high-latency traces are not sampled at 100%")
        services.append({"name": name, "estimated_spans_per_second": round(estimated, 2)})

    if not plan.get("services"):
        findings.append("sampling plan has no services")
    if budget and total > budget:
        findings.append(f"estimated volume {total:.2f} spans/s exceeds collector budget {budget:.2f} spans/s")

    return {
        "status": "FLAGGED" if findings else "PASS",
        "collector_budget_spans_per_second": budget,
        "estimated_spans_per_second": round(total, 2),
        "headroom_spans_per_second": round(budget - total, 2),
        "services": services,
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="JSON sampling plan")
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args()
    try:
        result = review(json.loads(args.plan.read_text()))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['status']}: estimated {result['estimated_spans_per_second']:.2f} spans/s, "
              f"headroom {result['headroom_spans_per_second']:.2f} spans/s")
        for finding in result["findings"]:
            print(f"- {finding}")
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
