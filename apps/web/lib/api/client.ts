import type {
  Agent,
  AgentRun,
  ErrorEvent,
  HealthResponse,
  Overview,
  ReadinessResponse,
  RunCreateResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the HTTP status text when no JSON error body is available.
    }
    throw new ApiError(detail || "API request failed", response.status);
  }

  return (await response.json()) as T;
}

export function getOverview() {
  return request<Overview>("/api/v1/overview");
}

export function listAgents() {
  return request<Agent[]>("/api/v1/agents");
}

export function getAgent(agentId: string) {
  return request<Agent>(`/api/v1/agents/${encodeURIComponent(agentId)}`);
}

export function listRuns(options: { limit?: number; offset?: number; agentId?: string } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 10));
  params.set("offset", String(options.offset ?? 0));
  if (options.agentId) {
    params.set("agent_id", options.agentId);
  }
  return request<AgentRun[]>(`/api/v1/runs?${params}`);
}

export function getRun(runId: string) {
  return request<AgentRun>(`/api/v1/runs/${encodeURIComponent(runId)}`);
}

export function createOperationalTestRun() {
  return request<RunCreateResponse>("/api/v1/runs", {
    method: "POST",
    body: JSON.stringify({ trigger_type: "manual" }),
  });
}

export function listErrors(options: { limit?: number; offset?: number } = {}) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 10),
    offset: String(options.offset ?? 0),
  });
  return request<ErrorEvent[]>(`/api/v1/errors?${params}`);
}

export function getApiHealth() {
  return request<HealthResponse>("/api/v1/health");
}

export function getRootHealth() {
  return request<HealthResponse>("/health");
}

export function getReadiness() {
  return request<ReadinessResponse>("/ready");
}
