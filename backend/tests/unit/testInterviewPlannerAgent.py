# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testInterviewPlannerAgent.py
#
# Unit tests for src.agents.interviewPlannerAgent
#
# All LLM calls are mocked — no real API calls are made.
#
# Tests validate:
#   1. Question count output matches the LENGTH_TARGETS total for each length
#   2. Plan output is always a list of strings (never None, never dict)
#   3. Role category detection is wired correctly through the agent
#   4. LLM over-generation is truncated to the max of the range
#   5. LLM under-generation is padded to the min of the range
#   6. Various LLM output formats are handled (list, dict wrapper, nested)
#   7. step_log is populated with agent entries
#   8. return dict only contains expected keys
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch


# ── Helpers ────────────────────────────────────────────────────────────────────

def makeState(
    targetRole: str = "Software Engineer",
    targetCompany: str = "Acme Corp",
    interviewLength: str = "medium",
    interviewMode: str = "mixed",
    confirmedSkills: list = None,
    skillsGap: list = None,
) -> dict:
    return {
        "session_id": "test-session-001",
        "candidate_id": "test-candidate-001",
        "interview_length": interviewLength,
        "interview_mode": interviewMode,
        "company_context": "Acme Corp is a leading software company.",
        "candidate": {
            "candidate_id": "test-candidate-001",
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "target_role": targetRole,
            "target_company": targetCompany,
            "confirmed_skills": confirmedSkills or ["Python", "FastAPI"],
            "uncertain_skills": ["Kubernetes"],
            "skills_gap": skillsGap or ["Docker", "Kubernetes"],
            "motivation": "Passionate about AI systems.",
            "required_skills_from_jd": ["Python", "Docker", "Kubernetes"],
            "education": [],
            "experience": [],
            "projects": [],
            "session_ids": ["test-session-001"],
            "created_at": "2026-01-01T00:00:00Z",
        },
        "step_log": ["[PREVIOUS] Prior step entry."],
    }


def makeLlmQuestionList(count: int) -> list:
    return [f"Question {i + 1} for this candidate?" for i in range(count)]


# ════════════════════════════════════════════════════════════════════════════════
# Question Count Targets per Interview Length
# ════════════════════════════════════════════════════════════════════════════════

class TestQuestionCountTargets:

    def _runAgent(self, length: str, llmReturnCount: int) -> dict:
        from src.agents.interviewPlannerAgent import interviewPlannerAgent
        state = makeState(interviewLength=length)
        with patch("src.agents.interviewPlannerAgent.callLlm",
                   return_value=makeLlmQuestionList(llmReturnCount)):
            return interviewPlannerAgent(state)

    def test_short_interview_produces_5_to_7_questions(self):
        result = self._runAgent("short", llmReturnCount=6)
        count = len(result["question_plan"])
        assert 5 <= count <= 7, f"Short interview produced {count} questions, expected 5–7"

    def test_medium_interview_produces_10_to_15_questions(self):
        result = self._runAgent("medium", llmReturnCount=12)
        count = len(result["question_plan"])
        assert 10 <= count <= 15, f"Medium interview produced {count} questions, expected 10–15"

    def test_long_interview_produces_18_to_25_questions(self):
        result = self._runAgent("long", llmReturnCount=21)
        count = len(result["question_plan"])
        assert 18 <= count <= 25, f"Long interview produced {count} questions, expected 18–25"

    def test_short_llm_over_generation_is_truncated(self):
        """LLM returns 20 questions for a short interview → must truncate to max=7."""
        result = self._runAgent("short", llmReturnCount=20)
        assert len(result["question_plan"]) <= 7

    def test_long_llm_under_generation_is_padded(self):
        """LLM returns only 3 questions for a long interview → must pad to min=18."""
        result = self._runAgent("long", llmReturnCount=3)
        assert len(result["question_plan"]) >= 18

    def test_medium_exact_target_preserved(self):
        """LLM returns exactly 12 questions → plan should be 12."""
        result = self._runAgent("medium", llmReturnCount=12)
        assert len(result["question_plan"]) == 12


# ════════════════════════════════════════════════════════════════════════════════
# Output Schema
# ════════════════════════════════════════════════════════════════════════════════

class TestPlannerOutputSchema:

    def _runAgent(self, llmReturn=None, length="medium") -> dict:
        from src.agents.interviewPlannerAgent import interviewPlannerAgent
        state = makeState(interviewLength=length)
        if llmReturn is None:
            llmReturn = makeLlmQuestionList(12)
        with patch("src.agents.interviewPlannerAgent.callLlm", return_value=llmReturn):
            return interviewPlannerAgent(state)

    def test_returns_dict(self):
        result = self._runAgent()
        assert isinstance(result, dict)

    def test_returns_question_plan_key(self):
        result = self._runAgent()
        assert "question_plan" in result

    def test_returns_role_category_key(self):
        result = self._runAgent()
        assert "role_category" in result

    def test_returns_step_log_key(self):
        result = self._runAgent()
        assert "step_log" in result

    def test_question_plan_is_list(self):
        result = self._runAgent()
        assert isinstance(result["question_plan"], list)

    def test_question_plan_contains_strings(self):
        result = self._runAgent()
        for q in result["question_plan"]:
            assert isinstance(q, str)

    def test_role_category_is_string(self):
        result = self._runAgent()
        assert isinstance(result["role_category"], str)

    def test_step_log_appended_not_replaced(self):
        """Pre-existing step_log entries must be preserved."""
        result = self._runAgent()
        assert any("[PREVIOUS]" in entry for entry in result["step_log"])

    def test_step_log_has_planner_entries(self):
        result = self._runAgent()
        assert any("[interviewPlannerAgent]" in entry for entry in result["step_log"])

    def test_no_extra_keys_in_output(self):
        """Agent must return exactly these keys — nothing more."""
        result = self._runAgent()
        expectedKeys = {"question_plan", "role_category", "step_log"}
        assert set(result.keys()) == expectedKeys


# ════════════════════════════════════════════════════════════════════════════════
# Role Category Detection
# ════════════════════════════════════════════════════════════════════════════════

class TestRoleCategoryDetection:

    def _runAgent(self, targetRole: str) -> dict:
        from src.agents.interviewPlannerAgent import interviewPlannerAgent
        state = makeState(targetRole=targetRole)
        with patch("src.agents.interviewPlannerAgent.callLlm",
                   return_value=makeLlmQuestionList(12)):
            return interviewPlannerAgent(state)

    def test_detects_software_engineer(self):
        result = self._runAgent("Senior Software Engineer")
        assert result["role_category"] == "software_engineer"

    def test_detects_ml_engineer(self):
        result = self._runAgent("ML Engineer")
        assert result["role_category"] == "ml_engineer"

    def test_detects_data_scientist(self):
        result = self._runAgent("Data Scientist")
        assert result["role_category"] == "data_scientist"

    def test_detects_product_manager(self):
        result = self._runAgent("Product Manager")
        assert result["role_category"] == "product_manager"

    def test_detects_business_analyst(self):
        result = self._runAgent("Business Analyst")
        assert result["role_category"] == "business_analyst"

    def test_unknown_role_defaults_to_software_engineer(self):
        result = self._runAgent("Professional Juggler")
        assert result["role_category"] == "software_engineer"

    def test_empty_role_defaults_to_software_engineer(self):
        result = self._runAgent("")
        assert result["role_category"] == "software_engineer"


# ════════════════════════════════════════════════════════════════════════════════
# LLM Output Format Handling
# ════════════════════════════════════════════════════════════════════════════════

class TestLlmOutputFormatHandling:

    def _runAgent(self, llmReturn, length="medium") -> dict:
        from src.agents.interviewPlannerAgent import interviewPlannerAgent
        state = makeState(interviewLength=length)
        with patch("src.agents.interviewPlannerAgent.callLlm", return_value=llmReturn):
            return interviewPlannerAgent(state)

    def test_handles_list_output(self):
        questions = makeLlmQuestionList(12)
        result = self._runAgent(questions)
        assert isinstance(result["question_plan"], list)
        assert len(result["question_plan"]) == 12

    def test_handles_dict_with_questions_key(self):
        """Some LLMs wrap the array: {'questions': [...]}"""
        questions = makeLlmQuestionList(12)
        result = self._runAgent({"questions": questions})
        assert isinstance(result["question_plan"], list)
        assert 10 <= len(result["question_plan"]) <= 15

    def test_handles_dict_with_question_plan_key(self):
        """Other models use {'question_plan': [...]}"""
        questions = makeLlmQuestionList(12)
        result = self._runAgent({"question_plan": questions})
        assert isinstance(result["question_plan"], list)

    def test_handles_empty_llm_response_gracefully(self):
        """Empty output → plan padded to minimum for the length."""
        result = self._runAgent([], length="short")
        assert isinstance(result["question_plan"], list)
        assert len(result["question_plan"]) >= 5  # min for short

    def test_strips_empty_strings_from_plan(self):
        """LLM sometimes returns empty strings in the list — must be stripped."""
        questionsWithEmpty = ["Q1?", "", "  ", "Q2?"] + makeLlmQuestionList(10)
        result = self._runAgent(questionsWithEmpty)
        for q in result["question_plan"]:
            assert q.strip() != "", "Empty strings should be stripped from plan"

    def test_handles_nested_list_from_llm(self):
        """Some LLMs return nested lists — should be flattened."""
        nestedList = [["Q1?", "Q2?"], ["Q3?"], ["Q4?", "Q5?", "Q6?", "Q7?", "Q8?", "Q9?"]]
        result = self._runAgent(nestedList, length="short")
        assert isinstance(result["question_plan"], list)
        # All nested items should be in the flat plan
        for q in result["question_plan"]:
            assert isinstance(q, str)


# ════════════════════════════════════════════════════════════════════════════════
# All interview modes produce valid plans
# ════════════════════════════════════════════════════════════════════════════════

class TestAllModes:

    VALID_MODES = ["mixed", "technical", "behavioral", "hr_culture_fit", "system_design"]

    def test_all_modes_produce_valid_plans(self):
        from src.agents.interviewPlannerAgent import interviewPlannerAgent
        for mode in self.VALID_MODES:
            state = makeState(interviewMode=mode, interviewLength="short")
            with patch("src.agents.interviewPlannerAgent.callLlm",
                       return_value=makeLlmQuestionList(6)):
                result = interviewPlannerAgent(state)
            assert isinstance(result["question_plan"], list), (
                f"Mode '{mode}' returned non-list plan"
            )
            assert 5 <= len(result["question_plan"]) <= 7, (
                f"Mode '{mode}' produced {len(result['question_plan'])} questions, "
                f"expected 5–7 for short length"
            )
