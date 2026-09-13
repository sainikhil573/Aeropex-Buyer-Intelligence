"""Enumerations approved in Data Contracts V0.1."""

from enum import StrEnum


class AgentStatus(StrEnum):
    ACTIVE = "active"
    IDLE = "idle"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    RETRY = "retry"
    SYSTEM = "system"


class AuthorityLevel(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SourceApprovalStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"


class SourceOperationalStatus(StrEnum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


class SourceAccessMethod(StrEnum):
    API = "api"
    HTTP = "http"
    BROWSER = "browser"
    MANUAL = "manual"


class ConnectorStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"


class ExtractionStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    UNSTRUCTURED = "unstructured"
    FAILED = "failed"


class ObservationReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class EvidenceType(StrEnum):
    PAGE_TEXT = "page_text"
    LISTING = "listing"
    DIRECTORY_ENTRY = "directory_entry"
    API_RECORD = "api_record"
    MANUAL_ENTRY = "manual_entry"
    UNKNOWN = "unknown"


class ErrorSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
