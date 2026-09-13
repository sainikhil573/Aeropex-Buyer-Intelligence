# ADR-018: Observation Review Workflow

## Status

Accepted

## Context

M2.3 introduced immutable `SourceObservation` evidence records. Operators now need a Control Panel workflow to inspect extracted candidate opportunity fields and raw evidence before any later normalization, entity-resolution, or verification work.

## Decision

The Buyer Intelligence UI will operate on `SourceObservation` records first.

Human review decisions are stored in a separate `ObservationReview` table. `SourceObservation` remains append-only evidence and is not mutated into a workflow object. Review state is mutable operational workflow metadata and may change over time.

Supported M2.4 review statuses are:

- `unreviewed`
- `needs_review`
- `accepted`
- `rejected`

`accepted` means approved for later processing, not externally verified. `rejected` means the observation should not progress further, not that evidence should be deleted.

One active review state is stored per observation. Review mutations create `AuditEvent` records with before and after state.

## Consequences

- Observation evidence remains preserved even after rejection.
- The UI can present an operations inbox without creating canonical Buyer or BuyerRequirement records.
- Later milestones can consume accepted observations for entity-resolution and verification workflows.
- Audit history records human review decisions without introducing a new audit framework.

## Non-Goals

ADR-018 does not introduce canonical Buyer creation, BuyerRequirement creation, entity resolution, deduplication, buyer verification, contact enrichment, matching, outreach, AI reasoning, or new connectors.
