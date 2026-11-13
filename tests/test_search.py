"""
Unit tests for BusSearchEngine module.
Verifies simulated bus catalog querying, offline local loading, and fault injection hooks.
"""

from pathlib import Path
import pytest

from redbus_automation.config import CONFIG
from redbus_automation.models import SearchRequest, TransientServiceError, DataFetchError
from redbus_automation.search_engine import BusSearchEngine


@pytest.fixture
def search_engine():
    """Provides initialized search engine with default catalog."""
    return BusSearchEngine()


@pytest.fixture
def sample_request():
    return SearchRequest(
        source="Bangalore",
        destination="Hyderabad",
        journey_date="2026-11-20",
    )


def test_catalog_contains_at_least_15_buses(search_engine):
    """Verifies that the simulated offline dataset satisfies the >= 15 buses requirement."""
    all_buses = search_engine._load_data(execution_id="TEST_COUNT")
    assert len(all_buses) >= 15, f"Expected at least 15 buses in catalog, found {len(all_buses)}."


def test_search_returns_matches_for_known_route(search_engine, sample_request):
    """Verifies search returns matching buses for Bangalore -> Hyderabad."""
    buses = search_engine.search(sample_request)
    assert len(buses) > 0
    for b in buses:
        assert b.source.lower() == "bangalore"
        assert b.destination.lower() == "hyderabad"
        assert b.bus_id
        assert b.fare > 0
        assert b.rating >= 0


def test_search_is_case_insensitive(search_engine):
    """Verifies search handles lowercase and uppercase input variations."""
    req_lower = SearchRequest(source="bangalore", destination="hyderabad", journey_date="2026-11-20")
    req_upper = SearchRequest(source="BANGALORE", destination="HYDERABAD", journey_date="2026-11-20")

    res_lower = search_engine.search(req_lower)
    res_upper = search_engine.search(req_upper)

    assert len(res_lower) == len(res_upper)
    assert [b.bus_id for b in res_lower] == [b.bus_id for b in res_upper]


def test_search_returns_empty_for_unserved_route(search_engine):
    """Verifies unserved routes return an empty list without error."""
    unserved_req = SearchRequest(source="Kashmir", destination="Kanyakumari", journey_date="2026-11-20")
    results = search_engine.search(unserved_req)
    assert results == []


def test_fault_injection_transient_failure(search_engine, sample_request):
    """Verifies simulate_transient_failure raises TransientServiceError."""
    with pytest.raises(TransientServiceError, match="FAULT INJECTION"):
        search_engine.search(sample_request, simulate_transient_failure=True)


def test_fault_injection_corruption(search_engine, sample_request):
    """Verifies simulate_corruption raises DataFetchError."""
    with pytest.raises(DataFetchError, match="FAULT INJECTION"):
        search_engine.search(sample_request, simulate_corruption=True)


def test_fault_injection_force_empty(search_engine, sample_request):
    """Verifies force_empty yields an empty list."""
    results = search_engine.search(sample_request, force_empty=True)
    assert results == []


def test_missing_catalog_raises_data_fetch_error(tmp_path, sample_request):
    """Verifies appropriate error handling when catalog file is absent."""
    non_existent_engine = BusSearchEngine(data_file=tmp_path / "absent.json")
    with pytest.raises(DataFetchError, match="catalog not found"):
        non_existent_engine.search(sample_request)


def test_get_all_routes(search_engine):
    """Verifies discovery of distinct routes in catalog."""
    routes = search_engine.get_all_routes()
    assert len(routes) > 0
    sources = [r["source"] for r in routes]
    assert "Bangalore" in sources
    assert "Hyderabad" in sources
