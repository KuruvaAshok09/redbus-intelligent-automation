"""
Unit tests for BookingEngine simulation module.
Verifies simulated seat layout generation, interactive seat reservation,
PNR issuance, and booking history tracking.
"""

import builtins
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest

from redbus_automation.models import Bus, BookingConfirmation
from redbus_automation.booking_engine import BookingEngine


@pytest.fixture
def sample_bus():
    return Bus(
        bus_id="BUS-TEST-BOOK-1",
        operator_name="Test Express",
        source="Bangalore",
        destination="Hyderabad",
        departure_time="21:00",
        arrival_time="06:00",
        fare=1000.0,
        available_seats=15,
        bus_type="AC Sleeper (2+1)",
        rating=4.7,
    )


def test_generate_seat_layout(sample_bus):
    """Verifies simulated seat layout generates proper seat numbers and availability."""
    engine = BookingEngine()
    seats = engine.generate_seat_layout(sample_bus)

    assert len(seats) >= 24
    available_seats = [s for s in seats if s.is_available]
    assert len(available_seats) == sample_bus.available_seats
    assert seats[0].seat_number == "1A"
    assert seats[0].deck in ("Lower", "Upper")


def test_create_simulated_booking(tmp_path, sample_bus):
    """Verifies simulated booking creation, PNR generation, and disclaimer."""
    bookings_file = tmp_path / "simulated_bookings.jsonl"
    engine = BookingEngine(bookings_file=bookings_file)

    confirmation = engine.create_booking(
        execution_id="EXEC-TEST-001",
        bus=sample_bus,
        passenger_name="Ashok Kuruva",
        passenger_email="ashok@example.com",
        passenger_phone="+91 9999999999",
        selected_seats=["1A", "1B"],
        journey_date="2026-11-20",
    )

    assert isinstance(confirmation, BookingConfirmation)
    assert confirmation.pnr_number.startswith("SIM-PNR-")
    assert confirmation.status == "CONFIRMED (SIMULATED)"
    assert confirmation.booking_request.total_fare == 2000.0
    assert "DEMO / SIMULATION MODE" in confirmation.disclaimer
    assert bookings_file.exists()


def test_get_booking_history(tmp_path, sample_bus):
    """Verifies retrieval of historical simulated bookings."""
    bookings_file = tmp_path / "simulated_bookings.jsonl"
    engine = BookingEngine(bookings_file=bookings_file)

    engine.create_booking(
        execution_id="EXEC-TEST-001",
        bus=sample_bus,
        passenger_name="Passenger One",
        passenger_email="p1@example.com",
        passenger_phone="+91 1111111111",
        selected_seats=["2A"],
        journey_date="2026-11-20",
    )

    history = engine.get_all_bookings()
    assert len(history) == 1
    assert history[0]["passenger_name"] == "Passenger One"
    assert history[0]["bus_id"] == "BUS-TEST-BOOK-1"


def test_duplicate_seat_booking_is_rejected(tmp_path, sample_bus):
    engine = BookingEngine(bookings_file=tmp_path / "simulated_bookings.jsonl")
    booking_args = {
        "execution_id": "EXEC-TEST-001",
        "bus": sample_bus,
        "passenger_name": "Demo Passenger",
        "passenger_email": "demo@example.invalid",
        "passenger_phone": "0000000000",
        "selected_seats": ["1A"],
        "journey_date": "2026-11-20",
    }

    engine.create_booking(**booking_args)

    with pytest.raises(ValueError, match="already been booked"):
        engine.create_booking(**booking_args)

    assert len(engine.get_all_bookings()) == 1


def test_failed_booking_does_not_reserve_seat(tmp_path, sample_bus):
    engine = BookingEngine(bookings_file=tmp_path / "simulated_bookings.jsonl")
    booking_args = {
        "execution_id": "EXEC-TEST-002",
        "bus": sample_bus,
        "passenger_name": "Demo Passenger",
        "passenger_email": "demo@example.invalid",
        "passenger_phone": "0000000000",
        "selected_seats": ["INVALID"],
        "journey_date": "2026-11-20",
    }

    with pytest.raises(ValueError, match="unavailable"):
        engine.create_booking(**booking_args)

    assert engine.get_all_bookings() == []
    confirmation = engine.create_booking(**{**booking_args, "selected_seats": ["1A"]})
    assert confirmation.booking_request.selected_seats == ["1A"]
    assert len(engine.get_all_bookings()) == 1


def test_persistence_failure_does_not_reserve_seat(tmp_path, sample_bus, monkeypatch):
    bookings_file = tmp_path / "simulated_bookings.jsonl"
    engine = BookingEngine(bookings_file=bookings_file)
    original_open = builtins.open

    def fail_append(file, mode="r", *args, **kwargs):
        if Path(file) == bookings_file and mode == "a+":
            raise OSError("Simulated storage failure")
        return original_open(file, mode, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(builtins, "open", fail_append)
        with pytest.raises(OSError, match="Simulated storage failure"):
            engine.create_booking(
                execution_id="EXEC-TEST-IO",
                bus=sample_bus,
                passenger_name="Demo Passenger",
                passenger_email="demo@example.invalid",
                passenger_phone="0000000000",
                selected_seats=["1A"],
                journey_date="2026-11-20",
            )

    assert engine.get_all_bookings() == []
    confirmation = engine.create_booking(
        execution_id="EXEC-TEST-IO-RECOVERED",
        bus=sample_bus,
        passenger_name="Demo Passenger",
        passenger_email="demo@example.invalid",
        passenger_phone="0000000000",
        selected_seats=["1A"],
        journey_date="2026-11-20",
    )
    assert confirmation.booking_request.selected_seats == ["1A"]


def test_concurrent_duplicate_booking_only_confirms_once(tmp_path, sample_bus):
    bookings_file = tmp_path / "simulated_bookings.jsonl"
    engines = [BookingEngine(bookings_file=bookings_file) for _ in range(2)]

    def attempt_booking(engine, execution_id):
        try:
            engine.create_booking(
                execution_id=execution_id,
                bus=sample_bus,
                passenger_name="Demo Passenger",
                passenger_email="demo@example.invalid",
                passenger_phone="0000000000",
                selected_seats=["1A"],
                journey_date="2026-11-20",
            )
            return "confirmed"
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(
            lambda args: attempt_booking(*args),
            [(engines[0], "EXEC-CONCURRENT-1"), (engines[1], "EXEC-CONCURRENT-2")],
        ))

    assert sorted(outcomes) == ["confirmed", "rejected"]
    assert len(engines[0].get_all_bookings()) == 1
