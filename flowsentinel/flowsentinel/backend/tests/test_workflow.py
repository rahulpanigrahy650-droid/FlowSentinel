"""Runs the real workflow nodes through the same routing logic the LangGraph graph uses."""
from app.workflow.nodes import WorkflowNodes, extractive_resolution


def run(nodes, title, description):
    state = {"title": title, "description": description, "trace": []}

    def apply(update):
        for k, v in update.items():
            state[k] = state.get("trace", []) + v if k == "trace" else v

    apply(nodes.triage(state))
    apply(nodes.retrieve(state))
    apply(nodes.grade(state))
    while nodes.route_after_grade(state) == "retrieve":
        apply(nodes.retrieve(state))
        apply(nodes.grade(state))
    apply(nodes.draft_resolution(state))
    apply(nodes.decide_route(state))
    return state


def test_vpn_incident_finds_vpn_runbook(retriever):
    s = run(WorkflowNodes(retriever), "VPN disconnects every 10 minutes",
            "GlobalProtect VPN drops roughly every 10 minutes and I have to reconnect.")
    assert s["category"] == "network"
    assert s["passages"][0]["title"].startswith("VPN")
    assert s["status"] == "open" and s["route"] in ("suggested", "manual")
    assert [t["node"] for t in s["trace"]][:3] == ["triage", "retrieve", "grade"]


def test_confident_match_is_suggested_with_citations(retriever):
    s = run(WorkflowNodes(retriever), "Locked out of my account after password change",
            "I changed my password yesterday and now my account is locked out on my phone and laptop.")
    assert s["passages"][0]["title"].startswith("Account Lockout")
    assert s["route"] == "suggested" and "Sources:" in s["resolution"] and "[1]" in s["resolution"]
    assert "Low-confidence" not in s["resolution"]


def test_unrelated_incident_gets_low_confidence_warning(retriever):
    s = run(WorkflowNodes(retriever), "Quarterly espresso machine descaling", "The kitchen espresso machine needs descaling.")
    assert s["route"] == "manual" and "Low-confidence" in s["resolution"]


def test_critical_incident_is_escalated_with_postgres_runbook(retriever):
    s = run(WorkflowNodes(retriever), "Production database primary not responding",
            "All users get errors, postgres connection pool exhausted, too many connections.")
    assert s["severity"] == "critical" and s["route"] == "escalate" and s["status"] == "escalated"
    assert s["assigned_team"] == "Database Administration"
    assert "PostgreSQL" in s["passages"][0]["title"]


def test_irrelevant_incident_retries_once_then_goes_manual(retriever):
    s = run(WorkflowNodes(retriever, min_score=0.9, auto_score=0.95), "Quarterly espresso machine descaling",
            "The kitchen espresso machine needs descaling.")
    assert s["attempt"] == 1
    assert [t["node"] for t in s["trace"]].count("retrieve") == 2
    assert s["route"] == "manual"


def test_llm_failure_falls_back_to_rules(retriever):
    class BrokenLLM:
        def triage(self, *a): raise RuntimeError("boom")
        def draft(self, *a): raise RuntimeError("boom")
        def rewrite_query(self, *a): raise RuntimeError("boom")

    s = run(WorkflowNodes(retriever, llm=BrokenLLM()), "Disk full on build server",
            "No space left on device, 40 developers cannot run pipelines")
    assert s["llm_used"] is False and s["resolution"] and s["category"] == "infrastructure"


def test_llm_cannot_downgrade_hard_critical(retriever):
    class SoftLLM:
        def triage(self, t, d):
            return {"category": "security", "severity": "low", "summary": "meh", "confidence": 0.9, "rationale": ["x"]}
        def draft(self, *a): return "1. do things [1]"
        def rewrite_query(self, *a): return "q"

    s = run(WorkflowNodes(retriever, llm=SoftLLM()), "Ransomware note on file server",
            "Our files are encrypted files and a ransom note appeared")
    assert s["llm_used"] is True and s["severity"] == "critical" and s["route"] == "escalate"


def test_extractive_resolution_without_passages_asks_for_details():
    assert "Escalate" in extractive_resolution([])
