from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["open", "in_progress", "escalated", "resolved"]
Severity = Literal["critical", "high", "medium", "low"]


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=5, max_length=10000)
    reporter: str = Field(default="", max_length=200)


class IncidentUpdate(BaseModel):
    status: Status | None = None
    severity: Severity | None = None
    category: str | None = Field(default=None, max_length=40)
    assigned_team: str | None = Field(default=None, max_length=100)
    resolution_notes: str | None = Field(default=None, max_length=10000)
    save_to_kb: bool = False  # when resolving: add the notes to the knowledge base


class FeedbackIn(BaseModel):
    helpful: bool
    note: str = Field(default="", max_length=1000)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    message: str
    created_at: datetime


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    reporter: str
    status: str
    analysis_status: str
    category: str
    severity: str
    severity_overridden: bool
    summary: str
    confidence: float
    suggested_resolution: str
    route: str
    assigned_team: str
    analysis: dict
    resolution_notes: str
    feedback: str
    created_at: datetime
    updated_at: datetime
    sla_due_at: datetime | None
    resolved_at: datetime | None


class IncidentDetail(IncidentOut):
    events: list[EventOut] = []


class IncidentList(BaseModel):
    items: list[IncidentOut]
    total: int


class DocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content: str = Field(min_length=20)
    source: str = Field(default="manual", max_length=300)


class DocumentOut(BaseModel):
    id: int
    title: str
    source: str
    created_at: datetime
    chunk_count: int


class SearchIn(BaseModel):
    query: str = Field(min_length=2)
    k: int = Field(default=5, ge=1, le=20)


class PassageOut(BaseModel):
    chunk_id: int
    document_id: int
    title: str
    heading: str
    content: str
    score: float
