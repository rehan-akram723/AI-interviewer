# ─────────────────────────────────────────────────────────────────────────────
# backend/src/api/routes/report.py
#
# Report Routes — JSON report retrieval and PDF streaming download
#
# Endpoints:
#   GET /api/sessions/{sessionId}/report        — fetch InterviewReport JSON
#   GET /api/sessions/{sessionId}/report/pdf    — stream the PDF binary
#   POST /api/sessions/{sessionId}/report/generate — trigger report generation
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
import os

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.core.exceptions import (
    ReportNotFoundError,
    SessionNotFoundError,
    SessionNotReadyError,
    PdfGenerationError,
)
from src.modules.interviewEngine.sessionManager import sessionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Report"])


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _resolveSession(sessionId: str) -> dict:
    session = sessionManager.getSession(sessionId)
    if session is None:
        session = await sessionManager.loadSessionAsync(sessionId)
    if session is None:
        raise SessionNotFoundError(sessionId=sessionId)
    return session


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/sessions/{sessionId}/report")
async def getReport(sessionId: str) -> JSONResponse:
    """
    Retrieve the completed InterviewReport JSON for a session.

    The report is available once the session status is "completed" and the
    evaluatorAgent has run (final_report is populated in session state).

    Returns:
        200 with full InterviewReport dict.
        404 if session or report not found.
        409 if the session has not completed yet.
    """
    session = await _resolveSession(sessionId)
    sessionStatus = session.get("status", "")

    if sessionStatus != "completed":
        raise SessionNotReadyError(sessionId=sessionId, currentStatus=sessionStatus)

    # Check in-memory session first
    finalReport = session.get("final_report")

    # Fall back to report file on disk
    if finalReport is None:
        finalReport = sessionManager.loadReport(sessionId)

    if finalReport is None:
        raise ReportNotFoundError(sessionId=sessionId)

    logger.info("Report retrieved for session %s", sessionId)
    return JSONResponse(content=finalReport)



@router.post("/sessions/{sessionId}/report/generate", status_code=status.HTTP_202_ACCEPTED)
async def generateReport(sessionId: str) -> JSONResponse:
    """
    Trigger report generation for a completed session.

    This endpoint is called after the interview is marked "completed" to
    run the reportGraph (evaluatorAgent → pdfGeneratorNode) asynchronously.

    Returns:
        202 Accepted immediately; the client polls GET /report for the result.
    """
    session = await _resolveSession(sessionId)
    sessionStatus = session.get("status", "")

    if sessionStatus not in ("completed", "in_progress"):
        raise SessionNotReadyError(sessionId=sessionId, currentStatus=sessionStatus)

    if session.get("final_report") is not None:
        # Report already exists — return immediately
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "session_id": sessionId,
                "status": "completed",
                "message": "Report already generated.",
            },
        )

    asyncio.create_task(_runReportGraph(sessionId=sessionId, session=session))

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "session_id": sessionId,
            "status": "generating",
            "message": "Report generation started. Poll GET /report for results.",
        },
    )


async def _runReportGraph(sessionId: str, session: dict) -> None:
    """Background worker: runs the reportGraph and persists the result."""
    from src.graph.reportGraph import reportGraph

    loop = asyncio.get_event_loop()
    try:
        logger.info("Report graph starting for session %s", sessionId)
        result: dict = await loop.run_in_executor(
            None,
            lambda: reportGraph.invoke(session),
        )
        sessionManager.updateSession(sessionId, result)
        updatedSession = sessionManager.getSession(sessionId)
        await sessionManager.saveSessionAsync(updatedSession)
        logger.info("Report graph complete for session %s", sessionId)

    except Exception as exc:
        logger.error("Report graph failed for session %s: %s", sessionId, exc, exc_info=True)
        try:
            sessionManager.setSessionStatus(
                sessionId, "error", error=f"Report generation failed: {exc}"
            )
            failedSession = sessionManager.getSession(sessionId)
            if failedSession:
                await sessionManager.saveSessionAsync(failedSession)
        except Exception:
            pass
