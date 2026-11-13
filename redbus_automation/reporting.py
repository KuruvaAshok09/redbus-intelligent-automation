"""
Operational Reporting Engine for RedBus Automation Platform.
Generates structured CSV and JSON audit artifacts for completed automation runs.
"""

import csv
import json
from pathlib import Path
from typing import Dict, Optional

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    WorkflowExecutionResult,
    ReportGenerationError,
    LogSeverity,
    AutomationEventType,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER


class ReportGenerator:
    """Generates auditable compliance and operational reports in CSV and JSON formats."""

    COMPONENT_NAME = "ReportGenerator"

    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = reports_dir or CONFIG.REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_report(
        self,
        result: WorkflowExecutionResult,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Serializes complete execution run and telemetry to structured JSON."""
        target_dir = output_dir or self.reports_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"report_{result.execution_id}.json"
        filepath = target_dir / filename

        try:
            payload = {
                "execution_id": result.execution_id,
                "status": result.status.value,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "duration_seconds": result.execution_duration_sec,
                "request": {
                    "source": result.request.source,
                    "destination": result.request.destination,
                    "journey_date": result.request.journey_date,
                    "passengers": result.request.passengers,
                    "max_budget": result.request.max_budget,
                    "preferred_operator": result.request.preferred_operator,
                    "min_rating": result.request.min_rating,
                },
                "autonomics_summary": {
                    "retry_count": len(result.retry_history),
                    "recovery_count": len(result.recovery_history),
                    "is_recovered": (result.status == WorkflowStatus.RECOVERED),
                    "retries": [
                        {
                            "attempt": r.attempt_number,
                            "timestamp": r.timestamp,
                            "delay_sec": r.delay_seconds,
                            "error": r.error_message,
                            "target": r.target_function,
                        }
                        for r in result.retry_history
                    ],
                    "recoveries": [
                        {
                            "action_id": a.action_id,
                            "failure_type": a.failure_type,
                            "strategy": a.strategy_used,
                            "successful": a.successful,
                            "details": a.details,
                            "timestamp": a.timestamp,
                        }
                        for a in result.recovery_history
                    ],
                },
                "search_results": {
                    "total_buses_found": len(result.buses_found),
                    "total_ranked_buses": len(result.ranked_buses),
                    "recommended_bus": (
                        {
                            "bus_id": result.recommended_bus.bus.bus_id,
                            "operator_name": result.recommended_bus.bus.operator_name,
                            "fare": result.recommended_bus.bus.fare,
                            "departure_time": result.recommended_bus.bus.departure_time,
                            "arrival_time": result.recommended_bus.bus.arrival_time,
                            "duration": result.recommended_bus.bus.duration_formatted,
                            "rating": result.recommended_bus.bus.rating,
                            "available_seats": result.recommended_bus.bus.available_seats,
                            "composite_score": result.recommended_bus.composite_score,
                            "reason": result.recommended_bus.recommendation_reason,
                        }
                        if result.recommended_bus
                        else None
                    ),
                    "ranked_buses": [
                        {
                            "rank": rb.rank,
                            "bus_id": rb.bus.bus_id,
                            "operator": rb.bus.operator_name,
                            "fare": rb.bus.fare,
                            "departure": rb.bus.departure_time,
                            "arrival": rb.bus.arrival_time,
                            "rating": rb.bus.rating,
                            "seats": rb.bus.available_seats,
                            "score": rb.composite_score,
                            "reason": rb.recommendation_reason,
                        }
                        for rb in result.ranked_buses
                    ],
                },
                "error_message": result.error_message,
                "disclaimer": CONFIG.SIMULATION_DISCLAIMER,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            LOGGER.log(
                execution_id=result.execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.REPORT_GENERATED,
                severity=LogSeverity.INFO,
                message=f"JSON execution report generated: {filepath.name}",
                status=result.status,
                metadata={"format": "JSON", "path": str(filepath)},
            )
            return filepath

        except Exception as e:
            err = f"Failed to generate JSON report: {e}"
            LOGGER.log(
                execution_id=result.execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.REPORT_GENERATED,
                severity=LogSeverity.ERROR,
                message=err,
                status=WorkflowStatus.FAILED,
            )
            raise ReportGenerationError(err) from e

    def generate_csv_report(
        self,
        result: WorkflowExecutionResult,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Serializes execution summary and bus comparisons to tabular CSV format."""
        target_dir = output_dir or self.reports_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"report_{result.execution_id}.csv"
        filepath = target_dir / filename

        headers = [
            "execution_id",
            "status",
            "start_time",
            "end_time",
            "duration_sec",
            "source",
            "destination",
            "journey_date",
            "passengers",
            "max_budget",
            "retries_count",
            "recovery_count",
            "rank",
            "bus_id",
            "operator_name",
            "departure_time",
            "arrival_time",
            "duration",
            "fare",
            "rating",
            "available_seats",
            "composite_score",
            "recommendation_reason",
            "error_message",
        ]

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                if result.ranked_buses:
                    for rb in result.ranked_buses:
                        writer.writerow([
                            result.execution_id,
                            result.status.value,
                            result.start_time,
                            result.end_time,
                            result.execution_duration_sec,
                            result.request.source,
                            result.request.destination,
                            result.request.journey_date,
                            result.request.passengers,
                            result.request.max_budget,
                            len(result.retry_history),
                            len(result.recovery_history),
                            rb.rank,
                            rb.bus.bus_id,
                            rb.bus.operator_name,
                            rb.bus.departure_time,
                            rb.bus.arrival_time,
                            rb.bus.duration_formatted,
                            rb.bus.fare,
                            rb.bus.rating,
                            rb.bus.available_seats,
                            rb.composite_score,
                            rb.recommendation_reason,
                            result.error_message or "",
                        ])
                else:
                    # Single audit row when no buses were ranked
                    writer.writerow([
                        result.execution_id,
                        result.status.value,
                        result.start_time,
                        result.end_time,
                        result.execution_duration_sec,
                        result.request.source,
                        result.request.destination,
                        result.request.journey_date,
                        result.request.passengers,
                        result.request.max_budget,
                        len(result.retry_history),
                        len(result.recovery_history),
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "No ranked buses available.",
                        result.error_message or "",
                    ])

            LOGGER.log(
                execution_id=result.execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.REPORT_GENERATED,
                severity=LogSeverity.INFO,
                message=f"CSV execution report generated: {filepath.name}",
                status=result.status,
                metadata={"format": "CSV", "path": str(filepath)},
            )
            return filepath

        except Exception as e:
            err = f"Failed to generate CSV report: {e}"
            LOGGER.log(
                execution_id=result.execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.REPORT_GENERATED,
                severity=LogSeverity.ERROR,
                message=err,
                status=WorkflowStatus.FAILED,
            )
            raise ReportGenerationError(err) from e

    def generate_all_reports(
        self,
        result: WorkflowExecutionResult,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, str]:
        """Generates both JSON and CSV reports and returns their absolute file paths."""
        json_path = self.generate_json_report(result, output_dir=output_dir)
        csv_path = self.generate_csv_report(result, output_dir=output_dir)
        return {
            "json": str(json_path.resolve()),
            "csv": str(csv_path.resolve()),
        }


# Global reporting singleton
REPORTER = ReportGenerator()
