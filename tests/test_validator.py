"""
Unit tests for InputValidator module.
Verifies rejection of invalid inputs and preservation of valid search parameters.
"""

from datetime import date, timedelta
import pytest

from redbus_automation.models import SearchRequest, ValidationError
from redbus_automation.validator import InputValidator


@pytest.fixture
def base_valid_request():
    """Provides a baseline valid search request."""
    tomorrow_str = (date(2026, 11, 14)).strftime("%Y-%m-%d")
    return SearchRequest(
        source="Bangalore",
        destination="Hyderabad",
        journey_date=tomorrow_str,
        passengers=2,
        max_budget=2000.0,
        preferred_operator="Orange Travels",
        min_rating=4.0,
    )


def test_validator_accepts_valid_request(base_valid_request):
    """Verifies that a well-formed request passes validation cleanly."""
    ref_date = date(2026, 11, 13)
    sanitized = InputValidator.validate(base_valid_request, reference_date=ref_date)
    assert sanitized.source == "Bangalore"
    assert sanitized.destination == "Hyderabad"
    assert sanitized.journey_date == "2026-11-14"
    assert sanitized.passengers == 2
    assert sanitized.max_budget == 2000.0
    assert sanitized.preferred_operator == "Orange Travels"
    assert sanitized.min_rating == 4.0


@pytest.mark.parametrize("empty_src", ["", "   ", "\t\n"])
def test_validator_rejects_empty_source(base_valid_request, empty_src):
    """Verifies rejection of empty or whitespace source city."""
    base_valid_request.source = empty_src
    with pytest.raises(ValidationError, match="Source city cannot be empty"):
        InputValidator.validate(base_valid_request)


@pytest.mark.parametrize("empty_dst", ["", "   ", "\t\n"])
def test_validator_rejects_empty_destination(base_valid_request, empty_dst):
    """Verifies rejection of empty or whitespace destination city."""
    base_valid_request.destination = empty_dst
    with pytest.raises(ValidationError, match="Destination city cannot be empty"):
        InputValidator.validate(base_valid_request)


def test_validator_rejects_identical_source_and_destination(base_valid_request):
    """Verifies rejection when source and destination are identical (case-insensitive)."""
    base_valid_request.source = "Bangalore"
    base_valid_request.destination = "bangalore"
    with pytest.raises(ValidationError, match="Source and destination cannot be identical"):
        InputValidator.validate(base_valid_request)


@pytest.mark.parametrize("invalid_name", ["A", "B@ngalore", "City#123", "12345"])
def test_validator_rejects_invalid_city_characters(base_valid_request, invalid_name):
    """Verifies rejection of non-alphabetic or excessively short city names."""
    base_valid_request.source = invalid_name
    with pytest.raises(ValidationError):
        InputValidator.validate(base_valid_request)


def test_validator_rejects_past_date(base_valid_request):
    """Verifies rejection of journey dates earlier than reference date."""
    ref_date = date(2026, 11, 14)
    base_valid_request.journey_date = "2026-11-13"  # Yesterday
    with pytest.raises(ValidationError, match="in the past relative to reference date"):
        InputValidator.validate(base_valid_request, reference_date=ref_date)


@pytest.mark.parametrize("bad_date", ["2026/11/14", "14-11-2026", "tomorrow", "2026-02-31"])
def test_validator_rejects_malformed_dates(base_valid_request, bad_date):
    """Verifies rejection of non-ISO formatted or non-existent calendar dates."""
    base_valid_request.journey_date = bad_date
    with pytest.raises(ValidationError, match="Expected format: YYYY-MM-DD"):
        InputValidator.validate(base_valid_request)


@pytest.mark.parametrize("bad_passengers", [0, -1, -5, 11, 20])
def test_validator_rejects_out_of_bound_passenger_counts(base_valid_request, bad_passengers):
    """Verifies passenger counts outside allowable range (1 to 10) are rejected."""
    base_valid_request.passengers = bad_passengers
    with pytest.raises(ValidationError):
        InputValidator.validate(base_valid_request)


@pytest.mark.parametrize("bad_budget", [0, -100, -0.01])
def test_validator_rejects_non_positive_budgets(base_valid_request, bad_budget):
    """Verifies rejection of zero or negative maximum budget limits."""
    base_valid_request.max_budget = bad_budget
    with pytest.raises(ValidationError, match="greater than zero"):
        InputValidator.validate(base_valid_request)


def test_validator_rejects_invalid_types(base_valid_request):
    """Verifies type enforcement for all search fields."""
    base_valid_request.source = 1234  # type: ignore
    with pytest.raises(ValidationError, match="Source city must be a string"):
        InputValidator.validate(base_valid_request)
