# ─────────────────────────────────────────────────────────────────────────────
# backend/src/api/routes/candidates.py
#
# Candidates Route — GET /api/candidates/{candidateId}
#
# Retrieves a CandidateProfile containing historical session metrics and
# extracted skills. Used by the frontend dashboard.
# ─────────────────────────────────────────────────────────────────────────────

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.core.exceptions import CandidateNotFoundError
from src.modules.interviewEngine.sessionManager import sessionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Candidates"])


@router.get("/candidates/{candidateId}")
async def getCandidateProfile(candidateId: str) -> JSONResponse:
    """
    Retrieve the full CandidateProfile for a given candidate ID.

    Includes extracted skills, experience, and a list of historical
    session IDs (session_ids) that belong to this candidate.

    Returns:
        200 with CandidateProfile JSON dict.
        404 if the candidate profile does not exist.
    """
    candidateData = await sessionManager.loadCandidateAsync(candidateId)
    if candidateData is None:
        raise CandidateNotFoundError(candidateId=candidateId)

    logger.info("Retrieved profile for candidate %s", candidateId)
    return JSONResponse(status_code=status.HTTP_200_OK, content=candidateData)
