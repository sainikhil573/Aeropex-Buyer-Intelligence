"use client";

import { useCallback, useEffect, useState } from "react";
import { formatDateTime } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import { approveSource, createSource, listSources, rejectSource, updateSource } from "@/lib/api/client";
import type { Source, SourceAccessMethod, SourceOperationalStatus } from "@/lib/api/types";

type SourceForm = {
  source_id: string;
  name: string;
  domain: string;
  country: string;
  source_type: string;
  access_method: SourceAccessMethod;
  operational_status: SourceOperationalStatus;
  notes: string;
};

const emptyForm: SourceForm = {
  source_id: "",
  name: "",
  domain: "",
  country: "",
  source_type: "trade_portal",
  access_method: "http",
  operational_status: "active",
  notes: "",
};

function reliabilityLabel(value: Source["reliability_score"]) {
  return value === null || value === undefined ? "-" : String(value);
}

function isEligible(source: Source) {
  return source.approval_status === "approved" && source.operational_status === "active";
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<SourceForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSources(await listSources());
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function edit(source: Source) {
    setEditingId(source.source_id);
    setForm({
      source_id: source.source_id,
      name: source.name,
      domain: source.domain ?? "",
      country: source.country ?? "",
      source_type: source.source_type,
      access_method: source.access_method,
      operational_status: source.operational_status,
      notes: source.notes ?? "",
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function submit() {
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        domain: form.domain || null,
        country: form.country || null,
        source_type: form.source_type,
        access_method: form.access_method,
        operational_status: form.operational_status,
        notes: form.notes || null,
      };
      if (editingId) {
        await updateSource(editingId, payload);
      } else {
        await createSource({ source_id: form.source_id, ...payload });
      }
      resetForm();
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to save source");
    } finally {
      setSaving(false);
    }
  }

  async function transition(sourceId: string, action: "approve" | "reject") {
    setSaving(true);
    try {
      if (action === "approve") {
        await approveSource(sourceId);
      } else {
        await rejectSource(sourceId);
      }
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to update source");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Configuration</p>
          <h1>Source Registry</h1>
          <p className="summary">
            Governed source metadata for later Buyer Discovery. Registry actions do not execute
            connectors or scraping.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      {error ? <div className="alert">{error}</div> : null}

      <section className="panel">
        <div className="panelHeader">
          <h2>{editingId ? "Edit Source" : "Create Candidate Source"}</h2>
          {editingId ? (
            <button onClick={resetForm} type="button">
              Cancel
            </button>
          ) : null}
        </div>
        <div className="formGrid">
          <label>
            Source ID
            <input disabled={Boolean(editingId)} onChange={(event) => setForm({ ...form, source_id: event.target.value })} value={form.source_id} />
          </label>
          <label>
            Name
            <input onChange={(event) => setForm({ ...form, name: event.target.value })} value={form.name} />
          </label>
          <label>
            Domain
            <input onChange={(event) => setForm({ ...form, domain: event.target.value })} value={form.domain} />
          </label>
          <label>
            Country
            <input maxLength={2} onChange={(event) => setForm({ ...form, country: event.target.value.toUpperCase() })} value={form.country} />
          </label>
          <label>
            Type
            <input onChange={(event) => setForm({ ...form, source_type: event.target.value })} value={form.source_type} />
          </label>
          <label>
            Access Method
            <select
              onChange={(event) => setForm({ ...form, access_method: event.target.value as SourceAccessMethod })}
              value={form.access_method}
            >
              <option value="api">API</option>
              <option value="http">HTTP</option>
              <option value="browser">Browser</option>
              <option value="manual">Manual</option>
            </select>
          </label>
          <label>
            Operational Status
            <select
              onChange={(event) => setForm({ ...form, operational_status: event.target.value as SourceOperationalStatus })}
              value={form.operational_status}
            >
              <option value="active">Active</option>
              <option value="degraded">Degraded</option>
              <option value="disabled">Disabled</option>
              <option value="unavailable">Unavailable</option>
            </select>
          </label>
          <label>
            Notes
            <input onChange={(event) => setForm({ ...form, notes: event.target.value })} value={form.notes} />
          </label>
          <div className="formActions">
            <button disabled={saving} onClick={() => void submit()} type="button">
              {editingId ? "Save Source" : "Create Source"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        {loading ? (
          <p className="emptyState">Loading sources...</p>
        ) : sources.length === 0 ? (
          <p className="emptyState">No source registry entries.</p>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Source Name</th>
                  <th>Domain</th>
                  <th>Country</th>
                  <th>Type</th>
                  <th>Access Method</th>
                  <th>Approval</th>
                  <th>Operational</th>
                  <th>Eligible</th>
                  <th>Reliability</th>
                  <th>Last Checked</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source) => (
                  <tr key={source.source_id}>
                    <td>
                      <strong>{source.name}</strong>
                      <div className="mutedText">{source.source_id}</div>
                    </td>
                    <td>{source.domain ?? "-"}</td>
                    <td>{source.country ?? "-"}</td>
                    <td>{source.source_type}</td>
                    <td>{source.access_method}</td>
                    <td>
                      <StatusBadge status={source.approval_status} />
                    </td>
                    <td>
                      <StatusBadge status={source.operational_status} />
                    </td>
                    <td>
                      <StatusBadge status={isEligible(source) ? "eligible" : "not_eligible"} />
                    </td>
                    <td>{reliabilityLabel(source.reliability_score)}</td>
                    <td>{formatDateTime(source.last_checked_at)}</td>
                    <td>
                      <div className="rowActions">
                        <button onClick={() => edit(source)} type="button">
                          Edit
                        </button>
                        {source.approval_status === "candidate" ? (
                          <>
                            <button disabled={saving} onClick={() => void transition(source.source_id, "approve")} type="button">
                              Approve
                            </button>
                            <button disabled={saving} onClick={() => void transition(source.source_id, "reject")} type="button">
                              Reject
                            </button>
                          </>
                        ) : null}
                      </div>
                    </td>
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
