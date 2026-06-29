# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testScoreCalculator.py
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch, MagicMock

from src.modules.reporting.scoreCalculator import (
    calculateTechnicalRelevance,
    calculateAllScores,
)

def makeMockState() -> dict:
    return {
        "session_id": "test-session-123",
        "candidate": {
            "confirmed_skills": ["Python", "FastAPI"],
            "uncertain_skills": ["Docker", "Kubernetes"]
        },
        "asked_questions": [
            {"index": 0, "text": "How do you build APIs?"}
        ],
        "answers": [
            {"question_index": 0, "text": "I use FastAPI."}
        ]
    }

class TestScoreCalculator:
    @patch("src.modules.reporting.scoreCalculator.callLlm")
    def test_technical_relevance_ignores_uncertain_skills(self, mockCallLlm):
        mockCallLlm.return_value = {
            "score": 9.0,
            "evidence": ["Mentioned FastAPI"],
            "rationale": "Good logic."
        }
        
        state = makeMockState()
        result = calculateTechnicalRelevance(state)
        
        # Verify LLM was called with confirmed skills only
        prompt = mockCallLlm.call_args.kwargs["prompt"]
        assert "Python" in prompt
        assert "FastAPI" in prompt
        assert "Docker" not in prompt
        assert "Kubernetes" not in prompt
        
        assert result.score == 9.0
        assert result.evidence == ["Mentioned FastAPI"]

    @patch("src.modules.reporting.scoreCalculator.callLlm")
    def test_calculate_all_scores_returns_all_6(self, mockCallLlm):
        mockCallLlm.return_value = {
            "score": 8.0,
            "evidence": [],
            "rationale": "Mock rationale"
        }
        
        state = makeMockState()
        scores = calculateAllScores(state)
        
        assert len(scores) == 6
        assert "communication_clarity" in scores
        assert "technical_relevance" in scores
        assert "problem_solving" in scores
        assert "motivation_fit" in scores
        assert "confidence" in scores
        assert "listening_comprehension" in scores
        
        for k, v in scores.items():
            assert v.score == 8.0
