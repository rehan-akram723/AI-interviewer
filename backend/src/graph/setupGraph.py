# ─────────────────────────────────────────────────────────────────────────────
# backend/src/graph/setupGraph.py
#
# Setup Graph — LangGraph state machine for the interview setup phase
#
# This graph runs ONCE per interview session, before the interview begins.
# It transforms raw input (CV bytes, JD text, motivation text) into a fully
# prepared session state with a ready question_plan.
#
# Node chain:
#   cvParserAgent → companyResearchAgent → interviewPlannerAgent → [END]
#
# Each node is a pure function: (state: dict) → partial dict.
# LangGraph merges each partial dict back into the full state automatically.
#
# Completion signal:
#   After interviewPlannerAgent runs, the session status is set to "ready"
#   by the API route that invokes this graph.
#
# Usage (from API route):
#   from src.graph.setupGraph import setupGraph
#   result = await setupGraph.ainvoke(initial_session_state)
#
# Exports: setupGraph (compiled StateGraph)
# ─────────────────────────────────────────────────────────────────────────────

from langgraph.graph import StateGraph, END

from src.graph.sessionState import InterviewSession
from src.agents.cvParserAgent import cvParserAgent
from src.agents.companyResearchAgent import companyResearchAgent
from src.agents.interviewPlannerAgent import interviewPlannerAgent


def _buildSetupGraph() -> StateGraph:
    """
    Construct and compile the setup phase StateGraph.

    Graph topology:
        START → cvParserAgent → companyResearchAgent → interviewPlannerAgent → END

    All edges are unconditional — each agent always runs in sequence.
    Error handling is done inside each agent node (they return status="error").
    """
    graph = StateGraph(InterviewSession)

    # ── Add nodes ──────────────────────────────────────────────────────────────
    graph.add_node("cvParserAgent", cvParserAgent)
    graph.add_node("companyResearchAgent", companyResearchAgent)
    graph.add_node("interviewPlannerAgent", interviewPlannerAgent)

    # ── Define linear edge chain ───────────────────────────────────────────────
    graph.set_entry_point("cvParserAgent")
    graph.add_edge("cvParserAgent", "companyResearchAgent")
    graph.add_edge("companyResearchAgent", "interviewPlannerAgent")
    graph.add_edge("interviewPlannerAgent", END)

    return graph.compile()


# Compile on import — singleton graph object
setupGraph = _buildSetupGraph()
