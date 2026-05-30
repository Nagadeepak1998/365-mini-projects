#!/usr/bin/env python3
import argparse
import json
import sys


def validate_payload(payload, schema):
    errors = []

    if schema.get("type") == "object" and not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    required = schema.get("required", [])
    for field in required:
        if field not in payload:
            errors.append(f"missing required field: {field}")

    properties = schema.get("properties", {})
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    for field, rules in properties.items():
        if field not in payload:
            continue

        expected_type = rules.get("type")
        expected_python = type_map.get(expected_type)
        if expected_python and not isinstance(payload[field], expected_python):
            errors.append(
                f"field '{field}' expected {expected_type}, got {type(payload[field]).__name__}"
            )

        enum_values = rules.get("enum")
        if enum_values is not None and payload[field] not in enum_values:
            errors.append(
                f"field '{field}' must be one of {enum_values}, got {payload[field]!r}"
            )

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate LLM JSON output against a schema")
    parser.add_argument("--schema", required=True, help="Path to schema JSON file")
    parser.add_argument("--input", required=True, help="Path to LLM output JSON file")
    args = parser.parse_args()

    try:
        with open(args.schema, "r", encoding="utf-8") as f:
            schema = json.load(f)
        with open(args.input, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError as exc:
        print(f"ERROR: file not found: {exc.filename}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {exc.doc[:30]!r} at position {exc.pos}")
        sys.exit(1)

    errors = validate_payload(payload, schema)
    if errors:
        print("INVALID")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)

    print("VALID")
    sys.exit(0)


if __name__ == "__main__":
    main()
