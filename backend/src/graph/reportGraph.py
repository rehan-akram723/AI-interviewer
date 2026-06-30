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


# ── PDF Generator Node ─────────────────────────────────────────────────────────

def pdfGeneratorNode(state: dict) -> dict:
    """
    LangGraph node: PDF generation step.

    Reads state["final_report"] (dict), re-hydrates it into an InterviewReport
    Pydantic model, and calls generatePdf() to produce a PDF at the configured
    output path.

    If final_report is None or status is "error" (set by evaluatorAgent on
    failure), this node skips PDF generation and returns immediately with
    pdf_path=None so the graph can still terminate cleanly.

    Returns:
        Partial state update:
        {
            "pdf_path": str | None,   — absolute path to the generated PDF
            "step_log": list          — appended
        }
    """
    stepLog = list(state.get("step_log", []))
    sessionId: str = state.get("session_id", "unknown")
    sessionStatus: str = state.get("status", "")
    finalReportDict: dict | None = state.get("final_report")

    # ── Skip if upstream failed ────────────────────────────────────────────────
    if sessionStatus == "error" or finalReportDict is None:
        logger.warning(
            "pdfGeneratorNode: Skipping PDF generation for session '%s' "
            "(status='%s', final_report=%s).",
            sessionId,
            sessionStatus,
            "None" if finalReportDict is None else "present",
        )
        stepLog.append(
            "[pdfGeneratorNode] Skipped — no report available or upstream error."
        )
        return {"pdf_path": None, "step_log": stepLog}

    # ── Re-hydrate the report dict into a Pydantic model ──────────────────────
    try:
        report = InterviewReport(**finalReportDict)
    except Exception as exc:
        logger.error(
            "pdfGeneratorNode: Failed to parse InterviewReport for session '%s': %s",
            sessionId,
            exc,
        )
        stepLog.append(f"[pdfGeneratorNode] Report parse error: {exc}")
        return {"pdf_path": None, "step_log": stepLog}

    # ── Build output path ──────────────────────────────────────────────────────
    pdfDir = settings.pdf_output_path
    pdfPath = os.path.join(pdfDir, f"{sessionId}.pdf")

    # ── Generate PDF ───────────────────────────────────────────────────────────
    try:
        from src.modules.reporting.pdfGenerator import generatePdf

        absPath = generatePdf(report=report, outputPath=pdfPath)
        stepLog.append(f"[pdfGeneratorNode] PDF generated at '{absPath}'.")
        logger.info(
            "pdfGeneratorNode: PDF written to '%s' for session '%s'.",
            absPath,
            sessionId,
        )
        return {"pdf_path": absPath, "step_log": stepLog}

    except Exception as exc:
        # PDF failure is non-fatal — the JSON report is already persisted.
        # Log the error and return pdf_path=None; the API route can expose
        # an appropriate message to the frontend.
        logger.error(
            "pdfGeneratorNode: PDF generation failed for session '%s': %s",
            sessionId,
            exc,
        )
        stepLog.append(f"[pdfGeneratorNode] PDF generation failed: {exc}")
        return {"pdf_path": None, "step_log": stepLog}


# ── Graph Builder ──────────────────────────────────────────────────────────────

def _buildReportGraph() -> StateGraph:
    """
    Construct and compile the report generation StateGraph.

    Graph topology:
        START → evaluatorAgent → pdfGeneratorNode → END

    All edges are unconditional — each node runs in sequence.
    Error handling is done inside each node (they set status="error" and
    return safe partial state updates; the graph always reaches END).
    """
    graph = StateGraph(InterviewSession)

    # ── Add nodes ──────────────────────────────────────────────────────────────
    graph.add_node("evaluatorAgent", evaluatorAgent)
    graph.add_node("pdfGeneratorNode", pdfGeneratorNode)

    # ── Linear edge chain ──────────────────────────────────────────────────────
    graph.set_entry_point("evaluatorAgent")
    graph.add_edge("evaluatorAgent", "pdfGeneratorNode")
    graph.add_edge("pdfGeneratorNode", END)

    return graph.compile()


# Compile on import — singleton graph object
reportGraph = _buildReportGraph()
