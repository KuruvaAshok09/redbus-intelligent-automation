"""
Central Automation Orchestrator for RedBus Automation Platform.
Orchestrates the entire end-to-end lifecycle:
User Request -> Input Validation -> Bus Search -> Failure Detection -> Bounded Retry -> Fallback Recovery -> Result Validation -> Final Response -> Logging.
Maintains execution state, stage tracking, incident lifecycle management, and autonomic self-healing.
"""

import time
import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    SearchRequest,
    Bus,
    RankedBus,
    WorkflowExecutionResult,
    WorkflowStatus,
    RetryAttempt,
    RecoveryAction,
    Incident,
    FailureCategory,
    ValidationError,
    TransientServiceError,
    DataFetchError,
    ReportGenerationError,
    UnrecoverableIncidentError,
    LogSeverity,
    AutomationEventType,
)
from redbus_automation.logger import LOGGER
from redbus_automation.validator import InputValidator
from redbus_automation.search_engine import BusSearchEngine
from redbus_automation.filter_engine import BusFilterEngine
from redbus_automation.comparison_engine import BusComparisonEngine
from redbus_automation.retry_engine import RetryEngine
from redbus_automation.recovery_engine import RecoveryEngine
from redbus_automation.monitoring import MONITOR
from redbus_automation.reporting import REPORTER
from redbus_automation.incident_manager import INCIDENT_MANAGER


class AutomationOrchestrator:
    """Master workflow orchestrator driving automated search, resilience, and observability."""

    COMPONENT_NAME = "AutomationOrchestrator"

    def __init__(
        self,
        search_engine: Optional[BusSearchEngine] = None,
        retry_engine: Optional[RetryEngine] = None,
        recovery_engine: Optional[RecoveryEngine] = None,
    ):
        self.search_engine = search_engine or BusSearchEngine()
        self.retry_engine = retry_engine or RetryEngine()
        self.recovery_engine = recovery_engine or RecoveryEngine()

    @staticmethod
    def generate_execution_id() -> str:
        """Generates a human-traceable, globally unique execution ID."""
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        rand = uuid.uuid4().hex[:6].upper()
        return f"EXEC-{ts}-{rand}"

    def run_workflow(
        self,
        request: SearchRequest,
        fault_injection: Optional[Dict[str, Any]] = None,
        reference_date: Optional[date] = None,
    ) -> WorkflowExecutionResult:
        """
        Executes the end-to-end intelligent automation workflow:
        User Request -> Input Validation -> Bus Search -> Failure Detection -> Retry -> Fallback Recovery -> Result Validation -> Final Response -> Logging.

        Supported Fault Injections (for resilience testing):
        - simulate_transient_failure: bool
        - simulate_corruption: bool
        - force_empty: bool
        - simulate_report_failure: bool
        - repeated_workflow_failure: bool
        - simulate_fallback_failure: bool
        """
        faults = fault_injection or {}
        execution_id = self.generate_execution_id()
        start_time_iso = datetime.now().isoformat()
        t0 = time.perf_counter()

        # Initialize tracking state
        current_status = WorkflowStatus.RUNNING
        stage_reached = "WORKFLOW_INITIALIZED"
        all_retry_history: List[RetryAttempt] = []
        all_recovery_history: List[RecoveryAction] = []
        workflow_incidents: List[Incident] = []
        buses_found: List[Bus] = []
        ranked_buses: List[RankedBus] = []
        recommended_bus: Optional[RankedBus] = None
        report_paths: Dict[str, str] = {}
        error_message: Optional[str] = None
        was_recovered: bool = False

        MONITOR.record_start(execution_id)
        LOGGER.log(
            execution_id=execution_id,
            component=self.COMPONENT_NAME,
            event_type=AutomationEventType.WORKFLOW_STARTED,
            severity=LogSeverity.INFO,
            message=f"Starting intelligent automation workflow for {request.source} -> {request.destination}.",
            status=WorkflowStatus.RUNNING,
            metadata={"request": request.__dict__},
        )

        try:
            # -------------------------------------------------------------
            # STEP 0: Check Repeated Workflow Failure Fault Injection
            # -------------------------------------------------------------
            if faults.get("repeated_workflow_failure"):
                stage_reached = "WORKFLOW_INITIATION"
                inc = INCIDENT_MANAGER.record_incident(
                    failure_category=FailureCategory.UNRECOVERABLE_ERROR,
                    is_recoverable=False,
                    error_message="FAULT INJECTION: Repeated unrecoverable system crash triggered.",
                    execution_id=execution_id,
                    final_status="FAILED",
                )
                workflow_incidents.append(inc)
                raise UnrecoverableIncidentError("FAULT INJECTION: Repeated unrecoverable system crash triggered.")

            # -------------------------------------------------------------
            # STEP 1: Input Validation (Permanent errors are NEVER retried)
            # -------------------------------------------------------------
            stage_reached = "INPUT_VALIDATION"
            try:
                validated_request = InputValidator.validate(
                    request=request,
                    execution_id=execution_id,
                    reference_date=reference_date,
                )
            except ValidationError as val_err:
                inc = INCIDENT_MANAGER.record_incident(
                    failure_category=FailureCategory.VALIDATION_ERROR,
                    is_recoverable=False,
                    error_message=str(val_err),
                    execution_id=execution_id,
                    final_status="FAILED",
                )
                workflow_incidents.append(inc)
                raise val_err

            # -------------------------------------------------------------
            # STEP 2: Simulated Bus Search with Bounded Retry Mechanism
            # -------------------------------------------------------------
            stage_reached = "CATALOG_SEARCH"
            sim_transient = bool(faults.get("simulate_transient_failure", False))
            sim_corrupt = bool(faults.get("simulate_corruption", False))
            force_empty = bool(faults.get("force_empty", False))

            try:
                # Execute search inside bounded retry engine
                raw_buses, retries = self.retry_engine.execute_with_retry(
                    operation=lambda: self.search_engine.search(
                        request=validated_request,
                        execution_id=execution_id,
                        simulate_transient_failure=sim_transient,
                        simulate_corruption=sim_corrupt,
                        force_empty=force_empty,
                    ),
                    operation_name="BusSearchEngine.search",
                    execution_id=execution_id,
                )
                all_retry_history.extend(retries)
                buses_found = raw_buses

            except (TransientServiceError, DataFetchError) as service_err:
                stage_reached = "AUTONOMIC_RECOVERY"
                category = (
                    FailureCategory.TRANSIENT_SERVICE_ERROR
                    if isinstance(service_err, TransientServiceError)
                    else FailureCategory.CATALOG_FETCH_ERROR
                )
                retry_events = [
                    entry
                    for entry in LOGGER.get_logs(execution_id)
                    if entry.get("event_type") == AutomationEventType.RETRY_TRIGGERED.value
                ]
                all_retry_history.extend(
                    RetryAttempt(
                        attempt_number=int(entry["metadata"]["attempt"]),
                        timestamp=str(entry["timestamp"]),
                        delay_seconds=float(entry["metadata"]["delay_sec"]),
                        error_message=str(entry["message"]).split("Cause: ", 1)[-1],
                        target_function=str(entry["metadata"]["target_function"]),
                    )
                    for entry in retry_events
                )

                # Record the operational incident
                inc = INCIDENT_MANAGER.record_incident(
                    failure_category=category,
                    is_recoverable=True,
                    error_message=str(service_err),
                    execution_id=execution_id,
                    retry_attempts=len(all_retry_history),
                    final_status="OPEN",
                    details={"retry_events": retry_events},
                )
                workflow_incidents.append(inc)

                LOGGER.log(
                    execution_id=execution_id,
                    component=self.COMPONENT_NAME,
                    event_type=AutomationEventType.RECOVERY_INITIATED,
                    severity=LogSeverity.WARNING,
                    message=f"Search failed after retries ({service_err}). Activating self-healing recovery.",
                    status=WorkflowStatus.RUNNING,
                )

                # Handle failure via fallback catalog / secondary mirror
                if faults.get("simulate_fallback_failure"):
                    # Complete recovery failure scenario
                    inc.final_status = "FAILED"
                    inc.recovery_action = "FALLBACK_CATALOG_FAILED"
                    raise UnrecoverableIncidentError("FAULT INJECTION: Secondary fallback provider also failed.")

                recovered_buses, rec_action = self.recovery_engine.handle_search_failure(
                    exc=service_err,
                    request=validated_request,
                    execution_id=execution_id,
                    fallback_search_fn=self.recovery_engine.query_fallback_catalog,
                )
                all_recovery_history.append(rec_action)

                if rec_action.successful and recovered_buses:
                    buses_found = recovered_buses
                    was_recovered = True
                    inc.final_status = "RESOLVED"
                    inc.recovery_action = rec_action.strategy_used
                    INCIDENT_MANAGER.resolve_incident(inc.incident_id, rec_action.strategy_used)
                else:
                    inc.final_status = "FAILED"
                    raise service_err

            # -------------------------------------------------------------
            # STEP 3: Domain Filtering Engine & Zero-Result Recovery
            # -------------------------------------------------------------
            stage_reached = "FILTERING"
            filtered_buses = BusFilterEngine.apply_filters(
                buses=buses_found,
                request=validated_request,
                execution_id=execution_id,
            )

            # Self-healing if filters eliminated all available buses on route
            if not filtered_buses and buses_found and not faults.get("disable_zero_result_recovery", False):
                stage_reached = "FILTER_RELAXATION_RECOVERY"
                zero_inc = INCIDENT_MANAGER.record_incident(
                    failure_category=FailureCategory.FILTER_ZERO_RESULTS,
                    is_recoverable=True,
                    error_message=f"Initial filters eliminated all {len(buses_found)} buses on route.",
                    execution_id=execution_id,
                    final_status="OPEN",
                )
                workflow_incidents.append(zero_inc)

                relaxed_req, rel_action = self.recovery_engine.remediate_zero_results(
                    request=validated_request,
                    raw_buses=buses_found,
                    execution_id=execution_id,
                )
                all_recovery_history.append(rel_action)
                was_recovered = True
                validated_request = relaxed_req
                filtered_buses = BusFilterEngine.apply_filters(
                    buses=buses_found,
                    request=validated_request,
                    execution_id=execution_id,
                )
                zero_inc.final_status = "RESOLVED"
                zero_inc.recovery_action = rel_action.strategy_used
                INCIDENT_MANAGER.resolve_incident(zero_inc.incident_id, rel_action.strategy_used)

            # -------------------------------------------------------------
            # STEP 4: Comparison & Explainable MCDA Ranking Engine
            # -------------------------------------------------------------
            stage_reached = "RANKING"
            ranked_buses = BusComparisonEngine.rank_buses(
                buses=filtered_buses,
                execution_id=execution_id,
            )
            if ranked_buses:
                recommended_bus = ranked_buses[0]

            # -------------------------------------------------------------
            # STEP 5: Report Generation (CSV & JSON)
            # -------------------------------------------------------------
            stage_reached = "REPORTING"
            if faults.get("simulate_report_failure"):
                rep_inc = INCIDENT_MANAGER.record_incident(
                    failure_category=FailureCategory.REPORT_GENERATION_ERROR,
                    is_recoverable=False,
                    error_message="FAULT INJECTION: Simulated filesystem write lock on report folder.",
                    execution_id=execution_id,
                    final_status="FAILED",
                )
                workflow_incidents.append(rep_inc)
                raise ReportGenerationError("FAULT INJECTION: Simulated filesystem write lock on report folder.")

            temp_result = WorkflowExecutionResult(
                execution_id=execution_id,
                status=WorkflowStatus.RECOVERED if was_recovered else WorkflowStatus.SUCCESS,
                request=validated_request,
                buses_found=buses_found,
                ranked_buses=ranked_buses,
                recommended_bus=recommended_bus,
                retry_history=all_retry_history,
                recovery_history=all_recovery_history,
                incidents=workflow_incidents,
                execution_duration_sec=round(time.perf_counter() - t0, 3),
                start_time=start_time_iso,
                end_time=datetime.now().isoformat(),
                stage_reached="REPORTING",
            )
            report_paths = REPORTER.generate_all_reports(temp_result)

            # -------------------------------------------------------------
            # FINALIZATION
            # -------------------------------------------------------------
            stage_reached = "COMPLETED"
            current_status = WorkflowStatus.RECOVERED if was_recovered else WorkflowStatus.SUCCESS
            LOGGER.log(
                execution_id=execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.WORKFLOW_COMPLETED,
                severity=LogSeverity.INFO,
                message=f"Workflow completed successfully with status {current_status.value}.",
                status=current_status,
                metadata={
                    "total_buses_ranked": len(ranked_buses),
                    "was_recovered": was_recovered,
                    "retries": len(all_retry_history),
                    "incidents": len(workflow_incidents),
                },
            )

        except ValidationError as val_err:
            current_status = WorkflowStatus.FAILED
            error_message = f"Validation Error: {val_err}"
            LOGGER.log(
                execution_id=execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.VALIDATION_FAILED,
                severity=LogSeverity.ERROR,
                message=error_message,
                status=WorkflowStatus.FAILED,
            )

        except Exception as unhandled_err:
            current_status = WorkflowStatus.FAILED
            error_message = f"{type(unhandled_err).__name__}: {unhandled_err}"
            LOGGER.log(
                execution_id=execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.WORKFLOW_TERMINATED,
                severity=LogSeverity.CRITICAL,
                message=f"Workflow failed at stage {stage_reached}: {error_message}",
                status=WorkflowStatus.FAILED,
            )

        # -------------------------------------------------------------
        # STEP 6: Telemetry Recording & Final Result Construction
        # -------------------------------------------------------------
        duration = round(time.perf_counter() - t0, 3)
        end_time_iso = datetime.now().isoformat()

        MONITOR.record_completion(
            execution_id=execution_id,
            status=current_status,
            duration_sec=duration,
            retry_count=len(all_retry_history),
            recovery_count=len(all_recovery_history),
        )

        final_result = WorkflowExecutionResult(
            execution_id=execution_id,
            status=current_status,
            request=request,
            buses_found=buses_found,
            ranked_buses=ranked_buses,
            recommended_bus=recommended_bus,
            retry_history=all_retry_history,
            recovery_history=all_recovery_history,
            incidents=workflow_incidents,
            execution_duration_sec=duration,
            start_time=start_time_iso,
            end_time=end_time_iso,
            error_message=error_message,
            stage_reached=stage_reached,
            report_paths=report_paths,
        )

        # If workflow failed, attempt generating a failure audit report
        if current_status == WorkflowStatus.FAILED and not faults.get("simulate_report_failure"):
            try:
                final_result.report_paths = REPORTER.generate_all_reports(final_result)
            except Exception:
                pass

        return final_result
