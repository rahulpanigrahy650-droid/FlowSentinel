"""LangGraph wiring for the incident-resolution workflow.

        START -> triage -> retrieve -> grade --(weak, first try)--> retrieve
                                          \\--(ok / retried)--> draft_resolution -> decide_route -> END
"""
from langgraph.graph import END, START, StateGraph

from .nodes import WorkflowNodes
from .state import WorkflowState


def build_graph(nodes: WorkflowNodes):
    g = StateGraph(WorkflowState)
    g.add_node("triage", nodes.triage)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("grade", nodes.grade)
    g.add_node("draft_resolution", nodes.draft_resolution)
    g.add_node("decide_route", nodes.decide_route)

    g.add_edge(START, "triage")
    g.add_edge("triage", "retrieve")
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", nodes.route_after_grade,
                            {"retrieve": "retrieve", "draft_resolution": "draft_resolution"})
    g.add_edge("draft_resolution", "decide_route")
    g.add_edge("decide_route", END)
    return g.compile()
