"""
Central Automation Orchestrator for RedBus Automation Platform.
Orchestrates the entire lifecycle:
Validation -> Search (with Bounded Retry) -> Filtering -> Comparison & Ranking -> Reporting -> Monitoring.
Guarantees execution tracking, state transitions, and autonomic self-healing.
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
        Executes the end-to-end intelligent automation workflow.

        Supported Fault Injections (for resilience testing):
        - simulate_transient_failure: bool
        - simulate_corruption: bool
        - force_empty: bool
        - simulate_report_failure: bool
        - repeated_workflow_failure: bool
        """
        faults = fault_injection or {}
        execution_id = self.generate_execution_id()
        start_time_iso = datetime.now().isoformat()
        t0 = time.perf_counter()

        # Initialize tracking state
        current_status = WorkflowStatus.RUNNING
        all_retry_history: List[RetryAttempt] = []
        all_recovery_history: List[RecoveryAction] = []
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
                raise UnrecoverableIncidentError("FAULT INJECTION: Repeated unrecoverable system crash triggered.")

            # -------------------------------------------------------------
            # STEP 1: Input Validation (Permanent errors are NEVER retried)
            # -------------------------------------------------------------
            validated_request = InputValidator.validate(
                request=request,
                execution_id=execution_id,
                reference_date=reference_date,
            )

            # -------------------------------------------------------------
            # STEP 2: Simulated Bus Search with Bounded Retry Mechanism
            # -------------------------------------------------------------
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
                # Bounded retry failed or exhausted -> Engage Self-Healing Recovery Engine
                LOGGER.log(
                    execution_id=execution_id,
                    component=self.COMPONENT_NAME,
                    event_type=AutomationEventType.RECOVERY_INITIATED,
                    severity=LogSeverity.WARNING,
                    message=f"Search failed after retries ({service_err}). Activating self-healing recovery.",
                    status=WorkflowStatus.RUNNING,
                )
                recovered_buses, rec_action = self.recovery_engine.handle_search_failure(
                    exc=service_err,
                    request=validated_request,
                    execution_id=execution_id,
                    fallback_search_fn=lambda req: self._safe_fallback_search(req, execution_id),
                )
                all_recovery_history.append(rec_action)
                if rec_action.successful:
                    buses_found = recovered_buses
                    was_recovered = True
                else:
                    raise service_err

            # -------------------------------------------------------------
            # STEP 3: Domain Filtering Engine
            # -------------------------------------------------------------
            filtered_buses = BusFilterEngine.apply_filters(
                buses=buses_found,
                request=validated_request,
                execution_id=execution_id,
            )

            # Self-healing if filters eliminated all available buses on route
            if not filtered_buses and buses_found and not faults.get("disable_zero_result_recovery", False):
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

            # -------------------------------------------------------------
            # STEP 4: Comparison & Explainable Ranking Engine
            # -------------------------------------------------------------
            ranked_buses = BusComparisonEngine.rank_buses(
                buses=filtered_buses,
                execution_id=execution_id,
            )
            if ranked_buses:
                recommended_bus = ranked_buses[0]

            # -------------------------------------------------------------
            # STEP 5: Report Generation (CSV & JSON)
            # -------------------------------------------------------------
            if faults.get("simulate_report_failure"):
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
                execution_duration_sec=round(time.perf_counter() - t0, 3),
                start_time=start_time_iso,
                end_time=datetime.now().isoformat(),
            )
            report_paths = REPORTER.generate_all_reports(temp_result)

            # -------------------------------------------------------------
            # SUCCESS / RECOVERED FINALIZATION
            # -------------------------------------------------------------
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
                message=f"Workflow failed: {error_message}",
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
            execution_duration_sec=duration,
            start_time=start_time_iso,
            end_time=end_time_iso,
            error_message=error_message,
            report_paths=report_paths,
        )

        # If workflow failed, attempt generating a failure audit report
        if current_status == WorkflowStatus.FAILED and not faults.get("simulate_report_failure"):
            try:
                final_result.report_paths = REPORTER.generate_all_reports(final_result)
            except Exception:
                pass

        return final_result

    def _safe_fallback_search(self, request: SearchRequest, execution_id: str) -> List[Bus]:
        """Secondary search routine invoked by recovery engine."""
        # Queries data file directly ignoring transient flags
        return self.search_engine.search(
            request=request,
            execution_id=execution_id,
            simulate_transient_failure=False,
            simulate_corruption=False,
            force_empty=False,
        )
