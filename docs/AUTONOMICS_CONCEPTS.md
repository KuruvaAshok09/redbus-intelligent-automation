# Autonomics Engineering Concepts
## RedBus Intelligent Ticket Search and Automation System
**Author:** Kuruva Ashok (Individual B.Tech Student Project for HCLTech Autonomics Role Evaluation)  
**Evaluation Focus:** Real-World Application of Enterprise Autonomics Principles  

---

## 1. What is Autonomics?

In modern software and IT infrastructure engineering, **Autonomics** refers to the paradigm of building self-managing, self-healing, self-optimizing, and self-protecting systems. Inspired by the human autonomic nervous system (which regulates breathing and heartbeat without conscious intervention), an autonomics system automatically detects runtime anomalies, applies corrective remedies, observes system health, and maintains operational service-level agreements (SLAs) without human toil.

This project implements the foundational autonomic control loop: **MAPE-K (Monitor, Analyze, Plan, Execute, Knowledge)**.

---

## 2. Autonomic Capabilities Implemented in the System

### A. Workflow Automation
- **Definition:** The automated execution of a structured series of business activities according to predefined rules.
- **Implementation:** The user defines search intentions (source, destination, budget, passengers). The system automatically sanitizes the inputs, queries offline inventory, prunes ineligible buses, ranks candidates, and writes compliance reports without manual intervention.

### B. Automation Orchestration
- **Definition:** Centralized management and coordination of disparate, loosely coupled services across a deterministic execution pipeline.
- **Implementation (`redbus_automation/orchestrator.py`):**
  - Coordinates `InputValidator` -> `RetryEngine` -> `BusSearchEngine` -> `BusFilterEngine` -> `BusComparisonEngine` -> `ReportGenerator` -> `AutomationMonitor`.
  - Enforces explicit state transitions: `PENDING` -> `RUNNING` -> `SUCCESS` / `RECOVERED` / `FAILED`.
  - Guarantees that `SUCCESS` is reserved exclusively for runs where all pipeline tasks completed cleanly without unhandled exceptions.

### C. Monitoring & Real-Time Metrics
- **Definition:** Continuous collection and aggregation of runtime performance counters.
- **Implementation (`redbus_automation/monitoring.py`):**
  - Measures total executions, successful runs, failed runs, and self-healed recoveries.
  - Dynamically calculates success rate ($\%$), failure rate ($\%$), and rolling average latency (seconds).
  - Employs execution ID deduplication to prevent double-counting of metrics.

### D. Incident Detection
- **Definition:** The automated identification of faults, SLA breaches, or environmental disruptions.
- **Implementation:**
  - Detects transient inventory service outages (`TransientServiceError`).
  - Detects data corruption or missing catalog files (`DataFetchError`).
  - Detects zero-result outages caused by overly restrictive user filter combinations.
  - Detects filesystem IO locking during report generation (`ReportGenerationError`).

### E. Bounded Retry Mechanism
- **Definition:** An automated resilience pattern that re-executes failed operations subject to finite attempt bounds and progressive delay intervals.
- **Implementation (`redbus_automation/retry_engine.py`):**
  - **Bounded Attempts:** Configured to a maximum of 3 attempts, preventing infinite retry loops and runaway resource consumption.
  - **Exponential Backoff:** Introduces progressive delays:
    $$\text{Delay}_k = \text{Initial} \times (\text{Factor})^{k-1}$$
  - **Error Classification:** Enforces zero retries for permanent errors (e.g. `ValidationError`, `TypeError`), while retrying only transient disruptions.

### F. Automated Recovery & Self-Healing
- **Definition:** The autonomic capability of a system to repair itself and restore normal operation upon failure without operator intervention.
- **Implementation (`redbus_automation/recovery_engine.py`):**
  1. **Secondary Offline Mirror Fallback (`SECONDARY_MIRROR_FALLBACK`):** When the primary search provider encounters transient timeouts, the engine automatically routes traffic to a verified secondary mirror.
  2. **Catalog Seed Reconstitution (`CATALOG_SEED_RECONSTITUTION`):** If the catalog JSON file is corrupted or deleted, the system reconstructs the master dataset from embedded seed definitions.
  3. **Constraint Relaxation (`CONSTRAINT_RELAXATION`):** If zero buses match strict user filters on an existing route, the engine dynamically increases budget by 25% and removes operator restrictions to prevent zero-result outages.
  4. **Unrecoverable Incident Escalation (`UnrecoverableIncidentError`):** If all self-healing actions fail, the incident is escalated with critical telemetry rather than falsely reporting success.

### G. Observability & Structured JSON Logging
- **Definition:** The degree to which internal system states can be inferred from external outputs, telemetry, and structured events.
- **Implementation (`redbus_automation/logger.py`):**
  - Outputs strictly validated, machine-parsable JSON lines to `logs/automation_execution.jsonl`.
  - Standard schema: `timestamp`, `execution_id`, `event_type`, `severity`, `component`, `message`, `execution_status`, `metadata`.

### H. Operational Reporting & Compliance
- **Definition:** The automated production of immutable, auditable records for regulatory compliance and business review.
- **Implementation (`redbus_automation/reporting.py`):**
  - Produces structured CSV (`reports/report_*.csv`) for data warehouse ingestion.
  - Produces structured JSON (`reports/report_*.json`) containing complete diagnostic payloads, autonomic retry histories, and decision justifications.

---

## 3. Comparison: Traditional Scripting vs. HCLTech Autonomics Engineering

| Feature | Traditional Scripting | HCLTech Autonomics Approach (This Project) |
|---|---|---|
| **Error Handling** | Bare `try/except: pass` or unhandled script crash | Typed exceptions, error classification, bounded retry |
| **Recovery** | Manual intervention required | Autonomic self-healing (mirrors, seed restore, constraint relaxation) |
| **Telemetry** | Unstructured `print()` statements | Strict structured JSONL logging + real-time KPI metrics |
| **Observability** | Guesswork from terminal logs | Dedicated monitoring service, success/failure rate calculations |
| **Reporting** | Ad-hoc text dumps | Standardized CSV and JSON compliance artifacts |
| **Architecture** | Spaghetti script mixing UI and logic | Strict modular decoupling, testable engines, clean CLI & Web UI |
| **Integrity** | May report success on silent failures | Guaranteed truth in telemetry; `SUCCESS` assigned only on true completion |
