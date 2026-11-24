from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Incident, utcnow
from ..services.incident_service import as_utc

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    rows = db.scalars(select(Incident)).all()
    now = utcnow()
    active = [i for i in rows if i.status != "resolved"]
    resolved = [i for i in rows if i.status == "resolved" and i.resolved_at]
    analysed = [i for i in rows if i.analysis_status == "done"]
    rated = [i for i in rows if i.feedback]

    days = [(now - timedelta(days=n)).date() for n in range(13, -1, -1)]
    per_day = Counter(as_utc(i.created_at).date() for i in rows)
    mttr = (sum((as_utc(i.resolved_at) - as_utc(i.created_at)).total_seconds() for i in resolved)
            / len(resolved) / 3600) if resolved else None

    return {
        "totals": {
            "total": len(rows),
            "active": len(active),
            "escalated": sum(1 for i in rows if i.status == "escalated"),
            "in_progress": sum(1 for i in rows if i.status == "in_progress"),
            "resolved": len(resolved),
        },
        "active_by_severity": {s: sum(1 for i in active if i.severity == s)
                               for s in ("critical", "high", "medium", "low")},
        "by_category": [{"category": c, "count": n} for c, n in Counter(i.category for i in rows).most_common()],
        "daily": [{"date": d.isoformat(), "count": per_day.get(d, 0)} for d in days],
        "mttr_hours": round(mttr, 1) if mttr is not None else None,
        "suggestion_rate": round(sum(1 for i in analysed if i.route == "suggested") / len(analysed), 2)
        if analysed else None,
        "helpful_rate": round(sum(1 for i in rated if i.feedback == "helpful") / len(rated), 2) if rated else None,
        "sla_breached": sum(1 for i in active if i.sla_due_at and as_utc(i.sla_due_at) < now),
    }
