"""
RedBus Intelligent Ticket Search and Automation System.
An enterprise offline-first autonomics and workflow automation platform.
"""

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    SearchRequest,
    Bus,
    RankedBus,
    WorkflowStatus,
    WorkflowExecutionResult,
    ValidationError,
    TransientServiceError,
    DataFetchError,
    ReportGenerationError,
    UnrecoverableIncidentError,
    Incident,
    FailureCategory,
    Seat,
    BookingRequest,
    BookingConfirmation,
)
from redbus_automation.validator import InputValidator
from redbus_automation.search_engine import BusSearchEngine
from redbus_automation.filter_engine import BusFilterEngine
from redbus_automation.comparison_engine import BusComparisonEngine
from redbus_automation.retry_engine import RetryEngine
from redbus_automation.recovery_engine import RecoveryEngine
from redbus_automation.monitoring import MONITOR, AutomationMonitor
from redbus_automation.logger import LOGGER, AutomationLogger
from redbus_automation.reporting import REPORTER, ReportGenerator
from redbus_automation.orchestrator import AutomationOrchestrator
from redbus_automation.incident_manager import INCIDENT_MANAGER, IncidentManager
from redbus_automation.booking_engine import BOOKING_ENGINE, BookingEngine

__version__ = "1.1.0"

__all__ = [
    "CONFIG",
    "SearchRequest",
    "Bus",
    "RankedBus",
    "WorkflowStatus",
    "WorkflowExecutionResult",
    "ValidationError",
    "TransientServiceError",
    "DataFetchError",
    "ReportGenerationError",
    "UnrecoverableIncidentError",
    "Incident",
    "FailureCategory",
    "Seat",
    "BookingRequest",
    "BookingConfirmation",
    "InputValidator",
    "BusSearchEngine",
    "BusFilterEngine",
    "BusComparisonEngine",
    "RetryEngine",
    "RecoveryEngine",
    "MONITOR",
    "AutomationMonitor",
    "LOGGER",
    "AutomationLogger",
    "REPORTER",
    "ReportGenerator",
    "AutomationOrchestrator",
    "INCIDENT_MANAGER",
    "IncidentManager",
    "BOOKING_ENGINE",
    "BookingEngine",
]
