# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testConductorAgent.py
#
# Unit tests for src.agents.conductorAgent
#
# Tests validate:
#   1. Agent returns correct Question schema fields
#   2. current_question_index increments correctly
#   3. current_phase is computed from flowController (not hardcoded)
#   4. Completion signal is returned when plan is exhausted
#   5. Error state when plan is empty
#   6. asked_questions list grows correctly
#   7. Status transitions: "in_progress" while active, "completed" when done
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from src.agents.conductorAgent import conductorAgent


# ── Fixtures ───────────────────────────────────────────────────────────────────

def makeState(
    questionPlan: list = None,
    currentIndex: int = 0,
    interviewLength: str = "short",
    interviewMode: str = "mixed",
    difficultyLevel: int = 2,
    answers: list = None,
    askedQuestions: list = None,
    status: str = "in_progress",
) -> dict:
    plan = questionPlan if questionPlan is not None else [
        "Tell me about yourself.",
        "Walk me through your most complex project.",
        "What is REST vs GraphQL?",
        "Design a URL shortener.",
        "Where do you see yourself in 3 years?",
    ]
    return {
        "session_id": "test-session-001",
        "candidate_id": "test-candidate-001",
        "question_plan": plan,
        "current_question_index": currentIndex,
        "interview_length": interviewLength,
        "interview_mode": interviewMode,
        "difficulty_level": difficultyLevel,
        "answers": answers or [],
        "asked_questions": askedQuestions or [],
        "status": status,
        "step_log": [],
    }


# ════════════════════════════════════════════════════════════════════════════════
# Question Delivery
# ════════════════════════════════════════════════════════════════════════════════

class TestQuestionDelivery:

    def test_returns_dict(self):
        state = makeState()
        result = conductorAgent(state)
        assert isinstance(result, dict)

    def test_next_question_is_dict(self):
        state = makeState()
        result = conductorAgent(state)
        assert isinstance(result["next_question"], dict)

    def test_next_question_text_matches_plan(self):
        state = makeState(currentIndex=0)
        result = conductorAgent(state)
        assert result["next_question"]["text"] == "Tell me about yourself."

    def test_next_question_index_matches_current(self):
        state = makeState(currentIndex=0)
        result = conductorAgent(state)
        assert result["next_question"]["index"] == 0

    def test_question_index_advances_on_second_call(self):
        state = makeState(currentIndex=1)
        result = conductorAgent(state)
        assert result["next_question"]["index"] == 1
        assert result["next_question"]["text"] == "Walk me through your most complex project."

    def test_question_has_followup_count_0(self):
        state = makeState()
        result = conductorAgent(state)
        assert result["next_question"]["followup_count"] == 0

    def test_question_has_difficulty_from_state(self):
        state = makeState(difficultyLevel=4)
        result = conductorAgent(state)
        assert result["next_question"]["difficulty"] == 4

    def test_question_has_phase_field(self):
        state = makeState()
        result = conductorAgent(state)
        assert result["next_question"]["phase"] in {
            "icebreaker", "cv_deep_dive", "dynamic_followup", "closing"
        }

    def test_question_has_category_field(self):
        state = makeState()
        result = conductorAgent(state)
        assert result["next_question"]["category"]
        assert isinstance(result["next_question"]["category"], str)

    def test_question_has_asked_at_timestamp(self):
        state = makeState()
        result = conductorAgent(state)
        assert result["next_question"]["asked_at"]


# ════════════════════════════════════════════════════════════════════════════════
# Index and State Updates
# ════════════════════════════════════════════════════════════════════════════════

class TestStateUpdates:

    def test_current_question_index_increments(self):
        state = makeState(currentIndex=0)
        result = conductorAgent(state)
        assert result["current_question_index"] == 1

    def test_current_question_index_increments_from_3(self):
        state = makeState(currentIndex=3)
        result = conductorAgent(state)
        assert result["current_question_index"] == 4

    def test_asked_questions_appended(self):
        state = makeState(currentIndex=0)
        result = conductorAgent(state)
        assert len(result["asked_questions"]) == 1

    def test_asked_questions_grows_cumulatively(self):
        """Second call state has pre-existing asked_questions."""
        existingQ = {"index": 0, "text": "Q0", "phase": "icebreaker",
                     "followup_count": 0, "category": "motivational", "difficulty": 2, "asked_at": ""}
        state = makeState(currentIndex=1, askedQuestions=[existingQ])
        result = conductorAgent(state)
        assert len(result["asked_questions"]) == 2

    def test_status_set_to_in_progress(self):
        state = makeState(currentIndex=0)
        result = conductorAgent(state)
        assert result["status"] == "in_progress"

    def test_current_phase_is_returned(self):
        state = makeState(currentIndex=0, interviewLength="short")
        result = conductorAgent(state)
        assert "current_phase" in result
        assert result["current_phase"] == "icebreaker"

    def test_step_log_appended(self):
        state = makeState()
        result = conductorAgent(state)
        assert len(result["step_log"]) > 0
        assert any("[conductorAgent]" in entry for entry in result["step_log"])


# ════════════════════════════════════════════════════════════════════════════════
# Phase Computation Across Index Points
# ════════════════════════════════════════════════════════════════════════════════

class TestPhaseComputation:

    def _planOfSize(self, n: int) -> list:
        return [f"Question {i}" for i in range(n)]

    def test_short_index_0_gives_icebreaker(self):
        state = makeState(currentIndex=0, interviewLength="short",
                          questionPlan=self._planOfSize(7))
        result = conductorAgent(state)
        assert result["current_phase"] == "icebreaker"

    def test_short_index_2_gives_cv_deep_dive(self):
        state = makeState(currentIndex=2, interviewLength="short",
                          questionPlan=self._planOfSize(7),
                          answers=[{"text": "A"}] * 2)
        result = conductorAgent(state)
        assert result["current_phase"] == "cv_deep_dive"

    def test_short_index_3_gives_dynamic_followup(self):
        state = makeState(currentIndex=3, interviewLength="short",
                          questionPlan=self._planOfSize(7),
                          answers=[{"text": "A"}] * 3)
        result = conductorAgent(state)
        assert result["current_phase"] == "dynamic_followup"

    def test_short_index_5_gives_closing(self):
        state = makeState(currentIndex=5, interviewLength="short",
                          questionPlan=self._planOfSize(7),
                          answers=[{"text": "A"}] * 5)
        result = conductorAgent(state)
        assert result["current_phase"] == "closing"

    def test_medium_index_8_gives_dynamic_followup(self):
        state = makeState(currentIndex=8, interviewLength="medium",
                          questionPlan=self._planOfSize(15),
                          answers=[{"text": "A"}] * 8)
        result = conductorAgent(state)
        assert result["current_phase"] == "dynamic_followup"

    def test_long_index_4_gives_cv_deep_dive(self):
        state = makeState(currentIndex=4, interviewLength="long",
                          questionPlan=self._planOfSize(25),
                          answers=[{"text": "A"}] * 4)
        result = conductorAgent(state)
        assert result["current_phase"] == "cv_deep_dive"


# ════════════════════════════════════════════════════════════════════════════════
# Completion Signal
# ════════════════════════════════════════════════════════════════════════════════

class TestCompletionSignal:

    def test_signals_complete_when_all_questions_answered(self):
        plan = ["Q0", "Q1", "Q2", "Q3", "Q4", "Q5"]
        answers = [{"text": "A", "question_index": i} for i in range(6)]
        state = makeState(
            questionPlan=plan,
            currentIndex=6,
            answers=answers,
        )
        result = conductorAgent(state)
        assert result["status"] == "completed"

    def test_next_question_is_none_on_completion(self):
        plan = ["Q0", "Q1", "Q2", "Q3", "Q4", "Q5"]
        answers = [{"text": "A", "question_index": i} for i in range(6)]
        state = makeState(
            questionPlan=plan,
            currentIndex=6,
            answers=answers,
        )
        result = conductorAgent(state)
        assert result["next_question"] is None

    def test_last_question_before_completion_is_not_complete(self):
        plan = ["Q0", "Q1", "Q2", "Q3", "Q4", "Q5"]
        answers = [{"text": "A", "question_index": i} for i in range(5)]
        state = makeState(
            questionPlan=plan,
            currentIndex=5,
            answers=answers,
        )
        result = conductorAgent(state)
        assert result["status"] == "in_progress"
        assert result["next_question"] is not None

    def test_step_log_has_completion_message(self):
        plan = ["Q0", "Q1", "Q2", "Q3", "Q4", "Q5"]
        answers = [{"text": "A", "question_index": i} for i in range(6)]
        state = makeState(questionPlan=plan, currentIndex=6, answers=answers)
        result = conductorAgent(state)
        assert any("complete" in entry.lower() for entry in result["step_log"])


# ════════════════════════════════════════════════════════════════════════════════
# Error States
# ════════════════════════════════════════════════════════════════════════════════

class TestErrorStates:

    def test_returns_error_when_plan_empty(self):
        state = makeState(questionPlan=[], currentIndex=0)
        result = conductorAgent(state)
        assert result["status"] == "error"

    def test_next_question_none_when_plan_empty(self):
        state = makeState(questionPlan=[], currentIndex=0)
        result = conductorAgent(state)
        assert result["next_question"] is None

    def test_error_contains_message(self):
        state = makeState(questionPlan=[], currentIndex=0)
        result = conductorAgent(state)
        assert "error" in result
        assert result["error"]


# ════════════════════════════════════════════════════════════════════════════════
# Mode-based Category Override
# ════════════════════════════════════════════════════════════════════════════════

class TestModeBasedCategoryOverride:

    def _planOfSize(self, n: int) -> list:
        return [f"Q{i}" for i in range(n)]

    def test_behavioral_mode_sets_behavioral_category(self):
        """In behavioral mode (non-icebreaker phase), category → behavioral."""
        state = makeState(
            currentIndex=2,  # cv_deep_dive for short
            interviewLength="short",
            interviewMode="behavioral",
            questionPlan=self._planOfSize(7),
            answers=[{"text": "A"}] * 2,
        )
        result = conductorAgent(state)
        assert result["next_question"]["category"] == "behavioral"

    def test_technical_mode_sets_technical_category(self):
        """In technical mode (non-icebreaker phase), category → technical."""
        state = makeState(
            currentIndex=2,  # cv_deep_dive for short
            interviewLength="short",
            interviewMode="technical",
            questionPlan=self._planOfSize(7),
            answers=[{"text": "A"}] * 2,
        )
        result = conductorAgent(state)
        assert result["next_question"]["category"] == "technical"

    def test_icebreaker_phase_always_motivational(self):
        """Icebreaker questions → always 'motivational' regardless of mode."""
        state = makeState(
            currentIndex=0,
            interviewLength="short",
            interviewMode="technical",  # Even technical mode
            questionPlan=self._planOfSize(7),
        )
        result = conductorAgent(state)
        assert result["next_question"]["category"] == "motivational"
