"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { formatDateTime } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import { getBuyerVerification, listBuyerRequirements, updateVerification } from "@/lib/api/client";
import type { BuyerRequirement, BuyerVerificationState, VerificationResult, VerificationStatus } from "@/lib/api/types";

const reviewStatuses: VerificationStatus[] = ["pending", "partially_verified", "verified", "rejected"];

export default function BuyerDetailPage({ params }: { params: { buyerId: string } }) {
  const [state, setState] = useState<BuyerVerificationState | null>(null);
  const [requirements, setRequirements] = useState<BuyerRequirement[]>([]);
  const [selectedVerificationId, setSelectedVerificationId] = useState("");
  const [reviewStatus, setReviewStatus] = useState<VerificationStatus>("pending");
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [verificationState, requirementRows] = await Promise.all([
        getBuyerVerification(params.buyerId),
        listBuyerRequirements(params.buyerId),
      ]);
      setState(verificationState);
      setRequirements(requirementRows);
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, [params.buyerId]);

  useEffect(() => {
    void load();
  }, [load]);

  const activeVerification = useMemo(() => {
    if (!state) return null;
    return (
      state.verification_results.find((result) => result.verification_id === selectedVerificationId) ??
      state.verification_results[0] ??
      null
    );
  }, [selectedVerificationId, state]);

  useEffect(() => {
    if (!activeVerification) return;
    setSelectedVerificationId(activeVerification.verification_id);
    setReviewStatus(activeVerification.status);
    setSummary(activeVerification.summary ?? "");
  }, [activeVerification]);

  async function saveReview() {
    if (!activeVerification || !state) return;
    try {
      setSaving(true);
      await updateVerification(state.buyer.buyer_id, activeVerification.verification_id, {
        status: reviewStatus,
        summary,
      });
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to save verification decision");
    } finally {
      setSaving(false);
    }
  }

  if (loading && state === null) return <p className="emptyState">Loading buyer verification...</p>;

  if (state === null) {
    return <div className="alert">Buyer verification unavailable: {error ?? "Buyer not found"}</div>;
  }

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Buyer Detail</p>
          <h1>{state.buyer.company_name}</h1>
          <p className="summary">
            Verification evidence and enrichment are reviewed separately from discovery and canonicalization.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      <section className="feedbackLine">
        Current verification status: <StatusBadge status={state.buyer.verification_status} />
      </section>
      {error ? <div className="alert">{error}</div> : null}

      <section className="detailGrid">
        <div className="detailItem">
          <span>Country</span>
          <strong>{state.buyer.country ?? "-"}</strong>
        </div>
        <div className="detailItem">
          <span>Website</span>
          <strong>{sourceLink(state.buyer.website)}</strong>
        </div>
        <div className="detailItem">
          <span>Primary Domain</span>
          <strong>{state.buyer.primary_domain ?? "-"}</strong>
        </div>
        <div className="detailItem">
          <span>Canonical ID</span>
          <strong>{state.buyer.buyer_id}</strong>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Verification Summary</h2>
          <span className="mutedText">{state.verification_results.length} results</span>
        </div>
        {activeVerification ? (
          <div className="reviewPanel">
            <label>
              Verification Result
              <select
                onChange={(event) => setSelectedVerificationId(event.target.value)}
                value={activeVerification.verification_id}
              >
                {state.verification_results.map((result) => (
                  <option key={result.verification_id} value={result.verification_id}>
                    {result.verification_id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Review Status
              <select onChange={(event) => setReviewStatus(event.target.value as VerificationStatus)} value={reviewStatus}>
                {reviewStatuses.map((status) => (
                  <option key={status} value={status}>
                    {status.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Review Notes / Summary
              <textarea onChange={(event) => setSummary(event.target.value)} value={summary} />
            </label>
            <div className="rowActions">
              <button disabled={saving} onClick={() => void saveReview()} type="button">
                Save Verification Decision
              </button>
              <StatusBadge status={activeVerification.status} />
            </div>
          </div>
        ) : (
          <p className="emptyState">No verification results have been created for this buyer.</p>
        )}
      </section>

      <DataSection title="Requirements" empty="No requirements are attached to this buyer.">
        {requirements.map((requirement) => (
          <tr key={requirement.requirement_id}>
            <td>{requirement.product_id ?? "-"}</td>
            <td className="clampedCell">{requirement.requirement_text ?? "-"}</td>
            <td>{requirement.quantity === null ? "-" : `${requirement.quantity}${requirement.unit ? ` ${requirement.unit}` : ""}`}</td>
            <td>
              <StatusBadge status={requirement.status} />
            </td>
          </tr>
        ))}
      </DataSection>

      <DataSection title="Contacts" empty="No contact candidates have been captured.">
        {state.contacts.map((contact) => (
          <tr key={contact.contact_id}>
            <td>{contact.name ?? "-"}</td>
            <td>{contact.email ?? "-"}</td>
            <td>{contact.phone ?? "-"}</td>
            <td>{contact.title ?? "-"}</td>
            <td>
              <StatusBadge status={contact.verification_status} />
            </td>
          </tr>
        ))}
      </DataSection>

      <DataSection title="Verification Evidence" empty="No verification evidence has been captured.">
        {state.evidence.map((evidence) => (
          <tr key={evidence.evidence_id}>
            <td>{evidence.claim_type}</td>
            <td>{evidence.source_type}</td>
            <td>{sourceLink(evidence.source_url)}</td>
            <td className="clampedCell">{evidence.evidence_text}</td>
            <td>{formatDateTime(evidence.captured_at)}</td>
          </tr>
        ))}
      </DataSection>

      <DataSection title="Enrichment Results" empty="No enrichment results have been captured.">
        {state.enrichments.map((enrichment) => (
          <tr key={enrichment.enrichment_id}>
            <td>{enrichment.field_name}</td>
            <td className="clampedCell">{enrichment.field_value}</td>
            <td>{sourceLink(enrichment.source_url) ?? enrichment.source_type}</td>
            <td>
              <StatusBadge status={enrichment.status} />
            </td>
          </tr>
        ))}
      </DataSection>
    </>
  );
}

function DataSection({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const rows = Array.isArray(children) ? children.filter(Boolean) : children;
  const hasRows = Array.isArray(rows) ? rows.length > 0 : Boolean(rows);
  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>{title}</h2>
      </div>
      {!hasRows ? (
        <p className="emptyState">{empty}</p>
      ) : (
        <div className="tableWrap">
          <table>
            <tbody>{children}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function sourceLink(url: string | null) {
  if (!url) return "-";
  return (
    <a href={url} rel="noopener noreferrer" target="_blank">
      {url}
    </a>
  );
}
