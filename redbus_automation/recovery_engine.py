"""
Automated Recovery Engine for RedBus Automation Platform.
Implements self-healing capabilities, incident detection, recovery strategies,
and unrecoverable incident escalation.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Callable

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    Bus,
    SearchRequest,
    RecoveryAction,
    TransientServiceError,
    DataFetchError,
    ReportGenerationError,
    UnrecoverableIncidentError,
    LogSeverity,
    AutomationEventType,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER


class RecoveryEngine:
    """Detects operational failures and executes automated self-healing remediation routines."""

    COMPONENT_NAME = "RecoveryEngine"

    def __init__(self):
        self.recovery_history: List[RecoveryAction] = []

    def handle_search_failure(
        self,
        exc: Exception,
        request: SearchRequest,
        execution_id: str = "SYSTEM_RECOVERY",
        fallback_search_fn: Optional[Callable[[SearchRequest], List[Bus]]] = None,
    ) -> Tuple[List[Bus], RecoveryAction]:
        """
        Remediates search failures through autonomic fallback mechanisms.

        Remediation Strategies:
        1. If TransientServiceError: Engage secondary offline mirror cache.
        2. If DataFetchError: Restore missing/damaged catalog from embedded seed.
        3. If Unrecoverable: Raise UnrecoverableIncidentError.
        """
        action_id = f"REC-{uuid.uuid4().hex[:8].upper()}"

        LOGGER.log(
            execution_id=execution_id,
            component=self.COMPONENT_NAME,
            event_type=AutomationEventType.RECOVERY_INITIATED,
            severity=LogSeverity.WARNING,
            message=f"Incident detected: {type(exc).__name__}: {exc}. Evaluating self-healing strategy...",
            status=WorkflowStatus.RUNNING,
            metadata={"action_id": action_id, "exception": str(exc)},
        )

        # Strategy 1: Transient Service Disruption -> Secondary Offline Cache
        if isinstance(exc, (TransientServiceError, TimeoutError)):
            strategy = "SECONDARY_MIRROR_FALLBACK"
            if fallback_search_fn:
                try:
                    fallback_buses = fallback_search_fn(request)
                    action = RecoveryAction(
                        action_id=action_id,
                        failure_type=type(exc).__name__,
                        strategy_used=strategy,
                        successful=True,
                        details=(
                            f"Recovered from transient error using secondary offline mirror. "
                            f"Retrieved {len(fallback_buses)} available buses."
                        ),
                        timestamp=datetime.now().isoformat(),
                    )
                    self.recovery_history.append(action)
                    self._log_recovery_completion(execution_id, action)
                    return fallback_buses, action
                except Exception as inner_err:
                    details = f"Secondary mirror fallback failed: {inner_err}"
            else:
                details = "No secondary fallback provider configured."

            # If fallback failed or wasn't available
            action = RecoveryAction(
                action_id=action_id,
                failure_type=type(exc).__name__,
                strategy_used=strategy,
                successful=False,
                details=details,
                timestamp=datetime.now().isoformat(),
            )
            self.recovery_history.append(action)
            self._log_recovery_failure(execution_id, action)
            raise UnrecoverableIncidentError(f"Self-healing failed: {details}") from exc

        # Strategy 2: Missing or Corrupt Catalog -> Seed Reconstitution
        elif isinstance(exc, DataFetchError):
            strategy = "CATALOG_SEED_RECONSTITUTION"
            try:
                self._restore_catalog_seed()
                if fallback_search_fn:
                    recovered_buses = fallback_search_fn(request)
                else:
                    recovered_buses = []

                action = RecoveryAction(
                    action_id=action_id,
                    failure_type=type(exc).__name__,
                    strategy_used=strategy,
                    successful=True,
                    details=f"Reconstituted master catalog from embedded seed. Found {len(recovered_buses)} buses.",
                    timestamp=datetime.now().isoformat(),
                )
                self.recovery_history.append(action)
                self._log_recovery_completion(execution_id, action)
                return recovered_buses, action

            except Exception as seed_err:
                action = RecoveryAction(
                    action_id=action_id,
                    failure_type=type(exc).__name__,
                    strategy_used=strategy,
                    successful=False,
                    details=f"Catalog seed reconstitution failed: {seed_err}",
                    timestamp=datetime.now().isoformat(),
                )
                self.recovery_history.append(action)
                self._log_recovery_failure(execution_id, action)
                raise UnrecoverableIncidentError(f"Self-healing failed: {seed_err}") from exc

        # Strategy 3: Unhandled or Permanent Exception -> Unrecoverable Incident
        else:
            action = RecoveryAction(
                action_id=action_id,
                failure_type=type(exc).__name__,
                strategy_used="NONE_APPLICABLE",
                successful=False,
                details=f"Permanent or unhandled exception cannot be automatically healed: {exc}",
                timestamp=datetime.now().isoformat(),
            )
            self.recovery_history.append(action)
            self._log_recovery_failure(execution_id, action)
            raise UnrecoverableIncidentError(f"Unrecoverable incident escalated: {exc}") from exc

    def remediate_zero_results(
        self,
        request: SearchRequest,
        raw_buses: List[Bus],
        execution_id: str = "SYSTEM_RECOVERY",
    ) -> Tuple[SearchRequest, RecoveryAction]:
        """
        Remediates scenarios where strict user filters eliminated all candidates.
        Self-healing strategy: Incrementally relax budget constraint by 25%.
        """
        action_id = f"REC-REL-{uuid.uuid4().hex[:8].upper()}"
        relaxed_budget = round(request.max_budget * 1.25, 2)

        relaxed_request = SearchRequest(
            source=request.source,
            destination=request.destination,
            journey_date=request.journey_date,
            passengers=request.passengers,
            max_budget=relaxed_budget,
            preferred_operator=None,  # Relax operator constraint
            min_rating=max(3.0, (request.min_rating or 4.0) - 0.5),  # Moderately relax rating
        )

        action = RecoveryAction(
            action_id=action_id,
            failure_type="ZeroFilteredResults",
            strategy_used="CONSTRAINT_RELAXATION",
            successful=True,
            details=(
                f"Expanded search criteria to avoid zero-result outage: "
                f"Budget raised from ₹{request.max_budget:.2f} to ₹{relaxed_budget:.2f}, "
                f"operator constraint relaxed."
            ),
            timestamp=datetime.now().isoformat(),
        )
        self.recovery_history.append(action)
        self._log_recovery_completion(execution_id, action)
        return relaxed_request, action

    def _restore_catalog_seed(self) -> None:
        """Restores minimal verified seed catalog if data file is corrupted or missing."""
        import json
        seed_data = [
            {
                "bus_id": "BUS-BLR-HYD-SEED01",
                "operator_name": "IntrCity SmartBus (Emergency Backup)",
                "source": "Bangalore",
                "destination": "Hyderabad",
                "departure_time": "21:00",
                "arrival_time": "06:30",
                "fare": 1150.0,
                "available_seats": 20,
                "bus_type": "AC Sleeper (2+1)",
                "rating": 4.8,
            },
            {
                "bus_id": "BUS-HYD-BLR-SEED02",
                "operator_name": "KSRTC Airavat (Emergency Backup)",
                "source": "Hyderabad",
                "destination": "Bangalore",
                "departure_time": "20:30",
                "arrival_time": "06:00",
                "fare": 990.0,
                "available_seats": 25,
                "bus_type": "Volvo Multi-Axle",
                "rating": 4.7,
            },
        ]
        CONFIG.DEFAULT_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG.DEFAULT_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(seed_data, f, indent=2)

    def _log_recovery_completion(self, execution_id: str, action: RecoveryAction) -> None:
        LOGGER.log(
            execution_id=execution_id,
            component=self.COMPONENT_NAME,
            event_type=AutomationEventType.RECOVERY_COMPLETED,
            severity=LogSeverity.INFO,
            message=f"Self-healing strategy '{action.strategy_used}' executed successfully: {action.details}",
            status=WorkflowStatus.RUNNING,
            metadata={"action_id": action.action_id, "strategy": action.strategy_used},
        )

    def _log_recovery_failure(self, execution_id: str, action: RecoveryAction) -> None:
        LOGGER.log(
            execution_id=execution_id,
            component=self.COMPONENT_NAME,
            event_type=AutomationEventType.WORKFLOW_TERMINATED,
            severity=LogSeverity.CRITICAL,
            message=f"Self-healing failed: {action.details}. Incident escalated.",
            status=WorkflowStatus.FAILED,
            metadata={"action_id": action.action_id, "strategy": action.strategy_used},
        )
