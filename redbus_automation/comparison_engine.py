"""
Comparison and Ranking Engine for RedBus Automation Platform.
Implements deterministic, multi-criteria normalization scoring with full explainability.
"""

from typing import List, Optional
from redbus_automation.config import CONFIG
from redbus_automation.models import (
    Bus,
    RankedBus,
    LogSeverity,
    AutomationEventType,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER


class BusComparisonEngine:
    """Ranks buses using normalized weighted multi-criteria decision analysis (MCDA)."""

    COMPONENT_NAME = "BusComparisonEngine"

    @classmethod
    def rank_buses(
        cls,
        buses: List[Bus],
        execution_id: str = "SYSTEM_RANKING",
    ) -> List[RankedBus]:
        """
        Ranks buses deterministically using weighted multi-criteria evaluation:
        - Fare (40%): Lower fare is superior.
        - Duration (25%): Shorter travel time is superior.
        - Rating (25%): Higher customer rating is superior.
        - Seat Availability (10%): Higher confirmed availability is superior.

        Produces an explainable recommendation text for every ranked bus.
        """
        if not buses:
            LOGGER.log(
                execution_id=execution_id,
                component=cls.COMPONENT_NAME,
                event_type=AutomationEventType.RANKING_COMPLETED,
                severity=LogSeverity.INFO,
                message="Ranking skipped: no candidate buses provided.",
                status=WorkflowStatus.RUNNING,
                metadata={"total_ranked": 0},
            )
            return []

        # Find bounds for min-max normalization
        fares = [b.fare for b in buses]
        durations = [b.duration_minutes for b in buses]

        min_fare, max_fare = min(fares), max(fares)
        min_dur, max_dur = min(durations), max(durations)

        scored_buses: List[tuple] = []

        for bus in buses:
            # 1. Fare Score: 1.0 for cheapest, 0.0 for most expensive
            if max_fare == min_fare:
                fare_score = 1.0
            else:
                fare_score = (max_fare - bus.fare) / (max_fare - min_fare)

            # 2. Duration Score: 1.0 for fastest, 0.0 for slowest
            if max_dur == min_dur:
                dur_score = 1.0
            else:
                dur_score = (max_dur - bus.duration_minutes) / (max_dur - min_dur)

            # 3. Rating Score: Normalized between 0.0 and 1.0 against 5-star scale
            rating_score = max(0.0, min(1.0, bus.rating / 5.0))

            # 4. Seat Score: Normalized up to 30 available seats
            seat_score = max(0.0, min(1.0, bus.available_seats / 30.0))

            # Composite Score (0.0 to 1.0)
            composite = (
                CONFIG.WEIGHT_FARE * fare_score
                + CONFIG.WEIGHT_DURATION * dur_score
                + CONFIG.WEIGHT_RATING * rating_score
                + CONFIG.WEIGHT_SEATS * seat_score
            )

            scored_buses.append((composite, bus, fare_score, dur_score, rating_score, seat_score))

        # Deterministic sorting: highest score first, then tie-breakers: lower fare, shorter duration, higher rating, bus_id
        scored_buses.sort(
            key=lambda item: (
                -round(item[0], 5),
                item[1].fare,
                item[1].duration_minutes,
                -item[1].rating,
                item[1].bus_id,
            )
        )

        ranked_results: List[RankedBus] = []
        for idx, (composite, bus, f_sc, d_sc, r_sc, s_sc) in enumerate(scored_buses, start=1):
            reason = cls._generate_explanation(
                bus=bus,
                rank=idx,
                composite=composite,
                is_cheapest=(bus.fare == min_fare),
                is_fastest=(bus.duration_minutes == min_dur),
                is_top_rated=(bus.rating == max(b.rating for b in buses)),
            )

            ranked_results.append(
                RankedBus(
                    bus=bus,
                    rank=idx,
                    composite_score=round(composite, 4),
                    recommendation_reason=reason,
                )
            )

        LOGGER.log(
            execution_id=execution_id,
            component=cls.COMPONENT_NAME,
            event_type=AutomationEventType.RANKING_COMPLETED,
            severity=LogSeverity.INFO,
            message=f"Ranking completed: {len(ranked_results)} buses evaluated. Top bus: {ranked_results[0].bus.bus_id}.",
            status=WorkflowStatus.RUNNING,
            metadata={
                "top_bus_id": ranked_results[0].bus.bus_id,
                "top_score": ranked_results[0].composite_score,
                "total_ranked": len(ranked_results),
            },
        )

        return ranked_results

    @classmethod
    def _generate_explanation(
        cls,
        bus: Bus,
        rank: int,
        composite: float,
        is_cheapest: bool,
        is_fastest: bool,
        is_top_rated: bool,
    ) -> str:
        """Constructs an explainable natural-language justification for the bus ranking."""
        highlights = []
        if is_cheapest:
            highlights.append("lowest fare in its class")
        if is_fastest:
            highlights.append("shortest transit duration")
        if is_top_rated:
            highlights.append("highest passenger satisfaction rating")
        if bus.rating >= 4.5:
            highlights.append(f"exceptional {bus.rating}★ rating")
        if bus.available_seats >= 15:
            highlights.append(f"high seat availability ({bus.available_seats} seats)")

        highlight_str = ", ".join(highlights) if highlights else f"balanced fare (₹{bus.fare:.2f}) and duration ({bus.duration_formatted})"

        if rank == 1:
            return f"Top Recommendation: Best overall composite value ({composite:.2f}) with {highlight_str}."
        elif rank <= 3:
            return f"Strong Alternative (Rank #{rank}): Highly competitive option offering {highlight_str}."
        else:
            return f"Standard Option (Rank #{rank}): Score {composite:.2f} based on ₹{bus.fare:.2f} fare, {bus.duration_formatted} duration, and {bus.rating}★ rating."
