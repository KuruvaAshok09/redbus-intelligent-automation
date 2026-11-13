"""
Simulated Bus Booking Workflow Engine for RedBus Automation Platform.
Provides seat layout generation, interactive seat reservation simulation,
PNR confirmation reference issuance, and booking audit history.

NOTE: Operating in DEMO / SIMULATION MODE. No real ticket is booked or paid.
"""

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    Bus,
    Seat,
    BookingRequest,
    BookingConfirmation,
    AutomationEventType,
    LogSeverity,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER


class BookingEngine:
    """Manages simulated seat layouts, reservations, and PNR references."""

    COMPONENT_NAME = "BookingEngine"
    _lock = threading.Lock()

    def __init__(self, bookings_file: Optional[Path] = None):
        self.bookings_file = bookings_file or CONFIG.BOOKINGS_FILE_PATH
        self.bookings_file.parent.mkdir(parents=True, exist_ok=True)
        self._in_memory_bookings: List[BookingConfirmation] = []

    def generate_seat_layout(self, bus: Bus) -> List[Seat]:
        """
        Generates deterministic simulated seat layout for a bus.
        Calculates available vs occupied seats matching bus.available_seats count.
        """
        total_seats = max(24, bus.available_seats + 6)
        # Bounded seat grid: Lower deck (1-18), Upper deck (19-total)
        seats: List[Seat] = []
        available_target = bus.available_seats

        for i in range(1, total_seats + 1):
            deck = "Lower" if i <= 18 else "Upper"
            seat_letter = ["A", "B", "C", "D"][(i - 1) % 4]
            row_num = ((i - 1) // 4) + 1
            seat_num = f"{row_num}{seat_letter}"
            berth_type = "Window" if seat_letter in ("A", "D") else "Aisle"

            # Allocate availability: available_target count available, remainder booked
            is_avail = (i <= available_target)

            seats.append(
                Seat(
                    seat_number=seat_num,
                    deck=deck,
                    berth_type=berth_type,
                    is_available=is_avail,
                    fare=bus.fare,
                )
            )

        return seats

    def create_booking(
        self,
        execution_id: str,
        bus: Bus,
        passenger_name: str,
        passenger_email: str,
        passenger_phone: str,
        selected_seats: List[str],
        journey_date: str,
    ) -> BookingConfirmation:
        """
        Processes simulated passenger booking and issues a unique PNR confirmation.
        Enforces clear DEMO / SIMULATION MODE labeling.
        """
        if not selected_seats:
            raise ValueError("Select at least one available seat.")
        if any(not isinstance(seat, str) for seat in selected_seats):
            raise ValueError("Seat numbers must be strings.")
        if len(set(selected_seats)) != len(selected_seats):
            raise ValueError("A seat cannot be selected more than once.")

        available_seat_numbers = {
            seat.seat_number
            for seat in self.generate_seat_layout(bus)
            if seat.is_available
        }
        if any(seat not in available_seat_numbers for seat in selected_seats):
            raise ValueError("One or more selected seats are unavailable.")

        booking_id = f"BKG-{uuid.uuid4().hex[:8].upper()}"
        pnr_number = f"SIM-PNR-{uuid.uuid4().hex[:6].upper()}"
        ts = datetime.now().isoformat()
        total_fare = round(bus.fare * len(selected_seats), 2)

        booking_req = BookingRequest(
            booking_id=booking_id,
            execution_id=execution_id,
            bus_id=bus.bus_id,
            operator_name=bus.operator_name,
            source=bus.source,
            destination=bus.destination,
            journey_date=journey_date,
            passenger_name=passenger_name.strip(),
            passenger_email=passenger_email.strip(),
            passenger_phone=passenger_phone.strip(),
            selected_seats=list(selected_seats),
            total_fare=total_fare,
            created_at=ts,
        )

        confirmation = BookingConfirmation(
            confirmation_reference=f"REF-{uuid.uuid4().hex[:8].upper()}",
            pnr_number=pnr_number,
            status="CONFIRMED (SIMULATED)",
            booking_request=booking_req,
            bus=bus,
            timestamp=ts,
            disclaimer=CONFIG.SIMULATION_DISCLAIMER,
        )

        with self._lock:
            existing_bookings = self._read_persisted_bookings()
            existing_bookings.extend(
                self._booking_to_record(existing)
                for existing in self._in_memory_bookings
            )
            booked_seats = {
                seat
                for existing in existing_bookings
                if existing.get("bus_id") == bus.bus_id
                and existing.get("journey_date") == journey_date
                for seat in existing.get("selected_seats", [])
            }
            if booked_seats.intersection(selected_seats):
                raise ValueError("One or more selected seats have already been booked for this bus and journey date.")

            record = self._booking_to_record(confirmation)
            with open(self.bookings_file, "a+", encoding="utf-8") as f:
                f.seek(0, 2)
                original_size = f.tell()
                try:
                    f.write(json.dumps(record) + "\n")
                    f.flush()
                except OSError:
                    f.seek(original_size)
                    f.truncate()
                    raise
            self._in_memory_bookings.append(confirmation)

        LOGGER.log(
            execution_id=execution_id,
            component=self.COMPONENT_NAME,
            event_type=AutomationEventType.BOOKING_SIMULATED,
            severity=LogSeverity.INFO,
            message=f"Simulated booking confirmed. PNR: {pnr_number} for {passenger_name} ({len(selected_seats)} seats).",
            status=WorkflowStatus.SUCCESS,
            metadata={"pnr": pnr_number, "bus_id": bus.bus_id, "total_fare": total_fare},
        )

        return confirmation

    def get_all_bookings(self) -> List[Dict[str, Any]]:
        """Retrieves history of simulated bookings."""
        with self._lock:
            if self.bookings_file.exists():
                return self._read_persisted_bookings()
            return [
                self._booking_to_record(confirmation)
                for confirmation in self._in_memory_bookings
            ]

    def _read_persisted_bookings(self) -> List[Dict[str, Any]]:
        """Reads booking records from the existing JSONL storage."""
        if not self.bookings_file.exists():
            return []

        records: List[Dict[str, Any]] = []
        with open(self.bookings_file, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"Invalid booking record at line {line_number} in {self.bookings_file}."
                        ) from error
        return records

    @staticmethod
    def _booking_to_record(confirmation: BookingConfirmation) -> Dict[str, Any]:
        """Converts a simulated confirmation into its persisted JSON shape."""
        request = confirmation.booking_request
        if request is None:
            raise ValueError("Booking confirmation is missing its request details.")
        return {
            "confirmation_reference": confirmation.confirmation_reference,
            "pnr_number": confirmation.pnr_number,
            "status": confirmation.status,
            "timestamp": confirmation.timestamp,
            "passenger_name": request.passenger_name,
            "passenger_email": request.passenger_email,
            "passenger_phone": request.passenger_phone,
            "bus_id": request.bus_id,
            "operator_name": request.operator_name,
            "source": request.source,
            "destination": request.destination,
            "journey_date": request.journey_date,
            "selected_seats": request.selected_seats,
            "total_fare": request.total_fare,
            "execution_id": request.execution_id,
            "disclaimer": confirmation.disclaimer,
        }

    def reset_bookings(self) -> None:
        """Wipes simulated booking storage for clean testing."""
        with self._lock:
            self._in_memory_bookings.clear()
            if self.bookings_file.exists():
                try:
                    self.bookings_file.unlink()
                except Exception:
                    pass


# Global Booking singleton
BOOKING_ENGINE = BookingEngine()
