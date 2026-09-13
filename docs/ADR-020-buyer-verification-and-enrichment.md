# ADR-020: Buyer Verification and Contact Enrichment

## Status

Accepted for M2.6.

## Context

M2.5 created canonical `Buyer` and `BuyerRequirement` records from accepted source observations. Canonicalization intentionally does not prove that a company exists, that a contact is associated with it, or that a buyer is commercially safe.

M2.6 adds the first persistence and review layer for verification and public business enrichment without adding public web research, scraping, browser automation, LLM/Astra usage, matching, or outreach.

## Decision

Verification is modeled as separate, evidence-backed workflow state:

- `VerificationResult` records a company/contact assessment and review status.
- `VerificationEvidence` records append-only evidence rows for claims such as company existence, domain association, contact association, and business relevance.
- `Contact` records canonical contact candidates associated with one buyer.
- `EnrichmentResult` records discovered public business fields with provenance and review status.

`SourceObservation` remains immutable source evidence. Verification evidence does not overwrite discovery evidence, and enrichment discoveries do not automatically overwrite canonical `Buyer` or `Contact` fields.

The controlled endpoint `POST /api/v1/buyers/{buyer_id}/verification/test` is deterministic runtime validation only. It does not fetch the internet and creates a pending verification result. A human review through `PATCH /api/v1/buyers/{buyer_id}/verification/{verification_id}` updates both the `VerificationResult.status` and `Buyer.verification_status`.

## Status Semantics

`verified` means sufficient evidence was reviewed for V0.1 identity verification. It does not mean financially safe, creditworthy, contractually approved, scam-proof, regulator-approved, or approved for outreach.

`accepted` observation review means eligible for downstream processing, not verified. `canonicalized` means resolved into canonical identity records, not verified.

## Consequences

Future research connectors can create verification evidence and enrichment rows without changing canonical buyer identity directly. Human review remains the boundary for final buyer verification status.

Contacts are created only from explicit values. Email normalization is limited to trim, lowercase, and basic format validation. Phone normalization preserves the provided value. Website/domain normalization uses explicit website/domain fields only and does not infer a website from email.
