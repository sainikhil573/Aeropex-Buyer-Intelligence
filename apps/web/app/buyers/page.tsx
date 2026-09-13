"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { formatDateTime } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import { listBuyers } from "@/lib/api/client";
import type { Buyer, VerificationStatus } from "@/lib/api/types";

export default function BuyersPage() {
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [status, setStatus] = useState<"" | VerificationStatus>("");
  const [country, setCountry] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setBuyers(await listBuyers({ country: country || undefined, verificationStatus: status || undefined }));
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, [country, status]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Canonical Buyers</p>
          <h1>Buyers</h1>
          <p className="summary">
            Canonical buyer records with verification state, requirement counts, and contact coverage.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      <section className="feedbackLine">
        Verified means evidence-reviewed identity confidence, not financial safety, credit approval, or outreach approval.
      </section>

      {error ? <div className="alert">Buyer API unavailable: {error}</div> : null}

      <section className="panel">
        <div className="panelHeader">
          <h2>Filters</h2>
          <button
            onClick={() => {
              setStatus("");
              setCountry("");
            }}
            type="button"
          >
            Reset
          </button>
        </div>
        <div className="formGrid">
          <label>
            Verification Status
            <select onChange={(event) => setStatus(event.target.value as "" | VerificationStatus)} value={status}>
              <option value="">All</option>
              <option value="unverified">Unverified</option>
              <option value="pending">Pending</option>
              <option value="partially_verified">Partially Verified</option>
              <option value="verified">Verified</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
          <label>
            Country
            <input onChange={(event) => setCountry(event.target.value)} placeholder="Country" value={country} />
          </label>
        </div>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Buyer Registry</h2>
          <span className="mutedText">{buyers.length} buyers</span>
        </div>
        {loading ? (
          <p className="emptyState">Loading buyers...</p>
        ) : buyers.length === 0 ? (
          <p className="emptyState">No canonical buyers match the current filters.</p>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Country</th>
                  <th>Verification Status</th>
                  <th>Requirement Count</th>
                  <th>Contact Count</th>
                  <th>Created At</th>
                </tr>
              </thead>
              <tbody>
                {buyers.map((buyer) => (
                  <tr key={buyer.buyer_id}>
                    <td>
                      <Link href={`/buyers/${buyer.buyer_id}`}>{buyer.company_name}</Link>
                      <div className="mutedText">{buyer.buyer_id}</div>
                    </td>
                    <td>{buyer.country ?? "-"}</td>
                    <td>
                      <StatusBadge status={buyer.verification_status} />
                    </td>
                    <td>{buyer.requirements_count ?? 0}</td>
                    <td>{buyer.contacts_count ?? 0}</td>
                    <td>{formatDateTime(buyer.created_at)}</td>
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
