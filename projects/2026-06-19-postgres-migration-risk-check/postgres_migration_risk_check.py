#!/usr/bin/env python3
"""Review PostgreSQL migration SQL for risky production-change patterns."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


RISK_PATTERNS = (
    (
        re.compile(r"\bdrop\s+table\b", re.IGNORECASE),
        "high",
        "drop-table",
        "drops a table",
    ),
    (
        re.compile(r"\bdrop\s+column\b", re.IGNORECASE),
        "high",
        "drop-column",
        "drops a column",
    ),
    (
        re.compile(r"\btruncate\s+table\b|\btruncate\s+[a-z_][\w.]*", re.IGNORECASE),
        "high",
        "truncate-table",
        "truncates table data",
    ),
    (
        re.compile(r"\block\s+table\b", re.IGNORECASE),
        "medium",
        "explicit-table-lock",
        "takes an explicit table lock",
    ),
)

CREATE_INDEX_RE = re.compile(r"\bcreate\s+(unique\s+)?index\b", re.IGNORECASE)
ADD_NOT_NULL_RE = re.compile(
    r"\balter\s+table\b.+\badd\s+column\b.+\bnot\s+null\b", re.IGNORECASE
)
SET_NOT_NULL_RE = re.compile(
    r"\balter\s+table\b.+\balter\s+column\b.+\bset\s+not\s+null\b", re.IGNORECASE
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    line: int
    statement: str
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "line": self.line,
            "statement": self.statement,
            "message": self.message,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review PostgreSQL migration SQL for production-risk patterns."
    )
    parser.add_argument("migration", type=Path, help="Path to a .sql migration file")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    return parser


def strip_inline_comment(line: str) -> str:
    quoted = False
    index = 0
    while index < len(line):
        char = line[index]
        if char == "'":
            quoted = not quoted
        if not quoted and line[index : index + 2] == "--":
            return line[:index]
        index += 1
    return line


def split_statements(sql: str) -> list[tuple[int, str]]:
    statements: list[tuple[int, str]] = []
    current: list[str] = []
    start_line = 1
    in_block_comment = False

    for line_number, raw_line in enumerate(sql.splitlines(), start=1):
        line = raw_line
        if in_block_comment:
            if "*/" in line:
                line = line.split("*/", 1)[1]
                in_block_comment = False
            else:
                continue

        while "/*" in line:
            before, after = line.split("/*", 1)
            if "*/" in after:
                line = before + after.split("*/", 1)[1]
            else:
                line = before
                in_block_comment = True
                break

        cleaned = strip_inline_comment(line).strip()
        if not cleaned:
            continue

        if not current:
            start_line = line_number
        current.append(cleaned)

        joined = " ".join(current)
        while ";" in joined:
            statement, remainder = joined.split(";", 1)
            statement = normalize_statement(statement)
            if statement:
                statements.append((start_line, statement))
            current = [remainder.strip()] if remainder.strip() else []
            start_line = line_number
            joined = " ".join(current)

    if current:
        statement = normalize_statement(" ".join(current))
        if statement:
            statements.append((start_line, statement))

    return statements


def normalize_statement(statement: str) -> str:
    return re.sub(r"\s+", " ", statement).strip()


def mask_string_literals(statement: str) -> str:
    return re.sub(r"'(?:''|[^'])*'", "''", statement)


def check_statement(line: int, statement: str) -> list[Finding]:
    findings: list[Finding] = []
    searchable = mask_string_literals(statement)

    for pattern, severity, code, message in RISK_PATTERNS:
        if pattern.search(searchable):
            findings.append(Finding(severity, code, line, statement, message))

    if CREATE_INDEX_RE.search(searchable) and not re.search(
        r"\bconcurrently\b", searchable, re.IGNORECASE
    ):
        findings.append(
            Finding(
                "medium",
                "non-concurrent-index",
                line,
                statement,
                "creates an index without CONCURRENTLY",
            )
        )

    if ADD_NOT_NULL_RE.search(searchable) and not re.search(
        r"\bdefault\b", searchable, re.IGNORECASE
    ):
        findings.append(
            Finding(
                "medium",
                "add-not-null-without-default",
                line,
                statement,
                "adds a NOT NULL column without a default value",
            )
        )

    if SET_NOT_NULL_RE.search(searchable):
        findings.append(
            Finding(
                "medium",
                "set-not-null",
                line,
                statement,
                "sets an existing column to NOT NULL and may need a backfill first",
            )
        )

    return findings


def collect_findings(sql: str) -> list[Finding]:
    findings: list[Finding] = []
    for line, statement in split_statements(sql):
        findings.extend(check_statement(line, statement))
    return findings


def render_text(findings: list[Finding]) -> str:
    if not findings:
        return "PASS: no PostgreSQL migration risk patterns detected"

    lines = [f"FLAGGED: {len(findings)} PostgreSQL migration risk pattern(s)"]
    for finding in findings:
        lines.append(
            (
                f"- [{finding.severity}] line {finding.line} "
                f"{finding.code}: {finding.message}"
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    sql = args.migration.read_text(encoding="utf-8")
    findings = collect_findings(sql)

    if args.format == "json":
        print(json.dumps({"findings": [item.as_dict() for item in findings]}, indent=2))
    else:
        print(render_text(findings))

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
