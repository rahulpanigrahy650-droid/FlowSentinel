from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..core.heuristics import CATEGORY_TEAMS, SLA_HOURS
from ..db import SessionLocal
from ..models import Incident, IncidentEvent, utcnow
from ..schemas import IncidentCreate, IncidentUpdate
from ..workflow.graph import build_graph
from ..workflow.nodes import WorkflowNodes
from .runtime import get_runtime, make_store

log = logging.getLogger("flowsentinel.incidents")


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def add_event(db: Session, incident: Incident, kind: str, message: str) -> None:
    db.add(IncidentEvent(incident_id=incident.id, kind=kind, message=message))


def create_incident(db: Session, payload: IncidentCreate) -> Incident:
    inc = Incident(title=payload.title.strip(), description=payload.description.strip(),
                   reporter=payload.reporter.strip(), status="open", analysis_status="pending")
    inc.sla_due_at = utcnow() + timedelta(hours=SLA_HOURS["medium"])
    db.add(inc)
    db.flush()
    add_event(db, inc, "created", f"Incident reported{' by ' + inc.reporter if inc.reporter else ''}")
    db.commit()
    return inc


def run_analysis(incident_id: int) -> None:
    """Background task: run the LangGraph workflow and persist the outcome."""
    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if inc is None:
            return
        try:
            analyze_incident(db, inc)
        except Exception as exc:  # never leave an incident stuck in "pending"
            log.exception("analysis failed for incident %s", incident_id)
            inc.analysis_status = "failed"
            add_event(db, inc, "analyzed", f"Automatic analysis failed: {type(exc).__name__}")
            db.commit()


def analyze_incident(db: Session, inc: Incident) -> Incident:
    rt = get_runtime()
    s = rt.settings
    store = make_store(db)
    nodes = WorkflowNodes(
        retriever=lambda q, k: store.search(q, k),
        llm=rt.llm, top_k=s.top_k, min_score=s.min_score, auto_score=s.auto_score,
    )
    state = build_graph(nodes).invoke({"title": inc.title, "description": inc.description, "trace": []})

    inc.category = state["category"]
    if not inc.severity_overridden:
        inc.severity = state["severity"]
    inc.summary = state["summary"]
    inc.confidence = float(state["confidence"])
    inc.suggested_resolution = state["resolution"]
    inc.route = state["route"]
    if inc.status not in ("resolved", "in_progress"):
        inc.status = "escalated" if state["route"] == "escalate" else "open"
    if not inc.assigned_team:
        inc.assigned_team = state["assigned_team"]
    inc.sla_due_at = as_utc(inc.created_at) + timedelta(hours=SLA_HOURS[inc.severity])
    inc.analysis = {
        "trace": state["trace"],
        "passages": state.get("passages", []),
        "rationale": state.get("rationale", []),
        "best_score": state.get("best_score", 0.0),
        "llm_used": state.get("llm_used", False),
    }
    inc.analysis_status = "done"
    add_event(db, inc, "analyzed",
              f"Analysed: {inc.category} / {inc.severity}; route '{inc.route}' -> {inc.assigned_team}")
    db.commit()
    return inc


def update_incident(db: Session, inc: Incident, patch: IncidentUpdate) -> Incident:
    if patch.severity and patch.severity != inc.severity:
        add_event(db, inc, "override", f"Severity changed {inc.severity} -> {patch.severity} by agent")
        inc.severity = patch.severity
        inc.severity_overridden = True
        inc.sla_due_at = as_utc(inc.created_at) + timedelta(hours=SLA_HOURS[inc.severity])
    if patch.category and patch.category != inc.category:
        add_event(db, inc, "override", f"Category changed {inc.category} -> {patch.category} by agent")
        inc.category = patch.category
        if not patch.assigned_team:
            inc.assigned_team = CATEGORY_TEAMS.get(patch.category, inc.assigned_team)
    if patch.assigned_team is not None and patch.assigned_team != inc.assigned_team:
        add_event(db, inc, "status", f"Assigned to {patch.assigned_team}")
        inc.assigned_team = patch.assigned_team
    if patch.resolution_notes is not None:
        inc.resolution_notes = patch.resolution_notes
    if patch.status and patch.status != inc.status:
        add_event(db, inc, "status", f"Status changed {inc.status} -> {patch.status}")
        inc.status = patch.status
        inc.resolved_at = utcnow() if patch.status == "resolved" else None
        if patch.status == "resolved" and patch.save_to_kb and inc.resolution_notes.strip():
            _learn_from_incident(db, inc)
    db.commit()
    return inc


def _learn_from_incident(db: Session, inc: Incident) -> None:
    """Workflow automation: a resolved incident becomes a knowledge-base article."""
    body = (f"# Resolved incident #{inc.id}: {inc.title}\n\n## Problem\n{inc.description}\n\n"
            f"## Resolution\n{inc.resolution_notes}\n")
    make_store(db).add_document(f"Resolved #{inc.id}: {inc.title}", body, source=f"incident/{inc.id}")
    add_event(db, inc, "note", "Resolution notes added to the knowledge base")


def record_feedback(db: Session, inc: Incident, helpful: bool, note: str) -> Incident:
    inc.feedback = "helpful" if helpful else "not_helpful"
    add_event(db, inc, "feedback", ("Suggestion marked helpful" if helpful else "Suggestion marked not helpful")
              + (f": {note}" if note else ""))
    db.commit()
    return inc
