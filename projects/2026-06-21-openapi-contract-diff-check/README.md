# OpenAPI Contract Diff Check

OpenAPI Contract Diff Check is a small Python CLI I built to compare a current API contract with a proposed OpenAPI contract before a release.

## Problem

API changes can look harmless in a pull request but still break a client. Removing an endpoint, making a query parameter required, changing a parameter type, or removing a response field can turn into a production support issue after deploy.

I wanted a quick local check that catches the most obvious breaking changes from two OpenAPI JSON files.

## What It Does

- compares two OpenAPI 3 JSON files
- flags removed paths and removed HTTP operations
- flags removed parameters, newly required parameters, and parameter type changes
- flags removed request fields and newly required request fields
- flags removed success responses
- flags removed JSON response fields and response fields that are no longer guaranteed
- follows local `#/components/...` `$ref` links for schemas and parameters

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for verification

## Folder Structure

```text
.
|-- README.md
|-- openapi_contract_diff_check.py
|-- samples
|   |-- current_openapi.json
|   |-- proposed_breaking_openapi.json
|   `-- proposed_safe_openapi.json
`-- tests
    `-- test_openapi_contract_diff_check.py
```

## How to Run

From this project folder:

```bash
python3 openapi_contract_diff_check.py samples/current_openapi.json samples/proposed_breaking_openapi.json
```

Expected result:

```text
FLAGGED: 10 breaking OpenAPI contract issue(s)
```

Check the safer sample:

```bash
python3 openapi_contract_diff_check.py samples/current_openapi.json samples/proposed_safe_openapi.json
```

Expected result:

```text
PASS: no breaking OpenAPI contract changes detected
```

Return JSON instead:

```bash
python3 openapi_contract_diff_check.py samples/current_openapi.json samples/proposed_breaking_openapi.json --format json
```

## Example

The breaking sample includes:

- `/refunds` removed
- `customerId` changed from a string query parameter to an integer
- `customerId` changed from optional to required
- a new required `region` query parameter
- `memo` removed from the create payment request
- `source` added as a required create payment field
- `201` success response removed from `POST /payments`
- response fields removed from the payment and payment list schemas

Those are the kinds of contract changes I would want to catch before merging or deploying an API change.

## Tests

```bash
python3 -m py_compile openapi_contract_diff_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

- This is a static contract review, not a full OpenAPI validator.
- The checker intentionally focuses on common top-level JSON object changes.
- Additive changes, such as optional request parameters or extra response fields, are treated as safe.
