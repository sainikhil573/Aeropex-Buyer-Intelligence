"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { formatDateTime } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import { getObservation, updateObservationReview } from "@/lib/api/client";
import type { ObservationReviewStatus, SourceObservation } from "@/lib/api/types";

export default function ObservationDetailPage({ params }: { params: { observationId: string } }) {
  const [observation, setObservation] = useState<SourceObservation | null>(null);
  const [status, setStatus] = useState<ObservationReviewStatus>("unreviewed");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const nextObservation = await getObservation(params.observationId);
      setObservation(nextObservation);
      setStatus(nextObservation.review_status);
      setNotes(nextObservation.review_notes ?? "");
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, [params.observationId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveReview(nextStatus = status) {
    setSaving(true);
    setMessage(null);
    try {
      const review = await updateObservationReview(params.observationId, {
        status: nextStatus,
        review_notes: notes || null,
      });
      setStatus(review.status);
      setObservation((current) =>
        current
          ? {
              ...current,
              review_id: review.review_id,
              review_status: review.status,
              review_notes: review.review_notes,
              reviewed_by: review.reviewed_by,
              reviewed_at: review.reviewed_at,
              review_created_at: review.created_at,
              review_updated_at: review.updated_at,
            }
          : current,
      );
      setMessage("Review saved.");
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to save review");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="emptyState">Loading observation...</p>;
  }

  if (error && observation === null) {
    return <div className="alert">Observation unavailable: {error}</div>;
  }

  if (observation === null) {
    return <p className="emptyState">Observation not found.</p>;
  }

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Candidate Opportunity</p>
          <h1>{observation.company_name ?? "Unknown company"}</h1>
          <p className="summary">
            Observation evidence is unverified. Review decisions only control progression to later
            verification and entity-resolution stages.
          </p>
        </div>
        <div className="headerActions">
          <Link href="/buyer-intelligence">Back to Inbox</Link>
          {observation.source_url ? (
            <a href={observation.source_url} rel="noopener noreferrer" target="_blank">
              Open Source
            </a>
          ) : null}
        </div>
      </header>

      {error ? <div className="alert">{error}</div> : null}
      {message ? <section className="feedbackLine">{message}</section> : null}

      <section className="detailGrid">
        <Detail label="Company" value={observation.company_name} />
        <Detail label="Country" value={observation.country} />
        <Detail label="Product" value={observation.product_id} />
        <Detail label="Quantity" value={quantityLabel(observation)} />
        <Detail label="Posted At" value={formatDateTime(observation.posted_at)} />
        <Detail label="Contact" value={contactSummary(observation)} />
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Review</h2>
          <StatusBadge status={status} />
        </div>
        <div className="reviewPanel">
          <label>
            Current Review Status
            <select onChange={(event) => setStatus(event.target.value as ObservationReviewStatus)} value={status}>
              <option value="unreviewed">Unreviewed</option>
              <option value="needs_review">Needs Review</option>
              <option value="accepted">Accepted</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
          <label>
            Review Notes
            <textarea onChange={(event) => setNotes(event.target.value)} rows={5} value={notes} />
          </label>
          <div className="rowActions">
            <button disabled={saving} onClick={() => void saveReview("accepted")} type="button">
              Accept
            </button>
            <button disabled={saving} onClick={() => void saveReview("needs_review")} type="button">
              Needs Review
            </button>
            <button disabled={saving} onClick={() => void saveReview("rejected")} type="button">
              Reject
            </button>
            <button disabled={saving} onClick={() => void saveReview("unreviewed")} type="button">
              Reset
            </button>
            <button disabled={saving} onClick={() => void saveReview()} type="button">
              Save Review
            </button>
          </div>
          <p className="mutedText">
            Last reviewed by {observation.reviewed_by ?? "Not recorded"} at {formatDateTime(observation.reviewed_at)}.
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Extracted Data</h2>
        </div>
        <dl className="dataList">
          <Field label="Requirement" value={observation.requirement_text} />
          <Field label="Contact Name" value={observation.contact_name} />
          <Field label="Contact Email" value={observation.contact_email} />
          <Field label="Contact Phone" value={observation.contact_phone} />
          <Field label="Confidence Score" value={observation.confidence_score} />
          <Field label="Specifications" value={JSON.stringify(observation.specifications, null, 2)} />
          <Field label="Metadata" value={JSON.stringify(observation.metadata, null, 2)} />
        </dl>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Source Evidence</h2>
        </div>
        <dl className="dataList">
          <Field label="Source" value={observation.source_id} />
          <Field label="Source URL" value={observation.source_url} />
          <Field label="Captured At" value={formatDateTime(observation.captured_at)} />
          <Field label="Run ID" value={observation.run_id} />
          <Field label="Evidence Type" value={observation.evidence_type} />
          <Field label="Extractor Type" value={observation.extractor_type} />
          <Field label="Extraction Status" value={observation.extraction_status} />
        </dl>
        <pre className="evidenceBox">{observation.raw_text ?? "No raw evidence captured."}</pre>
      </section>
    </>
  );
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="detailItem">
      <span>{label}</span>
      <strong>{value || "Not recorded"}</strong>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value === null || value === undefined || value === "" ? "Not recorded" : value}</dd>
    </>
  );
}

function quantityLabel(observation: SourceObservation) {
  if (observation.quantity === null) return "Not recorded";
  return `${observation.quantity}${observation.unit ? ` ${observation.unit}` : ""}`;
}

function contactSummary(observation: SourceObservation) {
  return [observation.contact_email, observation.contact_phone].filter(Boolean).join(" / ") || "Not recorded";
}
