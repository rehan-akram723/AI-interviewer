# ─────────────────────────────────────────────────────────────────────────────
# backend/src/api/routes/setup.py
#
# Setup Route — POST /api/sessions/setup
#
# Handles the initial document ingestion and session initialisation flow:
#   1. Validate and read the uploaded CV PDF bytes.
#   2. Generate UUIDs for the session and candidate.
#   3. Create the session in-memory via sessionManager.createSession().
#   4. Persist the initial skeleton session and candidate to disk.
#   5. Launch the setup graph (cvParserAgent → companyResearchAgent →
#      interviewPlannerAgent) in a background thread via asyncio.
#   6. Return the session_id and candidate_id immediately (202 Accepted).
#
# The client polls GET /api/sessions/{sessionId}/status to track progress.
#
# Multipart fields (all form fields — no JSON body):
#   cvFile           — PDF file upload (required)
#   jobDescription   — Raw JD text (required)
#   companyName      — Company name string (optional)
#   motivationLetter — Motivation letter text (optional)
#   interviewLength  — "short" | "medium" | "long"  (default: "medium")
#   interviewMode    — "mixed" | "technical" | "behavioral" |
#                      "hr_culture_fit" | "system_design" (default: "mixed")
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from src.core.appConfig import settings
from src.core.exceptions import CvParsingError, InvalidMimeTypeError
from src.modules.interviewEngine.sessionManager import sessionManager
from src.graph.setupGraph import setupGraph

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Setup"])

# ── Allowed MIME types for CV uploads ─────────────────────────────────────────
_ALLOWED_CV_MIMES = {"application/pdf", "application/octet-stream"}
_MAX_CV_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Route ──────────────────────────────────────────────────────────────────────

@router.post("/sessions/setup", status_code=status.HTTP_202_ACCEPTED)
async def setupSession(
    cvFile: UploadFile = File(..., description="Candidate CV — PDF only."),
    jobDescription: str = Form(..., description="Raw job description text."),
    companyName: str = Form("", description="Target company name."),
    motivationLetter: str = Form("", description="Candidate's motivation letter text."),
    interviewLength: str = Form("medium", description="short | medium | long"),
    interviewMode: str = Form("mixed", description="mixed | technical | behavioral | hr_culture_fit | system_design"),
) -> JSONResponse:
    """
    Initialise a new interview session.

    Accepts multipart/form-data with a CV PDF and text fields. Launches the
    setup graph asynchronously and returns immediately with the session and
    candidate identifiers for polling.

    Returns:
        202 Accepted with { session_id, candidate_id, status: "setting_up" }
    """
    # ── 1. MIME type guard ─────────────────────────────────────────────────────
    contentType = cvFile.content_type or ""
    if contentType not in _ALLOWED_CV_MIMES and not contentType.startswith("application/"):
        raise InvalidMimeTypeError(
            receivedMime=contentType,
            allowedMimes=list(_ALLOWED_CV_MIMES),
        )

    # ── 2. Read CV bytes ───────────────────────────────────────────────────────
    cvBytes = await cvFile.read()
    if not cvBytes:
        raise CvParsingError(detail="Uploaded CV file is empty.")

    # ── 3. Generate stable IDs ─────────────────────────────────────────────────
    candidateId = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # ── 4. Create skeleton session in memory ───────────────────────────────────
    sessionManager.ensureDirectories()
    session = sessionManager.createSession(
        candidateId=candidateId,
        interviewLength=interviewLength,
        interviewMode=interviewMode,
        targetCompany=companyName,
    )
    sessionId = session["session_id"]

    # Inject raw inputs as ephemeral fields (prefixed with "_" — stripped on disk write)
    session["_cv_bytes"] = cvBytes
    session["_jd_text"] = jobDescription
    session["_motivation_text"] = motivationLetter

    # Build initial candidate stub and persist it
    candidateStub = {
        "candidate_id": candidateId,
        "full_name": "",
        "email": None,
        "education": [],
        "experience": [],
        "projects": [],
        "confirmed_skills": [],
        "uncertain_skills": [],
        "motivation": "",
        "target_role": "",
        "target_company": companyName,
        "required_skills_from_jd": [],
        "skills_gap": [],
        "session_ids": [sessionId],
        "created_at": now,
    }
    sessionManager.saveCandidate(candidateStub)
    sessionManager.saveSession(session)

    logger.info(
        "Setup initiated | session=%s | candidate=%s | mode=%s | length=%s",
        sessionId, candidateId, interviewMode, interviewLength,
    )

    # ── 5. Launch setup graph in background ────────────────────────────────────
    asyncio.create_task(
        _runSetupGraph(sessionId=sessionId, initialState=session)
    )

    # ── 6. Return immediately ──────────────────────────────────────────────────
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "session_id": sessionId,
            "candidate_id": candidateId,
            "status": "setting_up",
        },
    )


@router.get("/sessions/{sessionId}/status")
async def getSessionStatus(sessionId: str) -> JSONResponse:
    """
    Poll the setup progress for a session.

    Returns the current status, the last step_log entry for the UI progress
    indicator, and the candidate_id.
    """
    from src.core.exceptions import SessionNotFoundError

    # Try memory first, fall back to disk
    session = sessionManager.getSession(sessionId)
    if session is None:
        session = await sessionManager.loadSessionAsync(sessionId)
    if session is None:
        raise SessionNotFoundError(sessionId=sessionId)

    stepLog = session.get("step_log", [])
    lastStep = stepLog[-1] if stepLog else "Initialising…"

    return JSONResponse(content={
        "session_id": sessionId,
        "candidate_id": session.get("candidate_id"),
        "status": session.get("status", "setting_up"),
        "last_step": lastStep,
        "error": session.get("error"),
    })


# ── Background worker ──────────────────────────────────────────────────────────

async def _runSetupGraph(sessionId: str, initialState: dict) -> None:
    """
    Runs the LangGraph setup graph in the event loop.

    The graph is CPU-bound (LLM calls use the synchronous OpenAI client), so we
    run it via asyncio.get_event_loop().run_in_executor() to avoid blocking the
    async event loop entirely. After completion, the updated state is merged back
    into memory and persisted to disk.
    """
    loop = asyncio.get_event_loop()
    try:
        logger.info("Setup graph starting for session %s", sessionId)

        # Run the synchronous graph invocation in a thread pool
        result: dict = await loop.run_in_executor(
            None,
            lambda: setupGraph.invoke(initialState),
        )

        # Merge result into the in-memory session
        sessionManager.updateSession(sessionId, result)
        updatedSession = sessionManager.getSession(sessionId)

        # Mark as ready if setup succeeded
        if updatedSession.get("status") != "error":
            sessionManager.setSessionStatus(sessionId, "ready")

        # Persist candidate profile with parsed data
        candidateData = updatedSession.get("candidate", {})
        if candidateData:
            sessionManager.saveCandidate(candidateData)

        await sessionManager.saveSessionAsync(updatedSession)
        logger.info(
            "Setup graph complete for session %s | status=%s",
            sessionId,
            updatedSession.get("status"),
        )

    except Exception as exc:
        logger.error("Setup graph failed for session %s: %s", sessionId, exc, exc_info=True)
        try:
            sessionManager.setSessionStatus(
                sessionId,
                "error",
                error=f"Setup failed: {exc}",
            )
            failedSession = sessionManager.getSession(sessionId)
            if failedSession:
                await sessionManager.saveSessionAsync(failedSession)
        except Exception as innerExc:
            logger.error(
                "Could not persist error state for session %s: %s",
                sessionId, innerExc,
            )
