import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi import BackgroundTasks

from src.modules.interviewEngine.sessionManager import sessionManager
from src.api.routes.interview import submitAnswer, getCurrentQuestion, AnswerSubmission

@pytest.fixture
def mock_session():
    session_id = "test-session-123"
    session = sessionManager.createSession(
        candidateId="cand-123",
        interviewLength="short",
        interviewMode="mixed"
    )
    # The createSession uses a random uuid, let's override it
    real_session_id = session["session_id"]
    sessionManager.setSessionStatus(real_session_id, "ready")
    session["question_plan"] = ["Q1", "Q2"]
    session["current_question_index"] = 0
    return real_session_id

@pytest.mark.asyncio
async def test_answer_endpoint_returns_before_coaching_completes(mock_session):
    with patch("src.agents.followUpAgent.followUpAgent") as mock_followup:
        mock_followup.return_value = {
            "next_question": {"text": "Followup?", "index": 1}
        }
        
        payload = AnswerSubmission(
            questionIndex=0,
            text="Here is my answer",
            durationSeconds=5.0
        )
        
        background_tasks = BackgroundTasks()
        
        with patch("src.api.routes.interview.analyzeAudio") as mock_audio, \
             patch("src.api.routes.interview.processFacialData") as mock_facial:
            
            mock_audio.return_value = MagicMock()
            mock_audio.return_value.model_dump.return_value = {"mock": "audio"}
            
            mock_facial.return_value = MagicMock()
            mock_facial.return_value.model_dump.return_value = {"mock": "facial"}
            
            response = await submitAnswer(mock_session, payload, background_tasks)
            
        data = json.loads(response.body.decode())
        
        assert data.get("coaching_pending") is True
        assert data.get("coaching_feedback") is None
        assert data.get("next_question") is not None
        assert len(background_tasks.tasks) > 0

@pytest.mark.asyncio
async def test_question_endpoint_serves_prefetched_when_available(mock_session):
    prefetched_question = {"text": "Prefetched Q", "index": 1}
    sessionManager.store_prefetched_question(mock_session, {"next_question": prefetched_question})
    
    background_tasks = BackgroundTasks()
    
    with patch("src.agents.conductorAgent.conductorAgent") as mock_conductor:
        response = await getCurrentQuestion(mock_session, background_tasks)
        
        mock_conductor.assert_not_called()
        
    data = json.loads(response.body.decode())
    
    assert data["question"]["text"] == "Prefetched Q"
    assert len(background_tasks.tasks) > 0
