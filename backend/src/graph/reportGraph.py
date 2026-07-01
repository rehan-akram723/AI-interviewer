# ─────────────────────────────────────────────────────────────────────────────
# backend/src/graph/reportGraph.py
#
# Report Graph — LangGraph state machine for the report generation phase
#
# This graph runs ONCE per session, after the interview phase is complete
# (conductorAgent has set status="completed"). It transforms the fully
# populated InterviewSession state into a persisted InterviewReport and
# an optional PDF file.
#
# Node chain:
#   evaluatorAgent → pdfGeneratorNode → [END]
#
# Both edges are unconditional. Each node either succeeds or sets
# status="error" — no conditional branching needed at the graph level.
# The API route inspects state["status"] after invocation to detect failures.
#
# Node responsibilities:
#   evaluatorAgent:   Runs calculateAllScores() + buildReport() → writes
#                     final_report to state and persists JSON to disk.
#   pdfGeneratorNode: Reads final_report from state, calls generatePdf(),
#                     writes pdf_path back to state.
#
# Usage (from API route):
#   from src.graph.reportGraph import reportGraph
#   result = await reportGraph.ainvoke(completed_session_state)
#   pdf_path = result["pdf_path"]
#
# Exports: reportGraph (compiled StateGraph), pdfGeneratorNode
# ─────────────────────────────────────────────────────────────────────────────

import logging
import os

from langgraph.graph import StateGraph, END

from src.graph.sessionState import InterviewSession
from src.agents.evaluatorAgent import evaluatorAgent
from src.core.appConfig import settings
from src.schemas.reportSchema import InterviewReport

logger = logging.getLogger(__name__)



# ── Graph Builder ──────────────────────────────────────────────────────────────

def _buildReportGraph() -> StateGraph:
    """
    Construct and compile the report generation StateGraph.

    Graph topology:
        START → evaluatorAgent → END

    All edges are unconditional — each node runs in sequence.
    Error handling is done inside each node (they set status="error" and
    return safe partial state updates; the graph always reaches END).
    """
    graph = StateGraph(InterviewSession)

    # ── Add nodes ──────────────────────────────────────────────────────────────
    graph.add_node("evaluatorAgent", evaluatorAgent)

    # ── Linear edge chain ──────────────────────────────────────────────────────
    graph.set_entry_point("evaluatorAgent")
    graph.add_edge("evaluatorAgent", END)

    return graph.compile()


# Compile on import — singleton graph object
reportGraph = _buildReportGraph()
