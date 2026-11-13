"""
Unit tests for IncidentManager module.
Verifies failure classification, incident creation, recovery tracking, and telemetry summary.
"""

from pathlib import Path
import pytest

from redbus_automation.models import FailureCategory
from redbus_automation.incident_manager import IncidentManager


@pytest.fixture
def incident_mgr(tmp_path):
    return IncidentManager(incidents_file=tmp_path / "test_incidents.jsonl")


def test_record_recoverable_incident(incident_mgr):
    """Verifies recording a transient recoverable failure."""
    inc = incident_mgr.record_incident(
        failure_category=FailureCategory.TRANSIENT_SERVICE_ERROR,
        is_recoverable=True,
        error_message="Gateway timeout 503",
        execution_id="EXEC-TEST-INC-1",
        retry_attempts=2,
    )

    assert inc.incident_id.startswith("INC-")
    assert inc.is_recoverable is True
    assert inc.final_status == "OPEN"
    assert inc.retry_attempts == 2

    # Check persistence & retrieval
    all_incs = incident_mgr.get_incidents()
    assert len(all_incs) == 1
    assert all_incs[0].incident_id == inc.incident_id


def test_record_non_recoverable_incident(incident_mgr):
    """Verifies recording an unrecoverable validation error."""
    inc = incident_mgr.record_incident(
        failure_category=FailureCategory.VALIDATION_ERROR,
        is_recoverable=False,
        error_message="Identical source and destination city",
        execution_id="EXEC-TEST-INC-2",
        final_status="FAILED",
    )

    assert inc.is_recoverable is False
    assert inc.final_status == "FAILED"


def test_resolve_incident(incident_mgr):
    """Verifies resolving an open incident through self-healing action."""
    inc = incident_mgr.record_incident(
        failure_category=FailureCategory.CATALOG_FETCH_ERROR,
        is_recoverable=True,
        error_message="Corrupted catalog",
        execution_id="EXEC-TEST-INC-3",
    )

    resolved = incident_mgr.resolve_incident(inc.incident_id, "CATALOG_SEED_RECONSTITUTION")
    assert resolved is True

    updated_inc = incident_mgr.get_incidents(execution_id="EXEC-TEST-INC-3")[0]
    assert updated_inc.final_status == "RESOLVED"
    assert updated_inc.recovery_action == "CATALOG_SEED_RECONSTITUTION"


def test_resolved_incident_survives_storage_reload(incident_mgr):
    inc = incident_mgr.record_incident(
        failure_category=FailureCategory.TRANSIENT_SERVICE_ERROR,
        is_recoverable=True,
        error_message="Transient service interruption",
        execution_id="EXEC-RELOAD-1",
    )

    assert incident_mgr.resolve_incident(inc.incident_id, "SECONDARY_MIRROR_FALLBACK")

    reloaded_manager = IncidentManager(incidents_file=incident_mgr.incidents_file)
    persisted = reloaded_manager.get_incidents(execution_id="EXEC-RELOAD-1")

    assert len(persisted) == 1
    assert persisted[0].final_status == "RESOLVED"
    assert persisted[0].recovery_action == "SECONDARY_MIRROR_FALLBACK"


def test_incident_summary_statistics(incident_mgr):
    """Verifies calculation of incident summary metrics."""
    incident_mgr.record_incident(
        failure_category=FailureCategory.TRANSIENT_SERVICE_ERROR,
        is_recoverable=True,
        error_message="Transient 1",
        final_status="RESOLVED",
    )
    incident_mgr.record_incident(
        failure_category=FailureCategory.VALIDATION_ERROR,
        is_recoverable=False,
        error_message="Validation 1",
        final_status="FAILED",
    )

    summary = incident_mgr.get_summary()
    assert summary["total_incidents"] == 2
    assert summary["resolved_incidents"] == 1
    assert summary["unresolved_incidents"] == 1
    assert summary["resolution_rate_percent"] == 50.0
    assert summary["by_category"]["TRANSIENT_SERVICE_ERROR"] == 1
    assert summary["by_category"]["VALIDATION_ERROR"] == 1
