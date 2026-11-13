"""
Unit tests for ReportGenerator module.
Verifies JSON and CSV audit artifact creation, content integrity, and error trapping.
"""

import csv
import json
from pathlib import Path
import pytest

from redbus_automation.models import (
    Bus,
    RankedBus,
    SearchRequest,
    WorkflowExecutionResult,
    WorkflowStatus,
    RetryAttempt,
    RecoveryAction,
    ReportGenerationError,
)
from redbus_automation.reporting import ReportGenerator


@pytest.fixture
def sample_execution_result():
    """Provides a sample completed execution result for reporting tests."""
    req = SearchRequest(source="Bangalore", destination="Hyderabad", journey_date="2026-11-20", max_budget=2000.0)
    bus = Bus(
        bus_id="BUS-TEST-1",
        operator_name="Test Operator",
        source="Bangalore",
        destination="Hyderabad",
        departure_time="21:00",
        arrival_time="06:00",
        fare=1000.0,
        available_seats=15,
        bus_type="AC Sleeper",
        rating=4.5,
    )
    ranked = RankedBus(bus=bus, rank=1, composite_score=0.88, recommendation_reason="Top test recommendation")

    return WorkflowExecutionResult(
        execution_id="EXEC-TEST-001",
        status=WorkflowStatus.SUCCESS,
        request=req,
        buses_found=[bus],
        ranked_buses=[ranked],
        recommended_bus=ranked,
        retry_history=[],
        recovery_history=[],
        execution_duration_sec=0.125,
        start_time="2026-11-20T10:00:00",
        end_time="2026-11-20T10:00:01",
    )


def test_generate_json_report(tmp_path, sample_execution_result):
    """Verifies generation of structured JSON report file."""
    generator = ReportGenerator(reports_dir=tmp_path)
    json_path = generator.generate_json_report(sample_execution_result)

    assert json_path.exists()
    assert json_path.name == "report_EXEC-TEST-001.json"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["execution_id"] == "EXEC-TEST-001"
    assert data["status"] == "SUCCESS"
    assert data["duration_seconds"] == 0.125
    assert data["request"]["source"] == "Bangalore"
    assert len(data["search_results"]["ranked_buses"]) == 1
    assert data["search_results"]["recommended_bus"]["bus_id"] == "BUS-TEST-1"
    assert "SIMULATED DATA" in data["disclaimer"]


def test_generate_csv_report(tmp_path, sample_execution_result):
    """Verifies generation of structured tabular CSV report file."""
    generator = ReportGenerator(reports_dir=tmp_path)
    csv_path = generator.generate_csv_report(sample_execution_result)

    assert csv_path.exists()
    assert csv_path.name == "report_EXEC-TEST-001.csv"

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    assert len(reader) >= 2  # Header + 1 row
    headers = reader[0]
    assert "execution_id" in headers
    assert "composite_score" in headers

    row = reader[1]
    assert row[0] == "EXEC-TEST-001"
    assert row[1] == "SUCCESS"
    assert "BUS-TEST-1" in row


def test_generate_all_reports(tmp_path, sample_execution_result):
    """Verifies generate_all_reports produces both JSON and CSV files."""
    generator = ReportGenerator(reports_dir=tmp_path)
    paths = generator.generate_all_reports(sample_execution_result)

    assert "json" in paths and "csv" in paths
    assert Path(paths["json"]).exists()
    assert Path(paths["csv"]).exists()
