#!/usr/bin/env python3
"""Build a focused incident timeline from normalized operational events."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)


def correlate(events: list[dict], incident_time: str, service: str, before: int, after: int) -> dict:
    anchor = parse_time(incident_time)
    start = anchor - timedelta(minutes=before)
    end = anchor + timedelta(minutes=after)
    required = {"timestamp", "source", "type", "service", "summary"}
    timeline = []

    for index, event in enumerate(events):
        missing = required - event.keys()
        if missing:
            raise ValueError(f"event {index} is missing: {', '.join(sorted(missing))}")
        occurred_at = parse_time(event["timestamp"])
        if event["service"] == service and start <= occurred_at <= end:
            timeline.append({**event, "_time": occurred_at})

    timeline.sort(key=lambda item: (item["_time"], item["source"], item["summary"]))
    changes = [event for event in timeline if event["type"] in {"deploy", "config", "feature_flag"} and event["_time"] <= anchor]
    symptoms = [event for event in timeline if event["type"] in {"alert", "log", "metric"}]
    return {
        "service": service,
        "incident_time": anchor.isoformat().replace("+00:00", "Z"),
        "window": {"before_minutes": before, "after_minutes": after},
        "likely_trigger": clean(changes[-1]) if changes else None,
        "symptom_count": len(symptoms),
        "events": [clean(event) for event in timeline],
    }


def clean(event: dict) -> dict:
    return {key: value for key, value in event.items() if key != "_time"}


def markdown(result: dict) -> str:
    lines = [
        f"# Incident timeline: {result['service']}",
        "",
        f"Incident anchor: `{result['incident_time']}`",
        f"Window: {result['window']['before_minutes']} minutes before / {result['window']['after_minutes']} minutes after",
        "",
    ]
    trigger = result["likely_trigger"]
    if trigger:
        lines += ["## Likely trigger to investigate", "", f"- `{trigger['timestamp']}` {trigger['summary']} ({trigger['source']})", ""]
    else:
        lines += ["## Likely trigger to investigate", "", "- No change event was found before the incident anchor.", ""]
    lines += ["## Events", ""]
    for event in result["events"]:
        lines.append(f"- `{event['timestamp']}` **{event['type']}** — {event['summary']} ({event['source']})")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path)
    parser.add_argument("--incident-time", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--before", type=int, default=30)
    parser.add_argument("--after", type=int, default=15)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    if args.before < 0 or args.after < 0:
        parser.error("window values must be non-negative")

    try:
        events = json.loads(args.events.read_text())
        if not isinstance(events, list):
            raise ValueError("input must be a JSON array")
        result = correlate(events, args.incident_time, args.service, args.before, args.after)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")

    print(json.dumps(result, indent=2) if args.format == "json" else markdown(result), end="\n" if args.format == "json" else "")
    return 0 if result["events"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
