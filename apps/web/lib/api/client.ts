import type {
  Agent,
  AgentRun,
  CanonicalizationResult,
  ErrorEvent,
  HealthResponse,
  Overview,
  Product,
  ProductCreate,
  ProductUpdate,
  ReadinessResponse,
  RunCreateResponse,
  Source,
  SourceApprovalStatus,
  SourceCreate,
  SourceObservation,
  SourceOperationalStatus,
  SourceUpdate,
  ExtractionStatus,
  ObservationReview,
  ObservationReviewStatus,
  UpdateObservationReview,
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

export function listProducts(options: { limit?: number; offset?: number; active?: boolean; category?: string } = {}) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 50),
    offset: String(options.offset ?? 0),
  });
  if (options.active !== undefined) params.set("active", String(options.active));
  if (options.category) params.set("category", options.category);
  return request<Product[]>(`/api/v1/products?${params}`);
}

export function createProduct(payload: ProductCreate) {
  return request<Product>("/api/v1/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProduct(productId: string, payload: ProductUpdate) {
  return request<Product>(`/api/v1/products/${encodeURIComponent(productId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function listSources(
  options: {
    limit?: number;
    offset?: number;
    approvalStatus?: SourceApprovalStatus;
    operationalStatus?: SourceOperationalStatus;
  } = {},
) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 50),
    offset: String(options.offset ?? 0),
  });
  if (options.approvalStatus) params.set("approval_status", options.approvalStatus);
  if (options.operationalStatus) params.set("operational_status", options.operationalStatus);
  return request<Source[]>(`/api/v1/sources?${params}`);
}

export function listEligibleSources(options: { limit?: number; offset?: number } = {}) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 50),
    offset: String(options.offset ?? 0),
  });
  return request<Source[]>(`/api/v1/sources/eligible?${params}`);
}

export function createSource(payload: SourceCreate) {
  return request<Source>("/api/v1/sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSource(sourceId: string, payload: SourceUpdate) {
  return request<Source>(`/api/v1/sources/${encodeURIComponent(sourceId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function approveSource(sourceId: string) {
  return request<Source>(`/api/v1/sources/${encodeURIComponent(sourceId)}/approve`, {
    method: "POST",
  });
}

export function rejectSource(sourceId: string) {
  return request<Source>(`/api/v1/sources/${encodeURIComponent(sourceId)}/reject`, {
    method: "POST",
  });
}

export function listObservations(
  options: {
    limit?: number;
    offset?: number;
    reviewStatus?: ObservationReviewStatus;
    sourceId?: string;
    productId?: string;
    extractionStatus?: ExtractionStatus;
  } = {},
) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 50),
    offset: String(options.offset ?? 0),
  });
  if (options.reviewStatus) params.set("review_status", options.reviewStatus);
  if (options.sourceId) params.set("source_id", options.sourceId);
  if (options.productId) params.set("product_id", options.productId);
  if (options.extractionStatus) params.set("extraction_status", options.extractionStatus);
  return request<SourceObservation[]>(`/api/v1/observations?${params}`);
}

export function getObservation(observationId: string) {
  return request<SourceObservation>(`/api/v1/observations/${encodeURIComponent(observationId)}`);
}

export function getObservationReview(observationId: string) {
  return request<ObservationReview>(`/api/v1/observations/${encodeURIComponent(observationId)}/review`);
}

export function updateObservationReview(observationId: string, payload: UpdateObservationReview) {
  return request<ObservationReview>(`/api/v1/observations/${encodeURIComponent(observationId)}/review`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function canonicalizeObservation(observationId: string) {
  return request<CanonicalizationResult>(`/api/v1/observations/${encodeURIComponent(observationId)}/canonicalize`, {
    method: "POST",
  });
}
