# ─────────────────────────────────────────────────────────────────────────────
# backend/src/api/routes/interview.py
#
# Interview Routes — question delivery and answer submission
#
# Endpoints:
#   GET  /api/sessions/{sessionId}/question  — return the current question
#   POST /api/sessions/{sessionId}/answer    — submit an answer, run one turn
#
# One-turn pipeline (POST /answer):
#   1. Load session, validate it is "ready" or "in_progress".
#   2. Persist the incoming Answer to state.
#   3. Run audio analysis (analyzeAudio) + facial analysis (processFacialData).
#   4. Append metrics to state.
#   5. Run the interview graph (liveCoachAgent → calibrator → followUpAgent →
#      optionally conductorAgent) in a thread pool.
#   6. Merge result back into memory, persist session, return response.
#
# WebSocket coaching frames are pushed from inside the graph nodes themselves
# via the connection registry maintained in interviewWs.py.
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.exceptions import (
    SessionNotFoundError,
    SessionNotReadyError,
    SessionAlreadyCompletedError,
)
from src.modules.interviewEngine.sessionManager import sessionManager
from src.modules.analysis.audioAnalyzer import analyzeAudio
from src.modules.analysis.facialPlaceholder import processFacialData
from src.graph.interviewGraph import interviewGraph
from src.agents.conductorAgent import conductorAgent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Interview"])


# ── Request / Response Models ──────────────────────────────────────────────────

class AnswerSubmission(BaseModel):
    """
    Payload for POST /api/sessions/{sessionId}/answer.

    In demo mode: text is required, audioBase64 and facialData are ignored.
    In production: audioBase64 carries the base64-encoded audio chunk.
    """
    questionIndex: int
    text: str = ""
    audioBase64: Optional[str] = None
    facialData: Optional[dict] = None
    durationSeconds: Optional[float] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _resolveSession(sessionId: str) -> dict:
    """
    Load a session from memory (preferred) or disk.
    Raises SessionNotFoundError if neither source has the session.
    """
    session = sessionManager.getSession(sessionId)
    if session is None:
        session = await sessionManager.loadSessionAsync(sessionId)
    if session is None:
        raise SessionNotFoundError(sessionId=sessionId)
    return session


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/sessions/{sessionId}/question")
async def getCurrentQuestion(sessionId: str) -> JSONResponse:
    """
    Return the current question for an in-progress session.

    If no question has been delivered yet (first turn), runs the conductorAgent
    synchronously to pull the first planned question.

    Returns:
        { question: Question dict, session_id, status }
    """
    session = await _resolveSession(sessionId)
    sessionStatus = session.get("status", "")

    if sessionStatus == "completed":
        return JSONResponse(content={
            "session_id": sessionId,
            "status": "completed",
            "question": None,
            "message": "Interview is complete. Retrieve your report.",
        })

    if sessionStatus in ("setting_up", "error"):
        raise SessionNotReadyError(sessionId=sessionId, currentStatus=sessionStatus)

    # Check if there is already a delivered question waiting for an answer
    askedQuestions = session.get("asked_questions", [])
    answers = session.get("answers", [])

    # If more questions have been asked than answers given, serve the unanswered one
    if len(askedQuestions) > len(answers):
        currentQ = askedQuestions[len(answers)]
        return JSONResponse(content={
            "session_id": sessionId,
            "status": sessionStatus,
            "question": currentQ,
        })

    # No pending question — run conductorAgent to deliver the next one
    loop = asyncio.get_event_loop()
    try:
        updatedFields: dict = await loop.run_in_executor(
            None,
            lambda: conductorAgent(session),
        )
        sessionManager.updateSession(sessionId, updatedFields)
        updatedSession = sessionManager.getSession(sessionId)
        await sessionManager.saveSessionAsync(updatedSession)

        nextQuestion = updatedFields.get("next_question")
        newStatus = updatedFields.get("status", sessionStatus)

        if newStatus == "completed" or nextQuestion is None:
            return JSONResponse(content={
                "session_id": sessionId,
                "status": "completed",
                "question": None,
                "message": "Interview is complete.",
            })

        return JSONResponse(content={
            "session_id": sessionId,
            "status": "in_progress",
            "question": nextQuestion,
        })

    except Exception as exc:
        logger.error(
            "getCurrentQuestion: conductorAgent failed for session %s: %s",
            sessionId, exc, exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "CONDUCTOR_FAILED", "message": str(exc)},
        )


@router.post("/sessions/{sessionId}/answer", status_code=status.HTTP_200_OK)
async def submitAnswer(sessionId: str, payload: AnswerSubmission) -> JSONResponse:
    """
    Submit a candidate's answer and run one full evaluation turn.

    Processing pipeline:
        1. Validate session state.
        2. Build Answer dict and append to state.
        3. Run audio + facial analysis.
        4. Run the full interview graph turn (coach → calibrator → followup → conductor).
        5. Persist updated session.
        6. Return coaching feedback and next question.

    Returns:
        {
            session_id, status, coaching_feedback, next_question,
            audio_metrics, is_complete
        }
    """
    session = await _resolveSession(sessionId)
    sessionStatus = session.get("status", "")

    # ── State guards ───────────────────────────────────────────────────────────
    if sessionStatus == "completed":
        raise SessionAlreadyCompletedError(sessionId=sessionId)
    if sessionStatus in ("setting_up", "error"):
        raise SessionNotReadyError(sessionId=sessionId, currentStatus=sessionStatus)

    # Transition to in_progress on first answer
    if sessionStatus == "ready":
        sessionManager.setSessionStatus(sessionId, "in_progress")
        session["status"] = "in_progress"

    # ── Build Answer object ────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    answerIndex = len(session.get("answers", []))

    answerDict = {
        "question_index": payload.questionIndex,
        "text": payload.text.strip(),
        "audio_path": None,
        "answered_at": now,
        "duration_seconds": payload.durationSeconds,
    }

    # Append answer to session state so the graph nodes see it
    currentAnswers = list(session.get("answers", []))
    currentAnswers.append(answerDict)
    currentTranscript = list(session.get("transcript", []))
    currentTranscript.append(payload.text.strip())

    sessionManager.updateSession(sessionId, {
        "answers": currentAnswers,
        "transcript": currentTranscript,
    })
    session = sessionManager.getSession(sessionId)

    # ── Audio analysis ─────────────────────────────────────────────────────────
    audioBytes: Optional[bytes] = None
    if payload.audioBase64:
        import base64
        try:
            audioBytes = base64.b64decode(payload.audioBase64)
        except Exception:
            logger.warning("submitAnswer: could not decode audioBase64 for session %s", sessionId)

    loop = asyncio.get_event_loop()
    audioMetrics = await loop.run_in_executor(
        None,
        lambda: analyzeAudio(
            audioBytes=audioBytes,
            transcript=payload.text,
            answerIndex=answerIndex,
        ),
    )
    audioMetricsDict = audioMetrics.model_dump()

    # ── Facial analysis ────────────────────────────────────────────────────────
    facialMetrics = await loop.run_in_executor(
        None,
        lambda: processFacialData(
            mediapipeJson=payload.facialData,
            answerIndex=answerIndex,
            durationSeconds=payload.durationSeconds,
        ),
    )

    # Append audio metrics and update facial summary in state
    currentAudioMetrics = list(session.get("audio_metrics_per_answer", []))
    currentAudioMetrics.append(audioMetricsDict)
    sessionManager.updateSession(sessionId, {
        "audio_metrics_per_answer": currentAudioMetrics,
        "facial_metrics_summary": facialMetrics.model_dump(),
    })
    session = sessionManager.getSession(sessionId)

    # ── Run interview graph turn ───────────────────────────────────────────────
    try:
        graphResult: dict = await loop.run_in_executor(
            None,
            lambda: interviewGraph.invoke(session),
        )
    except Exception as exc:
        logger.error(
            "submitAnswer: interviewGraph failed for session %s: %s",
            sessionId, exc, exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "GRAPH_FAILED", "message": str(exc)},
        )

    # ── Merge result and persist ───────────────────────────────────────────────
    sessionManager.updateSession(sessionId, graphResult)
    updatedSession = sessionManager.getSession(sessionId)
    await sessionManager.saveSessionAsync(updatedSession)

    # ── Extract coaching feedback for this turn ────────────────────────────────
    allFeedback = updatedSession.get("coaching_feedback", [])
    latestFeedback = allFeedback[-1] if allFeedback else None

    nextQuestion = graphResult.get("next_question")
    isComplete = updatedSession.get("status") == "completed"

    logger.info(
        "submitAnswer: turn complete | session=%s | answer_index=%d | complete=%s",
        sessionId, answerIndex, isComplete,
    )

    return JSONResponse(content={
        "session_id": sessionId,
        "status": updatedSession.get("status"),
        "is_complete": isComplete,
        "coaching_feedback": latestFeedback,
        "next_question": nextQuestion,
        "audio_metrics": audioMetricsDict,
    })
