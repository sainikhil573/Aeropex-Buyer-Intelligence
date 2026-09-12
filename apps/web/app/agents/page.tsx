"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { formatDateTime } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import { listAgents } from "@/lib/api/client";
import type { Agent } from "@/lib/api/types";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setAgents(await listAgents());
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 15000);
    return () => window.clearInterval(interval);
  }, [load]);

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Agents</h1>
          <p className="summary">
            Registered platform agents and worker capabilities. Registration does not imply that
            the underlying business workflow is implemented.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      {error ? <div className="alert">API unavailable: {error}</div> : null}

      <section className="panel">
        {loading ? (
          <p className="emptyState">Loading agents...</p>
        ) : agents.length === 0 ? (
          <p className="emptyState">No registered agents.</p>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Agent Name</th>
                  <th>Agent ID</th>
                  <th>Type</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Authority Level</th>
                  <th>Implementation</th>
                  <th>Last Heartbeat</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <tr key={agent.agent_id}>
                    <td>
                      <Link href={`/agents/${agent.agent_id}`}>{agent.name}</Link>
                    </td>
                    <td>{agent.agent_id}</td>
                    <td>{agent.type}</td>
                    <td>{agent.version}</td>
                    <td>
                      <StatusBadge status={agent.status} />
                    </td>
                    <td>{agent.authority_level}</td>
                    <td>
                      <StatusBadge
                        status={
                          agent.type === "buyer_discovery" ? "registered" : "future_milestone"
                        }
                      />
                    </td>
                    <td>{formatDateTime(agent.last_heartbeat_at)}</td>
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
