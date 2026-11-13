"""
Integration tests for AutomationOrchestrator module.
Verifies complete end-to-end lifecycle orchestration, state transitions,
fault injections, and self-healing autonomics.
"""

from datetime import date
import pytest

from redbus_automation.models import SearchRequest, WorkflowStatus
from redbus_automation.orchestrator import AutomationOrchestrator


@pytest.fixture
def orchestrator():
    return AutomationOrchestrator()


@pytest.fixture
def valid_request():
    return SearchRequest(
        source="Bangalore",
        destination="Hyderabad",
        journey_date="2026-11-20",
        passengers=1,
        max_budget=2500.0,
    )


def test_orchestrator_successful_e2e_workflow(orchestrator, valid_request):
    """Verifies end-to-end execution of a healthy automation workflow."""
    ref_date = date(2026, 11, 14)
    result = orchestrator.run_workflow(valid_request, reference_date=ref_date)

    assert result.status == WorkflowStatus.SUCCESS
    assert result.execution_id.startswith("EXEC-")
    assert result.execution_duration_sec > 0
    assert len(result.buses_found) > 0
    assert len(result.ranked_buses) > 0
    assert result.recommended_bus is not None
    assert result.recommended_bus.rank == 1
    assert "json" in result.report_paths
    assert "csv" in result.report_paths
    assert result.error_message is None


def test_orchestrator_handles_validation_failure_without_retry(orchestrator):
    """Verifies that validation failures immediately yield FAILED status with 0 retries."""
    invalid_req = SearchRequest(
        source="Bangalore",
        destination="Bangalore",  # Same city!
        journey_date="2026-11-20",
    )

    result = orchestrator.run_workflow(invalid_req)

    assert result.status == WorkflowStatus.FAILED
    assert len(result.retry_history) == 0  # CRITICAL: zero retries on validation errors
    assert "cannot be identical" in (result.error_message or "")


def test_orchestrator_self_heals_transient_failure(orchestrator, valid_request):
    """Verifies self-healing recovery under simulated transient service failure."""
    ref_date = date(2026, 11, 14)
    faults = {"simulate_transient_failure": True}
    result = orchestrator.run_workflow(valid_request, fault_injection=faults, reference_date=ref_date)

    # Should recover via secondary mirror and mark status RECOVERED
    assert result.status == WorkflowStatus.RECOVERED
    assert len(result.recovery_history) >= 1
    assert result.recovery_history[0].successful is True
    assert result.recommended_bus is not None


def test_orchestrator_self_heals_zero_filtered_results(orchestrator):
    """Verifies autonomic constraint relaxation when initial budget eliminates all buses."""
    ref_date = date(2026, 11, 14)
    # Budget of ₹870: SRS Travels is 850, but if budget is 800, no buses qualify
    overconstrained_req = SearchRequest(
        source="Bangalore",
        destination="Hyderabad",
        journey_date="2026-11-20",
        passengers=1,
        max_budget=800.0,  # All buses on BLR-HYD route cost >= 850
    )

    result = orchestrator.run_workflow(overconstrained_req, reference_date=ref_date)

    # Recovery engine relaxes budget by 25% (800 * 1.25 = 1000.0), unlocking SRS Travels (850) and KSRTC (980)
    assert result.status == WorkflowStatus.RECOVERED
    assert any(rec.strategy_used == "CONSTRAINT_RELAXATION" for rec in result.recovery_history)
    assert len(result.ranked_buses) > 0


def test_orchestrator_handles_simulated_report_failure(orchestrator, valid_request):
    """Verifies graceful degradation when report filesystem write fails."""
    ref_date = date(2026, 11, 14)
    faults = {"simulate_report_failure": True}
    result = orchestrator.run_workflow(valid_request, fault_injection=faults, reference_date=ref_date)

    assert result.status == WorkflowStatus.FAILED
    assert "ReportGenerationError" in (result.error_message or "")


def test_orchestrator_handles_repeated_workflow_failure(orchestrator, valid_request):
    """Verifies graceful handling of unrecoverable repeated workflow failure."""
    ref_date = date(2026, 11, 14)
    faults = {"repeated_workflow_failure": True}
    result = orchestrator.run_workflow(valid_request, fault_injection=faults, reference_date=ref_date)

    assert result.status == WorkflowStatus.FAILED
    assert "Repeated unrecoverable system crash" in (result.error_message or "")
