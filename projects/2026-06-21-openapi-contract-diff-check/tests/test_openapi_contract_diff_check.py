import unittest

from openapi_contract_diff_check import collect_findings, format_text, resolve_ref


class OpenApiContractDiffCheckTests(unittest.TestCase):
    def test_resolve_ref_reads_local_schema(self):
        spec = {
            "components": {
                "schemas": {
                    "Payment": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                    }
                }
            }
        }

        resolved = resolve_ref(spec, {"$ref": "#/components/schemas/Payment"})

        self.assertEqual(resolved["properties"]["id"]["type"], "string")

    def test_flags_removed_paths_operations_parameters_and_stricter_fields(self):
        old_spec = {
            "paths": {
                "/payments": {
                    "get": {
                        "parameters": [
                            {
                                "name": "customerId",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["items"],
                                            "properties": {
                                                "items": {"type": "array"},
                                                "nextPageToken": {"type": "string"},
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    },
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["amount"],
                                        "properties": {
                                            "amount": {"type": "number"},
                                            "memo": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "created"}},
                    },
                },
                "/refunds": {"post": {"responses": {"202": {"description": "ok"}}}},
            }
        }
        new_spec = {
            "paths": {
                "/payments": {
                    "get": {
                        "parameters": [
                            {
                                "name": "customerId",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "integer"},
                            },
                            {
                                "name": "region",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["items"],
                                            "properties": {"items": {"type": "array"}},
                                        }
                                    }
                                }
                            }
                        },
                    },
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["amount", "source"],
                                        "properties": {
                                            "amount": {"type": "number"},
                                            "source": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "created"}},
                    },
                }
            }
        }

        findings = collect_findings(old_spec, new_spec)
        codes = {item["code"] for item in findings}

        self.assertEqual(len(findings), 8)
        self.assertIn("removed-path", codes)
        self.assertIn("parameter-type-changed", codes)
        self.assertIn("parameter-became-required", codes)
        self.assertIn("added-required-parameter", codes)
        self.assertIn("removed-request-field", codes)
        self.assertIn("added-required-request-field", codes)
        self.assertIn("removed-success-response", codes)
        self.assertIn("removed-response-field", codes)

    def test_additive_contract_changes_pass(self):
        old_spec = {
            "paths": {
                "/payments": {
                    "get": {
                        "parameters": [
                            {
                                "name": "customerId",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["items"],
                                            "properties": {"items": {"type": "array"}},
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }
        new_spec = {
            "paths": {
                "/payments": {
                    "get": {
                        "parameters": [
                            {
                                "name": "customerId",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                            },
                            {
                                "name": "region",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                            },
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["items"],
                                            "properties": {
                                                "items": {"type": "array"},
                                                "totalCount": {"type": "integer"},
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }

        self.assertEqual(collect_findings(old_spec, new_spec), [])
        self.assertIn("PASS", format_text([]))


if __name__ == "__main__":
    unittest.main()
