"""
Data models, enumerations, and custom exception definitions for the RedBus Automation platform.
Adheres to strict dataclass usage, typing contracts, and domain-driven design.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class WorkflowStatus(str, Enum):
    """Lifecycle states of the automation workflow."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"


class LogSeverity(str, Enum):
    """Log severity levels conforming to structured logging contract."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AutomationEventType(str, Enum):
    """Domain events for telemetry and tracing."""
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    SEARCH_INITIATED = "SEARCH_INITIATED"
    SEARCH_COMPLETED = "SEARCH_COMPLETED"
    SEARCH_FAILED = "SEARCH_FAILED"
    FILTER_APPLIED = "FILTER_APPLIED"
    RANKING_COMPLETED = "RANKING_COMPLETED"
    RETRY_TRIGGERED = "RETRY_TRIGGERED"
    RECOVERY_INITIATED = "RECOVERY_INITIATED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    REPORT_GENERATED = "REPORT_GENERATED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_TERMINATED = "WORKFLOW_TERMINATED"


# ---------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------

class AutomationError(Exception):
    """Base exception for all domain-specific errors."""
    pass


class ValidationError(AutomationError):
    """Permanent input validation failure. Must NEVER be retried."""
    pass


class TransientServiceError(AutomationError):
    """Temporary simulation or network failure. Eligible for bounded retry."""
    pass


class DataFetchError(AutomationError):
    """Failure while loading or parsing local mock bus catalog."""
    pass


class ReportGenerationError(AutomationError):
    """Failure during CSV or JSON report creation."""
    pass


class UnrecoverableIncidentError(AutomationError):
    """Raised when recovery actions and bounded retries are exhausted."""
    pass


# ---------------------------------------------------------
# Core Domain Dataclasses
# ---------------------------------------------------------

@dataclass
class SearchRequest:
    """User search request parameters with strong typing."""
    source: str
    destination: str
    journey_date: str
    passengers: int = 1
    max_budget: float = 3000.0
    preferred_operator: Optional[str] = None
    min_rating: Optional[float] = None


@dataclass
class Bus:
    """Simulated bus specification."""
    bus_id: str
    operator_name: str
    source: str
    destination: str
    departure_time: str
    arrival_time: str
    fare: float
    available_seats: int
    bus_type: str
    rating: float

    @property
    def duration_minutes(self) -> int:
        """Calculates approximate journey duration in minutes."""
        try:
            dep_h, dep_m = map(int, self.departure_time.split(":"))
            arr_h, arr_m = map(int, self.arrival_time.split(":"))
            dep_total = dep_h * 60 + dep_m
            arr_total = arr_h * 60 + arr_m
            if arr_total >= dep_total:
                return arr_total - dep_total
            # Overnight arrival
            return (24 * 60 - dep_total) + arr_total
        except Exception:
            return 480  # Default 8 hours if parsing fails

    @property
    def duration_formatted(self) -> str:
        """Human-readable trip duration (e.g. '8h 30m')."""
        mins = self.duration_minutes
        hours = mins // 60
        rem_mins = mins % 60
        return f"{hours}h {rem_mins:02d}m"


@dataclass
class RankedBus:
    """Bus with computed ranking score and explainability."""
    bus: Bus
    rank: int
    composite_score: float
    recommendation_reason: str


@dataclass
class RetryAttempt:
    """Details of a single retry execution attempt."""
    attempt_number: int
    timestamp: str
    delay_seconds: float
    error_message: str
    target_function: str


@dataclass
class RecoveryAction:
    """Record of an automated self-healing action."""
    action_id: str
    failure_type: str
    strategy_used: str
    successful: bool
    details: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WorkflowExecutionResult:
    """Complete summary of an orchestrated automation run."""
    execution_id: str
    status: WorkflowStatus
    request: SearchRequest
    buses_found: List[Bus] = field(default_factory=list)
    ranked_buses: List[RankedBus] = field(default_factory=list)
    recommended_bus: Optional[RankedBus] = None
    retry_history: List[RetryAttempt] = field(default_factory=list)
    recovery_history: List[RecoveryAction] = field(default_factory=list)
    execution_duration_sec: float = 0.0
    start_time: str = ""
    end_time: str = ""
    error_message: Optional[str] = None
    report_paths: Dict[str, str] = field(default_factory=dict)
