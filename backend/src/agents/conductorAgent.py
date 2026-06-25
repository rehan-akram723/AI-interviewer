# ─────────────────────────────────────────────────────────────────────────────
# backend/src/agents/conductorAgent.py
#
# Conductor Agent — LangGraph node function
#
# Responsibilities:
#   1. Check whether the interview is complete (all planned questions delivered).
#   2. If not complete: pull the next question from question_plan, compute its
#      current phase via getCurrentPhase(), wrap it into a Question schema object.
#   3. Advance current_question_index and update current_phase in state.
#   4. Append the Question object (as dict) to asked_questions.
#
# Design decisions:
#   - The Conductor is intentionally thin: it does NOT call the LLM. It is a
#     deterministic router. The LLM call is only in the FollowUpAgent (Milestone 2.3)
#     for personalised follow-up questions.
#   - All "current_phase" updates go through getCurrent Phase() — never hardcoded.
#   - The Question object is serialised as a dict (not Pydantic) for LangGraph
#     state dict compatibility.
#
# LangGraph contract:
#   Input:  Full InterviewSession state dict
#   Output: Partial dict — only the keys this agent modifies:
#           {
#               "next_question":            dict (Question schema),
#               "asked_questions":          list (appended),
#               "current_question_index":   int  (incremented),
#               "current_phase":            str  (updated),
#               "status":                   str  ("in_progress" or "completed"),
#               "step_log":                 list (appended)
#           }
#
# Exports: conductorAgent
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone
from typing import Optional

from src.modules.interviewEngine.flowController import (
    getCurrentPhase,
    isInterviewComplete,
)
from src.schemas.interviewSchema import Question


def conductorAgent(state: dict) -> dict:
    """
    LangGraph node: Conductor Agent.

    Delivers the next planned question to the candidate, or signals interview
    completion. This agent runs:
      - Once at the start of the interview (first question).
      - Once after every answer is processed (next question in sequence).
      - When the FollowUpAgent signals "advance" (skip follow-up, move to plan).

    Complete interview signal:
      When isInterviewComplete() returns True, this agent returns:
        {
          "next_question": None,
          "status": "completed",
          "step_log": [...]
        }
      The graph's conditional edge uses this to route to the END node.

    Args:
        state: Full InterviewSession dict.

    Returns:
        Partial state update dict.
    """
    stepLog = list(state.get("step_log", []))
    questionPlan: list = state.get("question_plan", [])
    currentIndex: int = state.get("current_question_index", 0)
    difficultyLevel: int = state.get("difficulty_level", 2)
    interviewLength: str = state.get("interview_length", "medium")
    interviewMode: str = state.get("interview_mode", "mixed")

    # ── 1. Completion check ────────────────────────────────────────────────────
    if isInterviewComplete(state):
        stepLog.append(
            f"[conductorAgent] Interview complete. "
            f"{len(state.get('answers', []))} answers recorded."
        )
        return {
            "next_question": None,
            "status": "completed",
            "step_log": stepLog,
        }

    # ── 2. Guard: plan must be non-empty ───────────────────────────────────────
    if not questionPlan:
        stepLog.append(
            "[conductorAgent] ERROR: question_plan is empty. "
            "InterviewPlannerAgent must run first."
        )
        return {
            "next_question": None,
            "status": "error",
            "error": "conductorAgent: question_plan is empty. Run interviewPlannerAgent first.",
            "step_log": stepLog,
        }

    if currentIndex >= len(questionPlan):
        # Redundant safety net — isInterviewComplete() should catch this
        stepLog.append("[conductorAgent] Index out of bounds. Interview complete.")
        return {
            "next_question": None,
            "status": "completed",
            "step_log": stepLog,
        }

    # ── 3. Compute current phase ───────────────────────────────────────────────
    currentPhase = getCurrentPhase(state)

    # ── 4. Pull next question from plan ───────────────────────────────────────
    questionText: str = questionPlan[currentIndex]

    # Determine question category from phase
    # Phase → most natural category mapping (used for scoring metadata)
    phaseToCategory: dict[str, str] = {
        "icebreaker":       "motivational",
        "cv_deep_dive":     "technical",
        "dynamic_followup": "behavioral",
        "closing":          "motivational",
    }
    category = phaseToCategory.get(currentPhase, "behavioral")

    # Override with mode signal if mode is strongly typed
    if interviewMode == "behavioral":
        category = "behavioral"
    elif interviewMode == "technical" and currentPhase != "icebreaker":
        category = "technical"
    elif interviewMode == "system_design" and currentPhase not in ("icebreaker", "closing"):
        category = "system_design"

    # ── 5. Build Question schema dict ─────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    question = Question(
        index=currentIndex,
        text=questionText,
        phase=currentPhase,
        category=category,
        difficulty=difficultyLevel,
        followup_count=0,
        asked_at=now,
    )
    questionDict = question.model_dump()

    # ── 6. Update state partials ───────────────────────────────────────────────
    askedQuestions = list(state.get("asked_questions", []))
    askedQuestions.append(questionDict)

    newIndex = currentIndex + 1

    stepLog.append(
        f"[conductorAgent] Delivered question {currentIndex} | "
        f"phase={currentPhase} | category={category} | "
        f"difficulty={difficultyLevel} | "
        f"{newIndex}/{len(questionPlan)} total questions delivered."
    )

    return {
        "next_question": questionDict,
        "asked_questions": askedQuestions,
        "current_question_index": newIndex,
        "current_phase": currentPhase,
        "status": "in_progress",
        "step_log": stepLog,
    }
