# Final QA Audit

## Scope
This report records the final QA checks and the security and integrity fixes made after the code review. No project rebuild or architecture redesign was performed.

## Completed work already in place
- Project inspection and implementation review was already completed.
- The active app and backend workflow were already verified as implemented.
- Final QA documentation was already drafted before this pass.

## Verified results

### 1) Pytest
Latest command run:
`.\.venv\Scripts\python.exe -m pytest -q`

Result:
- 126 passed in 13.53s, no warnings
- exit code 0

Route expansion regression command:
`.\.venv\Scripts\python.exe -m pytest -q tests\test_routes.py tests\test_orchestrator.py::test_scenario_two_recovers_bangalore_chennai_after_retries`

Result: 43 passed. The route tests verify matching primary/fallback directional coverage, every added route's search, filtering, simulated seat selection and PNR, Scenario 2 fallback for all 20 directions, and explicit failure for an unsupported route.

Previously failing catalog and zero-result recovery tests:
`.\.venv\Scripts\python.exe -m pytest -q tests\test_search.py::test_catalog_contains_at_least_15_buses tests\test_orchestrator.py::test_orchestrator_self_heals_zero_filtered_results`

Result: 2 passed.

Scenario 2 recovery regression:
`.\.venv\Scripts\python.exe -m pytest -q tests\test_orchestrator.py::test_scenario_two_recovers_bangalore_chennai_after_retries`

Result: 1 passed. The test verifies three Gateway 503 retry events, a successful `SECONDARY_MIRROR_FALLBACK`, matching route/capacity/fare constraints, preserved journey date, and a resolved incident.

The primary catalog has 30 simulated bus entries across 21 directional routes; the secondary catalog has 26 entries and covers the same 21 directions. Ten inter-state city pairs are supported in both directions: Bangalore–Chennai, Bangalore–Hyderabad, Delhi–Jaipur, Mumbai–Ahmedabad, Mumbai–Panaji, Kolkata–Bhubaneswar, Lucknow–Patna, Chandigarh–Shimla, Kochi–Coimbatore, and Indore–Jaipur. Pune–Mumbai remains a legacy same-state route. Every catalog entry is marked `SIMULATED_DEMO`. Routes not listed are unsupported and have no matching candidates.

### 2) Streamlit startup and dashboard on port 8502
- Port 8502 was served by an existing `python -m streamlit run app.py` process (PID 656); this audit did not launch or terminate it.
- `http://127.0.0.1:8502/_stcore/health` returned HTTP 200 with body `ok`.
- The dashboard returned HTTP 200 and rendered the title `RedBus Intelligent Automation | Enterprise Autonomics Console` in the browser without a visible Streamlit application error.

Result: **PASS** for service health and dashboard loading. A fresh process startup was not tested because the port was already occupied by the app.

### 3) Browser workflow checks
- **Bangalore → Chennai search and booking — PASS:** selected Bangalore → Chennai for 2026-11-16, ran the search, saw the simulated recommendation and seat map, entered demo passenger details, and received simulated PNR `SIM-PNR-9E2CA6`.
- **Bangalore → Hyderabad zero-result recovery — PASS:** set max fare to ₹800 and ran search. The workflow panel showed `CONSTRAINT_RELAXATION`, raised the budget to ₹1,000, and the booking tab showed an eligible simulated bus priced ₹880.
- **Scenario 2 gateway failure and recovery — PASS in structured logs:** enabled “Scenario 2: Gateway 503 Timeout (Retry/Mirror)” for Bangalore → Chennai. Logs contain exactly 3 `RETRY_TRIGGERED` events, each recording the simulated HTTP 503. `SECONDARY_MIRROR_FALLBACK` completed successfully with 3 validated buses; the incident is `RESOLVED` with that recovery action.
- **Scenario 2 retry telemetry in UI — FAIL:** the Automation Workflow tab displayed “No retries triggered” for the same recovered run. This contradicts the three retry events in structured logs. Recovery and incident resolution succeeded; the UI retry-history display is inconsistent.

### 4) Fresh browser regression on port 8503 (2026-11-13)

A new Streamlit process was launched for this pass on previously unused port 8503 (PID 20852). The dashboard rendered without a visible Streamlit error. `http://127.0.0.1:8503/_stcore/health` returned HTTP 200 with body `ok`. This was a fresh process, not the existing port-8502 service.

| Requested route | UI selection/search | Fare/capacity filters (2 passengers, ₹2,000 cap) | Seat selection and simulated booking |
|---|---|---|---|
| Bangalore → Chennai | PASS | PASS: selected bus ₹950, 18 available seats | PASS: seats 1A/1B; PNR `SIM-PNR-E1F805` |
| Chennai → Bangalore | PASS | PASS: selected bus ₹900, 16 available seats | PASS: seats 4A/4B; PNR `SIM-PNR-FFD3A7` |
| Delhi → Jaipur | PASS | PASS: selected bus ₹600, 22 available seats | PASS: seats 4A/4B; PNR `SIM-PNR-F1276B` |
| Jaipur → Delhi | PASS | PASS: selected bus ₹650, 24 available seats | PASS: seats 4A/4B; PNR `SIM-PNR-D8E351` |
| Mumbai → Ahmedabad | BLOCKED | Not reached | Not reached |
| Ahmedabad → Mumbai | BLOCKED | Not reached | Not reached |
| Kochi → Coimbatore | BLOCKED | Not reached | Not reached |
| Coimbatore → Kochi | BLOCKED | Not reached | Not reached |

The sidebar exposes only Bangalore, Hyderabad, Chennai, Pune, Delhi, Mumbai, Jaipur, and Kolkata. Ahmedabad, Kochi, and Coimbatore are absent, so the four blocked routes cannot be selected in the actual UI despite their catalog entries. These are UI coverage failures, not failed catalog/backend searches.

- **Scenario 2 — PASS in execution and recovery:** browser run `EXEC-20261113-234747-55A1B3` generated exactly three `RETRY_TRIGGERED` structured log entries (attempts 1/3, 2/3, and 3/3). The Automation Workflow tab showed `SECONDARY_MIRROR_FALLBACK` as successful and reported three validated fallback buses.
- **Scenario 2 retry display — FAIL:** that same Workflow tab stated “No retries triggered. Primary catalog search succeeded on initial attempt.” The Incident Center also showed retry count `0` in the incident row. Both conflict with the three retry events in structured logs.
- **Scenario 2 incident status — PASS:** Incident Center showed a `TRANSIENT_SERVICE_ERROR` row with `SECONDARY_MIRROR_FALLBACK` and `RESOLVED`; its resolved-incidents metric was 5.
- **Unsupported route — PARTIAL PASS:** searched Bangalore → Jaipur, which has no catalog entry. No bus selector/results were rendered, so no fake bus was shown. However, the booking tab displayed the generic “Execute a search using the sidebar to view candidate buses and interactive booking.” message rather than a clear no-results explanation.
- **Dashboard load — PASS:** fresh port-8503 page title was `RedBus Intelligent Automation | Enterprise Autonomics Console`; health endpoint returned HTTP 200.
- Screenshots were unavailable from the browser capture tool in this environment. Evidence above is from the live browser page text and matching structured execution logs.

The complete pytest suite was run after these browser checks: **126 passed in 13.53s**, exit code 0.

This confirms the main execution path:
user search -> validation -> search -> retry -> recovery -> ranking -> reporting -> incident logging

Added regression coverage checks HTML escaping, persisted incident resolution after reload, rejection of duplicate/invalid seat bookings, no reservation after rejected booking, and concurrent duplicate booking attempts within one process.

## Completed
- Latest complete pytest suite after browser testing: 126 passed in 13.53s, no warnings
- Route expansion focused regressions: 43 passed
- Fresh Streamlit startup, health, and dashboard load on port 8503
- Browser search, fare/capacity filtering, seat selection, simulated booking, and PNR verified for the four requested routes available in the sidebar
- Scenario 2 structured logs confirm exactly 3 retries; mirror recovery succeeded and the incident row is resolved
- Unsupported Bangalore → Jaipur search rendered no bus selector or fake results
- Both previously failing tests: 2 passed
- Bangalore → Chennai Scenario 2 recovery regression: 1 passed
- Primary catalog minimum count and Bangalore → Hyderabad zero-result recovery restored with simulated data
- Streamlit health endpoint and dashboard browser load on port 8502
- Bangalore → Chennai browser search and simulated PNR booking
- Bangalore → Hyderabad browser constraint-relaxation recovery
- Scenario 2 exact retry count and incident resolution verified from structured logs

## Failed
- Scenario 2 Workflow tab incorrectly states “No retries triggered”; logs confirm exactly three retries.
- Mumbai–Ahmedabad, Ahmedabad–Mumbai, Kochi–Coimbatore, and Coimbatore–Kochi could not be selected in the actual UI because its hardcoded city options omit Ahmedabad, Kochi, and Coimbatore.
- Unsupported-route feedback is not explicit: the empty-results booking tab shows the generic instruction to execute a search.
- Workflow retry count and the incident-row retry count display 0 despite three logged retries.

## Unverified / not required for this pass
- Browser execution of routes not selectable from the sidebar, and browser automation of every other UI control
- Real external RedBus API integration, which is outside this offline demo scope

## Exact startup commands

### Start the app in Git Bash
`& "C:\Program Files\Git\bin\bash.exe" -lc './scripts/start.sh'`

### Start the app on Unix-like systems
`bash scripts/start.sh`

### If port 8501 is occupied, use port 8502
`$env:STREAMLIT_PORT = '8502'; & "C:\Program Files\Git\bin\bash.exe" -lc './scripts/start.sh'`

### Run tests in Git Bash
`& "C:\Program Files\Git\bin\bash.exe" --noprofile --norc -lc './scripts/test.sh'`

### Run tests on Unix-like systems
`bash scripts/test.sh`

### Direct Python test run
`.\.venv\Scripts\python.exe -m pytest -q`

All bus data, fallback results, booking confirmations, and PNRs are simulated offline. There is no live RedBus API, real booking, or payment integration. The standalone `scripts/monitor.sh` health probe does not expose live dashboard metrics.

## Latest final UI fix verification

This section supersedes the earlier browser failures recorded above. A fresh Streamlit process was launched on port 8503 for the final three-fix verification.

| Check | Result | Evidence |
|---|---|---|
| Fresh app startup and dashboard load | PASS | `http://127.0.0.1:8503/` loaded the dashboard; `/_stcore/health` returned `ok`. |
| Dynamic catalog-backed city options | PASS | The origin selector included Ahmedabad, Kochi, and Coimbatore. For Ahmedabad, destination choices excluded Ahmedabad itself. |
| Ahmedabad ↔ Mumbai UI search | PASS | Both directions were selectable and returned demo results: Ahmedabad → Mumbai, Demo Sabarmati Return Coach at ₹1,050; Mumbai → Ahmedabad, Demo Western Link at ₹1,100. |
| Kochi ↔ Coimbatore UI search | PASS | Both directions were selectable and returned demo results: Kochi → Coimbatore, Demo Malabar Connector at ₹850; Coimbatore → Kochi, Demo Kongu Return Coach at ₹820. |
| Kochi → Coimbatore UI booking | PASS | A selected seat was booked in simulation and generated PNR `SIM-PNR-EB83CA`. |
| Unsupported Bangalore → Jaipur message | PASS | Completed search displayed: “No simulated buses are available for this route. Please choose another supported route.” No bus result was shown. |
| Scenario 2 retry telemetry in Workflow | PASS | The panel showed “Bounded Retry Telemetry (3 events)” and attempts #1, #2, and #3, each with the simulated HTTP 503 cause. |
| Scenario 2 retry history in Incident Center | PASS | The expanded incident showed attempts 1/3, 2/3, and 3/3 as actual `RETRY_TRIGGERED` records, with status `RESOLVED` and recovery `SECONDARY_MIRROR_FALLBACK`. |
| Complete pytest suite | PASS | `.\.venv\Scripts\python.exe -m pytest -q` -> **128 passed in 13.73s**, exit code 0. |
| Python compilation | PASS | `.\.venv\Scripts\python.exe -m compileall -q app.py redbus_automation tests` completed successfully. |
| `git diff --check` | PASS | No whitespace errors; Git emitted only line-ending conversion warnings for existing working-tree files. |

### Changes in this final fix pass

- `app.py`: reads city options from the primary and fallback catalogs, excludes the selected origin from destination options, differentiates completed empty searches from the pre-search state, and exposes persisted retry counts/history/status/recovery in Incident Center.
- `redbus_automation/search_engine.py`: adds `get_all_cities()` to collect distinct city names from both local catalogs.
- `redbus_automation/orchestrator.py`: restores exhausted-retry history from the execution's actual structured `RETRY_TRIGGERED` log entries and persists those records with the incident.
- `tests/test_orchestrator.py`: verifies three retries are reflected in the workflow result and incident, and verifies unsupported routes return no candidates.
- `tests/test_routes.py`: verifies catalog-derived city options include all supported route cities, including Ahmedabad, Kochi, and Coimbatore.
- `README.md` and `PROJECT_STATUS.md`: update the current test count and verified UI status.

### Remaining limitations

- The application remains an offline simulation with no live RedBus API, booking, payment, or real seat reservation.
- Browser verification covered the scenarios listed above; it was not an exhaustive manual test of every UI control.

## Final recommendation

**READY FOR GITHUB PUSH** — the requested final UI regressions passed, the full test suite is green, and no commit or push was performed.
