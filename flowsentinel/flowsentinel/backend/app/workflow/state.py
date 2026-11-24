import operator
from typing import Annotated, TypedDict


class WorkflowState(TypedDict, total=False):
    # input
    title: str
    description: str
    # triage
    category: str
    severity: str
    summary: str
    confidence: float
    rationale: list[str]
    llm_used: bool
    hard_critical: bool
    # retrieval
    query: str
    attempt: int
    passages: list[dict]
    best_score: float
    retry: bool
    # outcome
    resolution: str
    route: str          # suggested | manual | escalate
    status: str
    assigned_team: str
    # audit trail: each node appends, LangGraph merges with operator.add
    trace: Annotated[list[dict], operator.add]
