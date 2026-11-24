"""Rule-based triage. Used (a) as the offline classifier and (b) as a safety net under the LLM:
the LLM may raise severity but can never lower it below what hard rules detect."""
from __future__ import annotations

import re

CATEGORY_TEAMS = {
    "network": "Network Operations",
    "security": "Security Operations (SOC)",
    "database": "Database Administration",
    "identity_access": "Identity & Access Management",
    "email_collab": "Collaboration Services",
    "hardware": "Desktop & Hardware Support",
    "infrastructure": "Platform / SRE",
    "application": "Application Support",
    "service_request": "Service Desk",
    "other": "Service Desk",
}
CATEGORIES = list(CATEGORY_TEAMS)
SEVERITIES = ["critical", "high", "medium", "low"]
SLA_HOURS = {"critical": 1, "high": 4, "medium": 24, "low": 72}

_CATEGORY_TERMS = {
    "network": ["vpn", "network", "wifi", "wi-fi", "dns", "dhcp", "firewall", "latency", "packet loss", "router",
                "switch", "bandwidth", "connectivity", "proxy", "gateway", "ping", "name resolution"],
    "security": ["phishing", "malware", "ransomware", "breach", "virus", "suspicious", "unauthorized", "compromised",
                 "leak", "vulnerability", "cve", "exfiltration", "security", "certificate", "ssl", "tls",
                 "encrypted files", "ddos", "intrusion"],
    "database": ["database", "postgres", "postgresql", "mysql", "sql", "deadlock", "replication", "replica",
                 "connection pool", "oracle", "mongodb", "redis", "slow query", "db"],
    "identity_access": ["password", "login", "log in", "sign in", "sso", "mfa", "2fa", "locked out", "account locked",
                        "permission", "access denied", "ldap", "active directory", "okta", "credentials",
                        "authenticator"],
    "email_collab": ["email", "outlook", "exchange", "teams", "slack", "zoom", "calendar", "mailbox", "smtp",
                     "sharepoint", "onedrive", "meeting"],
    "hardware": ["laptop", "printer", "monitor", "keyboard", "mouse", "battery", "hard drive", "ssd", "docking",
                 "usb", "screen", "headset", "raid", "toner", "paper jam"],
    "infrastructure": ["server", "kubernetes", "k8s", "docker", "container", "pod", "crashloopbackoff", "cpu",
                       "memory", "disk space", "disk full", "out of memory", "oom", "vm", "aws", "azure", "gcp",
                       "load balancer", "cluster", "node", "deployment", "pipeline", "no space left"],
    "application": ["application", "app", "crash", "500", "bug", "exception", "stack trace", "api", "timeout",
                    "page not loading", "slow", "website", "portal", "erp", "crm", "release", "checkout"],
    "service_request": ["install", "request", "new laptop", "how do i", "how to", "onboarding", "license",
                        "new account", "new starter"],
}

_CRITICAL = ["outage", "all users", "everyone", "entire company", "whole company", "production down", "prod down",
             "site is down", "system down", "is down for", "data loss", "ransomware", "data breach", "breach",
             "payments failing", "cannot process payments", "complete failure", "encrypted files",
             "security incident", "exfiltration"]
_HIGH = ["production", "prod ", "multiple users", "whole team", "entire team", "department", "many users", "failing",
         "failed", "degraded", "500 error", "error 500", "crash", "deadline", "customer", "revenue", "blocked",
         "cannot access", "can't access", "unable to", "unavailable", "data corruption", "deadlock", "disk full",
         "out of memory", "phishing", "compromised", "expired certificate", "certificate expired", "crashloop"]
_LOW = ["how to", "how do i", "question", "request", "cosmetic", "typo", "minor", "when possible", "not urgent",
        "low priority", "enhancement", "nice to have", "new account", "onboarding", "install", "just me", "only me"]
_HARD_CRITICAL = {"ransomware", "data breach", "exfiltration", "encrypted files", "production down", "prod down",
                  "site is down", "system down", "outage", "data loss"}
_COUNT = re.compile(r"\b(\d{1,5})\s+(users|employees|people|customers|servers|staff|colleagues|machines)\b")


def _has(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term.strip()) + r"(?![a-z0-9])", text) is not None


def classify_category(title: str, description: str) -> tuple[str, float, list[str]]:
    t, d = title.lower(), description.lower()
    scores: dict[str, float] = {}
    hits: dict[str, list[str]] = {}
    for cat, terms in _CATEGORY_TERMS.items():
        for term in terms:
            w = (2.0 if _has(t, term) else 0.0) + (1.0 if _has(d, term) else 0.0)
            if w:
                scores[cat] = scores.get(cat, 0.0) + w
                hits.setdefault(cat, []).append(term)
    if not scores:
        return "other", 0.3, []
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, top = ranked[0]
    total = sum(scores.values())
    conf = 0.4 + 0.5 * (top / total) * min(1.0, top / 3.0)
    return best, round(min(conf, 0.95), 2), hits[best][:5]


def assess_severity(title: str, description: str, category: str = "other") -> tuple[str, list[str], bool]:
    text = f"{title}\n{description}".lower()
    score = 0
    reasons: list[str] = []
    hard = False
    for term in _CRITICAL:
        if _has(text, term):
            score += 4
            reasons.append(f"critical signal: '{term}'")
            hard = hard or term in _HARD_CRITICAL
    for term in _HIGH:
        if _has(text, term):
            score += 2
            reasons.append(f"high-impact signal: '{term}'")
    for term in _LOW:
        if _has(text, term):
            score -= 2
            reasons.append(f"low-urgency signal: '{term}'")
    for m in _COUNT.finditer(text):
        n = int(m.group(1))
        pts = 3 if n >= 50 else 2 if n >= 10 else 1 if n >= 2 else 0
        if pts:
            score += pts
            reasons.append(f"{n} {m.group(2)} affected")
    if category == "security" and score > 0:
        score += 1
    sev = "critical" if score >= 6 else "high" if score >= 3 else "medium" if score >= 0 else "low"
    if hard:
        sev = "critical"
    return sev, reasons[:6], hard


def heuristic_triage(title: str, description: str) -> dict:
    category, cat_conf, cat_terms = classify_category(title, description)
    severity, reasons, hard = assess_severity(title, description, category)
    rationale = ([f"category keywords: {', '.join(cat_terms)}"] if cat_terms else []) + reasons
    first_sentence = re.split(r"(?<=[.!?])\s+", description.strip())[0][:200] if description.strip() else title
    return {
        "category": category,
        "severity": severity,
        "summary": f"{title.strip()}. {first_sentence}" if first_sentence and first_sentence != title else title,
        "confidence": cat_conf,
        "rationale": rationale or ["no strong signals; defaulted to medium"],
        "hard_critical": hard,
    }


def severity_rank(sev: str) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(sev, 1)
