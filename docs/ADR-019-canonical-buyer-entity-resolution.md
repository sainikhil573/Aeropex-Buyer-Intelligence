# ADR-019: Canonical Buyer Entity Resolution

Date: 2026-09-13

## Status

Accepted

## Context

M2.3 introduced immutable `SourceObservation` evidence. M2.4 introduced mutable `ObservationReview` workflow metadata. M2.5 needs the first canonical business-entity layer so accepted observations can progress into durable buyer and requirement records without weakening evidence provenance.

The platform must avoid unsafe duplicate merges. Incorrectly merging two different companies is worse than temporarily keeping duplicate canonical buyers.

## Decision

Add canonical `Buyer` and `BuyerRequirement` persistence plus a bounded `BuyerCanonicalizationService`.

The service canonicalizes only observations whose review status is `accepted`, whose `company_name` is usable, and whose linkage metadata is not already populated. It returns a typed result with status:

- `created`
- `matched`
- `ambiguous`
- `ineligible`
- `already_canonicalized`
- `failed`

Entity resolution V0.1 uses deterministic strong signals only:

- exact normalized company name plus exact normalized country
- exact normalized primary domain when available

If multiple buyers satisfy a rule, the service returns `ambiguous`, records an audit event, and leaves the observation unlinked. Weak signals such as partial name similarity, same product, same country alone, contacts, phone fragments, email local-parts, LLM similarity, or fuzzy semantic similarity do not auto-merge.

New buyers default to `verification_status = unverified`. Canonicalization is not company verification.

## Evidence Immutability

`SourceObservation` remains immutable evidence. M2.5 permits only controlled updates to linkage metadata:

- `buyer_id`
- `requirement_id`

Canonicalization must not modify `raw_text`, `source_url`, `captured_at`, `evidence_type`, or extracted fields.

## Transaction Boundary

Buyer creation or match, requirement creation, observation linkage, and audit events are committed as one unit. On failure the session is rolled back before further use, preventing partial canonicalization state.

## Consequences

The system may temporarily contain duplicate canonical buyers when confidence is insufficient. That is intentional for V0.1 and preserves safety. Full duplicate-resolution UI and verification workflows are deferred to later milestones.
