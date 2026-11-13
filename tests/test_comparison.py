"""
Unit tests for BusComparisonEngine and BusFilterEngine.
Verifies multi-criteria decision ranking determinism, explainability, and filter rules.
"""

import pytest
from redbus_automation.models import Bus, SearchRequest
from redbus_automation.comparison_engine import BusComparisonEngine
from redbus_automation.filter_engine import BusFilterEngine


@pytest.fixture
def candidate_buses():
    """Provides a controlled set of simulated buses for comparison."""
    return [
        Bus(
            bus_id="BUS-A",
            operator_name="Operator Fast Budget",
            source="Bangalore",
            destination="Hyderabad",
            departure_time="21:00",
            arrival_time="05:00",  # 8 hours = 480 mins
            fare=800.0,
            available_seats=20,
            bus_type="AC Sleeper",
            rating=4.8,
        ),
        Bus(
            bus_id="BUS-B",
            operator_name="Operator Slow Expensive",
            source="Bangalore",
            destination="Hyderabad",
            departure_time="18:00",
            arrival_time="06:00",  # 12 hours = 720 mins
            fare=1800.0,
            available_seats=5,
            bus_type="Non-AC Seater",
            rating=3.5,
        ),
        Bus(
            bus_id="BUS-C",
            operator_name="Operator Moderate",
            source="Bangalore",
            destination="Hyderabad",
            departure_time="22:00",
            arrival_time="07:00",  # 9 hours = 540 mins
            fare=1100.0,
            available_seats=15,
            bus_type="AC Semi-Sleeper",
            rating=4.2,
        ),
    ]


def test_ranking_empty_buses_returns_empty():
    """Verifies passing an empty list returns an empty ranked list."""
    assert BusComparisonEngine.rank_buses([]) == []


def test_ranking_is_deterministic(candidate_buses):
    """Verifies that ranking produces identical order and scores on repeated executions."""
    run1 = BusComparisonEngine.rank_buses(candidate_buses)
    run2 = BusComparisonEngine.rank_buses(candidate_buses)

    assert len(run1) == len(run2)
    for r1, r2 in zip(run1, run2):
        assert r1.bus.bus_id == r2.bus.bus_id
        assert r1.composite_score == r2.composite_score
        assert r1.rank == r2.rank
        assert r1.recommendation_reason == r2.recommendation_reason


def test_optimal_bus_ranks_first(candidate_buses):
    """Verifies that the bus with lower fare, shorter duration, and higher rating scores top."""
    ranked = BusComparisonEngine.rank_buses(candidate_buses)
    top_bus = ranked[0]

    assert top_bus.bus.bus_id == "BUS-A"
    assert top_bus.rank == 1
    assert top_bus.composite_score > ranked[1].composite_score
    assert "Top Recommendation" in top_bus.recommendation_reason


def test_all_ranked_buses_have_explainable_reasons(candidate_buses):
    """Verifies that every ranked bus receives a non-empty human-readable explanation."""
    ranked = BusComparisonEngine.rank_buses(candidate_buses)
    for rb in ranked:
        assert isinstance(rb.recommendation_reason, str)
        assert len(rb.recommendation_reason) > 10


def test_composite_scores_within_normalized_bounds(candidate_buses):
    """Verifies that composite MCDA scores are within the [0.0, 1.0] interval."""
    ranked = BusComparisonEngine.rank_buses(candidate_buses)
    for rb in ranked:
        assert 0.0 <= rb.composite_score <= 1.0


# -------------------------------------------------------------
# Filtering Engine Tests
# -------------------------------------------------------------

def test_filter_by_max_budget(candidate_buses):
    """Verifies buses exceeding max budget are excluded."""
    req = SearchRequest(source="Bangalore", destination="Hyderabad", journey_date="2026-11-20", max_budget=1000.0)
    filtered = BusFilterEngine.apply_filters(candidate_buses, req)

    assert len(filtered) == 1
    assert filtered[0].bus_id == "BUS-A"


def test_filter_by_passenger_seat_availability(candidate_buses):
    """Verifies buses with insufficient available seats are filtered out."""
    req = SearchRequest(source="Bangalore", destination="Hyderabad", journey_date="2026-11-20", passengers=10)
    filtered = BusFilterEngine.apply_filters(candidate_buses, req)

    # Only BUS-A (20 seats) and BUS-C (15 seats) should remain; BUS-B (5 seats) excluded
    assert len(filtered) == 2
    ids = [b.bus_id for b in filtered]
    assert "BUS-A" in ids
    assert "BUS-C" in ids
    assert "BUS-B" not in ids


def test_filter_by_minimum_rating(candidate_buses):
    """Verifies rating threshold enforcement."""
    req = SearchRequest(source="Bangalore", destination="Hyderabad", journey_date="2026-11-20", min_rating=4.5)
    filtered = BusFilterEngine.apply_filters(candidate_buses, req)

    assert len(filtered) == 1
    assert filtered[0].bus_id == "BUS-A"


def test_filter_by_preferred_operator(candidate_buses):
    """Verifies operator substring matching."""
    req = SearchRequest(source="Bangalore", destination="Hyderabad", journey_date="2026-11-20", preferred_operator="Moderate")
    filtered = BusFilterEngine.apply_filters(candidate_buses, req)

    assert len(filtered) == 1
    assert filtered[0].bus_id == "BUS-C"
