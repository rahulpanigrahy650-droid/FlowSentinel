from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Incident
from ..schemas import (FeedbackIn, IncidentCreate, IncidentDetail, IncidentList, IncidentOut, IncidentUpdate)
from ..services import incident_service as svc

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def _get_or_404(db: Session, incident_id: int) -> Incident:
    inc = db.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(404, "Incident not found")
    return inc


@router.post("", response_model=IncidentOut, status_code=201)
def create_incident(payload: IncidentCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    inc = svc.create_incident(db, payload)
    background.add_task(svc.run_analysis, inc.id)
    return inc


@router.get("", response_model=IncidentList)
def list_incidents(
    status: str | None = Query(None, description="open|in_progress|escalated|resolved|active"),
    severity: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Incident)
    if status == "active":
        stmt = stmt.where(Incident.status != "resolved")
    elif status:
        stmt = stmt.where(Incident.status == status)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if category:
        stmt = stmt.where(Incident.category == category)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Incident.title.ilike(like), Incident.description.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Incident.created_at.desc(), Incident.id.desc()).limit(limit).offset(offset)).all()
    return IncidentList(items=[IncidentOut.model_validate(i) for i in items], total=total)


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, incident_id)


@router.patch("/{incident_id}", response_model=IncidentDetail)
def update_incident(incident_id: int, patch: IncidentUpdate, db: Session = Depends(get_db)):
    return svc.update_incident(db, _get_or_404(db, incident_id), patch)


@router.post("/{incident_id}/reanalyze", response_model=IncidentOut, status_code=202)
def reanalyze(incident_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    inc = _get_or_404(db, incident_id)
    inc.analysis_status = "pending"
    db.commit()
    background.add_task(svc.run_analysis, inc.id)
    return inc


@router.post("/{incident_id}/feedback", response_model=IncidentDetail)
def feedback(incident_id: int, body: FeedbackIn, db: Session = Depends(get_db)):
    return svc.record_feedback(db, _get_or_404(db, incident_id), body.helpful, body.note)
