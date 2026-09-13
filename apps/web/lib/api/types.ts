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
export type ExtractionStatus = "success" | "partial" | "unstructured" | "failed";
export type EvidenceType = "page_text" | "listing" | "directory_entry" | "api_record" | "manual_entry" | "unknown";
export type ObservationReviewStatus = "unreviewed" | "needs_review" | "accepted" | "rejected";
export type VerificationStatus = "unverified" | "pending" | "partially_verified" | "verified" | "rejected";
export type VerificationType = "company" | "contact" | "requirement" | "manual";
export type VerificationClaimType =
  | "company_exists"
  | "website_association"
  | "domain_association"
  | "contact_association"
  | "phone_association"
  | "email_association"
  | "business_relevance"
  | "address_association"
  | "other";
export type ContactType = "general" | "procurement" | "sales" | "owner" | "operations" | "other";
export type EnrichmentStatus = "discovered" | "accepted" | "rejected";
export type EntityResolutionStatus =
  | "created"
  | "matched"
  | "ambiguous"
  | "ineligible"
  | "already_canonicalized"
  | "failed";

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
  unreviewed_observations: number;
  needs_review_observations: number;
  accepted_observations: number;
  rejected_observations: number;
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

export type SourceObservation = {
  observation_id: string;
  source_id: string;
  run_id: string;
  source_url: string | null;
  captured_at: string;
  raw_text: string | null;
  evidence_type: EvidenceType;
  confidence_score: number | null;
  buyer_id: string | null;
  requirement_id: string | null;
  product_id: string | null;
  company_name: string | null;
  country: string | null;
  requirement_text: string | null;
  quantity: number | null;
  unit: string | null;
  specifications: Record<string, unknown>;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  posted_at: string | null;
  extraction_status: ExtractionStatus;
  extractor_type: string;
  metadata: Record<string, unknown>;
  review_status: ObservationReviewStatus;
  review_notes: string | null;
  review_id: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_created_at: string | null;
  review_updated_at: string | null;
};

export type ObservationReview = {
  review_id: string | null;
  observation_id: string;
  status: ObservationReviewStatus;
  review_notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type UpdateObservationReview = {
  status: ObservationReviewStatus;
  review_notes?: string | null;
};

export type CanonicalizationResult = {
  status: EntityResolutionStatus;
  observation_id: string;
  buyer_id: string | null;
  requirement_id: string | null;
  matched_existing_buyer: boolean;
  candidate_buyer_ids: string[];
  reason: string | null;
};

export type Buyer = {
  buyer_id: string;
  company_name: string;
  normalized_company_name: string;
  country: string | null;
  website: string | null;
  primary_domain: string | null;
  company_type: string | null;
  verification_status: VerificationStatus;
  confidence_score: number | null;
  created_at: string;
  updated_at: string;
  requirements_count: number | null;
  contacts_count: number | null;
};

export type BuyerRequirement = {
  requirement_id: string;
  buyer_id: string;
  product_id: string | null;
  requirement_text: string | null;
  quantity: number | null;
  unit: string | null;
  specifications: Record<string, unknown>;
  destination: string | null;
  posted_at: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type VerificationResult = {
  verification_id: string;
  buyer_id: string;
  status: VerificationStatus;
  verification_type: VerificationType;
  summary: string | null;
  confidence_score: number | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  risk_flags: Record<string, unknown>;
  checks: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type VerificationEvidence = {
  evidence_id: string;
  verification_id: string;
  buyer_id: string;
  source_type: string;
  source_url: string | null;
  evidence_text: string;
  captured_at: string;
  claim_type: VerificationClaimType;
  claim_value: string | null;
  supports_claim: boolean | null;
  metadata: Record<string, unknown>;
};

export type Contact = {
  contact_id: string;
  buyer_id: string;
  name: string | null;
  email: string | null;
  normalized_email: string | null;
  phone: string | null;
  normalized_phone: string | null;
  title: string | null;
  department: string | null;
  contact_type: ContactType;
  verification_status: VerificationStatus;
  source_observation_id: string | null;
  created_at: string;
  updated_at: string;
};

export type EnrichmentResult = {
  enrichment_id: string;
  buyer_id: string;
  contact_id: string | null;
  field_name: string;
  field_value: string;
  source_type: string;
  source_url: string | null;
  captured_at: string;
  status: EnrichmentStatus;
  created_at: string;
};

export type BuyerVerificationState = {
  buyer: Buyer;
  verification_results: VerificationResult[];
  evidence: VerificationEvidence[];
  contacts: Contact[];
  enrichments: EnrichmentResult[];
};

export type UpdateVerification = {
  status: VerificationStatus;
  summary?: string | null;
  reviewed_by?: string | null;
};
