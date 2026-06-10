import json

from incident_log_summarizer import analyze_log, format_markdown
from incident_log_summarizer.cli import main


def test_kubernetes_incident_is_summarized_with_evidence():
    log_text = """
    2026-06-10T09:00:01Z INFO rollout started deployment/api
    2026-06-10T09:01:12Z ERROR pod/api-78d9 readiness probe failed: connection refused
    2026-06-10T09:01:40Z WARN Back-off restarting failed container api in pod/api-78d9
    2026-06-10T09:02:01Z ERROR last state terminated: OOMKilled exit code 137
    """

    report = analyze_log(log_text, source="sample.log")

    assert report["severity"] == "high"
    assert report["probable_cause"] == "Kubernetes workload health or rollout failure"
    assert report["time_window"] == "2026-06-10T09:00:01Z to 2026-06-10T09:02:01Z"
    assert {item["category"] for item in report["categories"]} >= {"kubernetes", "resources"}
    assert any(item["rule"] == "memory_pressure" for item in report["evidence"])


def test_secret_exposure_is_critical():
    report = analyze_log("2026-06-10 ERROR token=abc123 leaked in request logs")

    assert report["severity"] == "critical"
    assert report["probable_cause"] == "possible credential exposure in logs"


def test_clean_log_returns_low_severity_and_safe_actions():
    report = analyze_log("2026-06-10T10:00:00Z INFO deployment completed successfully")

    assert report["severity"] == "low"
    assert report["categories"] == []
    assert "No high-confidence failure pattern" in report["probable_cause"]


def test_markdown_report_contains_recruiter_readable_sections():
    report = analyze_log("ERROR could not connect to database: connection pool exhausted")

    markdown = format_markdown(report)

    assert "# Incident Summary" in markdown
    assert "## Signals" in markdown
    assert "## Evidence" in markdown
    assert "## Recommended Actions" in markdown


def test_cli_outputs_json(tmp_path, capsys):
    log_file = tmp_path / "incident.log"
    log_file.write_text("ERROR no such host service.internal\n", encoding="utf-8")

    exit_code = main([str(log_file), "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["severity"] == "high"
    assert output["categories"][0]["category"] == "network"


def test_cli_can_fail_on_threshold(tmp_path, capsys):
    log_file = tmp_path / "incident.log"
    log_file.write_text("ERROR unauthorized request returned 403\n", encoding="utf-8")

    exit_code = main([str(log_file), "--fail-on", "high"])
    capsys.readouterr()

    assert exit_code == 2
