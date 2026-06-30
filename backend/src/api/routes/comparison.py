# ─────────────────────────────────────────────────────────────────────────────
# backend/src/api/routes/comparison.py
#
# Comparison Route — GET /api/comparison
#
# Generates a ProgressComparison between two completed InterviewReports.
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, status, Query
from fastapi.responses import JSONResponse

from src.core.exceptions import ReportNotFoundError, AppBaseException
from src.modules.interviewEngine.sessionManager import sessionManager
from src.schemas.reportSchema import InterviewReport
from src.modules.reporting.comparisonBuilder import buildComparison

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Comparison"])


@router.get("/comparison")
async def getComparison(
    previousSessionId: str = Query(..., description="ID of the older session."),
    currentSessionId: str = Query(..., description="ID of the newer session."),
) -> JSONResponse:
    """
    Generate and retrieve a ProgressComparison between two completed sessions.

    Reads the final reports for both sessions, then synchronously invokes
    buildComparison (which calls an LLM to write the comparison narrative)
    in a background thread pool.

    Returns:
        200 with ProgressComparison JSON dict.
        404 if either report is missing.
    """
    # 1. Load reports
    prevReportDict = sessionManager.loadReport(previousSessionId)
    currReportDict = sessionManager.loadReport(currentSessionId)

    if prevReportDict is None:
        raise ReportNotFoundError(sessionId=previousSessionId)
    if currReportDict is None:
        raise ReportNotFoundError(sessionId=currentSessionId)

    # 2. Parse into Pydantic models
    try:
        prevReport = InterviewReport(**prevReportDict)
        currReport = InterviewReport(**currReportDict)
    except Exception as exc:
        logger.error("Failed to parse report schemas for comparison: %s", exc)
        raise AppBaseException(
            message=f"Failed to parse report schemas: {exc}",
            errorCode="REPORT_PARSE_ERROR",
            statusCode=500,
        )

    # 3. Generate comparison in thread pool (LLM call)
    loop = asyncio.get_event_loop()
    try:
        comparison = await loop.run_in_executor(
            None,
            lambda: buildComparison(previousReport=prevReport, currentReport=currReport),
        )
    except Exception as exc:
        logger.error("Failed to generate progress comparison: %s", exc, exc_info=True)
        raise AppBaseException(
            message=f"Failed to generate progress comparison: {exc}",
            errorCode="COMPARISON_FAILED",
            statusCode=500,
        )

    logger.info(
        "Progress comparison generated for %s vs %s",
        previousSessionId, currentSessionId,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=comparison.model_dump())
