"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { formatDateTime } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import { listObservations } from "@/lib/api/client";
import type { ExtractionStatus, ObservationReviewStatus, SourceObservation } from "@/lib/api/types";

type Filters = {
  reviewStatus: "" | ObservationReviewStatus;
  productId: string;
  sourceId: string;
  extractionStatus: "" | ExtractionStatus;
  country: string;
};

const initialFilters: Filters = {
  reviewStatus: "",
  productId: "",
  sourceId: "",
  extractionStatus: "",
  country: "",
};

export default function BuyerIntelligencePage() {
  const [observations, setObservations] = useState<SourceObservation[]>([]);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const rows = await listObservations({
        reviewStatus: filters.reviewStatus || undefined,
        productId: filters.productId || undefined,
        sourceId: filters.sourceId || undefined,
        extractionStatus: filters.extractionStatus || undefined,
      });
      setObservations(rows);
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, [filters.extractionStatus, filters.productId, filters.reviewStatus, filters.sourceId]);

  useEffect(() => {
    void load();
  }, [load]);

  const visibleObservations = useMemo(() => {
    const country = filters.country.trim().toLowerCase();
    if (!country) return observations;
    return observations.filter((observation) => (observation.country ?? "").toLowerCase().includes(country));
  }, [filters.country, observations]);

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Review</p>
          <h1>Buyer Intelligence</h1>
          <p className="summary">
            Review unverified buyer opportunity observations discovered by the platform.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      <section className="feedbackLine">
        Accepted means approved for further processing, not externally verified.
      </section>

      {error ? <div className="alert">Observation API unavailable: {error}</div> : null}

      <section className="panel">
        <div className="panelHeader">
          <h2>Observation Filters</h2>
          <button onClick={() => setFilters(initialFilters)} type="button">
            Reset
          </button>
        </div>
        <div className="formGrid">
          <label>
            Review Status
            <select
              onChange={(event) => setFilters({ ...filters, reviewStatus: event.target.value as Filters["reviewStatus"] })}
              value={filters.reviewStatus}
            >
              <option value="">All</option>
              <option value="unreviewed">Unreviewed</option>
              <option value="needs_review">Needs Review</option>
              <option value="accepted">Accepted</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
          <label>
            Product
            <input
              onChange={(event) => setFilters({ ...filters, productId: event.target.value })}
              placeholder="Product ID"
              value={filters.productId}
            />
          </label>
          <label>
            Source
            <input
              onChange={(event) => setFilters({ ...filters, sourceId: event.target.value })}
              placeholder="Source ID"
              value={filters.sourceId}
            />
          </label>
          <label>
            Extraction Status
            <select
              onChange={(event) => setFilters({ ...filters, extractionStatus: event.target.value as Filters["extractionStatus"] })}
              value={filters.extractionStatus}
            >
              <option value="">All</option>
              <option value="success">Success</option>
              <option value="partial">Partial</option>
              <option value="unstructured">Unstructured</option>
              <option value="failed">Failed</option>
            </select>
          </label>
          <label>
            Country
            <input
              onChange={(event) => setFilters({ ...filters, country: event.target.value })}
              placeholder="Country"
              value={filters.country}
            />
          </label>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Buyer Intelligence Inbox</h2>
          <span className="mutedText">{visibleObservations.length} observations</span>
        </div>
        {loading ? (
          <p className="emptyState">Loading buyer observations...</p>
        ) : observations.length === 0 ? (
          <p className="emptyState">No buyer observations have been captured yet.</p>
        ) : visibleObservations.length === 0 ? (
          <p className="emptyState">No observations match the current filters.</p>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Country</th>
                  <th>Product</th>
                  <th>Requirement</th>
                  <th>Quantity</th>
                  <th>Contact</th>
                  <th>Source</th>
                  <th>Extraction</th>
                  <th>Review Status</th>
                  <th>Captured At</th>
                </tr>
              </thead>
              <tbody>
                {visibleObservations.map((observation) => (
                  <tr key={observation.observation_id}>
                    <td>
                      <Link href={`/buyer-intelligence/${observation.observation_id}`}>
                        {observation.company_name ?? "Unknown company"}
                      </Link>
                      <div className="mutedText">{observation.observation_id}</div>
                    </td>
                    <td>{observation.country ?? "-"}</td>
                    <td>{observation.product_id ?? "-"}</td>
                    <td className="clampedCell">{observation.requirement_text ?? "-"}</td>
                    <td>{quantityLabel(observation)}</td>
                    <td>{contactLabel(observation)}</td>
                    <td>{observation.source_id}</td>
                    <td>
                      <StatusBadge status={observation.extraction_status} />
                    </td>
                    <td>
                      <StatusBadge status={observation.review_status} />
                    </td>
                    <td>{formatDateTime(observation.captured_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function quantityLabel(observation: SourceObservation) {
  if (observation.quantity === null) return "-";
  return `${observation.quantity}${observation.unit ? ` ${observation.unit}` : ""}`;
}

function contactLabel(observation: SourceObservation) {
  if (observation.contact_email && observation.contact_phone) return "Email and phone";
  if (observation.contact_email) return "Email available";
  if (observation.contact_phone) return "Phone available";
  return "No contact";
}
