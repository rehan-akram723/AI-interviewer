# ─────────────────────────────────────────────────────────────────────────────
# backend/src/agents/evaluatorAgent.py
#
# Evaluator Agent — LangGraph node function
#
# Responsibilities:
#   1. Guard: verify the session has enough data to evaluate (at least 1 answer).
#   2. Run calculateAllScores() to produce DimensionScore objects for all 6 dimensions.
#   3. Call buildReport() to assemble the full InterviewReport with LLM-generated
#      narrative sections (executive summary, strengths, areas for improvement).
#   4. Persist the InterviewReport as JSON to data/reports/{session_id}.json.
#   5. Write final_report (as dict), set status to "completed", and append to step_log.
#
# This is the terminal node of the report graph. It runs after the interview
# is complete (conductorAgent has set status="completed" and next_question=None).
#
# LangGraph contract:
#   Input:  Full InterviewSession state dict (status must be "completed")
#   Output: Partial dict:
#           {
#               "final_report":  dict           (InterviewReport serialised)
#               "status":        "completed"    (unchanged — already set)
#               "step_log":      list           (appended)
#           }
#
# Exports: evaluatorAgent
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
import os
from datetime import datetime, timezone

from src.core.appConfig import settings
from src.modules.reporting.scoreCalculator import calculateAllScores
from src.modules.reporting.reportBuilder import buildReport

logger = logging.getLogger(__name__)


def evaluatorAgent(state: dict) -> dict:
    """
    LangGraph node: Evaluator Agent — final scoring and report assembly.

    This node is the first step of the report graph. It runs once, after
    the interview phase is confirmed complete. It calls into the reporting
    module pipeline and writes the structured report back to state.

    Args:
        state: Full InterviewSession dict. Expected to have:
               - status == "completed"
               - at least one Answer in state["answers"]
               - at least one Question in state["asked_questions"]

    Returns:
        Partial state update dict containing final_report and updated step_log.
    """
    stepLog = list(state.get("step_log", []))
    sessionId: str = state.get("session_id", "unknown")
    answersCount: int = len(state.get("answers", []))

    # ── Guard: minimum data check ──────────────────────────────────────────────
    if answersCount == 0:
        logger.warning("evaluatorAgent: No answers found in session '%s'.", sessionId)
        stepLog.append(
            "[evaluatorAgent] ERROR: No answers recorded — cannot generate report."
        )
        return {
            "final_report": None,
            "status": "error",
            "error": "evaluatorAgent: Cannot generate report with zero answers.",
            "step_log": stepLog,
        }

    stepLog.append(
        f"[evaluatorAgent] Starting evaluation for session '{sessionId}' | "
        f"{answersCount} answers | "
        f"{len(state.get('asked_questions', []))} questions."
    )
    logger.info(
        "evaluatorAgent: Evaluating session '%s' with %d answers.",
        sessionId,
        answersCount,
    )

    # ── Step 1: Calculate all 6 dimension scores ───────────────────────────────
    try:
        dimensionScores = calculateAllScores(state)
        stepLog.append(
            f"[evaluatorAgent] Dimension scores calculated: "
            f"{ {k: round(v.score, 1) for k, v in dimensionScores.items()} }"
        )
    except Exception as exc:
        logger.error(
            "evaluatorAgent: Score calculation failed for session '%s': %s",
            sessionId,
            exc,
        )
        stepLog.append(f"[evaluatorAgent] Score calculation error: {exc}")
        return {
            "final_report": None,
            "status": "error",
            "error": f"evaluatorAgent: Score calculation failed — {exc}",
            "step_log": stepLog,
        }

    # ── Step 2: Build the full InterviewReport ─────────────────────────────────
    try:
        report = buildReport(state, dimensionScores)
        stepLog.append(
            f"[evaluatorAgent] Report built | overall_score={report.overall_score:.1f}/10.0."
        )
    except Exception as exc:
        logger.error(
            "evaluatorAgent: Report assembly failed for session '%s': %s",
            sessionId,
            exc,
        )
        stepLog.append(f"[evaluatorAgent] Report build error: {exc}")
        return {
            "final_report": None,
            "status": "error",
            "error": f"evaluatorAgent: Report assembly failed — {exc}",
            "step_log": stepLog,
        }

    # ── Step 3: Persist report JSON to disk ────────────────────────────────────
    reportDict = report.model_dump(by_alias=True)
    _persistReportJson(sessionId, reportDict, stepLog)

    stepLog.append(
        f"[evaluatorAgent] Session '{sessionId}' evaluation complete."
    )
    logger.info(
        "evaluatorAgent: Evaluation complete for session '%s' | score=%.1f",
        sessionId,
        report.overall_score,
    )

    return {
        "final_report": reportDict,
        "status": "completed",
        "step_log": stepLog,
    }


# ── Disk Persistence Helper ────────────────────────────────────────────────────

def _persistReportJson(sessionId: str, reportDict: dict, stepLog: list) -> None:
    """
    Write the serialised InterviewReport dict to disk as JSON.

    Path: {settings.report_storage_path}/{session_id}.json

    Errors are logged and appended to stepLog but do NOT raise — a persistence
    failure should not prevent the report from being returned in state. The API
    route can re-attempt persistence if needed.

    Args:
        sessionId:  The session UUID (used as the filename stem).
        reportDict: The report serialised as a plain dict (model_dump() output).
        stepLog:    Mutable list — persistence status is appended here.
    """
    try:
        reportDir = settings.report_storage_path
        os.makedirs(reportDir, exist_ok=True)
        reportPath = os.path.join(reportDir, f"{sessionId}.json")

        with open(reportPath, "w", encoding="utf-8") as fh:
            json.dump(reportDict, fh, indent=2, ensure_ascii=False)

        stepLog.append(f"[evaluatorAgent] Report persisted to '{reportPath}'.")
        logger.debug("evaluatorAgent: Report JSON written to '%s'.", reportPath)

    except OSError as exc:
        stepLog.append(
            f"[evaluatorAgent] WARNING: Could not persist report to disk — {exc}."
        )
        logger.warning(
            "evaluatorAgent: Disk persistence failed for session '%s': %s",
            sessionId,
            exc,
        )
