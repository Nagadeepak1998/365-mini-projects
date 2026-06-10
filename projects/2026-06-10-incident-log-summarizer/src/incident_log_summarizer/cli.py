from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .analyzer import SEVERITY_ORDER, analyze_log, format_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="incident-log-summarizer",
        description="Summarize incident logs into severity, evidence, probable cause, and runbook actions.",
    )
    parser.add_argument("log_file", help="Path to the log file. Use '-' to read from stdin.")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    parser.add_argument(
        "--max-evidence-per-rule",
        type=int,
        default=3,
        help="Maximum evidence lines retained for each detection rule.",
    )
    parser.add_argument(
        "--fail-on",
        choices=tuple(SEVERITY_ORDER),
        help="Exit with code 2 when detected severity is at or above this level.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = _read_log(args.log_file)
    report = analyze_log(text, source=args.log_file, max_evidence_per_rule=args.max_evidence_per_rule)

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(format_markdown(report))

    if args.fail_on and SEVERITY_ORDER[report["severity"]] >= SEVERITY_ORDER[args.fail_on]:
        return 2
    return 0


def _read_log(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")
