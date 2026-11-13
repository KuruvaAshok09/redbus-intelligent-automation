"""
Unit tests for RecoveryEngine module.
Verifies self-healing remediation, mirror fallbacks, catalog seed reconstruction,
and unrecoverable incident escalation.
"""

import pytest
from redbus_automation.models import (
    Bus,
    SearchRequest,
    TransientServiceError,
    DataFetchError,
    UnrecoverableIncidentError,
)
from redbus_automation.recovery_engine import RecoveryEngine


@pytest.fixture
def recovery_engine():
    return RecoveryEngine()


@pytest.fixture
def sample_request():
    return SearchRequest(
        source="Bangalore",
        destination="Hyderabad",
        journey_date="2026-11-20",
        passengers=1,
        max_budget=2000.0,
        preferred_operator="Orange",
    )


def test_recovery_handles_transient_failure_via_mirror(recovery_engine, sample_request):
    """Verifies successful self-healing via secondary offline mirror."""
    fallback_buses = [
        Bus(
            bus_id="BUS-FALLBACK-01",
            operator_name="Mirror Backup Travels",
            source="Bangalore",
            destination="Hyderabad",
            departure_time="20:00",
            arrival_time="05:00",
            fare=1000.0,
            available_seats=15,
            bus_type="AC Sleeper",
            rating=4.5,
        )
    ]

    exc = TransientServiceError("Simulated primary gateway timeout")
    buses, action = recovery_engine.handle_search_failure(
        exc=exc,
        request=sample_request,
        fallback_search_fn=lambda req: fallback_buses,
    )

    assert len(buses) == 1
    assert buses[0].bus_id == "BUS-FALLBACK-01"
    assert action.successful is True
    assert action.strategy_used == "SECONDARY_MIRROR_FALLBACK"
    assert len(recovery_engine.recovery_history) == 1


def test_recovery_escalates_when_fallback_fails(recovery_engine, sample_request):
    """Verifies escalation to UnrecoverableIncidentError when fallback provider crashes."""
    def broken_fallback(req):
        raise RuntimeError("Secondary mirror also unavailable")

    exc = TransientServiceError("Primary failure")
    with pytest.raises(UnrecoverableIncidentError, match="Self-healing failed"):
        recovery_engine.handle_search_failure(
            exc=exc,
            request=sample_request,
            fallback_search_fn=broken_fallback,
        )

    # Recovery history must record the failed action
    assert len(recovery_engine.recovery_history) == 1
    assert recovery_engine.recovery_history[0].successful is False


def test_recovery_remediates_zero_results(recovery_engine, sample_request):
    """Verifies self-healing constraint relaxation when strict filters yield zero buses."""
    raw_buses = [
        Bus(
            bus_id="BUS-EXP-01",
            operator_name="Luxury Travels",
            source="Bangalore",
            destination="Hyderabad",
            departure_time="21:00",
            arrival_time="06:00",
            fare=2400.0,  # Exceeds initial max_budget of 2000.0
            available_seats=10,
            bus_type="AC Sleeper",
            rating=4.6,
        )
    ]

    relaxed_req, action = recovery_engine.remediate_zero_results(
        request=sample_request,
        raw_buses=raw_buses,
    )

    assert action.successful is True
    assert action.strategy_used == "CONSTRAINT_RELAXATION"
    assert relaxed_req.max_budget > sample_request.max_budget
    assert relaxed_req.preferred_operator is None  # Relaxed operator filter
    assert len(recovery_engine.recovery_history) == 1
