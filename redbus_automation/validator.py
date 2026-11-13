"""
Input Validation Module for RedBus Automation Platform.
Enforces business rules and strict constraints on all user-supplied search parameters.
Permanent validation errors raise ValidationError and must NEVER be retried.
"""

from datetime import datetime, date
from typing import Optional
import re

from redbus_automation.models import (
    SearchRequest,
    ValidationError,
    LogSeverity,
    AutomationEventType,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER


class InputValidator:
    """Validates search parameters against domain and operational constraints."""

    COMPONENT_NAME = "InputValidator"

    @classmethod
    def validate(
        cls,
        request: SearchRequest,
        execution_id: str = "SYSTEM_VALIDATION",
        reference_date: Optional[date] = None,
    ) -> SearchRequest:
        """
        Validates all fields in SearchRequest.
        Returns the sanitized SearchRequest if valid; raises ValidationError otherwise.
        """
        ref_date = reference_date or datetime.now().date()

        # 1. Source City Validation
        if not isinstance(request.source, str):
            err = f"Source city must be a string, got {type(request.source).__name__}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        source_clean = request.source.strip()
        if not source_clean:
            err = "Source city cannot be empty or whitespace."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        if len(source_clean) < 2:
            err = f"Source city '{source_clean}' is too short (min 2 characters)."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        if not re.match(r"^[A-Za-z\s\-]+$", source_clean):
            err = f"Source city '{source_clean}' contains invalid characters."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        # 2. Destination City Validation
        if not isinstance(request.destination, str):
            err = f"Destination city must be a string, got {type(request.destination).__name__}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        dest_clean = request.destination.strip()
        if not dest_clean:
            err = "Destination city cannot be empty or whitespace."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        if len(dest_clean) < 2:
            err = f"Destination city '{dest_clean}' is too short (min 2 characters)."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        if not re.match(r"^[A-Za-z\s\-]+$", dest_clean):
            err = f"Destination city '{dest_clean}' contains invalid characters."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        # 3. Same Source & Destination Rejection
        if source_clean.lower() == dest_clean.lower():
            err = f"Source and destination cannot be identical ('{source_clean}')."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        # 4. Journey Date Validation
        if not isinstance(request.journey_date, str):
            err = f"Journey date must be a date string (YYYY-MM-DD), got {type(request.journey_date).__name__}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        try:
            parsed_date = datetime.strptime(request.journey_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            err = f"Journey date '{request.journey_date}' is invalid. Expected format: YYYY-MM-DD."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        if parsed_date < ref_date:
            err = f"Journey date {parsed_date} is in the past relative to reference date {ref_date}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        # 5. Passenger Count Validation
        if not isinstance(request.passengers, int):
            err = f"Passenger count must be an integer, got {type(request.passengers).__name__}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        if request.passengers < 1:
            err = f"Passenger count must be at least 1, got {request.passengers}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        if request.passengers > 10:
            err = f"Passenger count exceeds maximum allowable limit of 10, got {request.passengers}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        # 6. Maximum Budget Validation
        if not isinstance(request.max_budget, (int, float)):
            err = f"Maximum budget must be a positive number, got {type(request.max_budget).__name__}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        if request.max_budget <= 0:
            err = f"Maximum budget must be greater than zero, got {request.max_budget}."
            cls._log_failure(execution_id, err)
            raise ValidationError(err)

        # Log successful validation
        LOGGER.log(
            execution_id=execution_id,
            component=cls.COMPONENT_NAME,
            event_type=AutomationEventType.VALIDATION_PASSED,
            severity=LogSeverity.INFO,
            message=f"Validation passed for {source_clean} -> {dest_clean} on {request.journey_date}.",
            status=WorkflowStatus.RUNNING,
            metadata={
                "source": source_clean,
                "destination": dest_clean,
                "journey_date": request.journey_date,
                "passengers": request.passengers,
                "max_budget": request.max_budget,
            },
        )

        # Return sanitized copy
        return SearchRequest(
            source=source_clean,
            destination=dest_clean,
            journey_date=request.journey_date.strip(),
            passengers=request.passengers,
            max_budget=float(request.max_budget),
            preferred_operator=request.preferred_operator.strip() if request.preferred_operator else None,
            min_rating=float(request.min_rating) if request.min_rating is not None else None,
        )

    @classmethod
    def _log_failure(cls, execution_id: str, error_msg: str) -> None:
        """Internal helper to log validation rejection."""
        LOGGER.log(
            execution_id=execution_id,
            component=cls.COMPONENT_NAME,
            event_type=AutomationEventType.VALIDATION_FAILED,
            severity=LogSeverity.ERROR,
            message=error_msg,
            status=WorkflowStatus.FAILED,
        )
