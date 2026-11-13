"""
Configuration settings for RedBus Intelligent Ticket Search and Automation System.
Provides centralized path management, autonomics defaults, and operational parameters.
"""

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AppConfig:
    """Immutable application and autonomics configuration."""

    # Project directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    REPORTS_DIR: Path = BASE_DIR / "reports"

    # Default file paths
    DEFAULT_DATA_FILE: Path = DATA_DIR / "sample_buses.json"
    DEFAULT_FALLBACK_DATA_FILE: Path = DATA_DIR / "fallback_buses.json"
    LOG_FILE_PATH: Path = LOGS_DIR / "automation_execution.jsonl"
    INCIDENTS_FILE_PATH: Path = LOGS_DIR / "incidents.jsonl"
    BOOKINGS_FILE_PATH: Path = REPORTS_DIR / "simulated_bookings.jsonl"

    # Autonomics & Retry policies
    DEFAULT_MAX_RETRIES: int = 3
    DEFAULT_INITIAL_BACKOFF_SEC: float = 0.05  # Kept fast for responsiveness and tests
    DEFAULT_BACKOFF_FACTOR: float = 2.0
    CIRCUIT_BREAKER_MAX_FAILURES: int = 5

    # Ranking weights (Sum = 1.0)
    # Higher rating is better, lower fare is better, shorter duration is better, higher seats available is better
    WEIGHT_FARE: float = 0.40
    WEIGHT_DURATION: float = 0.25
    WEIGHT_RATING: float = 0.25
    WEIGHT_SEATS: float = 0.10

    # Simulation Notice
    SIMULATION_DISCLAIMER: str = (
        "SIMULATED DATA - DEMO / SIMULATION MODE: Offline demonstration only. "
        "No real booking, payment, or external RedBus APIs are contacted."
    )


# Global configuration singleton instance
CONFIG = AppConfig()

# Ensure directories exist
CONFIG.DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG.LOGS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
