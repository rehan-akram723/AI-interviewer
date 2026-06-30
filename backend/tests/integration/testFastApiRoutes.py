# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/integration/testFastApiRoutes.py
#
# Integration tests for FastAPI endpoint schemas and flows.
# ─────────────────────────────────────────────────────────────────────────────

import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.main import app
from src.modules.interviewEngine.sessionManager import sessionManager

client = TestClient(app)


# ════════════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_session_manager(tmp_path):
    """
    Patches the singleton sessionManager to use a temporary directory for tests
    so we don't pollute or read from the real data/ folder.
    """
    original_candidate_dir = sessionManager._candidateDir
    original_session_dir = sessionManager._sessionDir
    original_report_dir = sessionManager._reportDir
    
    sessionManager._candidateDir = tmp_path / "candidates"
    sessionManager._sessionDir = tmp_path / "sessions"
    sessionManager._reportDir = tmp_path / "reports"
    
    sessionManager.ensureDirectories()
    sessionManager._activeSessions.clear()
    
    yield sessionManager
    
    # Teardown
    sessionManager._candidateDir = original_candidate_dir
    sessionManager._sessionDir = original_session_dir
    sessionManager._reportDir = original_report_dir
    sessionManager._activeSessions.clear()


@pytest.fixture
def completed_session(mock_session_manager):
    """Creates a fake completed session and report for testing retrieval."""
    session_id = "test-session-completed-001"
    candidate_id = "test-candidate-001"
    
    session = {
        "session_id": session_id,
        "candidate_id": candidate_id,
        "status": "completed",
        "final_report": {
            "session_id": session_id,
            "candidate_id": candidate_id,
            "interview_mode": "mixed",
            "interview_length": "short",
            "overall_score": 8.5,
            "dimension_scores": {
                "communication": {
                    "score": 8.0,
                    "evidence": [],
                    "rationale": "Clear speech"
                }
            },
            "executive_summary": "Great.",
            "top_strengths": ["Python"],
            "areas_for_improvement": ["Docker"],
            "recommended_next_steps": "Learn Docker."
        },
        "pdf_path": None,
    }
    
    mock_session_manager.saveSession(session)
    mock_session_manager.saveReport(session["final_report"])
    return session_id


# ════════════════════════════════════════════════════════════════════════════════
# Tests
# ════════════════════════════════════════════════════════════════════════════════

@patch("src.api.routes.setup._runSetupGraph")
def test_setup_endpoint_returns_tracking_id(mock_run_setup, mock_session_manager):
    """
    Uploading files to POST /api/sessions/setup must return an initial 
    tracking ID (session_id) and candidate_id with a 202 Accepted.
    """
    files = {
        "cvFile": ("test_cv.pdf", b"fake pdf content", "application/pdf")
    }
    data = {
        "jobDescription": "Looking for a Python developer",
        "companyName": "TestCorp",
        "interviewLength": "short",
        "interviewMode": "technical"
    }
    
    response = client.post("/api/sessions/setup", files=files, data=data)
    
    assert response.status_code == 202
    json_resp = response.json()
    assert "session_id" in json_resp
    assert "candidate_id" in json_resp
    assert json_resp["status"] == "setting_up"
    
    # Check that the session was created in the mock DB
    session_id = json_resp["session_id"]
    saved_session = mock_session_manager.getSession(session_id)
    assert saved_session is not None
    assert saved_session["interview_length"] == "short"
    assert saved_session["interview_mode"] == "technical"
    
    # Background task should have been triggered
    mock_run_setup.assert_called_once()


def test_report_endpoint_returns_structured_json(completed_session):
    """
    Hitting GET /api/sessions/{id}/report must yield the structured report schema JSON.
    """
    response = client.get(f"/api/sessions/{completed_session}/report")
    
    assert response.status_code == 200
    json_resp = response.json()
    
    assert json_resp["session_id"] == completed_session
    assert "overall_score" in json_resp
    assert "dimension_scores" in json_resp
    assert "executive_summary" in json_resp


def test_health_endpoint():
    """Health endpoint should return 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
