"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { formatDateTime, formatNumber } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import { getAgent, listRuns } from "@/lib/api/client";
import type { Agent, AgentRun } from "@/lib/api/types";

export default function AgentDetailPage({ params }: { params: { agentId: string } }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [agent, runs] = await Promise.all([
        getAgent(params.agentId),
        listRuns({ limit: 10, agentId: params.agentId }),
      ]);
      setAgent(agent);
      setRuns(runs);
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, [params.agentId]);

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 15000);
    return () => window.clearInterval(interval);
  }, [load]);

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Agent Detail</p>
          <h1>{agent?.name ?? params.agentId}</h1>
          <p className="summary">
            Agent identity, operational registration, authority boundary, and recent run history.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      {error ? <div className="alert">API unavailable: {error}</div> : null}

      {loading ? (
        <p className="emptyState">Loading agent...</p>
      ) : agent ? (
        <>
          <section className="detailGrid">
            <Detail label="Agent ID" value={agent.agent_id} />
            <Detail label="Type" value={agent.type} />
            <Detail label="Version" value={agent.version} />
            <Detail label="Status" status={agent.status} />
            <Detail label="Authority Level" value={agent.authority_level} />
            <Detail label="Last Heartbeat" value={formatDateTime(agent.last_heartbeat_at)} />
            <Detail
              label="Implementation"
              value={
                agent.type === "buyer_discovery"
                  ? "Registered for operational tests only"
                  : "Planned for a future milestone"
              }
            />
            <Detail
              label="Capabilities"
              value={agent.capabilities.length ? agent.capabilities.join(", ") : "None registered"}
            />
          </section>

          <section className="panel">
            <div className="panelHeader">
              <h2>Recent Runs</h2>
            </div>
            {runs.length === 0 ? (
              <p className="emptyState">No runs yet for this agent.</p>
            ) : (
              <div className="tableWrap">
                <table>
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Trigger</th>
                      <th>Status</th>
                      <th>Started</th>
                      <th>Finished</th>
                      <th>Records Processed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((run) => (
                      <tr key={run.run_id}>
                        <td>
                          <Link href={`/runs/${run.run_id}`}>{run.run_id}</Link>
                        </td>
                        <td>{run.trigger_type}</td>
                        <td>
                          <StatusBadge status={run.status} />
                        </td>
                        <td>{formatDateTime(run.started_at)}</td>
                        <td>{formatDateTime(run.finished_at)}</td>
                        <td>{formatNumber(run.records_processed)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : (
        <p className="emptyState">Agent not found.</p>
      )}
    </>
  );
}

function Detail({ label, value, status }: { label: string; value?: string; status?: string }) {
  return (
    <div className="detailItem">
      <span>{label}</span>
      {status ? <StatusBadge status={status} /> : <strong>{value}</strong>}
    </div>
  );
}
