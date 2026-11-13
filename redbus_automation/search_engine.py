"""
Simulated Bus Search Engine for RedBus Automation Platform.
Loads simulated bus schedules from local JSON catalog completely offline.
Supports controlled fault injection for autonomics resilience testing.
"""

import json
from pathlib import Path
from typing import List, Optional

from redbus_automation.config import CONFIG
from redbus_automation.models import (
    Bus,
    SearchRequest,
    TransientServiceError,
    DataFetchError,
    LogSeverity,
    AutomationEventType,
    WorkflowStatus,
)
from redbus_automation.logger import LOGGER


class BusSearchEngine:
    """Offline bus catalog search engine operating on simulated datasets."""

    COMPONENT_NAME = "BusSearchEngine"

    def __init__(self, data_file: Optional[Path] = None):
        self.data_file = data_file or CONFIG.DEFAULT_DATA_FILE
        self._cached_buses: Optional[List[Bus]] = None

    def search(
        self,
        request: SearchRequest,
        execution_id: str = "SYSTEM_SEARCH",
        simulate_transient_failure: bool = False,
        simulate_corruption: bool = False,
        force_empty: bool = False,
    ) -> List[Bus]:
        """
        Executes bus search against local catalog.

        Controlled Fault Injections:
        - simulate_transient_failure: Triggers TransientServiceError to verify retry/recovery.
        - simulate_corruption: Triggers DataFetchError to verify unrecoverable data incidents.
        - force_empty: Forces search to yield zero results.
        """
        LOGGER.log(
            execution_id=execution_id,
            component=self.COMPONENT_NAME,
            event_type=AutomationEventType.SEARCH_INITIATED,
            severity=LogSeverity.INFO,
            message=f"Executing search for {request.source} -> {request.destination}.",
            status=WorkflowStatus.RUNNING,
        )

        # Fault Injection Check 1: Simulated transient gateway/service error
        if simulate_transient_failure:
            err_msg = "FAULT INJECTION: Temporary bus inventory service unavailable (HTTP 503 Simulated)."
            LOGGER.log(
                execution_id=execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.SEARCH_FAILED,
                severity=LogSeverity.WARNING,
                message=err_msg,
                status=WorkflowStatus.RUNNING,
            )
            raise TransientServiceError(err_msg)

        # Fault Injection Check 2: Data corruption error
        if simulate_corruption:
            err_msg = "FAULT INJECTION: Bus inventory data source corrupted."
            LOGGER.log(
                execution_id=execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.SEARCH_FAILED,
                severity=LogSeverity.ERROR,
                message=err_msg,
                status=WorkflowStatus.FAILED,
            )
            raise DataFetchError(err_msg)

        # Fault Injection Check 3: Force empty results
        if force_empty:
            LOGGER.log(
                execution_id=execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.SEARCH_COMPLETED,
                severity=LogSeverity.INFO,
                message="FAULT INJECTION: Forced empty search result.",
                status=WorkflowStatus.RUNNING,
                metadata={"buses_found": 0},
            )
            return []

        # Load raw data from disk
        all_buses = self._load_data(execution_id)

        # Match source and destination case-insensitively
        src_target = request.source.strip().lower()
        dst_target = request.destination.strip().lower()

        matched_buses: List[Bus] = [
            b for b in all_buses
            if b.source.strip().lower() == src_target and b.destination.strip().lower() == dst_target
        ]

        LOGGER.log(
            execution_id=execution_id,
            component=self.COMPONENT_NAME,
            event_type=AutomationEventType.SEARCH_COMPLETED,
            severity=LogSeverity.INFO,
            message=f"Search completed: found {len(matched_buses)} matching buses for route.",
            status=WorkflowStatus.RUNNING,
            metadata={
                "source": request.source,
                "destination": request.destination,
                "total_buses_found": len(matched_buses),
            },
        )

        return matched_buses

    def _load_data(self, execution_id: str) -> List[Bus]:
        """Loads and parses bus data from JSON catalog."""
        if not self.data_file.exists():
            err = f"Simulated bus catalog not found at: {self.data_file}"
            LOGGER.log(
                execution_id=execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.SEARCH_FAILED,
                severity=LogSeverity.ERROR,
                message=err,
                status=WorkflowStatus.FAILED,
            )
            raise DataFetchError(err)

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                raw_list = json.load(f)

            buses: List[Bus] = []
            for item in raw_list:
                bus = Bus(
                    bus_id=str(item["bus_id"]),
                    operator_name=str(item["operator_name"]),
                    source=str(item["source"]),
                    destination=str(item["destination"]),
                    departure_time=str(item["departure_time"]),
                    arrival_time=str(item["arrival_time"]),
                    fare=float(item["fare"]),
                    available_seats=int(item["available_seats"]),
                    bus_type=str(item["bus_type"]),
                    rating=float(item["rating"]),
                )
                buses.append(bus)

            return buses

        except Exception as e:
            err = f"Failed to parse bus catalog: {e}"
            LOGGER.log(
                execution_id=execution_id,
                component=self.COMPONENT_NAME,
                event_type=AutomationEventType.SEARCH_FAILED,
                severity=LogSeverity.ERROR,
                message=err,
                status=WorkflowStatus.FAILED,
            )
            raise DataFetchError(err) from e

    def get_all_routes(self) -> List[dict]:
        """Returns distinct source and destination pairs available in the catalog."""
        try:
            buses = self._load_data(execution_id="CATALOG_QUERY")
            routes = set((b.source, b.destination) for b in buses)
            return [{"source": s, "destination": d} for s, d in sorted(routes)]
        except Exception:
            return []

    def get_all_cities(self) -> List[str]:
        """Returns city names present in both primary and fallback catalogs."""
        cities = set()
        for catalog_file in (self.data_file, CONFIG.DEFAULT_FALLBACK_DATA_FILE):
            if not catalog_file.exists():
                raise DataFetchError(f"Simulated bus catalog not found at: {catalog_file}")
            try:
                with open(catalog_file, "r", encoding="utf-8") as catalog:
                    records = json.load(catalog)
                for record in records:
                    cities.update(
                        city.strip()
                        for city in (str(record["source"]), str(record["destination"]))
                        if city.strip()
                    )
            except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
                raise DataFetchError(
                    f"Failed to read simulated bus catalog {catalog_file}: {error}"
                ) from error

        return sorted(cities)
