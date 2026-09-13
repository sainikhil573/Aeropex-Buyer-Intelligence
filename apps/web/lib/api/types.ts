export type AgentStatus = "active" | "idle" | "running" | "degraded" | "failed" | "disabled";
export type RunStatus =
  | "queued"
  | "running"
  | "completed"
  | "completed_with_warnings"
  | "failed"
  | "cancelled";
export type TriggerType = "manual" | "scheduled" | "event" | "retry" | "system";
export type AuthorityLevel = "green" | "yellow" | "red";
export type ErrorSeverity = "info" | "warning" | "error" | "critical";
export type SourceApprovalStatus = "candidate" | "approved" | "rejected";
export type SourceOperationalStatus = "active" | "degraded" | "disabled" | "unavailable";
export type SourceAccessMethod = "api" | "http" | "browser" | "manual";

export type Agent = {
  agent_id: string;
  name: string;
  type: string;
  status: AgentStatus;
  version: string;
  capabilities: string[];
  authority_level: AuthorityLevel;
  last_heartbeat_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentRun = {
  run_id: string;
  agent_id: string;
  trigger_type: TriggerType;
  status: RunStatus;
  started_at: string | null;
  finished_at: string | null;
  records_processed: number;
  records_created: number;
  retry_count: number;
  error_count: number;
  summary: string | null;
};

export type RunCreateResponse = AgentRun & {
  task_id: string | null;
};

export type ErrorEvent = {
  error_id: string;
  run_id: string | null;
  agent_id: string | null;
  error_type: string;
  severity: ErrorSeverity;
  message: string;
  retryable: boolean;
  resolved: boolean;
  created_at: string;
};

export type Overview = {
  platform_status: string;
  total_agents: number;
  running_agents: number;
  recent_runs: number;
  failed_runs: number;
};

export type HealthResponse = {
  status: string;
  service: string;
  api_version?: string;
};

export type ReadinessResponse = {
  status: string;
  service: string;
  checks: Record<string, { status: string; detail?: string | null }>;
};

export type Product = {
  product_id: string;
  category: string;
  name: string;
  aliases: string[];
  variants: string[];
  hs_codes: string[];
  priority: number;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type ProductCreate = {
  product_id: string;
  category: string;
  name: string;
  aliases?: string[];
  variants?: string[];
  hs_codes?: string[];
  priority?: number;
  active?: boolean;
};

export type ProductUpdate = Partial<Omit<ProductCreate, "product_id">>;

export type Source = {
  source_id: string;
  name: string;
  domain: string | null;
  country: string | null;
  source_type: string;
  access_method: SourceAccessMethod;
  approval_status: SourceApprovalStatus;
  operational_status: SourceOperationalStatus;
  reliability_score: string | number | null;
  last_checked_at: string | null;
  notes: string | null;
  product_relevance: string[];
  created_at: string;
  updated_at: string;
};

export type SourceCreate = {
  source_id: string;
  name: string;
  domain?: string | null;
  country?: string | null;
  source_type: string;
  access_method: SourceAccessMethod;
  operational_status?: SourceOperationalStatus;
  reliability_score?: string | number | null;
  last_checked_at?: string | null;
  notes?: string | null;
  product_relevance?: string[];
};

export type SourceUpdate = Partial<Omit<SourceCreate, "source_id">>;
