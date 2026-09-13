import type { AgentStatus, ErrorSeverity, RunStatus } from "@/lib/api/types";

type StatusKind = RunStatus | AgentStatus | ErrorSeverity | string;

export function statusLabel(status: StatusKind) {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function statusTone(status: StatusKind) {
  if (["completed", "active", "ready", "healthy", "info", "approved", "eligible"].includes(status)) return "good";
  if (["running", "queued", "idle", "manual", "warning", "candidate"].includes(status)) return "notice";
  if (["completed_with_warnings", "degraded"].includes(status)) return "warn";
  if (["failed", "critical", "error", "unavailable", "not_ready", "disabled", "rejected"].includes(status)) {
    return "bad";
  }
  return "neutral";
}

export function StatusBadge({ status }: { status: StatusKind }) {
  return <span className={`badge ${statusTone(status)}`}>{statusLabel(status)}</span>;
}
