"""Regression coverage for simulated inter-state routes and mirror recovery."""

import json
from datetime import date

import pytest

from redbus_automation.booking_engine import BookingEngine
from redbus_automation.config import CONFIG
from redbus_automation.models import SearchRequest, WorkflowStatus
from redbus_automation.orchestrator import AutomationOrchestrator
from redbus_automation.search_engine import BusSearchEngine


INTERSTATE_ROUTE_DIRECTIONS = (
    ("Bangalore", "Chennai"),
    ("Chennai", "Bangalore"),
    ("Bangalore", "Hyderabad"),
    ("Hyderabad", "Bangalore"),
    ("Delhi", "Jaipur"),
    ("Jaipur", "Delhi"),
    ("Mumbai", "Ahmedabad"),
    ("Ahmedabad", "Mumbai"),
    ("Mumbai", "Panaji"),
    ("Panaji", "Mumbai"),
    ("Kolkata", "Bhubaneswar"),
    ("Bhubaneswar", "Kolkata"),
    ("Lucknow", "Patna"),
    ("Patna", "Lucknow"),
    ("Chandigarh", "Shimla"),
    ("Shimla", "Chandigarh"),
    ("Kochi", "Coimbatore"),
    ("Coimbatore", "Kochi"),
    ("Indore", "Jaipur"),
    ("Jaipur", "Indore"),
)


def test_primary_and_fallback_catalogs_cover_the_same_simulated_routes():
    with open(CONFIG.DEFAULT_DATA_FILE, encoding="utf-8") as file:
        primary_buses = json.load(file)
    with open(CONFIG.DEFAULT_FALLBACK_DATA_FILE, encoding="utf-8") as file:
        fallback_buses = json.load(file)

    primary_routes = {
        (bus["source"], bus["destination"]) for bus in primary_buses
    }
    fallback_routes = {
        (bus["source"], bus["destination"]) for bus in fallback_buses
    }

    assert set(INTERSTATE_ROUTE_DIRECTIONS) <= primary_routes
    assert primary_routes == fallback_routes
    assert all(
        bus["data_source"] == "SIMULATED_DEMO"
        for bus in primary_buses + fallback_buses
    )


def test_city_options_include_cities_from_primary_and_fallback_catalogs():
    cities = set(BusSearchEngine().get_all_cities())

    assert {"Ahmedabad", "Kochi", "Coimbatore"} <= cities
    assert {
        city
        for route in INTERSTATE_ROUTE_DIRECTIONS
        for city in route
    } <= cities


@pytest.mark.parametrize(("source", "destination"), INTERSTATE_ROUTE_DIRECTIONS)
def test_route_search_filter_and_simulated_booking(
    source, destination, tmp_path
):
    request = SearchRequest(
        source=source,
        destination=destination,
        journey_date="2026-11-20",
        passengers=2,
        max_budget=2000.0,
        min_rating=4.0,
    )
    result = AutomationOrchestrator().run_workflow(
        request,
        reference_date=date(2026, 11, 13),
    )

    assert result.status == WorkflowStatus.SUCCESS
    assert result.ranked_buses
    assert all(
        ranked.bus.source == source
        and ranked.bus.destination == destination
        and ranked.bus.fare <= request.max_budget
        and ranked.bus.available_seats >= request.passengers
        and ranked.bus.rating >= request.min_rating
        for ranked in result.ranked_buses
    )

    selected_bus = result.recommended_bus.bus
    booking_engine = BookingEngine(
        bookings_file=tmp_path / "simulated_bookings.jsonl"
    )
    seat = next(
        seat
        for seat in booking_engine.generate_seat_layout(selected_bus)
        if seat.is_available
    )
    confirmation = booking_engine.create_booking(
        execution_id=result.execution_id,
        bus=selected_bus,
        passenger_name="Demo Passenger",
        passenger_email="demo@example.invalid",
        passenger_phone="0000000000",
        selected_seats=[seat.seat_number],
        journey_date=request.journey_date,
    )

    assert confirmation.status == "CONFIRMED (SIMULATED)"
    assert confirmation.pnr_number.startswith("SIM-PNR-")


@pytest.mark.parametrize(("source", "destination"), INTERSTATE_ROUTE_DIRECTIONS)
def test_scenario_two_uses_matching_secondary_mirror_route(source, destination):
    request = SearchRequest(
        source=source,
        destination=destination,
        journey_date="2026-11-20",
        passengers=10,
        max_budget=2000.0,
        min_rating=4.0,
    )
    result = AutomationOrchestrator().run_workflow(
        request,
        fault_injection={"simulate_transient_failure": True},
        reference_date=date(2026, 11, 13),
    )

    assert result.status == WorkflowStatus.RECOVERED
    assert result.recovery_history[-1].strategy_used == "SECONDARY_MIRROR_FALLBACK"
    assert result.recovery_history[-1].successful
    assert result.buses_found
    assert all(
        bus.bus_id.startswith("FALLBACK-")
        and bus.source == source
        and bus.destination == destination
        and bus.fare <= request.max_budget
        and bus.available_seats >= request.passengers
        for bus in result.buses_found
    )


def test_scenario_two_fails_explicitly_when_mirror_route_is_missing():
    request = SearchRequest(
        source="Kashmir",
        destination="Kanyakumari",
        journey_date="2026-11-20",
        passengers=1,
        max_budget=2000.0,
    )
    result = AutomationOrchestrator().run_workflow(
        request,
        fault_injection={"simulate_transient_failure": True},
        reference_date=date(2026, 11, 13),
    )

    assert result.status == WorkflowStatus.FAILED
    assert "Self-healing failed" in (result.error_message or "")
    assert "zero valid candidate buses" in (result.error_message or "")
