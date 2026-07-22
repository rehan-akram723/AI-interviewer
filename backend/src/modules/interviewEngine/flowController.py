# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/interviewEngine/flowController.py
#
# Flow Controller — Dynamic phase boundaries + interview completion detection
#
# Responsibilities:
#   1. Compute the current interview phase from the question index and length config.
#   2. Detect when the interview is fully complete.
#   3. Provide follow-up count helpers (used by FollowUpAgent and ConductorAgent).
#
# Phase boundary model (from manifest §5.7):
#
#   Length   | Total    | Icebreaker | CV Deep Dive | Dynamic/Followup | Closing
#   ─────────┼──────────┼────────────┼──────────────┼──────────────────┼────────
#   short    | 5–7      | 1          | 2            | 2                | 1
#   medium   | 10–15    | 2–3        | 4–5          | 4–5              | 2
#   long     | 18–25    | 3–4        | 7–8          | 7–8              | 3
#
# Encoded as index boundaries (0-based, inclusive start / exclusive end):
#
#   short:   [0,0] icebreaker | [1,2] cv_deep_dive | [3,4] dynamic_followup | [5+] closing
#   medium:  [0,2] icebreaker | [3,7] cv_deep_dive | [8,12] dynamic_followup | [13+] closing
#   long:    [0,3] icebreaker | [4,11] cv_deep_dive | [12,19] dynamic_followup | [20+] closing
#
# Total question targets:
#   short  → target 6  (midpoint of 5–7)
#   medium → target 12 (midpoint of 10–15)
#   long   → target 21 (midpoint of 18–25)
#
# Exports: getCurrentPhase, isInterviewComplete, getFollowupCount, shouldFollowUp
#          PHASE_BOUNDARIES, LENGTH_TARGETS, MAX_FOLLOWUPS_PER_QUESTION
# ─────────────────────────────────────────────────────────────────────────────

from typing import Literal, Optional

# ── Hard System Constants ──────────────────────────────────────────────────────
MAX_FOLLOWUPS_PER_QUESTION: int = 2
"""Hard ceiling on follow-up chains per original question. Never adjust without manifest update."""

# ── Length-aware follow-up cap ─────────────────────────────────────────────────
# Short interviews get only 1 follow-up max per question (tight schedule).
MAX_FOLLOWUPS_BY_LENGTH: dict[str, int] = {
    "short":  1,
    "medium": 2,
    "long":   2,
}

# ── Absolute hard max questions per length ─────────────────────────────────────
# These are the HARD CEILINGS — the conductor will never exceed these regardless
# of what the question plan says. Prevents runaway or hallucinated extra questions.
MAX_QUESTIONS_PER_LENGTH: dict[str, int] = {
    "short":  7,
    "medium": 15,
    "long":   25,
}

# ── Phase Boundaries ──────────────────────────────────────────────────────────
# Each entry: (icebreaker_end_inclusive, cv_deep_dive_end_inclusive, dynamic_followup_end_inclusive)
# Any index > dynamic_followup_end → closing phase.
PHASE_BOUNDARIES: dict[str, tuple[int, int, int]] = {
    "short":  (0, 2, 4),    # idx 0 = icebreaker; 1–2 = cv_deep_dive; 3–4 = dynamic_followup; 5+ = closing
    "medium": (2, 7, 12),   # idx 0–2 = icebreaker; 3–7 = cv_deep_dive; 8–12 = dynamic_followup; 13+ = closing
    "long":   (3, 11, 19),  # idx 0–3 = icebreaker; 4–11 = cv_deep_dive; 12–19 = dynamic_followup; 20+ = closing
}

# ── Question Count Targets ─────────────────────────────────────────────────────
# Midpoint of each manifest range. Used by InterviewPlannerAgent to size the plan.
LENGTH_TARGETS: dict[str, dict[str, int]] = {
    "short": {
        "total": 6,          # range: 5–7; hard max 7
        "icebreaker": 1,
        "cv_deep_dive": 2,
        "dynamic_followup": 2,
        "closing": 1,
    },
    "medium": {
        "total": 12,         # range: 10–15; hard max 15
        "icebreaker": 2,
        "cv_deep_dive": 4,
        "dynamic_followup": 4,
        "closing": 2,
    },
    "long": {
        "total": 20,         # range: 18–25; hard max 25
        "icebreaker": 3,
        "cv_deep_dive": 7,
        "dynamic_followup": 7,
        "closing": 3,        # 3+7+7+3 = 20
    },
}

# ── Valid length literals ──────────────────────────────────────────────────────
_VALID_LENGTHS = frozenset(PHASE_BOUNDARIES.keys())



def getCurrentPhase(
    state: dict,
) -> Literal["icebreaker", "cv_deep_dive", "dynamic_followup", "closing"]:
    """
    Dynamically compute the interview phase for the current question index.

    The phase boundaries are determined solely by `interview_length` and
    `current_question_index` — NOT by `current_phase` stored in the state,
    which may be stale. This function is the authoritative source.

    Args:
        state: InterviewSession dict. Reads:
            - state["current_question_index"]: 0-based index of the NEXT question.
            - state["interview_length"]: "short" | "medium" | "long".

    Returns:
        The phase string: "icebreaker" | "cv_deep_dive" | "dynamic_followup" | "closing".

    Raises:
        ValueError: If interview_length is not one of the supported values.
    """
    idx: int = state.get("current_question_index", 0)
    length: str = state.get("interview_length", "medium")

    if length not in _VALID_LENGTHS:
        raise ValueError(
            f"Invalid interview_length '{length}'. Must be one of: {sorted(_VALID_LENGTHS)}"
        )

    icebreakerEnd, cvDeepDiveEnd, dynamicFollowupEnd = PHASE_BOUNDARIES[length]

    if idx <= icebreakerEnd:
        return "icebreaker"
    elif idx <= cvDeepDiveEnd:
        return "cv_deep_dive"
    elif idx <= dynamicFollowupEnd:
        return "dynamic_followup"
    else:
        return "closing"


def isInterviewComplete(state: dict) -> bool:
    """
    Return True when all planned questions have been asked AND answered.

    Completion criteria:
        1. question_plan is non-empty (planner has run).
        2. The number of answers equals or exceeds the number of questions in the plan.
        3. current_question_index has advanced past the last plan item.

    Note: We use the smaller of (plan length, answers count) as the ground truth
    because the ConductorAgent increments current_question_index before the answer
    is recorded. Using both guards prevents premature completion signals.

    Args:
        state: InterviewSession dict.

    Returns:
        True if interview is over, False if questions remain.
    """
    questionPlan: list = state.get("question_plan", [])
    answers: list = state.get("answers", [])
    currentIndex: int = state.get("current_question_index", 0)

    if not questionPlan:
        # Plan hasn't been built yet — definitely not complete
        return False

    planLength = len(questionPlan)
    answersCount = len(answers)

    # Both conditions must hold: index exhausted AND answers match plan length
    return currentIndex >= planLength and answersCount >= planLength


def getFollowupCount(state: dict, questionIndex: int) -> int:
    """
    Count how many follow-up questions have been generated for a given
    original question index.

    A follow-up question is identified by `parent_question_index == questionIndex`
    in the asked_questions list.

    Args:
        state:         InterviewSession dict.
        questionIndex: The 0-based index of the original question.

    Returns:
        Integer count of follow-ups generated for that question.
    """
    askedQuestions: list = state.get("asked_questions", [])
    return sum(
        1
        for q in askedQuestions
        if q.get("parent_question_index") == questionIndex
        and q.get("followup_count", 0) > 0
    )


def shouldFollowUp(state: dict) -> bool:
    """
    Determine whether a follow-up should be generated after the last answer.

    Rules:
        1. The last question's follow-up count must be < MAX_FOLLOWUPS_PER_QUESTION.
           If already at or above the limit → always return False (hard ceiling).
        2. There must be at least one answer in the session.
        3. The last coaching score_preview must be < 7 (below threshold → probe deeper)
           OR the last answer is non-empty and meaningful (heuristic: > 30 words).

    This function provides the decision signal. The FollowUpAgent makes the final
    LLM call to generate the actual follow-up question text.

    Args:
        state: InterviewSession dict.

    Returns:
        True if a follow-up should be attempted, False if the conductor should advance.
    """
    askedQuestions: list = state.get("asked_questions", [])
    answers: list = state.get("answers", [])
    coachingFeedback: list = state.get("coaching_feedback", [])

    if not askedQuestions or not answers:
        return False

    # Get the last original question index (non-follow-up question)
    lastQuestion = askedQuestions[-1]
    parentIdx: Optional[int] = lastQuestion.get("parent_question_index")
    # If it's itself an original question, its own index is the parent
    lastOriginalIdx = parentIdx if parentIdx is not None else lastQuestion.get("index", 0)

    # Check hard ceiling first
    followupCount = getFollowupCount(state, lastOriginalIdx)
    if followupCount >= MAX_FOLLOWUPS_PER_QUESTION:
        return False

    # Check score signal if coaching feedback available
    if coachingFeedback:
        lastScore = coachingFeedback[-1].get("score_preview", 10)
        if lastScore < 7:
            return True

    # Word count heuristic: short answers suggest the candidate needs probing
    lastAnswerText: str = answers[-1].get("text", "") if answers else ""
    wordCount = len(lastAnswerText.split())
    if wordCount < 50:
        return True

    return False


async def process_answer_pipeline(state: dict) -> dict:
    """
    Run the live coach, difficulty calibrator, and follow-up agents concurrently.
    Returns a dict with coaching_feedback, difficulty_level, and next_question.
    Raises PipelineError if any agent fails.
    """
    import asyncio
    from src.agents.liveCoachAgent import liveCoachAgent
    from src.agents.difficultyCalibratorAgent import difficultyCalibratorAgent
    from src.agents.followUpAgent import followUpAgent
    from src.core.exceptions import PipelineError

    loop = asyncio.get_event_loop()

    async def safe_run(agent_name: str, agent_func, state_ref: dict):
        try:
            return await loop.run_in_executor(None, agent_func, state_ref)
        except Exception as e:
            raise PipelineError(agentName=agent_name, originalException=e)

    results = await asyncio.gather(
        safe_run("live_coach_agent", liveCoachAgent, state),
        safe_run("difficulty_calibrator_agent", difficultyCalibratorAgent, state),
        safe_run("followup_agent", followUpAgent, state)
    )

    coach_res, calib_res, followup_res = results

    return {
        "coaching_feedback": coach_res.get("coaching_feedback"),
        "difficulty_level": calib_res.get("difficulty_level"),
        "next_question": followup_res.get("next_question")
    }
