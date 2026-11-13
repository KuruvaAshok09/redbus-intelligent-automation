"""
Incident Management Engine for RedBus Automation Platform.
Detects, classifies, logs, and tracks operational anomalies and self-healing remediations.
"""

import json
import os
import threading
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    Incident,
    FailureCategory,
    LogSeverity,
    AutomationEventType,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER


class IncidentManager:
    """Enterprise incident lifecycle tracker and auditor."""

    _lock = threading.Lock()

    def __init__(self, incidents_file: Optional[Path] = None):
        self.incidents_file = incidents_file or CONFIG.INCIDENTS_FILE_PATH
        self.incidents_file.parent.mkdir(parents=True, exist_ok=True)
        self._in_memory_incidents: List[Incident] = []

    def record_incident(
        self,
        failure_category: FailureCategory,
        is_recoverable: bool,
        error_message: str,
        execution_id: Optional[str] = None,
        retry_attempts: int = 0,
        recovery_action: Optional[str] = None,
        final_status: str = "OPEN",
        details: Optional[Dict[str, Any]] = None,
    ) -> Incident:
        """Creates, classifies, and records a structured incident."""
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        ts = datetime.now().isoformat()

        incident = Incident(
            incident_id=incident_id,
            timestamp=ts,
            failure_category=failure_category,
            is_recoverable=is_recoverable,
            error_message=str(error_message),
            retry_attempts=max(0, retry_attempts),
            recovery_action=recovery_action,
            final_status=final_status,
            execution_id=execution_id,
            details=details or {},
        )

        with self._lock:
            self._in_memory_incidents.append(incident)
            try:
                with open(self.incidents_file, "a", encoding="utf-8") as f:
                    record_dict = {
                        "incident_id": incident.incident_id,
                        "timestamp": incident.timestamp,
                        "failure_category": incident.failure_category.value,
                        "is_recoverable": incident.is_recoverable,
                        "error_message": incident.error_message,
                        "retry_attempts": incident.retry_attempts,
                        "recovery_action": incident.recovery_action,
                        "final_status": incident.final_status,
                        "execution_id": incident.execution_id,
                        "details": incident.details,
                    }
                    f.write(json.dumps(record_dict) + "\n")
            except Exception as e:
                print(f"[INCIDENT LOGGER ERROR] Failed writing incident file: {e}")

        LOGGER.log(
            execution_id=execution_id or "SYSTEM_INCIDENT",
            component="IncidentManager",
            event_type=AutomationEventType.INCIDENT_RECORDED,
            severity=LogSeverity.WARNING if is_recoverable else LogSeverity.CRITICAL,
            message=f"Incident {incident_id} ({failure_category.value}): {error_message}",
            status=WorkflowStatus.RUNNING if is_recoverable else WorkflowStatus.FAILED,
            metadata={"incident_id": incident_id, "category": failure_category.value, "recoverable": is_recoverable},
        )

        return incident

    def resolve_incident(self, incident_id: str, recovery_action: str) -> bool:
        """Marks an active incident as resolved through self-healing recovery."""
        self.get_incidents()
        with self._lock:
            for inc in self._in_memory_incidents:
                if inc.incident_id == incident_id:
                    previous_status = inc.final_status
                    previous_action = inc.recovery_action
                    inc.final_status = "RESOLVED"
                    inc.recovery_action = recovery_action
                    try:
                        self._persist_incidents()
                    except Exception:
                        inc.final_status = previous_status
                        inc.recovery_action = previous_action
                        raise
                    return True
        return False

    def _persist_incidents(self) -> None:
        """Atomically rewrites JSONL storage so lifecycle changes survive reloads."""
        temp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.incidents_file.parent,
                prefix=f".{self.incidents_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as f:
                temp_path = f.name
                for incident in self._in_memory_incidents:
                    f.write(json.dumps(self._incident_to_record(incident)) + "\n")
            os.replace(temp_path, self.incidents_file)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def _incident_to_record(incident: Incident) -> Dict[str, Any]:
        return {
            "incident_id": incident.incident_id,
            "timestamp": incident.timestamp,
            "failure_category": incident.failure_category.value,
            "is_recoverable": incident.is_recoverable,
            "error_message": incident.error_message,
            "retry_attempts": incident.retry_attempts,
            "recovery_action": incident.recovery_action,
            "final_status": incident.final_status,
            "execution_id": incident.execution_id,
            "details": incident.details,
        }

    def get_incidents(
        self,
        execution_id: Optional[str] = None,
        category: Optional[FailureCategory] = None,
        limit: Optional[int] = None,
    ) -> List[Incident]:
        """Retrieves structured incident records with optional filtering."""
        with self._lock:
            incidents = list(self._in_memory_incidents)

        # If in-memory is empty (e.g. fresh process restart), load from disk
        if not incidents and self.incidents_file.exists():
            with self._lock:
                try:
                    with open(self.incidents_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line)
                                inc = Incident(
                                    incident_id=data["incident_id"],
                                    timestamp=data["timestamp"],
                                    failure_category=FailureCategory(data["failure_category"]),
                                    is_recoverable=data["is_recoverable"],
                                    error_message=data["error_message"],
                                    retry_attempts=data.get("retry_attempts", 0),
                                    recovery_action=data.get("recovery_action"),
                                    final_status=data.get("final_status", "OPEN"),
                                    execution_id=data.get("execution_id"),
                                    details=data.get("details", {}),
                                )
                                self._in_memory_incidents.append(inc)
                    incidents = list(self._in_memory_incidents)
                except Exception:
                    pass

        if execution_id:
            incidents = [i for i in incidents if i.execution_id == execution_id]
        if category:
            incidents = [i for i in incidents if i.failure_category == category]

        if limit:
            return incidents[-limit:]
        return incidents

    def get_summary(self) -> Dict[str, Any]:
        """Returns statistical telemetry on incident trends."""
        incidents = self.get_incidents()
        total = len(incidents)
        resolved = sum(1 for i in incidents if i.final_status in ("RESOLVED", "RECOVERED"))
        unresolved = total - resolved
        categories = {}
        for i in incidents:
            cat_name = i.failure_category.value
            categories[cat_name] = categories.get(cat_name, 0) + 1

        return {
            "total_incidents": total,
            "resolved_incidents": resolved,
            "unresolved_incidents": unresolved,
            "resolution_rate_percent": round((resolved / total * 100.0), 1) if total > 0 else 100.0,
            "by_category": categories,
        }

    def reset_incidents(self) -> None:
        """Clears incident storage for clean test suites."""
        with self._lock:
            self._in_memory_incidents.clear()
            if self.incidents_file.exists():
                try:
                    self.incidents_file.unlink()
                except Exception:
                    pass


# Global Incident Manager singleton
INCIDENT_MANAGER = IncidentManager()
