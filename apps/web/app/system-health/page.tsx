"use client";

import { useCallback, useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { getApiHealth, getReadiness, getRootHealth } from "@/lib/api/client";
import type { HealthResponse, ReadinessResponse } from "@/lib/api/types";

export default function SystemHealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [versionedHealth, setVersionedHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [apiHealth, ready, versioned] = await Promise.all([
        getRootHealth(),
        getReadiness(),
        getApiHealth(),
      ]);
      setHealth(apiHealth);
      setReadiness(ready);
      setVersionedHealth(versioned);
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(interval);
  }, [load]);

  const postgresql = readiness?.checks.postgresql?.status ?? "unavailable";
  const redis = readiness?.checks.redis?.status ?? "unavailable";

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>System Health</h1>
          <p className="summary">
            API and dependency readiness. Service details are intentionally limited to safe
            operational state.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      {error ? <div className="alert">API unavailable: {error}</div> : null}

      {loading ? (
        <p className="emptyState">Loading system health...</p>
      ) : (
        <section className="metricGrid">
          <HealthMetric label="API Health" status={health?.status ?? "unavailable"} />
          <HealthMetric label="API v1 Health" status={versionedHealth?.status ?? "unavailable"} />
          <HealthMetric label="API Readiness" status={readiness?.status ?? "unavailable"} />
          <HealthMetric label="PostgreSQL Readiness" status={postgresql} />
          <HealthMetric label="Redis Readiness" status={redis} />
        </section>
      )}
    </>
  );
}

function HealthMetric({ label, status }: { label: string; status: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <StatusBadge status={normalizeStatus(status)} />
    </div>
  );
}

function normalizeStatus(status: string) {
  if (status === "ready" || status === "healthy") return status;
  if (status === "not_configured") return "degraded";
  return status || "unavailable";
}
