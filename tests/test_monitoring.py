"""
Unit tests for AutomationMonitor module.
Verifies operational KPI telemetry, latency averaging, double-counting safeguards, and state tracking.
"""

import pytest
from redbus_automation.models import WorkflowStatus
from redbus_automation.monitoring import AutomationMonitor


@pytest.fixture
def monitor():
    """Provides an isolated monitor instance for testing."""
    return AutomationMonitor()


def test_monitor_initial_state(monitor):
    """Verifies that a fresh monitor starts with zeroed counters."""
    metrics = monitor.get_metrics()
    assert metrics["total_executions"] == 0
    assert metrics["successful_executions"] == 0
    assert metrics["failed_executions"] == 0
    assert metrics["recovered_executions"] == 0
    assert metrics["success_rate_percent"] == 0.0
    assert metrics["failure_rate_percent"] == 0.0
    assert metrics["average_duration_sec"] == 0.0
    assert metrics["current_execution_status"] == WorkflowStatus.PENDING.value
    assert metrics["active_execution_id"] is None


def test_monitor_records_start_and_running_status(monitor):
    """Verifies transition to RUNNING state when execution begins."""
    monitor.record_start("EXEC-101")
    metrics = monitor.get_metrics()
    assert metrics["active_execution_id"] == "EXEC-101"
    assert metrics["current_execution_status"] == WorkflowStatus.RUNNING.value


def test_monitor_records_success_completion(monitor):
    """Verifies successful completion metrics update."""
    monitor.record_start("EXEC-101")
    monitor.record_completion(
        execution_id="EXEC-101",
        status=WorkflowStatus.SUCCESS,
        duration_sec=0.5,
        retry_count=1,
        recovery_count=0,
    )

    metrics = monitor.get_metrics()
    assert metrics["total_executions"] == 1
    assert metrics["successful_executions"] == 1
    assert metrics["failed_executions"] == 0
    assert metrics["total_retry_attempts"] == 1
    assert metrics["success_rate_percent"] == 100.0
    assert metrics["failure_rate_percent"] == 0.0
    assert metrics["average_duration_sec"] == 0.5
    assert metrics["active_execution_id"] is None


def test_monitor_prevents_double_counting(monitor):
    """CRITICAL: Verifies duplicate completion calls with the same ID are ignored."""
    monitor.record_completion(
        execution_id="EXEC-DUP",
        status=WorkflowStatus.SUCCESS,
        duration_sec=0.2,
    )
    # Second duplicate call with same ID
    monitor.record_completion(
        execution_id="EXEC-DUP",
        status=WorkflowStatus.SUCCESS,
        duration_sec=0.2,
    )

    metrics = monitor.get_metrics()
    assert metrics["total_executions"] == 1  # NOT 2
    assert metrics["successful_executions"] == 1


def test_monitor_computes_accuracy_of_mixed_executions(monitor):
    """Verifies precision of success rate, failure rate, and average latency across runs."""
    monitor.record_completion("RUN-1", WorkflowStatus.SUCCESS, duration_sec=1.0)
    monitor.record_completion("RUN-2", WorkflowStatus.FAILED, duration_sec=2.0)
    monitor.record_completion("RUN-3", WorkflowStatus.RECOVERED, duration_sec=3.0)
    monitor.record_completion("RUN-4", WorkflowStatus.SUCCESS, duration_sec=4.0)

    # Total = 4 (SUCCESS: 2, RECOVERED: 1 -> Counted as 3 successful completions, FAILED: 1)
    metrics = monitor.get_metrics()
    assert metrics["total_executions"] == 4
    assert metrics["successful_executions"] == 3
    assert metrics["failed_executions"] == 1
    assert metrics["recovered_executions"] == 1
    assert metrics["success_rate_percent"] == 75.0
    assert metrics["failure_rate_percent"] == 25.0
    assert metrics["average_duration_sec"] == 2.5


def test_monitor_reset(monitor):
    """Verifies that reset_metrics wipes all counters."""
    monitor.record_completion("RUN-1", WorkflowStatus.SUCCESS, duration_sec=1.0)
    assert monitor.get_metrics()["total_executions"] == 1

    monitor.reset_metrics()
    assert monitor.get_metrics()["total_executions"] == 0
