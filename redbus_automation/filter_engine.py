"""
Filtering Engine for RedBus Automation Platform.
Applies deterministic filtering rules including fare, seat availability, operator, and schedule.
"""

from typing import List, Optional, Tuple
from redbus_automation.models import (
    Bus,
    SearchRequest,
    LogSeverity,
    AutomationEventType,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER


class BusFilterEngine:
    """Applies multiple domain filters to raw search results."""

    COMPONENT_NAME = "BusFilterEngine"

    @classmethod
    def apply_filters(
        cls,
        buses: List[Bus],
        request: SearchRequest,
        execution_id: str = "SYSTEM_FILTER",
        departure_window: Optional[Tuple[str, str]] = None,
    ) -> List[Bus]:
        """
        Filters a list of buses according to user criteria:
        - Budget: bus.fare <= request.max_budget
        - Seat availability: bus.available_seats >= request.passengers
        - Minimum rating: bus.rating >= request.min_rating (if specified)
        - Operator: substring match on request.preferred_operator (if specified)
        - Departure time window: (start_time, end_time) e.g. ("18:00", "23:59")
        """
        initial_count = len(buses)
        filtered: List[Bus] = []

        for bus in buses:
            # 1. Budget constraint
            if bus.fare > request.max_budget:
                continue

            # 2. Seat availability constraint
            if bus.available_seats < request.passengers:
                continue

            # 3. Minimum rating constraint
            if request.min_rating is not None and bus.rating < request.min_rating:
                continue

            # 4. Preferred operator constraint
            if request.preferred_operator:
                req_op = request.preferred_operator.strip().lower()
                if req_op not in bus.operator_name.lower():
                    continue

            # 5. Departure time window constraint
            if departure_window:
                start_t, end_t = departure_window
                if not (start_t <= bus.departure_time <= end_t):
                    continue

            filtered.append(bus)

        LOGGER.log(
            execution_id=execution_id,
            component=cls.COMPONENT_NAME,
            event_type=AutomationEventType.FILTER_APPLIED,
            severity=LogSeverity.INFO,
            message=f"Filtering applied: {len(filtered)}/{initial_count} buses retained.",
            status=WorkflowStatus.RUNNING,
            metadata={
                "initial_count": initial_count,
                "filtered_count": len(filtered),
                "max_budget": request.max_budget,
                "passengers": request.passengers,
                "preferred_operator": request.preferred_operator,
                "min_rating": request.min_rating,
            },
        )

        return filtered
