"""
Unified Structured JSON Logging Engine for RedBus Automation Platform.
Implements a single, strictly typed contract for all system modules.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import threading

from redbus_automation.config import CONFIG
from redbus_automation.models import LogSeverity, AutomationEventType, WorkflowStatus


class AutomationLogger:
    """Enterprise-grade structured JSON logger enforcing consistent log contracts."""

    _lock = threading.Lock()

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file or CONFIG.LOG_FILE_PATH
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        execution_id: str,
        component: str,
        event_type: AutomationEventType,
        severity: LogSeverity,
        message: str,
        status: WorkflowStatus,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Unified logging interface contract. All modules MUST call this method.

        Log Schema:
        - timestamp: ISO 8601 string
        - execution_id: Unique identifier of the automation run
        - event_type: AutomationEventType string
        - severity: LogSeverity string
        - component: Originating system module
        - message: Contextual diagnostic string
        - execution_status: Current WorkflowStatus string
        - metadata: Optional additional telemetry payload
        """
        record: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "execution_id": execution_id,
            "event_type": event_type.value if hasattr(event_type, "value") else str(event_type),
            "severity": severity.value if hasattr(severity, "value") else str(severity),
            "component": component,
            "message": message,
            "execution_status": status.value if hasattr(status, "value") else str(status),
            "metadata": metadata or {},
        }

        # Thread-safe append to JSONL file
        try:
            with self._lock:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
        except Exception as e:
            # Fallback to standard stream in critical IO failures
            print(f"[LOGGER FALLBACK ERROR] Unable to write JSON log: {e}")

        return record

    def get_logs(self, execution_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve historical structured logs, optionally filtered by execution_id."""
        if not self.log_file.exists():
            return []

        logs: List[Dict[str, Any]] = []
        with self._lock:
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entry = json.loads(line)
                                if execution_id is None or entry.get("execution_id") == execution_id:
                                    logs.append(entry)
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                print(f"[LOGGER READ ERROR] Error reading log file: {e}")

        return logs

    def clear_logs(self) -> None:
        """Utility to safely wipe test logs during fresh test runs."""
        with self._lock:
            if self.log_file.exists():
                self.log_file.unlink()


# Global logger instance
LOGGER = AutomationLogger()
