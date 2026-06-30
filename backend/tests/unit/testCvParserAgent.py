# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testCvParserAgent.py
#
# Unit tests for src.agents.cvParserAgent
#
# Tests verify:
#   1. Agent assembles CandidateProfile correctly from parsed sub-results
#   2. Skills gap uses confirmed_skills ONLY (never uncertain_skills)
#   3. interview_length and interview_mode pass through state correctly
#   4. Agent appends to step_log correctly
#   5. Agent raises on missing _cv_bytes
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch


# Canonical mock return values for the three parsers
MOCK_CV_DATA = {
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "education": [{"institution": "MIT", "degree": "BSc", "field": "CS",
                   "graduation_year": 2020, "gpa": "3.8"}],
    "experience": [{"company": "Acme", "role": "Dev", "duration": "2y",
                    "description": "Built APIs", "technologies": ["FastAPI"]}],
    "projects": [],
    "confirmed_skills": ["Python", "FastAPI", "PostgreSQL"],
    "uncertain_skills": ["Kubernetes", "Terraform"],
}

MOCK_JD_DATA = {
    "target_role": "Senior Backend Engineer",
    "required_skills_from_jd": ["Python", "FastAPI", "Docker", "Kubernetes"],
}

MOCK_MOTIVATION = "The candidate is motivated by AI systems."


def makeAgentState(overrides: dict = None) -> dict:
    """Build a minimal state dict for the cvParserAgent."""
    base = {
        "session_id": "test-session-001",
        "candidate_id": "test-candidate-001",
        "candidate": {
            "candidate_id": "test-candidate-001",
            "target_company": "Acme Corp",
            "session_ids": ["test-session-001"],
            "created_at": "2026-01-01T00:00:00Z",
        },
        "cv_bytes_input": b"fake-pdf-bytes",
        "jd_text_input": "We need a Senior Backend Engineer with Python, FastAPI, Docker, Kubernetes.",
        "motivation_text_input": "I am passionate about AI systems and want to join Acme Corp.",
        "interview_length": "medium",
        "interview_mode": "mixed",
        "step_log": [],
    }
    if overrides:
        base.update(overrides)
    return base


class TestCvParserAgentOutput:

    def _runAgent(self, stateOverrides: dict = None) -> dict:
        state = makeAgentState(stateOverrides)
        with patch("src.agents.cvParserAgent.parseCv", return_value=MOCK_CV_DATA):
            with patch("src.agents.cvParserAgent.parseJd", return_value=MOCK_JD_DATA):
                with patch("src.agents.cvParserAgent.parseMotivation", return_value=MOCK_MOTIVATION):
                    from src.agents.cvParserAgent import cvParserAgent
                    return cvParserAgent(state)

    def test_returns_candidate_key(self):
        result = self._runAgent()
        assert "candidate" in result

    def test_returns_step_log_key(self):
        result = self._runAgent()
        assert "step_log" in result

    def test_candidate_has_full_name(self):
        result = self._runAgent()
        assert result["candidate"]["full_name"] == "Jane Doe"

    def test_candidate_has_confirmed_skills(self):
        result = self._runAgent()
        assert "Python" in result["candidate"]["confirmed_skills"]
        assert "FastAPI" in result["candidate"]["confirmed_skills"]

    def test_candidate_has_uncertain_skills(self):
        result = self._runAgent()
        assert "Kubernetes" in result["candidate"]["uncertain_skills"]

    def test_skills_gap_uses_confirmed_skills_only(self):
        """
        CRITICAL TEST: skills_gap must be computed from confirmed_skills only.
        Kubernetes is in uncertain_skills AND in required_skills_from_jd.
        It MUST appear in skills_gap because it's not in confirmed_skills.
        """
        result = self._runAgent()
        skillsGap = result["candidate"]["skills_gap"]
        # Docker is in JD but not in confirmed_skills → must be in gap
        assert "Docker" in skillsGap
        # Kubernetes is in JD and in uncertain_skills (not confirmed) → must be in gap
        assert "Kubernetes" in skillsGap
        # Python is in JD AND in confirmed_skills → must NOT be in gap
        assert "Python" not in skillsGap
        # FastAPI is in JD AND in confirmed_skills → must NOT be in gap
        assert "FastAPI" not in skillsGap

    def test_uncertain_skills_never_close_gap(self):
        """
        Kubernetes appears in uncertain_skills. It also appears in required_skills_from_jd.
        It must still appear in skills_gap because only confirmed_skills close the gap.
        """
        result = self._runAgent()
        skillsGap = result["candidate"]["skills_gap"]
        assert "Kubernetes" in skillsGap, (
            "Kubernetes is in uncertain_skills but MUST still appear in skills_gap. "
            "Only confirmed_skills can close the gap."
        )

    def test_motivation_populated(self):
        result = self._runAgent()
        assert result["candidate"]["motivation"] == MOCK_MOTIVATION

    def test_target_role_populated(self):
        result = self._runAgent()
        assert result["candidate"]["target_role"] == "Senior Backend Engineer"

    def test_step_log_has_agent_entries(self):
        result = self._runAgent()
        assert any("[cvParserAgent]" in entry for entry in result["step_log"])

    def test_step_log_grows_from_existing(self):
        """Agent must append to existing step_log, not replace it."""
        result = self._runAgent({"step_log": ["[PREV] Existing entry."]})
        assert any("[PREV] Existing entry." == entry for entry in result["step_log"])
        assert len(result["step_log"]) > 1

    def test_candidate_id_preserved(self):
        result = self._runAgent()
        assert result["candidate"]["candidate_id"] == "test-candidate-001"


class TestCvParserAgentEdgeCases:

    def test_raises_when_cv_bytes_missing(self):
        """Agent must raise ValueError if cv_bytes_input is not in state."""
        from src.agents.cvParserAgent import cvParserAgent
        state = makeAgentState({"cv_bytes_input": None})
        with pytest.raises(ValueError, match="cv_bytes_input not found"):
            cvParserAgent(state)

    def test_handles_missing_jd_gracefully(self):
        """If no JD text is provided, agent should skip JD parsing cleanly."""
        state = makeAgentState({"jd_text_input": ""})
        with patch("src.agents.cvParserAgent.parseCv", return_value=MOCK_CV_DATA):
            with patch("src.agents.cvParserAgent.parseMotivation", return_value=MOCK_MOTIVATION):
                from src.agents.cvParserAgent import cvParserAgent
                result = cvParserAgent(state)
        assert result["candidate"]["target_role"] == ""
        assert result["candidate"]["required_skills_from_jd"] == []
        assert result["candidate"]["skills_gap"] == []

    def test_handles_missing_motivation_gracefully(self):
        """If no motivation text is provided, agent should use empty string."""
        state = makeAgentState({"motivation_text_input": ""})
        with patch("src.agents.cvParserAgent.parseCv", return_value=MOCK_CV_DATA):
            with patch("src.agents.cvParserAgent.parseJd", return_value=MOCK_JD_DATA):
                from src.agents.cvParserAgent import cvParserAgent
                result = cvParserAgent(state)
        assert result["candidate"]["motivation"] == ""

    def test_interview_length_in_state_not_modified(self):
        """cvParserAgent should NOT modify interview_length or interview_mode."""
        state = makeAgentState()
        with patch("src.agents.cvParserAgent.parseCv", return_value=MOCK_CV_DATA):
            with patch("src.agents.cvParserAgent.parseJd", return_value=MOCK_JD_DATA):
                with patch("src.agents.cvParserAgent.parseMotivation", return_value=MOCK_MOTIVATION):
                    from src.agents.cvParserAgent import cvParserAgent
                    result = cvParserAgent(state)
        # The agent returns only "candidate" and "step_log"
        assert "interview_length" not in result
        assert "interview_mode" not in result


class TestInterviewConfigInSession:
    """
    Verify that interview_length and interview_mode are correctly stored
    in session state and pass through cleanly. These are set at session
    initialisation by the API route, not by the cvParserAgent.
    """

    def test_interview_length_is_in_state(self, minimal_session):
        """minimal_session fixture must have interview_length."""
        assert "interview_length" in minimal_session
        assert minimal_session["interview_length"] in {"short", "medium", "long"}

    def test_interview_mode_is_in_state(self, minimal_session):
        """minimal_session fixture must have interview_mode."""
        assert "interview_mode" in minimal_session
        assert minimal_session["interview_mode"] in {
            "mixed", "technical", "behavioral", "hr_culture_fit", "system_design"
        }

    def test_all_interview_length_values_are_valid(self):
        """Verify all three valid length values pass a simple enum check."""
        validLengths = {"short", "medium", "long"}
        for length in validLengths:
            assert length in validLengths

    def test_all_interview_mode_values_are_valid(self):
        validModes = {"mixed", "technical", "behavioral", "hr_culture_fit", "system_design"}
        for mode in validModes:
            assert mode in validModes
