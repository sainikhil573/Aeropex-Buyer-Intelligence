# ADR-017 - Evidence-First Extraction Architecture

## Status

Accepted

## Context

M2.2 introduced governed connectors that acquire source data and return `ConnectorResult` objects. The next platform step needs to interpret successful connector output into structured candidate opportunity observations while preserving provenance and avoiding premature buyer verification or entity creation.

The platform must distinguish:

- Acquisition: retrieving source content.
- Extraction: interpreting source content into candidate fields.
- Verification: determining whether a company, contact, or opportunity is trustworthy.

Mixing these responsibilities would make provenance unclear and could cause unverified source text to become canonical buyer data too early.

## Decision

`ConnectorResult` is interpreted by a bounded Extractor layer.

Extraction produces immutable `SourceObservation` evidence.

`SourceObservation` may exist before Buyer or BuyerRequirement entity resolution, so `buyer_id` and `requirement_id` are nullable in M2.3.

Extraction does not imply verification.

For M2.3, the only implemented extractor is deterministic controlled JSON extraction. Unsupported content is preserved as unstructured evidence rather than routed through brittle scraping heuristics or AI interpretation.

Product matching is deterministic: active Product names, aliases, and variants are compared case-insensitively. Ambiguous product matches leave `product_id` null.

## Consequences

- Connector code remains responsible only for governed data acquisition.
- Extraction code remains independent of persistence until `ExtractionService` creates SourceObservation records.
- SourceObservation is append-only from the API perspective: create through extraction, read by ID, and list with bounded filters.
- Buyer and BuyerRequirement creation remain deferred to downstream entity-resolution workflows.
- Missing fields remain null and raw evidence remains traceable.
- Future extractors such as structured HTML, JSON API, trade listing, or LLM extractors can be added behind `ExtractorFactory` without changing connector governance.

## Non-Goals

M2.3 does not implement buyer legitimacy verification, contact enrichment, company enrichment, semantic AI extraction, generic HTML scraping, browser automation, buyer deduplication, matching, outreach, ADLS/Bronze persistence, or production scheduling.
