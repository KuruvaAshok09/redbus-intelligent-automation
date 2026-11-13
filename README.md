# RedBus Intelligent Automation

An offline-first demonstration of autonomic workflow orchestration for bus search and simulated booking.

![Test result](https://img.shields.io/badge/Tests-128%20passed-brightgreen)
![Mode](https://img.shields.io/badge/Mode-Offline%20simulation-orange)

> **Simulation notice:** Bus schedules, fares, availability, fault injection, bookings, and PNR references are simulated. This project does not connect to a live RedBus API, scrape RedBus, reserve real seats, or process payments.

## Project overview and objective

The project demonstrates how an automation workflow can search a local bus catalog, rank available options, simulate a booking, and respond to failures without requiring a live travel service. Its objective is to make the workflow observable and resilient: validate requests, detect operational failures, retry transient errors, attempt a fallback, and record execution and incident details.

It includes a Streamlit dashboard, a Python workflow engine, a command-line search entry point, simulated booking, operational telemetry, and CSV/JSON reports.

## Why this is an Autonomics project

Rather than stopping at a failed search, the workflow observes its execution, classifies failures, and takes bounded recovery actions. In practice, the project demonstrates an autonomic feedback loop:

1. **Monitor:** Collect execution metrics, retry and recovery history, and structured events.
2. **Analyze:** Validate requests and detect simulated transient failures or other unsuccessful outcomes.
3. **Plan and act:** Retry transient errors within configured limits and attempt recovery when needed.
4. **Record:** Log workflow and incident outcomes for dashboard review and reports.

This is a local simulation of autonomic behavior, not a production connection to external booking infrastructure.

## Architecture and folder structure

```text
redbus-intelligent-automation/
├── app.py                       # Streamlit dashboard and simulated booking UI
├── redbus_automation/
│   ├── main.py                  # Search CLI
│   ├── orchestrator.py          # Workflow lifecycle and coordination
│   ├── validator.py             # Search request validation
│   ├── search_engine.py         # Local catalog search and fault injection
│   ├── filter_engine.py         # Search result filtering
│   ├── comparison_engine.py     # Result ranking
│   ├── retry_engine.py          # Bounded retries for transient errors
│   ├── recovery_engine.py       # Fallback and recovery actions
│   ├── booking_engine.py        # Simulated seat booking and PNR references
│   ├── incident_manager.py     # Incident tracking and summaries
│   ├── monitoring.py            # Runtime metrics
│   ├── logger.py                # Structured event logging
│   ├── reporting.py             # CSV and JSON report generation
│   ├── config.py                # Paths and application configuration
│   └── models.py                # Workflow and domain models
├── data/
│   ├── sample_buses.json        # Primary simulated catalog
│   └── fallback_buses.json      # Offline fallback catalog
├── scripts/                     # Setup, startup, test, and health scripts
├── tests/                       # Pytest coverage for core modules and workflows
├── docs/                        # Architecture, autonomics, and demo documentation
├── logs/                        # Runtime structured logs
├── reports/                     # Generated CSV and JSON reports
├── requirements.txt
└── FINAL_QA_AUDIT.md            # Final verified QA results
```

### Main workflow

```text
Dashboard or CLI request
  -> validation
  -> local catalog search
  -> bounded retry for transient failures
  -> recovery, if needed
  -> filtering and ranking
  -> simulated booking (dashboard)
  -> metrics, incident/event logs, and reports
```

The Streamlit dashboard has tabs for the Executive Dashboard, Automation Workflow, Bus Search & Booking Simulation, Incident Center, and Reports & Audit Center. Dashboard metrics are obtained from the runtime monitoring and incident components.

## Failure detection, retry, recovery, and incident logging

- The orchestrator validates a search request before processing it. Invalid requests are treated as non-retryable failures.
- The retry engine retries transient search failures with a bounded backoff policy; it does not retry every error indiscriminately.
- When primary search attempts fail, the recovery engine can use `SECONDARY_MIRROR_FALLBACK`, which searches the local fallback catalog. The QA audit verified this recovery path.
- Recovery actions and workflow failures are recorded in structured logs and surfaced through incident tracking. Unrecovered failures remain failures; they are not reported as successful recoveries.
- When a successful search is available, the system filters and ranks options. The dashboard can then simulate a seat selection and booking confirmation.

The fallback catalog, booking confirmation, and PNR are all local simulation data; they do not represent a real reservation.

### Simulated route coverage

The local catalogs currently cover these 10 inter-state city pairs in both directions: Bangalore–Chennai, Bangalore–Hyderabad, Delhi–Jaipur, Mumbai–Ahmedabad, Mumbai–Panaji, Kolkata–Bhubaneswar, Lucknow–Patna, Chandigarh–Shimla, Kochi–Coimbatore, and Indore–Jaipur. The existing Pune–Mumbai route remains available as a legacy same-state demo route. Each supported direction has matching primary and secondary mirror data. Other routes are unsupported and return no catalog candidates. All schedules and fares are illustrative demo data, not live RedBus availability.

## Technologies used

- **Python** for the workflow engine and CLI.
- **Streamlit** for the dashboard and interactive simulation.
- **Pandas** for dashboard data handling.
- **Pytest** for automated tests.
- **Python standard library** modules, including JSON and CSV support, for local data, logs, and reports.
- **Bash** scripts for environment setup, application startup, health checks, and test execution; the repository also contains a GitHub Actions workflow.

`requirements.txt` directly lists Streamlit and pytest.

## Installation

### Windows with Git Bash

Install Python and Git for Windows, clone the repository, and open Git Bash in its root directory:

```bash
git clone https://github.com/KuruvaAshok09/redbus-intelligent-automation.git
cd redbus-intelligent-automation
bash scripts/setup.sh
bash scripts/health_check.sh
```

The setup script creates or uses the project `.venv` and installs the dependencies from `requirements.txt`.

From PowerShell, if Git Bash is installed at its default location, the setup command is:

```powershell
& 'C:\Program Files\Git\bin\bash.exe' -lc './scripts/setup.sh'
```

### Unix-like systems

From the repository root:

```bash
bash scripts/setup.sh
bash scripts/health_check.sh
```

## Start the application

From Git Bash or a Unix-like shell in the repository root:

```bash
bash scripts/start.sh
```

Then open [http://localhost:8501](http://localhost:8501). The startup script uses port 8501 by default and supports overriding it with `STREAMLIT_PORT`.

To select port 8502 from Git Bash:

```bash
STREAMLIT_PORT=8502 bash scripts/start.sh
```

From PowerShell with Git Bash at its default installation path:

```powershell
$env:STREAMLIT_PORT = '8502'
& 'C:\Program Files\Git\bin\bash.exe' -lc './scripts/start.sh'
```

The repository also retains `scripts/start_app.sh` as a compatibility wrapper. `scripts/start.sh` is the canonical startup script.

## Run tests

From the project environment:

```bash
python -m pytest -q
```

Or use the repository test script from Git Bash or a Unix-like shell:

```bash
bash scripts/test.sh
```

**Verified result:** `128 passed` (`.\.venv\Scripts\python.exe -m pytest -q`), with no warnings in the latest run. See [FINAL_QA_AUDIT.md](./FINAL_QA_AUDIT.md).

The final browser regression on a fresh Streamlit process on port 8503 verified that the sidebar options include cities from the local catalogs, including Ahmedabad, Kochi, and Coimbatore, and exclude the selected origin from the destination list. Ahmedabad ↔ Mumbai and Kochi ↔ Coimbatore returned simulated results in both directions; a Kochi → Coimbatore booking produced simulated PNR `SIM-PNR-EB83CA`. Unsupported Bangalore → Jaipur displayed the explicit no-simulated-buses message. Scenario 2 displayed all three retries in both the Workflow and Incident Center, with `SECONDARY_MIRROR_FALLBACK` and a resolved incident.

The compatibility wrapper `scripts/run_tests.sh` is also present; `scripts/test.sh` is the canonical test script.

## Demo

1. Start the dashboard and open `http://localhost:8501`.
2. Set the route, journey date, passenger count, and any available search filters in the sidebar.
3. Select **Search & Orchestrate Workflow** to execute a search and inspect results, workflow stages, dashboard metrics, incidents, and reports in the tabs.
4. In **Bus Search & Booking Simulation**, select an available simulated seat, enter the requested demo passenger details, and issue a simulated confirmation. No ticket or payment is created.
5. To demonstrate recovery from the CLI, run:

   ```bash
   python -m redbus_automation.main --source Bangalore --destination Hyderabad --simulate-transient-failure
   ```

   The verified failure/recovery workflow completed with a `RECOVERED` outcome using `SECONDARY_MIRROR_FALLBACK`. The CLI also supports `--simulate-corruption` and `--force-empty` for exercising other simulated failure conditions.

6. To demonstrate the same transient-failure recovery in the dashboard, enable the transient-failure fault injection control in the sidebar before running the workflow.

## Limitations

- The application uses offline simulated catalogs; it has no live RedBus API integration and does not scrape the RedBus website.
- Bookings, seat availability, confirmations, and PNR references are simulated. There is no live seat reservation, ticket issuance, or payment processing.
- The project is an offline demonstration; the test and browser verification do not establish live RedBus availability or real booking, payment, or seat reservation.
- Browser verification covered the routes and controls listed in [FINAL_QA_AUDIT.md](./FINAL_QA_AUDIT.md); it was not an exhaustive manual test of every UI control.

For detailed design notes and a guided walkthrough, see [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md), [docs/AUTONOMICS_CONCEPTS.md](./docs/AUTONOMICS_CONCEPTS.md), and [docs/DEMO_GUIDE.md](./docs/DEMO_GUIDE.md).

## Project contribution

Developed by Kuruva Ashok as an individual B.Tech Computer Science and Engineering project for HCLTech Autonomics role evaluation. See [@KuruvaAshok09](https://github.com/KuruvaAshok09).
