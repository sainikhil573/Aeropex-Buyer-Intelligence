# ADR-016 - Governed Connector Architecture

## Status

Accepted

## Context

Buyer Discovery needs a source-access layer that can retrieve data from approved external sources without becoming an unrestricted fetch service or mixing acquisition with buyer interpretation.

M2.1 introduced the Source Registry with approval and operational status. M2.2 needs to consume those records, enforce eligibility, resolve a connector implementation, retrieve controlled HTTP content, and return a standard result for later milestones.

## Decision

External source access occurs through typed connectors selected by a `ConnectorFactory` and executed through a governance-aware `ConnectorExecutionService`.

Connectors acquire data but do not interpret buyer intent.

Only approved and active sources may execute:

```text
approval_status == approved
AND
operational_status == active
```

Target URLs must conform to Source Registry governance. The target hostname must match the source domain or an allowed subdomain, and obvious internal/private destinations are rejected by default.

For M2.2, only `SourceAccessMethod.HTTP` is implemented. Unsupported methods fail clearly as `unsupported`; they are not silently routed through HTTP.

## Consequences

- Buyer Discovery can later consume `ConnectorResult` without knowing connector implementation details.
- Source access remains auditable and tied to `request_id`, `run_id`, and `source_id`.
- The API does not expose a general-purpose URL proxy.
- Extraction, buyer creation, buyer requirement creation, AI interpretation, SourceObservation persistence, ADLS, and Bronze ingestion remain deferred.
- Future `ApiConnector`, `BrowserConnector`, and `ManualConnector` implementations can be added behind the factory without changing downstream business logic.

## Implementation Notes

The HTTP connector uses explicit timeout, bounded attempts, retry only for plausibly temporary failures, redirect limits, transparent User-Agent, response-size rejection, content-type capture, HTTP status capture, duration measurement, and structured connector errors.

Meaningful final connector failures create one `ErrorEvent`; retry internals are not persisted as noisy duplicate events.
