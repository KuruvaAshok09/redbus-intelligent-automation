# Provider Interface Design

## Status

This document defines a **conceptual, provider-neutral design target** for a future, separately approved implementation. No interface, adapter, endpoint, credential, or provider capability is currently implemented. Method names below are illustrative application-level operations, not redBus API names or claims about a redBus product.

## Design goals

- Keep the existing local simulation behavior and data path intact.
- Isolate official provider protocols and schemas from domain logic.
- Make operating mode and provider provenance explicit.
- Represent uncertainty and partial outcomes rather than fabricating success.
- Keep booking and payment side effects distinct from search and availability.
- Require live access, secrets, and operational controls to be supplied only through approved mechanisms.

## Conceptual domain types

A future provider-neutral contract could exchange domain objects such as:

- **Search criteria:** origin, destination, journey date, passenger count, and supported filters.
- **Bus option:** provider-scoped service identifier, route, schedule, fare quotation, and provider/mode provenance.
- **Availability result:** provider-scoped service identifier, observation time, expiry or validity information if supplied by the official provider, and an explicitly represented availability state.
- **Seat layout:** provider-scoped seat identifiers and availability as returned by the authorized provider. Do not synthesize a live layout from the offline simulation.
- **Boarding/drop-off option:** only the locations and identifiers supplied by the provider for the selected service.
- **Booking request/result:** a request correlation or idempotency value where supported, explicit pending/success/failure/unknown status, and provider-issued identifiers only when returned.
- **Payment handoff/result:** an opaque approved payment reference or status, not raw card data or authentication secrets in application logs.
- **Typed provider error:** category, retryability where documented, safe diagnostic text, and provider correlation reference with sensitive values removed.

Provider identifiers must be scoped by provider and kept separate from local demo IDs. A local `SIM-PNR-...` value is not a real PNR and must never be accepted as proof of a live booking.

## Conceptual operations

The following signatures are pseudocode for responsibilities, not executable code or an API specification:

```text
search_buses(criteria) -> list[BusOption]
check_availability(provider_service_id, journey_details) -> AvailabilityResult
get_seat_layout(provider_service_id, journey_details) -> SeatLayout
get_boarding_drop_points(provider_service_id, journey_details) -> PointOptions
create_booking(confirmed_booking_request, idempotency_context) -> BookingOutcome
get_booking_status(provider_booking_reference) -> BookingStatus
verify_pnr(provider_booking_reference or provider-supported lookup input) -> VerificationResult
```

An eventual implementation should include only operations actually supported and authorized under the official provider contract. If a capability is unavailable, the adapter must report it as unsupported rather than emulating it with guessed values.

### Operation expectations

1. **`search_buses`** accepts normalized criteria and returns provider-backed options with fare and availability freshness clearly identified. It must not label stale or simulated inventory as live.
2. **`check_availability`** obtains a fresh provider response when supported. Availability is time-sensitive; the application must not treat a prior search result as a reservation.
3. **`get_seat_layout`** returns only provider-issued seat choices and status. Any provider-required hold/reservation step must be explicitly modeled if officially documented.
4. **`get_boarding_drop_points`** returns the selected service's actual provider-supplied points, where that capability exists.
5. **`create_booking`** submits only after required user confirmation and preconditions. It returns an explicit outcome; a timeout or ambiguous response is `UNKNOWN`/`PENDING`, not success or failure by assumption.
6. **`get_booking_status` / `verify_pnr`** use only an officially supported status or verification mechanism. A reference is verified only when a trusted provider response confirms the corresponding booking.
7. **Payment** should be a separate approved boundary or a provider-authorized payment handoff. The application must not collect or store raw card numbers, security codes, OTPs, passwords, or payment credentials; approved provider-managed flows must keep those values outside the application.

The interface should expose provider capabilities explicitly, so the workflow can determine which operations are supported without relying on undocumented behavior.

## Error and result semantics

Avoid success-shaped fallback values. A future adapter should distinguish at least:

- invalid request or unsupported capability;
- no matching results;
- stale or unavailable inventory;
- authentication/authorization failure;
- rate limiting or transient provider unavailability;
- provider rejection;
- payment declined or pending;
- booking rejected;
- request outcome unknown after timeout;
- provider data or contract error.

Map provider errors to normalized categories only where the official contract supports the mapping. Preserve a safe provider correlation reference for support, but redact credentials, payment data, and unnecessary personal data. Retry only when both the operation semantics and provider contract permit it.

## Configuration and provider selection

Provider choice is a future policy decision, not an implemented setting. A safe design would:

- use an explicit enumerated mode such as `simulation` or an approved provider identifier;
- default to simulation, never live;
- reject unknown values and fail closed;
- require a deliberate operator/deployment enablement for live mode in addition to valid authorization and credentials;
- source secrets from an approved secret manager or deployment secret facility, never source code, checked-in config, command-line arguments, or logs;
- prevent a missing live credential or provider outage from silently switching to simulation;
- record selected provider/mode for audit while excluding secret values.

Credentials alone must never activate live mode. A live booking must also pass the applicable user-consent, policy, environment, and operational gates.

## Adapter and test boundaries

The offline adapter should preserve the current local catalogs, simulated seat layout, local booking persistence, and clearly marked simulated confirmation. It is not a live-service fallback.

A future authorized adapter should be independently testable with contract-approved mocks or a partner-provided non-production environment. Tests should cover schema mapping, unsupported capabilities, stale availability, error classification, redaction, idempotency behavior, ambiguous outcomes, and provider provenance. No real booking or payment should be used for routine automated tests.

This proposal does not add files to the application package, change its current interfaces, or imply that the current models already satisfy this contract.

## Related documents

- [Proposed provider-based architecture](./ARCHITECTURE.md)
- [Proposed live booking workflow](./LIVE_BOOKING_WORKFLOW.md)
- [Official access and readiness requirements](./INTEGRATION_REQUIREMENTS.md)
- Existing [domain models](../../redbus_automation/models.py)
- Existing [retry engine](../../redbus_automation/retry_engine.py)
- Existing [recovery engine](../../redbus_automation/recovery_engine.py)
