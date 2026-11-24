export const SEVERITIES = ["critical", "high", "medium", "low"];
export const STATUSES = ["open", "in_progress", "escalated", "resolved"];
export const STATUS_LABELS = { open: "Open", in_progress: "In progress", escalated: "Escalated", resolved: "Resolved" };
export const CATEGORY_LABELS = {
  network: "Network",
  security: "Security",
  database: "Database",
  identity_access: "Identity & access",
  email_collab: "Email & collaboration",
  hardware: "Hardware",
  infrastructure: "Infrastructure",
  application: "Application",
  service_request: "Service request",
  other: "Other",
};
export const CATEGORIES = Object.keys(CATEGORY_LABELS);
export const NODE_LABELS = {
  triage: "Triage",
  retrieve: "Retrieve documentation",
  grade: "Check relevance",
  draft_resolution: "Draft resolution",
  decide_route: "Route",
};
export const ROUTE_LABELS = {
  escalate: "Escalated to on-call",
  suggested: "Fix suggested from documentation",
  manual: "Needs human triage",
};

// The API returns naive timestamps on SQLite; treat anything without a zone as UTC.
export function parseDate(value) {
  if (!value) return null;
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}

export function formatDate(value) {
  const d = parseDate(value);
  return d ? d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "";
}

export function timeAgo(value) {
  const d = parseDate(value);
  if (!d) return "";
  const mins = Math.max(0, Math.round((Date.now() - d.getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs} h ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

function span(ms) {
  const mins = Math.round(Math.abs(ms) / 60000);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  return mins % 60 ? `${h} h ${mins % 60} min` : `${h} h`;
}

export function slaInfo(incident) {
  if (incident.status === "resolved") {
    const start = parseDate(incident.created_at);
    const end = parseDate(incident.resolved_at);
    return start && end ? { text: `Resolved in ${span(end - start)}`, overdue: false } : { text: "Resolved", overdue: false };
  }
  const due = parseDate(incident.sla_due_at);
  if (!due) return { text: "", overdue: false };
  const diff = due.getTime() - Date.now();
  return diff >= 0 ? { text: `Due in ${span(diff)}`, overdue: false } : { text: `Overdue by ${span(diff)}`, overdue: true };
}

export function severityRank(sev) {
  return SEVERITIES.indexOf(sev) === -1 ? 99 : SEVERITIES.indexOf(sev);
}

export function go(path) {
  window.location.hash = path;
}

// "Runbook title > Section" -> "Section" (empty when the passage sits directly under the title)
export function subHeading(heading) {
  return (heading || "").split(" > ").slice(1).join(" > ");
}
