"""
Monitoring and Observability Engine for RedBus Automation Platform.
Tracks operational metrics, success/failure rates, latencies, and active workflow states.
Prevents double counting and provides real-time telemetry for the Streamlit dashboard and CLI.
"""

import threading
from typing import Dict, Any, Optional, Set
from redbus_automation.models import WorkflowStatus


class AutomationMonitor:
    """Enterprise observability service maintaining precise lifecycle metrics."""

    _lock = threading.Lock()

    def __init__(self):
        self._total_executions: int = 0
        self._successful_executions: int = 0
        self._failed_executions: int = 0
        self._recovered_executions: int = 0
        self._total_retry_attempts: int = 0
        self._total_recovery_actions: int = 0
        self._total_duration_sec: float = 0.0

        self._active_execution_id: Optional[str] = None
        self._current_status: WorkflowStatus = WorkflowStatus.PENDING
        self._processed_executions: Set[str] = set()

    def record_start(self, execution_id: str) -> None:
        """Signals start of an automation workflow."""
        with self._lock:
            self._active_execution_id = execution_id
            self._current_status = WorkflowStatus.RUNNING

    def record_completion(
        self,
        execution_id: str,
        status: WorkflowStatus,
        duration_sec: float,
        retry_count: int = 0,
        recovery_count: int = 0,
    ) -> None:
        """
        Records the terminal state of an automation execution.
        Safeguarded against double-counting via execution_id deduplication.
        """
        with self._lock:
            if execution_id in self._processed_executions:
                # Prevent duplicate metric inflation
                return

            self._processed_executions.add(execution_id)
            self._total_executions += 1
            self._total_duration_sec += max(0.0, duration_sec)
            self._total_retry_attempts += max(0, retry_count)
            self._total_recovery_actions += max(0, recovery_count)

            if status == WorkflowStatus.SUCCESS:
                self._successful_executions += 1
            elif status == WorkflowStatus.RECOVERED:
                self._recovered_executions += 1
                # Recovered workflows count as successful completions achieved through self-healing
                self._successful_executions += 1
            elif status == WorkflowStatus.FAILED:
                self._failed_executions += 1

            self._current_status = status
            self._active_execution_id = None

    def get_metrics(self) -> Dict[str, Any]:
        """Calculates and returns current system telemetry summary."""
        with self._lock:
            total = self._total_executions
            success = self._successful_executions
            failed = self._failed_executions
            recovered = self._recovered_executions

            avg_dur = (self._total_duration_sec / total) if total > 0 else 0.0
            success_rate = (success / total * 100.0) if total > 0 else 0.0
            failure_rate = (failed / total * 100.0) if total > 0 else 0.0

            return {
                "total_executions": total,
                "successful_executions": success,
                "failed_executions": failed,
                "recovered_executions": recovered,
                "total_retry_attempts": self._total_retry_attempts,
                "total_recovery_actions": self._total_recovery_actions,
                "average_duration_sec": round(avg_dur, 3),
                "success_rate_percent": round(success_rate, 1),
                "failure_rate_percent": round(failure_rate, 1),
                "current_execution_status": self._current_status.value,
                "active_execution_id": self._active_execution_id,
            }

    def reset_metrics(self) -> None:
        """Resets all metrics counters for clean test suite runs."""
        with self._lock:
            self._total_executions = 0
            self._successful_executions = 0
            self._failed_executions = 0
            self._recovered_executions = 0
            self._total_retry_attempts = 0
            self._total_recovery_actions = 0
            self._total_duration_sec = 0.0
            self._active_execution_id = None
            self._current_status = WorkflowStatus.PENDING
            self._processed_executions.clear()


# Global monitoring singleton
MONITOR = AutomationMonitor()
