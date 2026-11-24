"""Workflow nodes. Framework-free on purpose: LangGraph only wires them together in graph.py,
so they can be unit-tested with fakes (no DB, no LLM, no network)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable, Protocol

from ..core.heuristics import CATEGORY_TEAMS, heuristic_triage, severity_rank
from .state import WorkflowState


class LLMLike(Protocol):
    def triage(self, title: str, description: str) -> dict: ...
    def draft(self, title: str, description: str, category: str, passages: list[dict]) -> str: ...
    def rewrite_query(self, title: str, description: str) -> str: ...


Retriever = Callable[[str, int], list[dict]]


def _step(node: str, detail: str) -> dict:
    return {"node": node, "detail": detail, "at": datetime.now(timezone.utc).isoformat()}


class WorkflowNodes:
    MAX_RETRIES = 1

    def __init__(self, retriever: Retriever, llm: LLMLike | None = None, *,
                 top_k: int = 4, min_score: float = 0.10, auto_score: float = 0.20):
        self.retriever = retriever
        self.llm = llm
        self.top_k = top_k
        self.min_score = min_score
        self.auto_score = auto_score

    # 1. triage -------------------------------------------------------------------
    def triage(self, state: WorkflowState) -> dict:
        title, desc = state["title"], state["description"]
        rules = heuristic_triage(title, desc)
        result, llm_used, note = dict(rules), False, "rule-based triage"
        if self.llm is not None:
            try:
                ai = self.llm.triage(title, desc)
                result.update(category=ai["category"], summary=ai["summary"], confidence=float(ai["confidence"]),
                              rationale=list(ai["rationale"]))
                # Safety floor: the model may escalate, never downgrade past hard rules.
                result["severity"] = ai["severity"]
                if severity_rank(rules["severity"]) > severity_rank(ai["severity"]) and rules["hard_critical"]:
                    result["severity"] = rules["severity"]
                    result["rationale"].append("severity floor applied: hard-critical keywords detected")
                llm_used, note = True, "LLM triage"
            except Exception as exc:  # fall back to rules
                note = f"LLM triage failed ({type(exc).__name__}); used rules"
        query = f"{title}. {result['summary']}"
        return {
            "category": result["category"], "severity": result["severity"], "summary": result["summary"],
            "confidence": result["confidence"], "rationale": result["rationale"], "llm_used": llm_used,
            "hard_critical": rules["hard_critical"], "query": query, "attempt": 0,
            "trace": [_step("triage", f"{note}: {result['category']} / {result['severity']} "
                                      f"(confidence {result['confidence']:.2f})")],
        }

    # 2. retrieve -----------------------------------------------------------------
    def retrieve(self, state: WorkflowState) -> dict:
        passages = self.retriever(state["query"], self.top_k)
        best = max((p["score"] for p in passages), default=0.0)
        return {"passages": passages, "best_score": best,
                "trace": [_step("retrieve", f"{len(passages)} passage(s), best similarity {best:.2f} "
                                            f"(attempt {state.get('attempt', 0) + 1})")]}

    # 3. grade (corrective RAG) -----------------------------------------------------
    def grade(self, state: WorkflowState) -> dict:
        relevant = state.get("best_score", 0.0) >= self.min_score
        if relevant or state.get("attempt", 0) >= self.MAX_RETRIES:
            verdict = "relevant" if relevant else "no relevant documentation found"
            return {"retry": False, "trace": [_step("grade", f"retrieval graded: {verdict}")]}
        new_query = state["description"][:400]
        if self.llm is not None:
            try:
                new_query = self.llm.rewrite_query(state["title"], state["description"]) or new_query
            except Exception:
                pass
        return {"retry": True, "attempt": state.get("attempt", 0) + 1, "query": new_query,
                "trace": [_step("grade", "weak retrieval; rewriting query and retrying")]}

    def route_after_grade(self, state: WorkflowState) -> str:
        return "retrieve" if state.get("retry") else "draft_resolution"

    # 4. draft resolution -----------------------------------------------------------
    def draft_resolution(self, state: WorkflowState) -> dict:
        passages = [p for p in state.get("passages", []) if p["score"] >= self.min_score]
        text, note = None, "extractive answer"
        if self.llm is not None:
            try:
                text = self.llm.draft(state["title"], state["description"], state["category"], passages)
                note = "LLM answer grounded in retrieved passages"
            except Exception as exc:
                note = f"LLM drafting failed ({type(exc).__name__}); extractive answer"
        if not text:
            text = extractive_resolution(passages, confident=state.get("best_score", 0.0) >= self.auto_score)
        return {"resolution": text, "trace": [_step("draft_resolution", f"{note}; {len(passages)} source(s)")]}

    # 5. decide route ---------------------------------------------------------------
    def decide_route(self, state: WorkflowState) -> dict:
        sev, best, conf = state["severity"], state.get("best_score", 0.0), state.get("confidence", 0.0)
        team = CATEGORY_TEAMS.get(state["category"], "Service Desk")
        if sev == "critical":
            route, status, why = "escalate", "escalated", "critical severity: paged on-call"
        elif best >= self.auto_score and conf >= 0.5:
            route, status, why = "suggested", "open", "confident documented fix available"
        else:
            route, status, why = "manual", "open", "low retrieval confidence: needs human triage"
        return {"route": route, "status": status, "assigned_team": team,
                "trace": [_step("decide_route", f"{route} -> {team} ({why})")]}


_STEP = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+\S")


def extractive_resolution(passages: list[dict], confident: bool = True) -> str:
    if not passages:
        return ("No matching runbook was found.\n\n1. Collect error messages, timestamps and the list of affected users.\n"
                "2. Check recent changes or deployments.\n3. Escalate to the owning team with the details above.")
    lines: list[str] = []
    if not confident:
        lines += ["_Low-confidence match: check that this runbook really applies before following the steps._", ""]
    for i, p in enumerate(passages[:2], 1):
        steps = [ln.strip() for ln in p["content"].splitlines() if _STEP.match(ln)]
        if not steps:
            steps = [p["content"].strip()[:500]]
        lines.append(f"**From {p['title']} [{i}]**")
        lines.extend(steps[:7])
        lines.append("")
    lines.append("Sources: " + "; ".join(f"[{i}] {p['title']}" + (f" - {p['heading']}" if p["heading"] else "")
                                         for i, p in enumerate(passages, 1)))
    return "\n".join(lines).strip()
