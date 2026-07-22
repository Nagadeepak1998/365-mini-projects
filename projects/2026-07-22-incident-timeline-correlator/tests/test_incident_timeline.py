import unittest

from incident_timeline import correlate, markdown


EVENTS = [
    {"timestamp": "2026-07-22T09:58:00Z", "source": "grafana", "type": "alert", "service": "checkout", "summary": "Error rate exceeded 5%"},
    {"timestamp": "2026-07-22T09:45:00Z", "source": "argocd", "type": "deploy", "service": "checkout", "summary": "Deployed checkout-api 2.4.0"},
    {"timestamp": "2026-07-22T10:03:00Z", "source": "loki", "type": "log", "service": "checkout", "summary": "Payment client timeout"},
    {"timestamp": "2026-07-22T09:50:00Z", "source": "argocd", "type": "deploy", "service": "catalog", "summary": "Deployed catalog 1.9.0"},
]


class CorrelateTests(unittest.TestCase):
    def test_filters_service_and_window_then_sorts(self):
        result = correlate(EVENTS, "2026-07-22T10:00:00Z", "checkout", 20, 10)
        self.assertEqual([event["type"] for event in result["events"]], ["deploy", "alert", "log"])

    def test_selects_latest_pre_incident_change(self):
        result = correlate(EVENTS, "2026-07-22T10:00:00Z", "checkout", 20, 10)
        self.assertEqual(result["likely_trigger"]["summary"], "Deployed checkout-api 2.4.0")
        self.assertEqual(result["symptom_count"], 2)

    def test_rejects_incomplete_events(self):
        with self.assertRaisesRegex(ValueError, "missing: summary"):
            correlate([{key: value for key, value in EVENTS[0].items() if key != "summary"}], "2026-07-22T10:00:00Z", "checkout", 20, 10)

    def test_markdown_explains_absent_trigger(self):
        result = correlate(EVENTS[:1], "2026-07-22T10:00:00Z", "checkout", 20, 10)
        self.assertIn("No change event was found", markdown(result))


if __name__ == "__main__":
    unittest.main()
