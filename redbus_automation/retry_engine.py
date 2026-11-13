"""
Bounded Retry Engine with Exponential Backoff for RedBus Automation Platform.
Implements resilient autonomic retries for transient service disruptions.
Guarantees zero retries for permanent validation failures and bounded limits to prevent infinite loops.
"""

import time
from datetime import datetime
from typing import Callable, TypeVar, Optional, List, Tuple, Type

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    RetryAttempt,
    ValidationError,
    TransientServiceError,
    LogSeverity,
    AutomationEventType,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER

T = TypeVar("T")


class RetryEngine:
    """Enterprise retry mechanism with bounded attempts, backoff, and strict safety contracts."""

    COMPONENT_NAME = "RetryEngine"

    def __init__(
        self,
        max_retries: int = CONFIG.DEFAULT_MAX_RETRIES,
        initial_backoff_sec: float = CONFIG.DEFAULT_INITIAL_BACKOFF_SEC,
        backoff_factor: float = CONFIG.DEFAULT_BACKOFF_FACTOR,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        non_retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ):
        self.max_retries = max(1, max_retries)
        self.initial_backoff_sec = max(0.0, initial_backoff_sec)
        self.backoff_factor = max(1.0, backoff_factor)
        self.retryable_exceptions = retryable_exceptions or (TransientServiceError, TimeoutError, ConnectionError)
        self.non_retryable_exceptions = non_retryable_exceptions or (ValidationError, ValueError, TypeError)

    def execute_with_retry(
        self,
        operation: Callable[[], T],
        operation_name: str,
        execution_id: str = "SYSTEM_RETRY",
    ) -> Tuple[T, List[RetryAttempt]]:
        """
        Executes a callable with bounded retry logic and exponential backoff.

        Returns:
            Tuple of (Result, List of RetryAttempt records)

        Raises:
            ValidationError immediately if non-retryable.
            Original exception once bounded max retries are exhausted.
        """
        attempts_history: List[RetryAttempt] = []
        attempt = 0

        while attempt <= self.max_retries:
            try:
                # Normal execution attempt
                result = operation()
                return result, attempts_history

            except Exception as exc:
                # Rule 1: NEVER retry permanent validation or deterministic type errors
                if isinstance(exc, self.non_retryable_exceptions):
                    LOGGER.log(
                        execution_id=execution_id,
                        component=self.COMPONENT_NAME,
                        event_type=AutomationEventType.VALIDATION_FAILED,
                        severity=LogSeverity.ERROR,
                        message=f"Non-retryable exception encountered in {operation_name}: {exc}. Halting retries.",
                        status=WorkflowStatus.FAILED,
                        metadata={"operation": operation_name, "error": str(exc)},
                    )
                    raise exc

                # Rule 2: Only retry approved transient exceptions
                if not isinstance(exc, self.retryable_exceptions):
                    LOGGER.log(
                        execution_id=execution_id,
                        component=self.COMPONENT_NAME,
                        event_type=AutomationEventType.WORKFLOW_TERMINATED,
                        severity=LogSeverity.ERROR,
                        message=f"Unexpected non-transient error in {operation_name}: {exc}. Halting retries.",
                        status=WorkflowStatus.FAILED,
                    )
                    raise exc

                attempt += 1

                # Rule 3: Check bounds to prevent infinite loops
                if attempt > self.max_retries:
                    LOGGER.log(
                        execution_id=execution_id,
                        component=self.COMPONENT_NAME,
                        event_type=AutomationEventType.WORKFLOW_TERMINATED,
                        severity=LogSeverity.CRITICAL,
                        message=f"Bounded retry limit ({self.max_retries}) exhausted for {operation_name}. Last error: {exc}.",
                        status=WorkflowStatus.FAILED,
                        metadata={"total_attempts": attempt - 1, "final_error": str(exc)},
                    )
                    raise exc

                # Compute exponential backoff delay
                delay = self.initial_backoff_sec * (self.backoff_factor ** (attempt - 1))

                retry_record = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now().isoformat(),
                    delay_seconds=round(delay, 4),
                    error_message=str(exc),
                    target_function=operation_name,
                )
                attempts_history.append(retry_record)

                LOGGER.log(
                    execution_id=execution_id,
                    component=self.COMPONENT_NAME,
                    event_type=AutomationEventType.RETRY_TRIGGERED,
                    severity=LogSeverity.WARNING,
                    message=f"Retry {attempt}/{self.max_retries} scheduled for '{operation_name}' after {delay:.3f}s. Cause: {exc}",
                    status=WorkflowStatus.RUNNING,
                    metadata={
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "delay_sec": delay,
                        "target_function": operation_name,
                    },
                )

                if delay > 0:
                    time.sleep(delay)

        # Defensive fallback: should not be reached due to loop termination
        raise RuntimeError(f"Retry loop exited abnormally for {operation_name}.")
