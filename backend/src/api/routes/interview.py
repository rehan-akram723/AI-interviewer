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

from fastapi import APIRouter, status, BackgroundTasks
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
from src.modules.analysis.sttService import transcribe
from src.graph.interviewGraph import interviewGraph
from src.agents.conductorAgent import conductorAgent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Interview"])

class WsManager:
    async def send(self, session_id: str, payload: dict):
        from src.api.websockets.interviewWs import pushToClientSync
        pushToClientSync(session_id, payload)

ws_manager = WsManager()


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
async def getCurrentQuestion(sessionId: str, background_tasks: BackgroundTasks) -> JSONResponse:
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
async def submitAnswer(sessionId: str, payload: AnswerSubmission, background_tasks: BackgroundTasks) -> JSONResponse:
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

    # ── Decode audio bytes early so both STT and audio analysis share them ────
    audioBytes: Optional[bytes] = None
    if payload.audioBase64:
        import base64 as _base64
        try:
            audioBytes = _base64.b64decode(payload.audioBase64)
        except Exception:
            logger.warning("submitAnswer: could not decode audioBase64 for session %s", sessionId)

    loop = asyncio.get_event_loop()

    # ── Transcribe audio → text (Whisper in production, passthrough in demo) ──
    # This is the critical step: without it, voice answers are stored as ""
    # and every downstream agent receives an empty answer.
    transcribedText = await loop.run_in_executor(
        None,
        lambda: transcribe(audioBytes=audioBytes, textInput=payload.text),
    )
    logger.info(
        "submitAnswer: transcription for session %s: '%s...'",
        sessionId, transcribedText[:60],
    )

    answerDict = {
        "question_index": payload.questionIndex,
        "text": transcribedText,
        "audio_path": None,
        "answered_at": now,
        "duration_seconds": payload.durationSeconds,
    }

    # Append answer to session state so the graph nodes see it
    currentAnswers = list(session.get("answers", []))
    currentAnswers.append(answerDict)
    currentTranscript = list(session.get("transcript", []))
    currentTranscript.append(transcribedText)

    sessionManager.updateSession(sessionId, {
        "answers": currentAnswers,
        "transcript": currentTranscript,
    })
    session = sessionManager.getSession(sessionId)

    # ── Audio analysis (reuses already-decoded audioBytes from above) ─────────
    audioMetrics = await loop.run_in_executor(
        None,
        lambda: analyzeAudio(
            audioBytes=audioBytes,
            transcript=transcribedText,
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

    # ── Dispatch Background Pipeline ──────────────────────────────────────────
    background_tasks.add_task(run_full_pipeline, session, sessionId)

    logger.info(
        "submitAnswer: HTTP response dispatched immediately | session=%s | answer_index=%d",
        sessionId, answerIndex,
    )

    return JSONResponse(content={
        "session_id": sessionId,
        "status": "processing",
        "is_complete": False,
        "coaching_feedback": None,
        "coaching_pending": True,
        "next_question": None,
        "audio_metrics": audioMetricsDict,
    })

async def run_full_pipeline(state: dict, session_id: str):
    from src.agents.liveCoachAgent import liveCoachAgent
    from src.agents.difficultyCalibratorAgent import difficultyCalibratorAgent
    from src.agents.followUpAgent import followUpAgent
    from src.agents.conductorAgent import conductorAgent
    from src.api.websockets.interviewWs import pushToClientSync
    loop = asyncio.get_event_loop()
    try:
        # 1. Coaching and Calibration (Concurrent)
        coach_res, calib_res = await asyncio.gather(
            loop.run_in_executor(None, liveCoachAgent, state),
            loop.run_in_executor(None, difficultyCalibratorAgent, state)
        )
        
        updates = {}
        if "coaching_feedback" in coach_res:
            updates["coaching_feedback"] = coach_res["coaching_feedback"]
        if "difficulty_level" in calib_res:
            updates["difficulty_level"] = calib_res["difficulty_level"]
        if "difficulty_dimensions" in calib_res:
            updates["difficulty_dimensions"] = calib_res["difficulty_dimensions"]
            
        updated_session = sessionManager.updateSession(session_id, updates)
        
        # 2. Follow-Up Agent
        followup_res = await loop.run_in_executor(None, lambda: followUpAgent(updated_session))
        updated_session = sessionManager.updateSession(session_id, followup_res)
        next_question = followup_res.get("next_question")
        
        # 3. Conductor Agent (if no follow-up was generated)
        if not next_question:
            conductor_res = await loop.run_in_executor(None, lambda: conductorAgent(updated_session))
            updated_session = sessionManager.updateSession(session_id, conductor_res)
            next_question = conductor_res.get("next_question")

        await sessionManager.saveSessionAsync(updated_session)

        # 4. Push Results via WebSocket
        is_complete = updated_session.get("status") == "completed"
        if is_complete or not next_question:
            pushToClientSync(session_id, {"type": "interview_complete", "payload": {}})
        else:
            pushToClientSync(session_id, {"type": "next_question", "payload": next_question})
            
    except Exception as exc:
        logger.error("Background pipeline failed: %s", exc, exc_info=True)
        try:
            pushToClientSync(session_id, {"type": "error", "payload": {"message": str(exc)}})
        except Exception:
            pass

