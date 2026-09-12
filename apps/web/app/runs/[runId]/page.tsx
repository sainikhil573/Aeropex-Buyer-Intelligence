"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { formatDateTime, formatNumber } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import { getRun, listErrors } from "@/lib/api/client";
import type { AgentRun, ErrorEvent } from "@/lib/api/types";

export default function RunDetailPage({ params }: { params: { runId: string } }) {
  const [run, setRun] = useState<AgentRun | null>(null);
  const [errors, setErrors] = useState<ErrorEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [run, allErrors] = await Promise.all([getRun(params.runId), listErrors({ limit: 50 })]);
      setRun(run);
      setErrors(allErrors.filter((event) => event.run_id === params.runId));
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, [params.runId]);

  const shouldPoll = useMemo(() => run?.status === "queued" || run?.status === "running", [run]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!shouldPoll) return;
    const interval = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(interval);
  }, [load, shouldPoll]);

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Run Detail</p>
          <h1>{params.runId}</h1>
          <p className="summary">
            Operational execution state for a single agent run, including bounded error visibility.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      {error ? <div className="alert">API unavailable: {error}</div> : null}

      {loading ? (
        <p className="emptyState">Loading run...</p>
      ) : run ? (
        <>
          <section className="detailGrid">
            <Detail label="Run ID" value={run.run_id} />
            <Detail
              label="Agent"
              value={<Link href={`/agents/${run.agent_id}`}>{run.agent_id}</Link>}
            />
            <Detail label="Trigger Type" value={run.trigger_type} />
            <Detail label="Status" status={run.status} />
            <Detail label="Started" value={formatDateTime(run.started_at)} />
            <Detail label="Finished" value={formatDateTime(run.finished_at)} />
            <Detail label="Records Processed" value={formatNumber(run.records_processed)} />
            <Detail label="Records Created" value={formatNumber(run.records_created)} />
            <Detail label="Retry Count" value={formatNumber(run.retry_count)} />
            <Detail label="Error Count" value={formatNumber(run.error_count)} />
          </section>

          <section className="panel">
            <div className="panelHeader">
              <h2>Summary</h2>
            </div>
            <p className="emptyState">{run.summary ?? "No run summary recorded."}</p>
          </section>

          <section className="panel">
            <div className="panelHeader">
              <h2>Run Errors</h2>
            </div>
            {errors.length === 0 ? (
              <p className="emptyState">No errors recorded for this run.</p>
            ) : (
              <div className="tableWrap">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Severity</th>
                      <th>Error Type</th>
                      <th>Message</th>
                      <th>Retryable</th>
                      <th>Resolved</th>
                    </tr>
                  </thead>
                  <tbody>
                    {errors.map((event) => (
                      <tr key={event.error_id}>
                        <td>{formatDateTime(event.created_at)}</td>
                        <td>
                          <StatusBadge status={event.severity} />
                        </td>
                        <td>{event.error_type}</td>
                        <td>{event.message}</td>
                        <td>{event.retryable ? "Yes" : "No"}</td>
                        <td>{event.resolved ? "Yes" : "No"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : (
        <p className="emptyState">Run not found.</p>
      )}
    </>
  );
}

function Detail({
  label,
  value,
  status,
}: {
  label: string;
  value?: ReactNode;
  status?: string;
}) {
  return (
    <div className="detailItem">
      <span>{label}</span>
      {status ? <StatusBadge status={status} /> : <strong>{value}</strong>}
    </div>
  );
}
