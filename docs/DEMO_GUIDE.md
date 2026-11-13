# Technical Demonstration Guide & Interview Preparation
## RedBus Intelligent Ticket Search and Automation System
**Author:** Kuruva Ashok (Individual B.Tech Student Project for HCLTech Autonomics Role Evaluation)  

---

# PART 1: 5-MINUTE TECHNICAL DEMONSTRATION SCRIPT

This step-by-step sequence is designed to showcase the complete engineering architecture to evaluators in exactly 5 minutes.

---

### Step 1: Health Audit & Verification (Minute 1: 00:00 - 01:00)
- **Objective:** Prove environmental readiness and clean dependency status.
- **Action:** Open terminal (Git Bash or PowerShell) and run:
  ```bash
  bash scripts/test.sh
  ```
- **What to Demonstrate:**
  - The latest recorded test run: 126 passed, no warnings.
  - Explain that all current unit, integration, validation, retry, recovery, and reporting tests pass.
  - Highlight the offline nature: zero external network calls are made.

---

### Step 2: Normal CLI Automation Run (Minute 2: 01:00 - 02:00)
- **Objective:** Demonstrate end-to-end workflow execution, ranking, and compliance artifact creation.
- **Action:** Run the command-line orchestrator:
  ```bash
  python -m redbus_automation.main --source Bangalore --destination Hyderabad
  ```
- **What to Highlight in Output:**
  - `Execution ID`: Traceable unique run identifier (e.g., `EXEC-20261113-194947-5A04EC`).
  - `Status`: `SUCCESS` with execution duration (~0.03 seconds).
  - `Decision Explainability`: Show the natural language reason for the top-ranked simulated demo bus.
  - `Generated Artifacts`: Point out the generated JSON and CSV reports in `reports/`.

---

### Step 3: Fault Injection & Self-Healing Resilience (Minute 3: 02:00 - 03:30)
- **Objective:** Prove autonomics capabilities under simulated infrastructure failure.
- **Action:** Execute the CLI with simulated service disruption:
  ```bash
  python -m redbus_automation.main --source Bangalore --destination Hyderabad --simulate-transient-failure
  ```
- **What to Highlight in Output:**
  - Show how the system detected the simulated HTTP 503 gateway timeout.
  - Show the activation of `RecoveryEngine`.
  - Point out the `[REC-XXXXXXXX] Strategy: SECONDARY_MIRROR_FALLBACK (SUCCESS)` message.
  - Emphasize that the workflow status transitioned to `RECOVERED` (not blindly claiming pure SUCCESS, but acknowledging successful automated remediation).

---

### Step 4: Streamlit Enterprise Dashboard (Minute 4 & 5: 03:30 - 05:00)
- **Objective:** Demonstrate user-facing observability, real-time KPI tiles, and report downloads.
- **Action:** Start the dashboard:
  ```bash
  bash scripts/start.sh
  ```
- **What to Walk Through:**
  1. **Top Notice:** Point out the clear `[SIMULATED DATA]` indicator.
  2. **Sidebar:** Enter route (Bangalore -> Hyderabad), pick journey date, click **"Search & Execute Automation"**.
  3. **Overview Tab:** Show the Recommended Bus card, composite score, and explainability text.
  4. **Executive Dashboard:** Show runtime KPI telemetry: Total Executions, Success Rate %, Latency, and recovery counts. These in-process dashboard metrics are not shared with the standalone health probe.
  5. **Incident Tab:** Show retry telemetry and self-healing action history.
  6. **Execution Logs Tab:** Show live structured JSON audit lines.
  7. **Reports Tab:** Click **"Download CSV"** and **"Download JSON"** to inspect compliance reports.

---

# PART 2: TECHNICAL INTERVIEW PREPARATION (15 QUESTIONS & ANSWERS)

These answers directly reflect the actual codebase and engineering decisions implemented in this project.

---

### 1. Why did you select this project?
> *"I selected this project because intelligent travel search embodies real enterprise automation challenges: handling transient upstream API disruptions, enforcing multi-variable business constraints, balancing multi-criteria optimization (fare, duration, ratings), and delivering observable, auditable outcomes. It provided the ideal real-world context to apply HCLTech Autonomics principles—such as self-healing, bounded retries, and automated operational reporting—within a deterministic, offline-first architecture."*

### 2. What is Autonomics?
> *"Autonomics is the discipline of designing software and operational workflows that manage, heal, protect, and optimize themselves with minimal human intervention. Based on the MAPE-K loop (Monitor, Analyze, Plan, Execute, Knowledge), an autonomic system detects operational disruptions, applies predefined remediation actions, tracks system health through real-time telemetry, and escalates unrecoverable incidents safely."*

### 3. What is automation orchestration?
> *"Automation orchestration is the centralized coordination of multiple discrete tasks, services, and error boundaries across a defined lifecycle. In my project, `AutomationOrchestrator` acts as the single coordinator that manages the sequential pipeline: Input Validation -> Bounded Retry Search -> Domain Filtering -> Explainable Ranking -> Reporting -> Monitoring. It maintains execution state (`PENDING`, `RUNNING`, `SUCCESS`, `RECOVERED`, `FAILED`) and assigns unique execution IDs to ensure end-to-end traceability."*

### 4. What is monitoring?
> *"Monitoring is the active collection, aggregation, and tracking of system health indicators and performance counters. In `monitoring.py`, the `AutomationMonitor` singleton records total executions, successes, failures, recoveries, retries, and durations. It computes rolling metrics such as success rate percentage and average latency, and features execution ID deduplication to prevent double-counting."*

### 5. What is incident detection?
> *"Incident detection is the automated identification of runtime faults, exceptions, or environmental anomalies before they cause user-facing outages. The system actively detects transient network timeouts (`TransientServiceError`), catalog data corruption or missing files (`DataFetchError`), zero-result filter over-constraints, and filesystem write locks during reporting."*

### 6. What is retry?
> *"A retry mechanism automatically re-executes an operation that failed due to a temporary disruption. In `retry_engine.py`, retries are strictly bounded (default maximum 3 attempts) with progressive exponential delays. Crucially, the retry engine classifies errors: it retries transient exceptions while immediately rejecting permanent errors like `ValidationError` without retrying."*

### 7. What is recovery?
> *"Recovery is the autonomic execution of corrective strategies when normal operation or retries fail. In `recovery_engine.py`, the system implements three self-healing remediation routines: (1) `SECONDARY_MIRROR_FALLBACK` for transient search failures, (2) `CATALOG_SEED_RECONSTITUTION` for corrupted data files, and (3) `CONSTRAINT_RELAXATION` (expanding budget by 25%) when user filters eliminate all buses. If recovery fails, it escalates an `UnrecoverableIncidentError` rather than falsely reporting success."*

### 8. What is exponential backoff?
> *"Exponential backoff is a retry pacing algorithm where the delay between successive attempts increases exponentially: $\text{Delay} = \text{Initial} \times (\text{Factor})^{\text{attempt}-1}$. For example, with an initial delay of 0.05s and a factor of 2.0, attempts occur after 0.05s, 0.10s, and 0.20s. This prevents overwhelming a recovering upstream service with thundering herd traffic while allowing temporary glitches to resolve."*

### 9. Why use Python?
> *"Python was chosen for its rich standard library, clean dataclasses and type hinting, modular design capabilities, and rapid testing ecosystem (Pytest). It allows strict separation of concerns between headless business logic and user presentation layers (CLI and Streamlit), making it ideal for enterprise-grade automation."*

### 10. Why use Bash?
> *"Bash scripts provide portable, automated environment bootstrapping, continuous testing, and health checks across Windows 11 Git Bash and Linux environments. Scripts like `setup.sh`, `test.sh`, and `health_check.sh` enforce deterministic CI/CD and deployment standards without manual commands. Compatibility wrappers such as `run_tests.sh` remain available for convenience."*

### 11. How does the system work offline?
> *"The platform is completely offline-first. Simulated bus inventory is stored in a structured local JSON file (`data/sample_buses.json`). All filtering, scoring, retries, self-healing, logging, and reporting run entirely on local CPU cycles without making external HTTP requests or relying on external cloud APIs."*

### 12. What happens when the search engine fails?
> *"When search fails:
> 1. The `RetryEngine` catches the `TransientServiceError` and retries up to 3 times with exponential backoff.
> 2. If all retries fail, the `RecoveryEngine` activates `SECONDARY_MIRROR_FALLBACK` to retrieve candidate buses from an offline secondary replica.
> 3. If recovery succeeds, the workflow completes with status `RECOVERED`.
> 4. If all fallbacks fail, the orchestrator catches the unrecoverable incident, transitions to `FAILED`, logs critical telemetry, and generates an incident report."*

### 13. How are execution metrics calculated?
> *"In `monitoring.py`, metrics are computed in real time:
> - $\text{Success Rate (\%)} = (\frac{\text{Successful Executions} + \text{Recovered Executions}}{\text{Total Executions}}) \times 100$
> - $\text{Failure Rate (\%)} = (\frac{\text{Failed Executions}}{\text{Total Executions}}) \times 100$
> - $\text{Average Latency (s)} = \frac{\sum \text{Duration}}{\text{Total Executions}}$
> An internal `_processed_executions` set prevents duplicate completions from skewing counts."*

### 14. How is the recommended bus selected?
> *"Selection uses a deterministic Multi-Criteria Decision Analysis (MCDA) algorithm. Candidate buses are normalized (0.0 to 1.0) and evaluated with calibrated weights:
> - Fare (40% weight): Lower fare is preferred.
> - Duration (25% weight): Shorter travel time is preferred.
> - Rating (25% weight): Higher customer rating is preferred.
> - Seat Availability (10% weight): Higher seat count is preferred.
> The bus with the highest composite score is selected as Rank #1, and an explainable reason is dynamically composed from its performance factors."*

### 15. How do you prevent infinite retries?
> *"Infinite retries are prevented through two strict controls in `retry_engine.py`:
> 1. **Bounded Iteration Loop:** The retry counter is capped at `max_retries` (default 3). If `attempt > max_retries`, the loop terminates and re-raises the underlying exception.
> 2. **Error Classification Gate:** Permanent exceptions (`ValidationError`, `TypeError`, `ValueError`) are caught and re-raised immediately on the first attempt without ever entering the retry loop."*
