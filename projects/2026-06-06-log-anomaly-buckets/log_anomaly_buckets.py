#!/usr/bin/env python3
import re
import sys
from collections import defaultdict
from pathlib import Path


LATENCY_PATTERN = re.compile(r"\blatency_ms=(\d+)\b")
STATUS_PATTERN = re.compile(r"\bstatus=(\d{3})\b")
TIMEOUT_TERMS = ("timeout", "timed out", "deadline exceeded")
CONNECTION_TERMS = ("connection refused", "tls handshake", "dns failure")
ERROR_TERMS = ("traceback", "exception", "panic")


def detect_bucket(line: str, slow_ms: int) -> str | None:
    lowered = line.lower()

    status_match = STATUS_PATTERN.search(line)
    if status_match:
        status_code = int(status_match.group(1))
        if status_code >= 500:
            return "server_error"
        if status_code == 429:
            return "rate_limited"

    latency_match = LATENCY_PATTERN.search(line)
    if latency_match and int(latency_match.group(1)) >= slow_ms:
        return "slow_request"

    if any(term in lowered for term in TIMEOUT_TERMS):
        return "timeout"

    if any(term in lowered for term in CONNECTION_TERMS):
        return "connectivity"

    if any(term in lowered for term in ERROR_TERMS):
        return "application_error"

    return None


def bucket_lines(lines: list[str], slow_ms: int) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        bucket = detect_bucket(line, slow_ms)
        if bucket:
            buckets[bucket].append(line.rstrip())
    return dict(buckets)


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print(
            "Usage: python3 log_anomaly_buckets.py <logfile> [slow_ms]",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 2

    slow_ms = int(sys.argv[2]) if len(sys.argv) == 3 else 1000

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"Failed to read log file: {exc}", file=sys.stderr)
        return 2

    buckets = bucket_lines(lines, slow_ms)
    if not buckets:
        print("PASS: no suspicious log lines matched the built-in buckets")
        return 0

    print(f"FLAGGED: {sum(len(items) for items in buckets.values())} suspicious line(s)")
    for bucket in sorted(buckets):
        print(f"[{bucket}] {len(buckets[bucket])} hit(s)")
        print(f"  sample: {buckets[bucket][0]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
