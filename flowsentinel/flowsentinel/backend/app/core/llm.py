"""Thin LangChain adapter. Every method may raise; the workflow nodes catch and fall back
to rule-based / extractive behaviour, so the platform keeps working without an LLM."""
from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field

from .heuristics import CATEGORIES

log = logging.getLogger("flowsentinel.llm")


class TriageResult(BaseModel):
    category: Literal[tuple(CATEGORIES)] = Field(description="Best matching IT category")  # type: ignore[valid-type]
    severity: Literal["critical", "high", "medium", "low"] = Field(
        description="critical: outage/security breach/many users blocked; high: major function degraded or team blocked; "
        "medium: single user or workaround exists; low: question or cosmetic request"
    )
    summary: str = Field(description="One-sentence plain-English summary of the problem")
    confidence: float = Field(ge=0, le=1, description="Confidence in the classification")
    rationale: list[str] = Field(description="2-4 short reasons for the category and severity")


TRIAGE_SYSTEM = (
    "You are an expert IT service-desk triage engineer. Classify the incident. "
    "Judge severity by business impact (number of users affected, production vs. internal, data or security risk, "
    "availability of a workaround), not by the reporter's tone."
)
RESOLVE_SYSTEM = (
    "You are a senior IT support engineer. Write a concise troubleshooting plan for the incident using ONLY the "
    "numbered knowledge-base passages provided. Output Markdown: a numbered list of concrete steps, then a line "
    "'Escalate if:' with the condition. Cite passages inline like [1] or [2]. If the passages do not really cover the "
    "problem, say so plainly and list what information to collect instead of guessing."
)
REWRITE_SYSTEM = (
    "Rewrite this IT incident as a short search query (max 20 words) made of the technical symptoms, product names "
    "and error messages. Output only the query."
)


class LLMAdapter:
    def __init__(self, model):
        self.model = model

    def triage(self, title: str, description: str) -> dict:
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [("system", TRIAGE_SYSTEM), ("human", "Title: {title}\n\nDescription:\n{description}")]
        )
        chain = prompt | self.model.with_structured_output(TriageResult)
        result: TriageResult = chain.invoke({"title": title, "description": description})
        return result.model_dump()

    def draft(self, title: str, description: str, category: str, passages: list[dict]) -> str:
        from langchain_core.prompts import ChatPromptTemplate

        context = "\n\n".join(
            f"[{i}] {p['title']} - {p['heading']}\n{p['content']}" for i, p in enumerate(passages, 1)
        ) or "(no relevant passages were found)"
        prompt = ChatPromptTemplate.from_messages(
            [("system", RESOLVE_SYSTEM),
             ("human", "Category: {category}\nTitle: {title}\nDescription:\n{description}\n\nPassages:\n{context}")]
        )
        msg = (prompt | self.model).invoke(
            {"category": category, "title": title, "description": description, "context": context}
        )
        content = msg.content
        if isinstance(content, list):  # some providers return content blocks
            content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
        return str(content).strip()

    def rewrite_query(self, title: str, description: str) -> str:
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [("system", REWRITE_SYSTEM), ("human", "Title: {title}\n\n{description}")]
        )
        msg = (prompt | self.model).invoke({"title": title, "description": description})
        return str(msg.content).strip()


def get_llm(settings) -> LLMAdapter | None:
    provider = settings.llm_provider.lower()
    if provider == "none":
        return None
    try:
        if provider in ("auto", "anthropic") and settings.anthropic_api_key:
            from langchain_anthropic import ChatAnthropic

            return LLMAdapter(ChatAnthropic(
                model=settings.anthropic_model, api_key=settings.anthropic_api_key,
                temperature=0, timeout=40, max_retries=1, max_tokens=1200,
            ))
        if provider in ("auto", "openai") and settings.openai_api_key:
            from langchain_openai import ChatOpenAI

            return LLMAdapter(ChatOpenAI(
                model=settings.openai_model, api_key=settings.openai_api_key,
                temperature=0, timeout=40, max_retries=1,
            ))
    except Exception as exc:  # pragma: no cover
        log.warning("LLM unavailable, using offline mode: %s", exc)
    return None
