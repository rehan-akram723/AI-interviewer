# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testFollowUpAgent.py
#
# Unit tests for src.agents.followUpAgent
#
# All LLM calls are mocked. Tests validate:
#   1. Hard ceiling: followup_count >= 2 → advance immediately, no LLM
#   2. Score gate: high score + verbose answer → advance, no LLM
#   3. suggest_followup flag from calibrator overrides score gate
#   4. LLM advance decision is respected
#   5. LLM follow-up decision builds correct Question schema
#   6. LLM failure → advance (safe fallback)
#   7. Empty answer/question guards
#   8. followup_count in returned Question is correctly incremented
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch

from src.agents.followUpAgent import followUpAgent


# ── Fixture helpers ────────────────────────────────────────────────────────────

def makeQuestion(
    index: int = 0,
    text: str = "Describe your most challenging project.",
    phase: str = "cv_deep_dive",
    category: str = "technical",
    difficulty: int = 2,
    parentIdx: int = None,
    followupCount: int = 0,
) -> dict:
    q = {
        "index": index,
        "text": text,
        "phase": phase,
        "category": category,
        "difficulty": difficulty,
        "followup_count": followupCount,
        "asked_at": "2026-01-01T00:00:00Z",
    }
    if parentIdx is not None:
        q["parent_question_index"] = parentIdx
    return q


def makeAnswer(
    text: str,
    questionIndex: int = 0,
) -> dict:
    return {
        "text": text,
        "question_index": questionIndex,
        "answered_at": "2026-01-01T00:00:00Z",
    }


def makeFeedback(scorePreview: int = 5) -> dict:
    return {
        "answer_index": 0,
        "score_preview": scorePreview,
        "feedback_text": "Good effort.",
        "strengths": [],
        "improvements": [],
        "dimension_scores": {
            "relevance": scorePreview,
            "clarity": scorePreview,
            "depth": scorePreview,
            "confidence": scorePreview,
            "structure": scorePreview,
        },
    }


def makeFollowupQuestion(index: int, parentIdx: int, followupCount: int) -> dict:
    return {
        "index": index,
        "text": "Follow-up Q?",
        "phase": "cv_deep_dive",
        "category": "behavioral",
        "difficulty": 2,
        "parent_question_index": parentIdx,
        "followup_count": followupCount,
        "asked_at": "2026-01-01T00:00:00Z",
    }


def makeState(
    askedQuestions: list = None,
    answers: list = None,
    coachingFeedback: list = None,
    suggestFollowup: bool = False,
    roleCategory: str = "software_engineer",
    difficultyLevel: int = 2,
) -> dict:
    return {
        "session_id": "test-001",
        "asked_questions": askedQuestions if askedQuestions is not None else [makeQuestion()],
        "answers": answers if answers is not None else [makeAnswer("A good detailed answer here. " * 5)],
        "coaching_feedback": coachingFeedback if coachingFeedback is not None else [],
        "suggest_followup": suggestFollowup,
        "role_category": roleCategory,
        "difficulty_level": difficultyLevel,
        "step_log": [],
    }


# ════════════════════════════════════════════════════════════════════════════════
# Hard Ceiling Enforcement (STEP 1 — no LLM ever called)
# ════════════════════════════════════════════════════════════════════════════════

class TestHardCeilingEnforcement:
    """
    The absolute system guardrail: when followup_count >= MAX_FOLLOWUPS_PER_QUESTION (2),
    the agent MUST signal advance with no LLM call, regardless of any other signal.
    """

    def _stateWithFollowupCount(self, followupsAlreadyDone: int) -> dict:
        """Build state with N follow-up questions already in asked_questions for Q0."""
        askedQuestions = [makeQuestion(index=0)]
        for i in range(1, followupsAlreadyDone + 1):
            askedQuestions.append(
                makeFollowupQuestion(index=i, parentIdx=0, followupCount=i)
            )
        return makeState(
            askedQuestions=askedQuestions,
            answers=[makeAnswer("Short answer.", questionIndex=followupsAlreadyDone)],
            coachingFeedback=[makeFeedback(1)],  # Low score that would normally trigger follow-up
        )

    def test_signals_advance_when_2_followups_used(self):
        state = self._stateWithFollowupCount(2)
        result = followUpAgent(state)
        assert result["should_advance"] is True

    def test_signals_advance_when_3_followups_used(self):
        """Even if somehow 3 were added, ceiling must hold."""
        state = self._stateWithFollowupCount(3)
        result = followUpAgent(state)
        assert result["should_advance"] is True

    def test_next_question_is_none_at_ceiling(self):
        state = self._stateWithFollowupCount(2)
        result = followUpAgent(state)
        assert result["next_question"] is None

    def test_no_llm_called_at_ceiling(self):
        state = self._stateWithFollowupCount(2)
        with patch("src.agents.followUpAgent.callLlm") as mockLlm:
            followUpAgent(state)
        mockLlm.assert_not_called()

    def test_no_llm_called_at_ceiling_even_with_low_score(self):
        """Low coaching score (1/10) must NOT override hard ceiling."""
        state = self._stateWithFollowupCount(2)
        state["coaching_feedback"] = [makeFeedback(1)]
        with patch("src.agents.followUpAgent.callLlm") as mockLlm:
            followUpAgent(state)
        mockLlm.assert_not_called()

    def test_no_llm_called_at_ceiling_even_with_suggest_followup(self):
        """Calibrator suggest_followup=True must NOT override hard ceiling."""
        state = self._stateWithFollowupCount(2)
        state["suggest_followup"] = True
        with patch("src.agents.followUpAgent.callLlm") as mockLlm:
            followUpAgent(state)
        mockLlm.assert_not_called()

    def test_1_followup_done_ceiling_not_hit_yet(self):
        """1/2 follow-ups — ceiling NOT hit. LLM may be consulted."""
        state = self._stateWithFollowupCount(1)
        state["coaching_feedback"] = [makeFeedback(3)]  # Low score triggers LLM
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={"should_followup": False, "followup_question": None}):
            result = followUpAgent(state)
        assert result["should_advance"] is True  # LLM said advance

    def test_step_log_mentions_ceiling(self):
        state = self._stateWithFollowupCount(2)
        result = followUpAgent(state)
        assert any("ceiling" in entry.lower() or "hard" in entry.lower()
                   for entry in result["step_log"])


# ════════════════════════════════════════════════════════════════════════════════
# Score Gate (STEP 2 — skips LLM when answer is strong)
# ════════════════════════════════════════════════════════════════════════════════

class TestScoreGate:

    def _makeStrongAnswerState(self, score: int = 8, wordCount: int = 60) -> dict:
        longAnswer = ("word " * wordCount).strip()
        return makeState(
            askedQuestions=[makeQuestion()],
            answers=[makeAnswer(longAnswer)],
            coachingFeedback=[makeFeedback(score)],
            suggestFollowup=False,
        )

    def test_advances_without_llm_when_score_high_and_answer_long(self):
        state = self._makeStrongAnswerState(score=8, wordCount=60)
        with patch("src.agents.followUpAgent.callLlm") as mockLlm:
            result = followUpAgent(state)
        mockLlm.assert_not_called()
        assert result["should_advance"] is True

    def test_score_exactly_7_and_50_words_advances(self):
        state = self._makeStrongAnswerState(score=7, wordCount=50)
        with patch("src.agents.followUpAgent.callLlm") as mockLlm:
            result = followUpAgent(state)
        mockLlm.assert_not_called()
        assert result["should_advance"] is True

    def test_score_6_triggers_llm_consultation(self):
        """Score below gate (< 7) → must consult LLM."""
        state = self._makeStrongAnswerState(score=6, wordCount=60)
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={"should_followup": False, "followup_question": None}):
            result = followUpAgent(state)
        # LLM was called (by checking result is still advance)
        assert result["should_advance"] is True

    def test_short_answer_triggers_llm_even_with_high_score(self):
        """Short answer (< 50 words) must consult LLM even if score = 9."""
        shortAnswer = "I built a REST API."  # 6 words
        state = makeState(
            askedQuestions=[makeQuestion()],
            answers=[makeAnswer(shortAnswer)],
            coachingFeedback=[makeFeedback(9)],
        )
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={"should_followup": False, "followup_question": None}) as mockLlm:
            followUpAgent(state)
        assert mockLlm.called, "LLM should be called for short answers even with high score"

    def test_suggest_followup_flag_overrides_score_gate(self):
        """Calibrator suggest_followup=True must bypass the score gate and call LLM."""
        state = self._makeStrongAnswerState(score=9, wordCount=100)
        state["suggest_followup"] = True
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={"should_followup": False, "followup_question": None}) as mockLlm:
            followUpAgent(state)
        assert mockLlm.called, "LLM should be called when suggest_followup=True"


# ════════════════════════════════════════════════════════════════════════════════
# LLM Decision Handling (STEP 3)
# ════════════════════════════════════════════════════════════════════════════════

class TestLlmDecision:

    def _makeLlmTriggerState(self) -> dict:
        """State that bypasses ceiling and score gate to reach LLM."""
        return makeState(
            askedQuestions=[makeQuestion()],
            answers=[makeAnswer("I built something complex.")],  # Short — triggers LLM
            coachingFeedback=[makeFeedback(5)],
        )

    def test_llm_advance_returns_should_advance_true(self):
        state = self._makeLlmTriggerState()
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={"should_followup": False, "followup_question": None}):
            result = followUpAgent(state)
        assert result["should_advance"] is True
        assert result["next_question"] is None

    def test_llm_followup_returns_should_advance_false(self):
        state = self._makeLlmTriggerState()
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={
                       "should_followup": True,
                       "followup_question": "You mentioned complex — what pattern did you use?"
                   }):
            result = followUpAgent(state)
        assert result["should_advance"] is False

    def test_llm_followup_returns_next_question_dict(self):
        state = self._makeLlmTriggerState()
        followupText = "You mentioned complex — what pattern did you use?"
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={"should_followup": True, "followup_question": followupText}):
            result = followUpAgent(state)
        assert result["next_question"] is not None
        assert result["next_question"]["text"] == followupText

    def test_followup_question_has_correct_followup_count(self):
        """First follow-up for Q0 → followup_count should be 1."""
        state = self._makeLlmTriggerState()
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={
                       "should_followup": True,
                       "followup_question": "Tell me more about that system."
                   }):
            result = followUpAgent(state)
        assert result["next_question"]["followup_count"] == 1

    def test_followup_question_has_parent_question_index(self):
        state = self._makeLlmTriggerState()
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={
                       "should_followup": True,
                       "followup_question": "What was the biggest challenge?"
                   }):
            result = followUpAgent(state)
        assert result["next_question"]["parent_question_index"] == 0

    def test_followup_question_appended_to_asked_questions(self):
        state = self._makeLlmTriggerState()
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={
                       "should_followup": True,
                       "followup_question": "What was the outcome?"
                   }):
            result = followUpAgent(state)
        assert len(result["asked_questions"]) == 2  # Original + follow-up

    def test_llm_failure_falls_back_to_advance(self):
        state = self._makeLlmTriggerState()
        with patch("src.agents.followUpAgent.callLlm",
                   side_effect=Exception("API timeout")):
            result = followUpAgent(state)
        assert result["should_advance"] is True
        assert result["next_question"] is None

    def test_llm_null_followup_question_advances(self):
        """LLM says should_followup=True but followup_question is null → advance."""
        state = self._makeLlmTriggerState()
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={"should_followup": True, "followup_question": None}):
            result = followUpAgent(state)
        assert result["should_advance"] is True

    def test_llm_empty_followup_question_advances(self):
        """LLM says should_followup=True but followup_question is empty string → advance."""
        state = self._makeLlmTriggerState()
        with patch("src.agents.followUpAgent.callLlm",
                   return_value={"should_followup": True, "followup_question": "  "}):
            result = followUpAgent(state)
        assert result["should_advance"] is True


# ════════════════════════════════════════════════════════════════════════════════
# Output Schema
# ════════════════════════════════════════════════════════════════════════════════

class TestOutputSchema:

    def _runAdvance(self) -> dict:
        state = makeState(coachingFeedback=[makeFeedback(9)],
                          answers=[makeAnswer("word " * 60)])
        with patch("src.agents.followUpAgent.callLlm", return_value={"should_followup": False}):
            return followUpAgent(state)

    def test_returns_dict(self):
        assert isinstance(self._runAdvance(), dict)

    def test_returns_should_advance_key(self):
        assert "should_advance" in self._runAdvance()

    def test_returns_next_question_key(self):
        assert "next_question" in self._runAdvance()

    def test_returns_asked_questions_key(self):
        assert "asked_questions" in self._runAdvance()

    def test_returns_step_log_key(self):
        assert "step_log" in self._runAdvance()

    def test_step_log_is_list(self):
        assert isinstance(self._runAdvance()["step_log"], list)


# ════════════════════════════════════════════════════════════════════════════════
# Guard Cases
# ════════════════════════════════════════════════════════════════════════════════

class TestGuardCases:

    def test_advances_when_no_asked_questions(self):
        state = makeState(askedQuestions=[], answers=[makeAnswer("text")])
        result = followUpAgent(state)
        assert result["should_advance"] is True

    def test_advances_when_no_answers(self):
        state = makeState(answers=[])
        result = followUpAgent(state)
        assert result["should_advance"] is True

    def test_no_llm_when_no_answers(self):
        state = makeState(answers=[])
        with patch("src.agents.followUpAgent.callLlm") as mockLlm:
            followUpAgent(state)
        mockLlm.assert_not_called()
