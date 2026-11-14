# Claude-Assisted Development Guide

## Purpose and scope

This guide describes ways developers may use Claude as an **optional development assistant** while working on the RedBus Intelligent Automation Autonomics project. It does not describe a change to the project architecture, application behavior, dependencies, or runtime.

The examples and prompts below are illustrative. They are not evidence that Claude was used to develop, test, or review this repository. No Claude integration or API connection is required to follow this guide.

The project is an offline demonstration: its bus search uses local simulated catalogs, and its booking flow creates simulated confirmations rather than real tickets or payments. Claude's suggestions should be evaluated against the source, tests, and project requirements.

## A. Ways Claude can assist

### Code review

Provide a focused diff and the relevant surrounding code. Ask Claude to identify correctness risks, regressions, missing edge cases, and tests that would demonstrate the intended behavior. Request concrete file and symbol references and ask it to distinguish verified behavior from assumptions.

For changes in the autonomics workflow, useful context may include the [orchestrator](../redbus_automation/orchestrator.py), [retry engine](../redbus_automation/retry_engine.py), [recovery engine](../redbus_automation/recovery_engine.py), and the tests that cover them. Ask for review of the proposed change, not automatic approval of it.

### Python debugging

Claude can help interpret a traceback, compare expected and actual state, and propose a minimal reproduction. Include the relevant input, execution stage, exception type, and sanitized log entries. Ask it to trace the path through the existing code before proposing a fix.

For example, distinguish a failure in catalog search or fallback from a failure while validating a seat or persisting a simulated booking. These paths do not necessarily share the same retry behavior.

### Root-cause analysis

Ask Claude to construct a timeline from structured events, identify the earliest meaningful failure, and list evidence for and against each likely cause. The application writes structured JSON Lines records to `logs/automation_execution.jsonl` and incident records to `logs/incidents.jsonl`. Events can be associated with an `execution_id` and include fields such as `component`, `event_type`, `message`, and `metadata`.

Treat a proposed cause as a hypothesis until confirmed by the relevant source, data, and a reproducible check. A later error may be a consequence of an earlier failure rather than its cause.

### Test-case generation

Claude can suggest pytest cases from existing contracts and test patterns. Ask it to specify the setup, action, and observable assertions, and to use isolated temporary paths for files. Compare suggestions with [retry tests](../tests/test_retry.py), [recovery tests](../tests/test_recovery.py), [incident tests](../tests/test_incident.py), and [orchestrator tests](../tests/test_orchestrator.py) before adopting them.

### Shell-script review

Claude can review Bash scripts for quoting, exit-code preservation, path assumptions, signal handling, and Git Bash compatibility. Ask it to explain the effect of commands that start processes, write files, or clean up temporary directories. Review any suggested shell command before running it; do not run a command solely because Claude produced it.

The shell tools in [autonomics_tools](.) can start the app, check its HTTP health endpoint, and run tests in an isolated temporary copy. They are independent of any Claude integration.

### Documentation assistance

Claude can draft or clarify developer guides, explain workflows, and check that terminology is consistent. Verify file names, commands, exception behavior, and test claims against the repository. Documentation generated with AI should not claim a command was executed, a test passed, or a feature exists unless that claim has been independently confirmed.

## B. Project-specific illustrative examples

### Example 1: A simulated booking journey fails after retries

**Illustrative scenario, not an observed incident:** a developer sees a failed simulated booking journey and retry-related entries for its execution. The first step is to determine whether the retries belong to catalog search or whether the failure occurred later in simulated booking.

In the current workflow, `AutomationOrchestrator` invokes `RetryEngine` around `BusSearchEngine.search`. By default, the retry engine retries transient service errors, timeouts, and connection errors; validation and type errors are non-retryable. With the default configuration, there are three retries after the initial search attempt. If search still fails with a transient error, the orchestrator records an incident and attempts recovery through the secondary offline mirror. Fallback results are filtered for route, fare, passenger capacity, and rating constraints. A successful recovery resolves the incident with `SECONDARY_MIRROR_FALLBACK`.

The simulated booking operation is a separate path. For example, selecting an already booked seat can raise `ValueError`, and a storage write can raise `OSError`. The search retry loop does not establish that either booking error was retried. The developer should identify the failing stage before drawing conclusions.

**Illustrative prompt:**

> Help me diagnose this RedBus Intelligent Automation issue. Do not edit files or assume a fix. First trace the relevant flow in `redbus_automation/orchestrator.py`, `retry_engine.py`, `recovery_engine.py`, and `booking_engine.py`.
>
> The sanitized JSONL entries below are illustrative evidence for execution `EXEC-EXAMPLE`. Please group entries by execution ID, order them by timestamp, and explain which events show search retries, recovery, incident status, and (if present) a booking-stage failure. The project retry engine wraps catalog search; do not assume booking persistence is retried.
>
> ```text
> [Paste only a small, sanitized excerpt here; replace names, contact details,
> > booking identifiers, and any other sensitive values.]
> ```
>
> Give me: (1) the most likely failure stage, (2) evidence and alternative explanations, (3) the next read-only checks to distinguish them, and (4) a minimal pytest reproduction using temporary files if a test is warranted. Do not recommend changing retry, fallback, incident, or booking behavior until the cause is verified.

Possible diagnostic questions include:

- Are there `RETRY_TRIGGERED` entries for this execution, and do their `metadata.attempt` values align with the configured retry limit?
- Which component emitted the last `SEARCH_FAILED`, `RECOVERY_INITIATED`, `RECOVERY_COMPLETED`, or `WORKFLOW_TERMINATED` event?
- Does the incident record show `retry_attempts`, `final_status`, and a `recovery_action`? Is the status actually `FAILED`, or did search recover and the later booking step fail?
- If recovery used the secondary mirror, did the selected route exist in the fallback catalog, and did candidate buses satisfy the request's budget and passenger capacity?
- If the booking step failed, does the error concern input/seat validation or persistence rather than search availability?

### Example 2: Suggest additional pytest scenarios

**Illustrative prompt:**

> Review the existing tests in `tests/test_retry.py`, `tests/test_recovery.py`, `tests/test_incident.py`, and `tests/test_orchestrator.py`. Suggest additional pytest scenarios for retry handling, secondary mirror fallback, and incident resolution. Do not edit files yet.
>
> For each proposed scenario, give the behavior under test, setup, action, and precise assertions. Cover at least:
>
> - a transient operation that succeeds after one or more retry attempts;
> - retry exhaustion and preservation of the original exception;
> - a permanent validation error that is attempted once and is not retried;
> - fallback results rejected because the route, budget, or passenger capacity does not match;
> - a successful secondary-mirror recovery with retry history and a resolved incident;
> - fallback failure and the resulting unsuccessful recovery/incident state; and
> - incident resolution that remains correct after reloading persisted JSONL data.
>
> Follow the repository's current pytest style. Use `tmp_path` for files and avoid writing to the project's shared logs or reports. Do not weaken existing assertions or change production behavior.

Before implementing a suggested case, confirm its expected behavior from the current code. In particular, distinguish a retry-engine unit test from an orchestrator integration test: the latter can also exercise logging, incident recording, recovery, and workflow status.

## C. Practical prompts

Adapt these prompts to the task and supply only the minimum relevant context:

**Review a change**

> Review this diff for correctness and regressions against the existing RedBus Autonomics behavior. Cite the changed lines and relevant existing functions. List only actionable findings, explain confidence, and suggest focused tests. Do not rewrite the diff.

**Trace a Python failure**

> Trace this traceback from the entry point through the relevant functions. Separate what the code proves from hypotheses. Identify the smallest reproduction and a read-only check that could confirm the root cause before proposing a change.

**Analyze an execution**

> Using these sanitized events for one `execution_id`, build a timestamp-ordered workflow timeline. Identify the first failure, each retry, any recovery action, and the final incident/workflow status. Do not infer that a later booking error was retried by the catalog-search retry engine.

**Propose tests**

> Suggest pytest cases for this behavior using the existing test conventions. Include exact assertions and isolate file writes with `tmp_path`. Do not modify files; flag any expected behavior that is not supported by the current implementation.

**Review a shell script**

> Review this Bash script for path handling, quoting, exit status, duplicate process startup, and Git Bash on Windows. Explain any risky command and give a minimal patch suggestion, but do not execute commands or change files.

**Improve documentation**

> Draft a concise documentation section based only on these source files. Mark uncertain details rather than guessing, and do not claim that tests, builds, or manual checks passed unless I provide their output.

## D. Development assistant versus runtime integration

### Claude as a development assistant

In this mode, a developer asks Claude to explain code, review a diff, diagnose sanitized evidence, or suggest tests. The developer chooses what repository content to share, verifies the response, and decides whether to make changes. This use does not require the application to call Claude, does not alter the Streamlit app, and does not add a package or API integration.

### Claude integrated into the application at runtime

Runtime integration would mean that application code sends prompts or data to a Claude service while the RedBus app is running and uses the response in an application feature. That is a separate architecture, privacy, dependency, and security decision. This guide does not add, recommend as an implicit step, or claim such an integration exists.

Do not paste real passenger information, credentials, API keys, session cookies, or unredacted booking records into a development assistant. Follow your organization’s data-handling and AI-use policies before sharing source code, logs, or incident records with any external service.

## E. Review, verification, security, and limitations

### Human code review

Claude can miss context, misunderstand a contract, or recommend a change that conflicts with project requirements. A developer must review every proposed code or shell change, check the diff, and confirm that it changes only intended files. For resilience changes, pay particular attention to retry bounds, retryable versus permanent errors, fallback validation, incident transitions, and side effects.

### Test verification

Generated tests and explanations are suggestions, not proof. Confirm that assertions test the required behavior, that tests fail for the intended reason when appropriate, and that test data and file paths are isolated. Run the relevant verification command yourself and inspect its actual output and exit status. For this project, the Phase 1 `autonomics_tools/run_tests.sh` wrapper runs the existing suite from a temporary copy to avoid changing project runtime logs and reports; do not substitute a direct test command when avoiding those side effects is required.

Do not report “Claude tested this” as equivalent to running pytest. Report exactly which command was executed and what it returned.

### Security and privacy

Logs and incident records can contain request details, error text, execution IDs, and operational metadata. Booking records may contain passenger contact information. Share only the smallest relevant excerpt, redact personal data and identifiers, and never include secrets. Do not expose production data or confidential repository content unless permitted by applicable policy.

Treat AI-generated shell commands as untrusted input. Read them first, understand file writes and cleanup behavior, and avoid commands that can overwrite or delete project data. Claude should not receive credentials to run project operations.

### Limitations of AI-generated code

Claude may invent APIs, misread retry counts, conflate search recovery with booking behavior, miss file-system side effects, or generate tests that assert an implementation detail instead of a required contract. It may also produce plausible but incorrect explanations from incomplete logs. Check claims against source and actual command output; keep changes minimal, preserve existing behavior, and ask for evidence when a claim cannot be verified.

## References in this repository

- [Orchestrator](../redbus_automation/orchestrator.py)
- [Retry engine](../redbus_automation/retry_engine.py)
- [Recovery engine](../redbus_automation/recovery_engine.py)
- [Incident manager](../redbus_automation/incident_manager.py)
- [Booking engine](../redbus_automation/booking_engine.py)
- [Retry tests](../tests/test_retry.py)
- [Recovery tests](../tests/test_recovery.py)
- [Incident tests](../tests/test_incident.py)
- [Orchestrator tests](../tests/test_orchestrator.py)
