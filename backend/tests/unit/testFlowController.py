# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testFlowController.py
#
# Unit tests for src.modules.interviewEngine.flowController
#
# Tests validate:
#   1. getCurrentPhase — exact boundary transitions for all three lengths
#   2. isInterviewComplete — dual guard (index + answer count)
#   3. getFollowupCount — counting follow-up questions by parent index
#   4. shouldFollowUp — hard ceiling, score signal, word count heuristic
#   5. Constants — PHASE_BOUNDARIES, LENGTH_TARGETS, MAX_FOLLOWUPS_PER_QUESTION
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from src.modules.interviewEngine.flowController import (
    getCurrentPhase,
    isInterviewComplete,
    getFollowupCount,
    shouldFollowUp,
    PHASE_BOUNDARIES,
    LENGTH_TARGETS,
    MAX_FOLLOWUPS_PER_QUESTION,
)


# ════════════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════════════

def makeState(
    index: int = 0,
    length: str = "medium",
    questionPlan: list | None = None,
    answers: list | None = None,
    askedQuestions: list | None = None,
    coachingFeedback: list | None = None,
) -> dict:
    return {
        "current_question_index": index,
        "interview_length": length,
        "question_plan": questionPlan or ["Q"] * 15,
        "answers": answers or [],
        "asked_questions": askedQuestions or [],
        "coaching_feedback": coachingFeedback or [],
    }


# ════════════════════════════════════════════════════════════════════════════════
# Constants
# ════════════════════════════════════════════════════════════════════════════════

class TestConstants:

    def test_max_followups_is_2(self):
        assert MAX_FOLLOWUPS_PER_QUESTION == 2

    def test_phase_boundaries_has_all_lengths(self):
        assert set(PHASE_BOUNDARIES.keys()) == {"short", "medium", "long"}

    def test_phase_boundaries_tuples_have_3_elements(self):
        for length, bounds in PHASE_BOUNDARIES.items():
            assert len(bounds) == 3, f"PHASE_BOUNDARIES['{length}'] must have 3 elements"

    def test_length_targets_has_all_lengths(self):
        assert set(LENGTH_TARGETS.keys()) == {"short", "medium", "long"}

    def test_length_targets_have_required_keys(self):
        required = {"total", "icebreaker", "cv_deep_dive", "dynamic_followup", "closing"}
        for length, targets in LENGTH_TARGETS.items():
            missing = required - set(targets.keys())
            assert not missing, f"LENGTH_TARGETS['{length}'] missing: {missing}"

    def test_length_targets_total_within_manifest_ranges(self):
        """Total targets must fall within manifest ranges: short 5-7, medium 10-15, long 18-25."""
        ranges = {"short": (5, 7), "medium": (10, 15), "long": (18, 25)}
        for length, (minQ, maxQ) in ranges.items():
            total = LENGTH_TARGETS[length]["total"]
            assert minQ <= total <= maxQ, (
                f"LENGTH_TARGETS['{length}']['total'] = {total} is outside range {minQ}–{maxQ}"
            )

    def test_length_target_phases_sum_to_total(self):
        """Icebreaker + cv_deep_dive + dynamic_followup + closing should sum to total."""
        for length, targets in LENGTH_TARGETS.items():
            phaseSum = (
                targets["icebreaker"]
                + targets["cv_deep_dive"]
                + targets["dynamic_followup"]
                + targets["closing"]
            )
            assert phaseSum == targets["total"], (
                f"LENGTH_TARGETS['{length}']: phase sum {phaseSum} != total {targets['total']}"
            )


# ════════════════════════════════════════════════════════════════════════════════
# getCurrentPhase — SHORT
# Boundaries: (0, 2, 4)
# 0 → icebreaker | 1–2 → cv_deep_dive | 3–4 → dynamic_followup | 5+ → closing
# ════════════════════════════════════════════════════════════════════════════════

class TestGetCurrentPhaseShort:

    def test_index_0_is_icebreaker(self):
        assert getCurrentPhase(makeState(0, "short")) == "icebreaker"

    def test_index_1_is_cv_deep_dive(self):
        assert getCurrentPhase(makeState(1, "short")) == "cv_deep_dive"

    def test_index_2_is_cv_deep_dive(self):
        assert getCurrentPhase(makeState(2, "short")) == "cv_deep_dive"

    def test_index_3_is_dynamic_followup(self):
        assert getCurrentPhase(makeState(3, "short")) == "dynamic_followup"

    def test_index_4_is_dynamic_followup(self):
        assert getCurrentPhase(makeState(4, "short")) == "dynamic_followup"

    def test_index_5_is_closing(self):
        assert getCurrentPhase(makeState(5, "short")) == "closing"

    def test_index_6_is_closing(self):
        assert getCurrentPhase(makeState(6, "short")) == "closing"

    def test_index_99_is_closing(self):
        """Any index beyond boundaries → closing."""
        assert getCurrentPhase(makeState(99, "short")) == "closing"


# ════════════════════════════════════════════════════════════════════════════════
# getCurrentPhase — MEDIUM
# Boundaries: (2, 7, 12)
# 0–2 → icebreaker | 3–7 → cv_deep_dive | 8–12 → dynamic_followup | 13+ → closing
# ════════════════════════════════════════════════════════════════════════════════

class TestGetCurrentPhaseMedium:

    def test_index_0_is_icebreaker(self):
        assert getCurrentPhase(makeState(0, "medium")) == "icebreaker"

    def test_index_1_is_icebreaker(self):
        assert getCurrentPhase(makeState(1, "medium")) == "icebreaker"

    def test_index_2_is_icebreaker(self):
        assert getCurrentPhase(makeState(2, "medium")) == "icebreaker"

    def test_index_3_is_cv_deep_dive(self):
        assert getCurrentPhase(makeState(3, "medium")) == "cv_deep_dive"

    def test_index_5_is_cv_deep_dive(self):
        assert getCurrentPhase(makeState(5, "medium")) == "cv_deep_dive"

    def test_index_7_is_cv_deep_dive(self):
        assert getCurrentPhase(makeState(7, "medium")) == "cv_deep_dive"

    def test_index_8_is_dynamic_followup(self):
        assert getCurrentPhase(makeState(8, "medium")) == "dynamic_followup"

    def test_index_10_is_dynamic_followup(self):
        assert getCurrentPhase(makeState(10, "medium")) == "dynamic_followup"

    def test_index_12_is_dynamic_followup(self):
        assert getCurrentPhase(makeState(12, "medium")) == "dynamic_followup"

    def test_index_13_is_closing(self):
        assert getCurrentPhase(makeState(13, "medium")) == "closing"

    def test_index_14_is_closing(self):
        assert getCurrentPhase(makeState(14, "medium")) == "closing"

    def test_index_50_is_closing(self):
        assert getCurrentPhase(makeState(50, "medium")) == "closing"

    # ── Critical boundary transitions ─────────────────────────────────────────
    def test_transition_icebreaker_to_cv_at_index_3(self):
        assert getCurrentPhase(makeState(2, "medium")) == "icebreaker"
        assert getCurrentPhase(makeState(3, "medium")) == "cv_deep_dive"

    def test_transition_cv_to_dynamic_at_index_8(self):
        assert getCurrentPhase(makeState(7, "medium")) == "cv_deep_dive"
        assert getCurrentPhase(makeState(8, "medium")) == "dynamic_followup"

    def test_transition_dynamic_to_closing_at_index_13(self):
        assert getCurrentPhase(makeState(12, "medium")) == "dynamic_followup"
        assert getCurrentPhase(makeState(13, "medium")) == "closing"


# ════════════════════════════════════════════════════════════════════════════════
# getCurrentPhase — LONG
# Boundaries: (3, 11, 19)
# 0–3 → icebreaker | 4–11 → cv_deep_dive | 12–19 → dynamic_followup | 20+ → closing
# ════════════════════════════════════════════════════════════════════════════════

class TestGetCurrentPhaseLong:

    def test_index_0_is_icebreaker(self):
        assert getCurrentPhase(makeState(0, "long")) == "icebreaker"

    def test_index_3_is_icebreaker(self):
        assert getCurrentPhase(makeState(3, "long")) == "icebreaker"

    def test_index_4_is_cv_deep_dive(self):
        assert getCurrentPhase(makeState(4, "long")) == "cv_deep_dive"

    def test_index_7_is_cv_deep_dive(self):
        assert getCurrentPhase(makeState(7, "long")) == "cv_deep_dive"

    def test_index_11_is_cv_deep_dive(self):
        assert getCurrentPhase(makeState(11, "long")) == "cv_deep_dive"

    def test_index_12_is_dynamic_followup(self):
        assert getCurrentPhase(makeState(12, "long")) == "dynamic_followup"

    def test_index_15_is_dynamic_followup(self):
        assert getCurrentPhase(makeState(15, "long")) == "dynamic_followup"

    def test_index_19_is_dynamic_followup(self):
        assert getCurrentPhase(makeState(19, "long")) == "dynamic_followup"

    def test_index_20_is_closing(self):
        assert getCurrentPhase(makeState(20, "long")) == "closing"

    def test_index_24_is_closing(self):
        assert getCurrentPhase(makeState(24, "long")) == "closing"

    # ── Critical boundary transitions ─────────────────────────────────────────
    def test_transition_icebreaker_to_cv_at_index_4(self):
        assert getCurrentPhase(makeState(3, "long")) == "icebreaker"
        assert getCurrentPhase(makeState(4, "long")) == "cv_deep_dive"

    def test_transition_cv_to_dynamic_at_index_12(self):
        assert getCurrentPhase(makeState(11, "long")) == "cv_deep_dive"
        assert getCurrentPhase(makeState(12, "long")) == "dynamic_followup"

    def test_transition_dynamic_to_closing_at_index_20(self):
        assert getCurrentPhase(makeState(19, "long")) == "dynamic_followup"
        assert getCurrentPhase(makeState(20, "long")) == "closing"


# ════════════════════════════════════════════════════════════════════════════════
# getCurrentPhase — Edge Cases
# ════════════════════════════════════════════════════════════════════════════════

class TestGetCurrentPhaseEdgeCases:

    def test_default_length_medium_on_missing_key(self):
        """Missing interview_length defaults to medium."""
        state = {"current_question_index": 5}
        # Medium: idx 5 → cv_deep_dive (3–7)
        assert getCurrentPhase(state) == "cv_deep_dive"

    def test_default_index_0_on_missing_key(self):
        """Missing current_question_index defaults to 0."""
        state = {"interview_length": "short"}
        assert getCurrentPhase(state) == "icebreaker"

    def test_raises_on_invalid_length(self):
        state = {"current_question_index": 0, "interview_length": "marathon"}
        with pytest.raises(ValueError, match="Invalid interview_length"):
            getCurrentPhase(state)

    def test_all_phases_reachable_in_short(self):
        phases = {getCurrentPhase(makeState(i, "short")) for i in range(7)}
        assert phases == {"icebreaker", "cv_deep_dive", "dynamic_followup", "closing"}

    def test_all_phases_reachable_in_medium(self):
        phases = {getCurrentPhase(makeState(i, "medium")) for i in range(15)}
        assert phases == {"icebreaker", "cv_deep_dive", "dynamic_followup", "closing"}

    def test_all_phases_reachable_in_long(self):
        phases = {getCurrentPhase(makeState(i, "long")) for i in range(25)}
        assert phases == {"icebreaker", "cv_deep_dive", "dynamic_followup", "closing"}


# ════════════════════════════════════════════════════════════════════════════════
# isInterviewComplete
# ════════════════════════════════════════════════════════════════════════════════

class TestIsInterviewComplete:

    def _makeCompletedState(self, planSize: int) -> dict:
        return {
            "question_plan": ["Q"] * planSize,
            "answers": [{"text": "A", "question_index": i} for i in range(planSize)],
            "current_question_index": planSize,
        }

    def _makeIncompleteState(self, planSize: int, answeredCount: int) -> dict:
        return {
            "question_plan": ["Q"] * planSize,
            "answers": [{"text": "A", "question_index": i} for i in range(answeredCount)],
            "current_question_index": answeredCount,
        }

    def test_returns_false_when_plan_empty(self):
        state = {"question_plan": [], "answers": [], "current_question_index": 0}
        assert isInterviewComplete(state) is False

    def test_returns_true_when_short_interview_complete(self):
        assert isInterviewComplete(self._makeCompletedState(6)) is True

    def test_returns_true_when_medium_interview_complete(self):
        assert isInterviewComplete(self._makeCompletedState(12)) is True

    def test_returns_true_when_long_interview_complete(self):
        assert isInterviewComplete(self._makeCompletedState(21)) is True

    def test_returns_false_when_answers_behind_plan(self):
        """Index advanced but no answers yet → not complete."""
        state = {
            "question_plan": ["Q"] * 12,
            "answers": [],
            "current_question_index": 12,
        }
        assert isInterviewComplete(state) is False

    def test_returns_false_at_first_question(self):
        assert isInterviewComplete(self._makeIncompleteState(12, 0)) is False

    def test_returns_false_at_midpoint(self):
        assert isInterviewComplete(self._makeIncompleteState(12, 6)) is False

    def test_returns_false_one_answer_short(self):
        """11/12 answers → not complete."""
        assert isInterviewComplete(self._makeIncompleteState(12, 11)) is False

    def test_returns_true_at_exact_completion(self):
        """12/12 answers and index==12 → complete."""
        assert isInterviewComplete(self._makeCompletedState(12)) is True

    def test_index_beyond_plan_but_answers_short_is_not_complete(self):
        """Guard: index > plan but answers not caught up → not complete."""
        state = {
            "question_plan": ["Q"] * 5,
            "answers": [{"text": "A"}] * 3,
            "current_question_index": 10,
        }
        assert isInterviewComplete(state) is False


# ════════════════════════════════════════════════════════════════════════════════
# getFollowupCount
# ════════════════════════════════════════════════════════════════════════════════

class TestGetFollowupCount:

    def _makeFollowupQuestion(self, parentIdx: int, followupCount: int) -> dict:
        return {
            "index": 99,
            "text": "Follow-up question?",
            "parent_question_index": parentIdx,
            "followup_count": followupCount,
        }

    def test_returns_0_when_no_followups(self):
        state = makeState(askedQuestions=[{"index": 0, "followup_count": 0}])
        assert getFollowupCount(state, 0) == 0

    def test_counts_one_followup(self):
        state = makeState(askedQuestions=[
            {"index": 0, "followup_count": 0},
            self._makeFollowupQuestion(parentIdx=0, followupCount=1),
        ])
        assert getFollowupCount(state, 0) == 1

    def test_counts_two_followups(self):
        state = makeState(askedQuestions=[
            {"index": 0, "followup_count": 0},
            self._makeFollowupQuestion(parentIdx=0, followupCount=1),
            self._makeFollowupQuestion(parentIdx=0, followupCount=2),
        ])
        assert getFollowupCount(state, 0) == 2

    def test_does_not_count_followups_for_other_questions(self):
        """Followups for question 1 must not count toward question 0."""
        state = makeState(askedQuestions=[
            {"index": 0, "followup_count": 0},
            {"index": 1, "followup_count": 0},
            self._makeFollowupQuestion(parentIdx=1, followupCount=1),
        ])
        assert getFollowupCount(state, 0) == 0
        assert getFollowupCount(state, 1) == 1

    def test_returns_0_when_asked_questions_empty(self):
        state = makeState(askedQuestions=[])
        assert getFollowupCount(state, 0) == 0


# ════════════════════════════════════════════════════════════════════════════════
# shouldFollowUp
# ════════════════════════════════════════════════════════════════════════════════

class TestShouldFollowUp:

    def _makeQuestion(self, index: int, parentIdx=None, followupCount=0) -> dict:
        q = {"index": index, "text": "Q?", "followup_count": followupCount}
        if parentIdx is not None:
            q["parent_question_index"] = parentIdx
        return q

    def _makeAnswer(self, text: str, questionIndex: int = 0) -> dict:
        return {"text": text, "question_index": questionIndex}

    def _makeFeedback(self, scorePreview: int) -> dict:
        return {"score_preview": scorePreview, "answer_index": 0}

    def test_returns_false_when_no_questions(self):
        state = makeState()
        assert shouldFollowUp(state) is False

    def test_returns_false_when_no_answers(self):
        state = makeState(askedQuestions=[self._makeQuestion(0)])
        assert shouldFollowUp(state) is False

    def test_returns_false_when_followup_at_ceiling(self):
        """Hard ceiling: 2 follow-ups already generated → always False."""
        state = makeState(
            askedQuestions=[
                {"index": 0, "followup_count": 0},
                {"index": 1, "parent_question_index": 0, "followup_count": 1, "text": "F?"},
                {"index": 2, "parent_question_index": 0, "followup_count": 2, "text": "F?"},
            ],
            answers=[self._makeAnswer("A good answer " * 20)],
            coachingFeedback=[self._makeFeedback(9)],  # High score — no score signal
        )
        # 2 followups for question 0 → ceiling hit
        # (getFollowupCount will count 2 for parent=0)
        assert shouldFollowUp(state) is False

    def test_returns_true_when_score_below_7(self):
        state = makeState(
            askedQuestions=[self._makeQuestion(0)],
            answers=[self._makeAnswer("Short answer.")],
            coachingFeedback=[self._makeFeedback(6)],  # Below threshold
        )
        assert shouldFollowUp(state) is True

    def test_returns_true_when_answer_has_few_words(self):
        """Answer < 50 words triggers follow-up heuristic."""
        state = makeState(
            askedQuestions=[self._makeQuestion(0)],
            answers=[self._makeAnswer("I did some work there.")],
            coachingFeedback=[self._makeFeedback(8)],  # Good score, but answer is short
        )
        assert shouldFollowUp(state) is True

    def test_returns_false_when_score_high_and_answer_long(self):
        """Good score + verbose answer → no follow-up needed."""
        longAnswer = "word " * 60  # 60 words — above 50 word threshold
        state = makeState(
            askedQuestions=[self._makeQuestion(0)],
            answers=[self._makeAnswer(longAnswer)],
            coachingFeedback=[self._makeFeedback(8)],
        )
        assert shouldFollowUp(state) is False

    def test_max_followups_overrides_low_score(self):
        """Even a score of 1 cannot override the hard ceiling."""
        state = makeState(
            askedQuestions=[
                {"index": 0, "followup_count": 0},
                {"index": 1, "parent_question_index": 0, "followup_count": 1, "text": "F?"},
                {"index": 2, "parent_question_index": 0, "followup_count": 2, "text": "F?"},
            ],
            answers=[self._makeAnswer("bad answer")],
            coachingFeedback=[self._makeFeedback(1)],  # Terrible score
        )
        # 2 followups already for question 0 → ceiling enforced
        assert shouldFollowUp(state) is False

    # Helper to make follow-up question (avoids walrus operator issues above)
    def _makeFollowupQuestion(self, parentIdx: int, followupCount: int) -> dict:
        return {
            "index": 99,
            "text": "Follow-up?",
            "parent_question_index": parentIdx,
            "followup_count": followupCount,
        }
