import unittest

from response_contract_check import evaluate, value_at


class ResponseContractCheckTests(unittest.TestCase):
    def test_passing_json_and_text_contracts(self):
        report = evaluate(
            [
                {
                    "id": "json",
                    "output": '{"route":"billing","meta":{"priority":"high"}}',
                    "latency_ms": 120,
                    "contract": {
                        "type": "json",
                        "required_keys": ["meta.priority"],
                        "exact_values": {"route": "billing"},
                        "max_latency_ms": 200,
                    },
                },
                {
                    "id": "text",
                    "output": "I cannot share that token. Rotate it instead.",
                    "contract": {
                        "required_terms": ["cannot", "rotate"],
                        "forbidden_terms": ["sk-live-"],
                    },
                },
            ]
        )
        self.assertEqual((report["passed"], report["failed"]), (2, 0))

    def test_reports_all_contract_regressions(self):
        report = evaluate(
            [
                {
                    "id": "regression",
                    "output": '{"route":"general","note":"password exposed"}',
                    "latency_ms": 350,
                    "cost_usd": 0.03,
                    "contract": {
                        "type": "json",
                        "required_keys": ["owner"],
                        "exact_values": {"route": "billing"},
                        "forbidden_terms": ["password"],
                        "max_latency_ms": 200,
                        "max_cost_usd": 0.01,
                    },
                }
            ]
        )
        failures = report["results"][0]["failures"]
        self.assertEqual(report["failed"], 1)
        self.assertEqual(len(failures), 5)

    def test_invalid_json_is_a_case_failure(self):
        report = evaluate([{"id": "bad-json", "output": "not json", "contract": {"type": "json"}}])
        self.assertIn("not valid JSON", report["results"][0]["failures"][0])

    def test_rejects_invalid_contract_shape(self):
        with self.assertRaisesRegex(ValueError, "required_keys"):
            evaluate([{"id": "bad-contract", "output": "{}", "contract": {"type": "json", "required_keys": "route"}}])

    def test_value_at_supports_nested_paths(self):
        self.assertEqual(value_at({"a": {"b": 3}}, "a.b"), 3)


if __name__ == "__main__":
    unittest.main()
