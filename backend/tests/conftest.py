# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/conftest.py
#
# Shared pytest fixtures for the entire test suite.
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from typing import Any


@pytest.fixture
def minimal_session() -> dict:
    """
    A minimal valid InterviewSession dict for unit testing.
    All fields required by the TypedDict are present with sensible defaults.
    Tests can override individual fields as needed.
    """
    return {
        # Identity
        "session_id": "test-session-001",
        "candidate_id": "test-candidate-001",
        "created_at": "2026-01-01T00:00:00Z",
        "app_mode": "demo",

        # Configuration
        "interview_length": "medium",
        "interview_mode": "mixed",

        # Module 1 — Ingestion outputs
        "candidate": {
            "candidate_id": "test-candidate-001",
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "education": [],
            "experience": [],
            "projects": [],
            "confirmed_skills": ["Python", "FastAPI"],
            "uncertain_skills": ["Kubernetes"],
            "motivation": "Passionate about AI systems.",
            "target_role": "Senior Backend Engineer",
            "target_company": "Acme Corp",
            "required_skills_from_jd": ["Python", "Docker", "Kubernetes"],
            "skills_gap": ["Docker", "Kubernetes"],
            "session_ids": ["test-session-001"],
            "created_at": "2026-01-01T00:00:00Z",
        },
        "company_context": "",
        "question_plan": [
            "Tell me about yourself.",
            "Walk me through your FastAPI experience.",
            "How do you approach system design under constraints?",
        ],
        "role_category": "software_engineer",

        # Module 2 — Interview Engine outputs
        "current_phase": "icebreaker",
        "current_question_index": 0,
        "asked_questions": [],
        "answers": [],
        "coaching_feedback": [],
        "difficulty_level": 2,
        "difficulty_dimensions": {
            "relevance": 2,
            "clarity": 2,
            "depth": 2,
            "confidence": 2,
            "structure": 2,
        },

        # Module 3 — Analysis outputs
        "audio_metrics_per_answer": [],
        "facial_metrics_summary": {
            "eye_contact_percentage": None,
            "avg_blink_rate_per_minute": None,
            "head_movement_score": None,
            "engagement_score": None,
            "demo_mode": True,
        },
        "transcript": [],

        # Module 4 — Report outputs
        "final_report": None,
        "pdf_path": None,

        # System Fields
        "status": "ready",
        "error": None,
        "step_log": ["[CONFTEST] Minimal test session created."],

        # Ephemeral runtime input fields (None by default in test context)
        "cv_bytes_input": None,
        "jd_text_input": None,
        "motivation_text_input": None,
    }
