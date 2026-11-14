# Future Live Booking Workflow

## Status and safety boundary

This is a proposed end-to-end workflow for a future integration **only after official authorization, technical documentation, commercial approval, and security review**. The current application is offline simulation. No live search, seat reservation, payment, booking, or actual PNR verification is implemented here.

The current application must not be used to make real bookings or payments. This document does not authorize scraping, browser automation against website restrictions, unofficial APIs, CAPTCHA or OTP bypass, or any circumvention of login, payment security, or access controls.

## Expected future workflow

### 1. Bus search

Validate the requested route, journey date, and passenger criteria using approved domain rules, then request search results through an explicitly selected, authorized provider. Display provider provenance and the time of the provider response. Do not present local catalog results as live inventory.

### 2. Live availability

Before a consequential selection or booking, request fresh availability using the provider-supported operation. Treat availability, fare, and terms as provider-sourced and potentially time-sensitive. A search result is not a held seat or a confirmed reservation.

If availability cannot be refreshed, show an actionable failure; do not silently substitute the local fallback catalog.

### 3. Seat selection

Retrieve the seat layout from the authorized provider, if supported. Display only provider-returned seat identifiers and availability. Recheck availability or obtain a provider-issued hold only if the official contract supports it. Clearly communicate that a seat is not reserved until the provider confirms the relevant state.

### 4. Boarding and dropping points

Retrieve the boarding and dropping options for the selected provider service when available. Require selection of valid provider-returned identifiers and reflect any provider-supplied constraints or fees. Do not invent locations or infer them from local simulation data.

### 5. Authorized booking request

Show the user a final review of route, date, passengers, seats, boarding/drop-off points, total quoted fare, terms, provider, and operating mode. Obtain explicit confirmation before creating the booking. Send the request only through the authorized integration and only with the minimum required personal data.

Use provider-supported idempotency or request-correlation mechanisms where documented. Treat network timeout after submission as an **ambiguous outcome**, not proof that no booking exists. Do not automatically resubmit a potentially non-idempotent request.

### 6. Payment through an approved provider

If payment is in scope, use only the payment method, authorization flow, and provider boundary formally approved for the integration. Make the payable amount, currency, payee, and payment status explicit. Keep payment credentials and authentication factors out of application logs and ordinary storage.

The application must not collect, persist, or transmit card security codes, passwords, OTPs, or raw payment credentials. If user authentication or payment details are required, they must be entered only into a formally approved, provider-managed secure flow and must not be exposed to this application. Never bypass payment authentication or security controls.

### 7. Booking confirmation

Show a success state only after receiving an authoritative provider confirmation for the matching booking. Clearly distinguish `PENDING`, `FAILED`, and `UNKNOWN` outcomes. Do not show the current simulated `SIM-PNR-...` format or a locally generated reference as a live booking confirmation.

### 8. Actual PNR verification

Verify a PNR only through a documented, authorized provider mechanism. Associate the result with the correct provider booking reference, journey, and passenger context using minimum necessary data. A locally generated identifier, successful HTTP request, payment result, or unverified provider response is not by itself proof of a confirmed ticket.

If verification is unavailable or inconclusive, tell the user that the booking status is unresolved and direct the case to the approved support/reconciliation procedure. Do not invent a PNR.

### 9. Failure handling and incident logging

Record a redacted, correlated timeline for search, availability, booking submission, payment handoff/result, confirmation, and verification. Include operating mode, provider identity, timestamps, workflow correlation ID, safe provider request/reference IDs, normalized result category, and final status as permitted by the data policy.

Do not log credentials, payment secrets, OTPs, full card data, or unnecessary passenger information. Apply documented retry rules per operation: search retries may be safe under provider limits, whereas booking/payment retries can duplicate consequential side effects. Resolve ambiguous booking/payment outcomes through the official status/reconciliation mechanism or human support; do not assume failure and repeat the transaction.

Raise incidents for authorization failures, provider contract violations, unexpected status, unreconciled payment, booking/PNR mismatch, repeated outages, or ambiguous transaction outcomes. Route them to an explicitly staffed support process with appropriate access controls and retention.

## Workflow state model (proposed)

An implementation should define documented states and transitions before enabling live use. One possible conceptual sequence is:

```text
SEARCH_REQUESTED
  -> SEARCH_RESULTS
  -> AVAILABILITY_CHECKED
  -> SELECTION_REVIEWED
  -> USER_CONFIRMED
  -> BOOKING_PENDING
  -> PAYMENT_PENDING (if required)
  -> PROVIDER_CONFIRMED
  -> PNR_VERIFIED
```

Terminal or operator-review outcomes should include `NO_RESULTS`, `UNAVAILABLE`, `REJECTED`, `PAYMENT_FAILED`, `BOOKING_FAILED`, `UNKNOWN`, `RECONCILIATION_REQUIRED`, and `CANCELLED` only when cancellation is actually supported and confirmed by the provider. These are proposed labels, not current application states or provider response values.

## Current versus future

| Capability | Current project | Future requirement |
|---|---|---|
| Search | Local simulated JSON catalogs | Authorized provider-backed search |
| Availability | Catalog fields are simulated | Fresh provider-backed availability |
| Seats and points | Generated simulated seats; no live provider points | Provider-sourced choices if officially supported |
| Booking | Local simulated record | Authorized provider booking with explicit user confirmation |
| Payment | Not implemented | Approved payment flow, if included in authorized scope |
| Confirmation/PNR | Locally generated `SIM-PNR-...` | Provider-issued result and official verification |
| Failures | Existing simulation retry/recovery and incident handling | Operation-specific, contract-driven behavior and reconciliation |

## Related documents

- [Proposed provider-based architecture](./ARCHITECTURE.md)
- [Provider interface proposal](./PROVIDER_INTERFACE_DESIGN.md)
- [Official access and readiness requirements](./INTEGRATION_REQUIREMENTS.md)
- Existing [booking engine](../../redbus_automation/booking_engine.py)
- Existing [incident manager](../../redbus_automation/incident_manager.py)
