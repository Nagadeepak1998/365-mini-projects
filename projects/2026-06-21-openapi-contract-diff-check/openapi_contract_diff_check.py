#!/usr/bin/env python3
"""Compare two OpenAPI JSON files for likely breaking API contract changes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
JSON_CONTENT_TYPES = ("application/json", "application/problem+json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Flag likely breaking changes between two OpenAPI JSON specs."
    )
    parser.add_argument("old_spec", type=Path, help="Path to the current OpenAPI JSON")
    parser.add_argument("new_spec", type=Path, help="Path to the proposed OpenAPI JSON")
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="Output format"
    )
    return parser


def load_spec(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        spec = json.load(handle)
    if not isinstance(spec, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return spec


def resolve_ref(spec: dict[str, Any], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    ref = value.get("$ref")
    if not isinstance(ref, str):
        return value
    if not ref.startswith("#/"):
        return value

    current: Any = spec
    for part in ref[2:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            return value
        current = current[key]
    return current if isinstance(current, dict) else value


def paths_from(spec: dict[str, Any]) -> dict[str, Any]:
    paths = spec.get("paths", {})
    return paths if isinstance(paths, dict) else {}


def operations_from(path_item: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(path_item, dict):
        return {}
    return {
        method: operation
        for method, operation in path_item.items()
        if method in HTTP_METHODS and isinstance(operation, dict)
    }


def operation_parameters(
    spec: dict[str, Any], path_item: Any, operation: dict[str, Any]
) -> dict[tuple[str, str], dict[str, Any]]:
    values: list[Any] = []
    if isinstance(path_item, dict) and isinstance(path_item.get("parameters"), list):
        values.extend(path_item["parameters"])
    if isinstance(operation.get("parameters"), list):
        values.extend(operation["parameters"])

    parameters: dict[tuple[str, str], dict[str, Any]] = {}
    for raw_parameter in values:
        parameter = resolve_ref(spec, raw_parameter)
        name = parameter.get("name")
        location = parameter.get("in")
        if isinstance(name, str) and isinstance(location, str):
            parameters[(location, name)] = parameter
    return parameters


def json_schema_from_content(spec: dict[str, Any], content: Any) -> dict[str, Any]:
    if not isinstance(content, dict):
        return {}
    for content_type in JSON_CONTENT_TYPES:
        media = content.get(content_type)
        if isinstance(media, dict):
            return resolve_ref(spec, media.get("schema"))
    for content_type, media in content.items():
        if "json" in str(content_type) and isinstance(media, dict):
            return resolve_ref(spec, media.get("schema"))
    return {}


def request_schema(spec: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    request_body = resolve_ref(spec, operation.get("requestBody"))
    return json_schema_from_content(spec, request_body.get("content"))


def response_schemas(
    spec: dict[str, Any], operation: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return {}

    schemas: dict[str, dict[str, Any]] = {}
    for status, response in responses.items():
        status_text = str(status)
        if not status_text.startswith("2"):
            continue
        resolved_response = resolve_ref(spec, response)
        schema = json_schema_from_content(spec, resolved_response.get("content"))
        if schema:
            schemas[status_text] = schema
    return schemas


def success_response_statuses(operation: dict[str, Any]) -> set[str]:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return set()
    return {str(status) for status in responses if str(status).startswith("2")}


def object_shape(spec: dict[str, Any], schema: dict[str, Any]) -> tuple[set[str], set[str]]:
    schema = resolve_ref(spec, schema)
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    property_names = set(properties) if isinstance(properties, dict) else set()
    required_names = {name for name in required if isinstance(name, str)}
    return property_names, required_names


def finding(
    severity: str,
    code: str,
    path: str,
    method: str,
    message: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "path": path,
        "method": method.upper() if method else "",
        "message": message,
    }


def compare_parameters(
    old_spec: dict[str, Any],
    new_spec: dict[str, Any],
    path: str,
    method: str,
    old_path_item: Any,
    new_path_item: Any,
    old_operation: dict[str, Any],
    new_operation: dict[str, Any],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    old_parameters = operation_parameters(old_spec, old_path_item, old_operation)
    new_parameters = operation_parameters(new_spec, new_path_item, new_operation)

    for key in sorted(old_parameters):
        if key not in new_parameters:
            location, name = key
            severity = "high" if location == "path" else "medium"
            findings.append(
                finding(
                    severity,
                    "removed-parameter",
                    path,
                    method,
                    f"{location} parameter '{name}' was removed",
                )
            )

    for key, new_parameter in sorted(new_parameters.items()):
        old_parameter = old_parameters.get(key)
        location, name = key
        if old_parameter is None:
            if new_parameter.get("required") is True:
                findings.append(
                    finding(
                        "high",
                        "added-required-parameter",
                        path,
                        method,
                        f"new required {location} parameter '{name}' was added",
                    )
                )
            continue

        old_type = resolve_ref(old_spec, old_parameter.get("schema")).get("type")
        new_type = resolve_ref(new_spec, new_parameter.get("schema")).get("type")
        if old_type and new_type and old_type != new_type:
            findings.append(
                finding(
                    "medium",
                    "parameter-type-changed",
                    path,
                    method,
                    f"{location} parameter '{name}' changed type from {old_type} to {new_type}",
                )
            )
        if old_parameter.get("required") is not True and new_parameter.get("required") is True:
            findings.append(
                finding(
                    "high",
                    "parameter-became-required",
                    path,
                    method,
                    f"{location} parameter '{name}' became required",
                )
            )

    return findings


def compare_object_contract(
    old_spec: dict[str, Any],
    new_spec: dict[str, Any],
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    path: str,
    method: str,
    context: str,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    old_properties, old_required = object_shape(old_spec, old_schema)
    new_properties, new_required = object_shape(new_spec, new_schema)

    for name in sorted(old_properties - new_properties):
        severity = "high" if context == "response" and name in old_required else "medium"
        findings.append(
            finding(
                severity,
                f"removed-{context}-field",
                path,
                method,
                f"{context} field '{name}' was removed",
            )
        )

    for name in sorted(new_required - old_required):
        if context == "request":
            findings.append(
                finding(
                    "high",
                    "added-required-request-field",
                    path,
                    method,
                    f"request field '{name}' became required",
                )
            )

    for name in sorted((old_required - new_required) & new_properties):
        if context == "response":
            findings.append(
                finding(
                    "high",
                    "response-field-no-longer-required",
                    path,
                    method,
                    f"response field '{name}' is no longer guaranteed",
                )
            )

    return findings


def compare_operation_contract(
    old_spec: dict[str, Any],
    new_spec: dict[str, Any],
    path: str,
    method: str,
    old_path_item: Any,
    new_path_item: Any,
    old_operation: dict[str, Any],
    new_operation: dict[str, Any],
) -> list[dict[str, str]]:
    findings = compare_parameters(
        old_spec,
        new_spec,
        path,
        method,
        old_path_item,
        new_path_item,
        old_operation,
        new_operation,
    )

    old_request_schema = request_schema(old_spec, old_operation)
    new_request_schema = request_schema(new_spec, new_operation)
    if old_request_schema and new_request_schema:
        findings.extend(
            compare_object_contract(
                old_spec,
                new_spec,
                old_request_schema,
                new_request_schema,
                path,
                method,
                "request",
            )
        )

    old_statuses = success_response_statuses(old_operation)
    new_statuses = success_response_statuses(new_operation)
    old_response_schemas = response_schemas(old_spec, old_operation)
    new_response_schemas = response_schemas(new_spec, new_operation)
    for status in sorted(old_statuses):
        if status not in new_statuses:
            findings.append(
                finding(
                    "high",
                    "removed-success-response",
                    path,
                    method,
                    f"success response {status} was removed",
                )
            )
            continue
        if status not in old_response_schemas or status not in new_response_schemas:
            continue
        findings.extend(
            compare_object_contract(
                old_spec,
                new_spec,
                old_response_schemas[status],
                new_response_schemas[status],
                path,
                method,
                "response",
            )
        )

    return findings


def collect_findings(
    old_spec: dict[str, Any], new_spec: dict[str, Any]
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    old_paths = paths_from(old_spec)
    new_paths = paths_from(new_spec)

    for path in sorted(old_paths):
        if path not in new_paths:
            findings.append(
                finding("high", "removed-path", path, "", f"path '{path}' was removed")
            )
            continue

        old_operations = operations_from(old_paths[path])
        new_operations = operations_from(new_paths[path])
        for method, old_operation in sorted(old_operations.items()):
            new_operation = new_operations.get(method)
            if new_operation is None:
                findings.append(
                    finding(
                        "high",
                        "removed-operation",
                        path,
                        method,
                        f"{method.upper()} operation was removed",
                    )
                )
                continue

            findings.extend(
                compare_operation_contract(
                    old_spec,
                    new_spec,
                    path,
                    method,
                    old_paths[path],
                    new_paths[path],
                    old_operation,
                    new_operation,
                )
            )

    return findings


def format_text(findings: list[dict[str, str]]) -> str:
    if not findings:
        return "PASS: no breaking OpenAPI contract changes detected"

    lines = [f"FLAGGED: {len(findings)} breaking OpenAPI contract issue(s)"]
    for item in findings:
        operation = f"{item['method']} " if item["method"] else ""
        lines.append(
            f"- [{item['severity']}] {item['code']} {operation}{item['path']}: {item['message']}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    findings = collect_findings(load_spec(args.old_spec), load_spec(args.new_spec))
    if args.format == "json":
        print(json.dumps({"findings": findings}, indent=2, sort_keys=True))
    else:
        print(format_text(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
