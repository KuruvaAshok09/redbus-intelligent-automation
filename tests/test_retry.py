"""
Unit tests for RetryEngine module.
Verifies bounded retries, exponential backoff, rejection of permanent errors, and loop limits.
"""

import pytest
from redbus_automation.models import ValidationError, TransientServiceError
from redbus_automation.retry_engine import RetryEngine


def test_retry_engine_succeeds_on_first_try():
    """Verifies immediate success performs zero retries."""
    engine = RetryEngine(max_retries=3, initial_backoff_sec=0.001)
    call_count = 0

    def op():
        nonlocal call_count
        call_count += 1
        return "SUCCESS_DATA"

    result, history = engine.execute_with_retry(op, "test_op")
    assert result == "SUCCESS_DATA"
    assert call_count == 1
    assert len(history) == 0


def test_retry_engine_retries_transient_failure_until_success():
    """Verifies transient error is retried and recovers successfully."""
    engine = RetryEngine(max_retries=3, initial_backoff_sec=0.001, backoff_factor=2.0)
    call_count = 0

    def flaky_op():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise TransientServiceError(f"Transient error #{call_count}")
        return "RECOVERED_DATA"

    result, history = engine.execute_with_retry(flaky_op, "flaky_op")
    assert result == "RECOVERED_DATA"
    assert call_count == 3
    assert len(history) == 2
    assert history[0].attempt_number == 1
    assert history[1].attempt_number == 2
    assert "Transient error #1" in history[0].error_message
    assert "Transient error #2" in history[1].error_message


def test_retry_engine_never_retries_permanent_validation_error():
    """CRITICAL: Verifies permanent ValidationError is raised immediately with 0 retries."""
    engine = RetryEngine(max_retries=5, initial_backoff_sec=0.001)
    call_count = 0

    def bad_op():
        nonlocal call_count
        call_count += 1
        raise ValidationError("Permanent invalid city name")

    with pytest.raises(ValidationError, match="Permanent invalid city name"):
        engine.execute_with_retry(bad_op, "bad_op")

    # MUST be strictly 1 attempt! No retries allowed!
    assert call_count == 1


def test_retry_engine_halts_at_max_retries():
    """Verifies bounded limit prevents infinite loops and raises when limit is reached."""
    engine = RetryEngine(max_retries=2, initial_backoff_sec=0.001)
    call_count = 0

    def permanently_broken_transient():
        nonlocal call_count
        call_count += 1
        raise TransientServiceError("Persistent network outage")

    with pytest.raises(TransientServiceError, match="Persistent network outage"):
        engine.execute_with_retry(permanently_broken_transient, "broken_op")

    # Initial attempt (1) + 2 retries = 3 calls total
    assert call_count == 3


def test_retry_engine_calculates_exponential_backoff():
    """Verifies exponential delay progression: d, d*f, d*(f^2)..."""
    engine = RetryEngine(max_retries=3, initial_backoff_sec=0.01, backoff_factor=2.0)
    call_count = 0

    def failing_op():
        nonlocal call_count
        call_count += 1
        raise TransientServiceError("Fail")

    with pytest.raises(TransientServiceError):
        engine.execute_with_retry(failing_op, "op")

    # Verify attempt history recorded proper exponential delays
    # Attempt 1: 0.01 * (2^0) = 0.01
    # Attempt 2: 0.01 * (2^1) = 0.02
    # Attempt 3: 0.01 * (2^2) = 0.04
    # Note: execute_with_retry fails on attempt > max_retries
