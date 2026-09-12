"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { formatDateTime, formatNumber } from "@/components/format";
import { StatusBadge } from "@/components/StatusBadge";
import {
  createOperationalTestRun,
  getOverview,
  listAgents,
  listErrors,
  listRuns,
} from "@/lib/api/client";
import type { Agent, AgentRun, ErrorEvent, Overview } from "@/lib/api/types";

type LoadState = {
  overview: Overview | null;
  agents: Agent[];
  runs: AgentRun[];
  errors: ErrorEvent[];
  loading: boolean;
  error: string | null;
};

const initialState: LoadState = {
  overview: null,
  agents: [],
  runs: [],
  errors: [],
  loading: true,
  error: null,
};

export default function OverviewPage() {
  const [state, setState] = useState<LoadState>(initialState);
  const [submitState, setSubmitState] = useState("Idle");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [overview, agents, runs, errors] = await Promise.all([
        getOverview(),
        listAgents(),
        listRuns({ limit: 10 }),
        listErrors({ limit: 5 }),
      ]);
      setState({ overview, agents, runs, errors, loading: false, error: null });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "API unavailable",
      }));
    }
  }, []);

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(interval);
  }, [load]);

  async function runOperationalTest() {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setSubmitState("Submitting");
    try {
      const run = await createOperationalTestRun();
      setSubmitState(statusCopy(run.status));
      await load();
    } catch (error) {
      setSubmitState(error instanceof Error ? error.message : "Failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  const runningAgents = state.agents.filter((agent) => agent.status === "running").length;

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Overview</h1>
          <p className="summary">
            Live operational foundation for platform health, registered agents, safe test runs,
            and recent failures.
          </p>
        </div>
        <div className="headerActions">
          <button onClick={() => void load()} type="button">
            Refresh
          </button>
          <button disabled={isSubmitting} onClick={() => void runOperationalTest()} type="button">
            {isSubmitting ? "Submitting" : "Run Operational Test"}
          </button>
        </div>
      </header>

      <section aria-live="polite" className="feedbackLine">
        Run control: {submitState}
      </section>

      {state.error ? <div className="alert">API unavailable: {state.error}</div> : null}

      <section className="metricGrid" aria-label="Operational summary">
        <Metric
          label="Platform Status"
          value={state.overview?.platform_status ?? (state.loading ? "Loading" : "Unavailable")}
          status={state.overview?.platform_status}
        />
        <Metric label="Total Agents" value={formatNumber(state.overview?.total_agents)} />
        <Metric
          label="Running Agents"
          value={formatNumber(state.overview?.running_agents ?? runningAgents)}
        />
        <Metric label="Recent Runs" value={formatNumber(state.overview?.recent_runs)} />
        <Metric label="Failed Runs" value={formatNumber(state.overview?.failed_runs)} />
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Recent Agent Runs</h2>
        </div>
        {state.loading ? (
          <p className="emptyState">Loading runs...</p>
        ) : state.runs.length === 0 ? (
          <p className="emptyState">No runs yet.</p>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Agent</th>
                  <th>Trigger</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Finished</th>
                  <th>Records Processed</th>
                </tr>
              </thead>
              <tbody>
                {state.runs.map((run) => (
                  <tr key={run.run_id}>
                    <td>
                      <Link href={`/runs/${run.run_id}`}>{run.run_id}</Link>
                    </td>
                    <td>{run.agent_id}</td>
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

      <section className="panel">
        <div className="panelHeader">
          <h2>Recent Errors</h2>
        </div>
        {state.loading ? (
          <p className="emptyState">Loading errors...</p>
        ) : state.errors.length === 0 ? (
          <p className="emptyState">No recent errors.</p>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Severity</th>
                  <th>Agent</th>
                  <th>Run</th>
                  <th>Error Type</th>
                  <th>Message</th>
                  <th>Resolved</th>
                </tr>
              </thead>
              <tbody>
                {state.errors.map((error) => (
                  <tr key={error.error_id}>
                    <td>{formatDateTime(error.created_at)}</td>
                    <td>
                      <StatusBadge status={error.severity} />
                    </td>
                    <td>{error.agent_id ?? "Platform"}</td>
                    <td>{error.run_id ? <Link href={`/runs/${error.run_id}`}>{error.run_id}</Link> : "None"}</td>
                    <td>{error.error_type}</td>
                    <td>{error.message}</td>
                    <td>{error.resolved ? "Yes" : "No"}</td>
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

function Metric({ label, value, status }: { label: string; value: string; status?: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      {status ? <StatusBadge status={status} /> : <strong>{value}</strong>}
    </div>
  );
}

function statusCopy(status: AgentRun["status"]) {
  if (status === "queued") return "Queued";
  if (status === "running") return "Running";
  if (status === "completed") return "Completed";
  if (status === "completed_with_warnings") return "Completed with warnings";
  if (status === "failed") return "Failed";
  return "Cancelled";
}
