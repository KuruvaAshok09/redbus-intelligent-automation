"""
Integration tests for AutomationOrchestrator module.
Verifies complete end-to-end lifecycle orchestration, state transitions,
fault injections, and self-healing autonomics.
"""

from datetime import date
import pytest

from redbus_automation.config import CONFIG
from redbus_automation.incident_manager import INCIDENT_MANAGER
from redbus_automation.logger import LOGGER
from redbus_automation.models import SearchRequest, WorkflowStatus
from redbus_automation.orchestrator import AutomationOrchestrator
from redbus_automation.booking_engine import BookingEngine


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


def test_bangalore_chennai_search_results_can_be_booked(orchestrator, tmp_path):
    """Keeps the requested offline route connected from orchestration through booking."""
    request = SearchRequest(
        source="Bangalore",
        destination="Chennai",
        journey_date="2026-11-16",
        passengers=1,
        max_budget=2500.0,
        min_rating=3.0,
    )
    result = orchestrator.run_workflow(
        request,
        reference_date=date(2026, 11, 13),
    )

    assert result.status == WorkflowStatus.SUCCESS
    assert result.buses_found
    assert result.ranked_buses
    assert result.recommended_bus is not None
    assert all(
        ranked.bus.source == "Bangalore"
        and ranked.bus.destination == "Chennai"
        and ranked.bus.fare <= request.max_budget
        and ranked.bus.available_seats >= request.passengers
        and ranked.bus.rating >= request.min_rating
        for ranked in result.ranked_buses
    )

    selected_bus = result.recommended_bus.bus
    booking_engine = BookingEngine(
        bookings_file=tmp_path / "simulated_bookings.jsonl"
    )
    available_seats = [
        seat.seat_number
        for seat in booking_engine.generate_seat_layout(selected_bus)
        if seat.is_available
    ]
    confirmation = booking_engine.create_booking(
        execution_id=result.execution_id,
        bus=selected_bus,
        passenger_name="Demo Passenger",
        passenger_email="demo@example.invalid",
        passenger_phone="0000000000",
        selected_seats=[available_seats[0]],
        journey_date=request.journey_date,
    )

    assert confirmation.status == "CONFIRMED (SIMULATED)"
    assert confirmation.booking_request.bus_id == selected_bus.bus_id
    assert confirmation.booking_request.journey_date == request.journey_date


def test_scenario_two_recovers_bangalore_chennai_after_retries(orchestrator):
    """Uses valid secondary-mirror inventory after simulated gateway failures."""
    request = SearchRequest(
        source="Bangalore",
        destination="Chennai",
        journey_date="2026-11-16",
        passengers=10,
        max_budget=1000.0,
        min_rating=3.0,
    )

    result = orchestrator.run_workflow(
        request,
        fault_injection={"simulate_transient_failure": True},
        reference_date=date(2026, 11, 13),
    )

    assert result.status == WorkflowStatus.RECOVERED
    assert result.request.journey_date == request.journey_date
    assert result.buses_found
    assert all(
        bus.bus_id.startswith("FALLBACK-BLR-CHN-")
        and bus.source == request.source
        and bus.destination == request.destination
        and bus.available_seats >= request.passengers
        and bus.fare <= request.max_budget
        for bus in result.buses_found
    )
    assert result.recovery_history[-1].strategy_used == "SECONDARY_MIRROR_FALLBACK"
    assert result.recovery_history[-1].successful is True

    execution_logs = LOGGER.get_logs(result.execution_id)
    retry_logs = [
        entry
        for entry in execution_logs
        if entry["event_type"] == "RETRY_TRIGGERED"
    ]
    assert len(retry_logs) == CONFIG.DEFAULT_MAX_RETRIES
    assert any("HTTP 503 Simulated" in entry["message"] for entry in retry_logs)
    assert len(result.retry_history) == len(retry_logs)
    assert [attempt.attempt_number for attempt in result.retry_history] == [1, 2, 3]

    incidents = INCIDENT_MANAGER.get_incidents(execution_id=result.execution_id)
    assert len(incidents) == 1
    assert incidents[0].final_status == "RESOLVED"
    assert incidents[0].recovery_action == "SECONDARY_MIRROR_FALLBACK"
    assert "HTTP 503 Simulated" in incidents[0].error_message
    assert incidents[0].retry_attempts == len(retry_logs)
    assert incidents[0].details["retry_events"] == retry_logs


def test_unsupported_route_returns_no_simulated_buses(orchestrator):
    request = SearchRequest(
        source="Bangalore",
        destination="Jaipur",
        journey_date="2026-11-20",
        passengers=1,
        max_budget=2500.0,
    )

    result = orchestrator.run_workflow(
        request,
        reference_date=date(2026, 11, 14),
    )

    assert result.status == WorkflowStatus.SUCCESS
    assert result.buses_found == []
    assert result.ranked_buses == []


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
