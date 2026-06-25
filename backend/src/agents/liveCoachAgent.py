# ─────────────────────────────────────────────────────────────────────────────
# backend/src/agents/liveCoachAgent.py
#
# Live Coach Agent — LangGraph node function
#
# Runs immediately after each candidate answer submission.
# Evaluates the answer across five independent dimensions and returns
# structured, actionable coaching feedback.
#
# Key design decisions:
#   - All five dimensions are scored independently by the LLM.
#     The composite score_preview is NOT a simple average — it is
#     a holistic signal requested directly from the LLM.
#   - score_preview (1–10) is the fast signal for the frontend sidebar.
#     dimension_scores are the granular signals consumed by DifficultyCalibrator.
#   - If the LLM returns malformed JSON, the agent falls back to safe defaults
#     rather than crashing the interview session.
#   - Handles missing answers gracefully (returns a placeholder feedback object
#     if the answer list is empty).
#
# LangGraph contract:
#   Input:  Full InterviewSession state dict
#   Output: Partial dict:
#           {
#               "coaching_feedback": list (appended with new CoachingFeedback dict),
#               "step_log":          list (appended)
#           }
#
# Exports: liveCoachAgent
# ─────────────────────────────────────────────────────────────────────────────

import logging
from datetime import datetime, timezone
from typing import Optional

from src.core.llmClient import callLlm
from src.schemas.interviewSchema import CoachingFeedback

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────────
_COACH_SYSTEM_PROMPT = """\
You are an elite professional interview coach providing real-time, calibrated feedback.
You evaluate candidate answers with precision, honesty, and constructive specificity.
Be encouraging but accurate. Never inflate scores. Focus on concrete, actionable improvements.
Always respond in valid JSON only — no markdown, no commentary outside the JSON block.\
"""

# ── Evaluation prompt ──────────────────────────────────────────────────────────
_COACH_PROMPT_TEMPLATE = """\
The candidate just answered an interview question. Evaluate their response carefully.

INTERVIEW CONTEXT:
Role Category: {roleCategory}
Difficulty Level: {difficultyLevel}/5
Interview Phase: {phase}

QUESTION ASKED:
{question}

CANDIDATE'S ANSWER:
{answer}

EVALUATION CRITERIA:

1. Relevance (1-10):
   Did they directly answer what was asked? Did they stay on topic?
   10 = perfect alignment, 1 = completely off-topic.

2. Clarity (1-10):
   Was the response easy to follow? Clear sentence structure, logical flow?
   10 = crystal clear, 1 = confusing or rambling.

3. Depth (1-10):
   Did they provide sufficient technical or experiential detail without padding?
   10 = thorough with evidence, 1 = vague generalities only.

4. Confidence (1-10):
   Did the answer convey assurance and ownership of their experience?
   10 = assertive and authoritative, 1 = hesitant and self-undermining.

5. Structure (1-10):
   Did they use STAR (Situation, Task, Action, Result) or a clear logical structure?
   10 = textbook STAR, 1 = no discernible structure.

REQUIRED OUTPUT FORMAT (JSON only):
{{
  "feedback_text": "2-3 sentences of specific, actionable coaching. Reference what they said. Start with a strength, then address the key improvement.",
  "score_preview": <integer 1-10, holistic overall signal>,
  "strengths": ["Strength 1", "Strength 2"],
  "improvements": ["Improvement 1", "Improvement 2"],
  "dimension_scores": {{
    "relevance": <integer 1-10>,
    "clarity": <integer 1-10>,
    "depth": <integer 1-10>,
    "confidence": <integer 1-10>,
    "structure": <integer 1-10>
  }}
}}

Rules:
- strengths: 1-3 bullet points. Each must be specific (reference what they said).
- improvements: 1-3 bullet points. Each must be actionable ("next time, do X").
- dimension_scores: All five dimensions MUST be present. Integers only.
- feedback_text: Must be 2-3 sentences. Do not start with "I".
- score_preview: 1-10 integer. Reflects overall impression holistically.

Evaluate now:\
"""

# ── Valid dimension keys ───────────────────────────────────────────────────────
_REQUIRED_DIMENSIONS = {"relevance", "clarity", "depth", "confidence", "structure"}


def _buildFallbackFeedback(answerIndex: int) -> dict:
    """
    Safe fallback CoachingFeedback used when the LLM returns malformed output.
    Scores are neutral (5/10) to avoid artificially skewing the difficulty calibrator.
    """
    return CoachingFeedback(
        answer_index=answerIndex,
        feedback_text=(
            "Your response was noted. Focus on providing specific examples with "
            "clear situation, action, and result components in your next answer."
        ),
        score_preview=5,
        strengths=["Engaged with the question"],
        improvements=[
            "Add concrete examples from your experience",
            "Structure your answer using the STAR method",
        ],
        dimension_scores={
            "relevance": 5,
            "clarity": 5,
            "depth": 5,
            "confidence": 5,
            "structure": 5,
        },
    ).model_dump()


def _sanitiseDimensionScores(rawScores: dict) -> dict:
    """
    Validate and clamp per-dimension scores.
    - Ensures all 5 required dimensions are present.
    - Clamps each value to [1, 10].
    - Fills missing dimensions with 5 (neutral).
    """
    sanitised = {}
    for dim in _REQUIRED_DIMENSIONS:
        rawValue = rawScores.get(dim, 5)
        try:
            clamped = max(1, min(10, int(rawValue)))
        except (TypeError, ValueError):
            clamped = 5
        sanitised[dim] = clamped
    return sanitised


def liveCoachAgent(state: dict) -> dict:
    """
    LangGraph node: Live Coach Agent.

    Reads from state:
        state["answers"]          — list of Answer dicts
        state["asked_questions"]  — list of Question dicts
        state["role_category"]    — detected role category
        state["difficulty_level"] — current difficulty level (1-5)

    Returns:
        {
            "coaching_feedback": list (existing list + new CoachingFeedback dict),
            "step_log":          list (appended)
        }
    """
    stepLog = list(state.get("step_log", []))
    answers: list = state.get("answers", [])
    askedQuestions: list = state.get("asked_questions", [])
    coachingFeedback: list = list(state.get("coaching_feedback", []))
    roleCategory: str = state.get("role_category", "software_engineer")
    difficultyLevel: int = state.get("difficulty_level", 2)

    # ── 1. Guard: need at least one answer ────────────────────────────────────
    if not answers:
        stepLog.append("[liveCoachAgent] No answers in state — skipping evaluation.")
        return {"coaching_feedback": coachingFeedback, "step_log": stepLog}

    lastAnswer: dict = answers[-1]
    answerText: str = lastAnswer.get("text", "").strip()
    answerIndex: int = lastAnswer.get("question_index", len(answers) - 1)

    # ── 2. Find the matching question for this answer ─────────────────────────
    questionText: str = ""
    questionPhase: str = "cv_deep_dive"
    if askedQuestions:
        # Prefer exact question_index match; fall back to last asked question
        for q in reversed(askedQuestions):
            if q.get("index") == answerIndex:
                questionText = q.get("text", "")
                questionPhase = q.get("phase", "cv_deep_dive")
                break
        if not questionText and askedQuestions:
            questionText = askedQuestions[-1].get("text", "")
            questionPhase = askedQuestions[-1].get("phase", "cv_deep_dive")

    if not answerText:
        stepLog.append("[liveCoachAgent] Empty answer text — using fallback feedback.")
        coachingFeedback.append(_buildFallbackFeedback(answerIndex))
        return {"coaching_feedback": coachingFeedback, "step_log": stepLog}

    # ── 3. Build prompt ────────────────────────────────────────────────────────
    prompt = _COACH_PROMPT_TEMPLATE.format(
        roleCategory=roleCategory,
        difficultyLevel=difficultyLevel,
        phase=questionPhase,
        question=questionText or "(Question text not available)",
        answer=answerText,
    )

    stepLog.append(
        f"[liveCoachAgent] Evaluating answer {answerIndex} "
        f"(phase={questionPhase}, difficulty={difficultyLevel})..."
    )

    # ── 4. Call LLM ────────────────────────────────────────────────────────────
    try:
        rawOutput = callLlm(
            prompt=prompt,
            systemPrompt=_COACH_SYSTEM_PROMPT,
            temperature=0.2,   # Low temperature — scoring must be consistent
            maxTokens=800,
            jsonMode=True,
        )
    except Exception as exc:
        logger.warning("liveCoachAgent: LLM call failed — using fallback. Error: %s", exc)
        stepLog.append(f"[liveCoachAgent] LLM error: {exc}. Using fallback feedback.")
        coachingFeedback.append(_buildFallbackFeedback(answerIndex))
        return {"coaching_feedback": coachingFeedback, "step_log": stepLog}

    # ── 5. Parse and validate ─────────────────────────────────────────────────
    if not isinstance(rawOutput, dict):
        stepLog.append(
            f"[liveCoachAgent] Unexpected LLM output type "
            f"({type(rawOutput).__name__}) — using fallback."
        )
        coachingFeedback.append(_buildFallbackFeedback(answerIndex))
        return {"coaching_feedback": coachingFeedback, "step_log": stepLog}

    try:
        # Sanitise dimension scores (clamp, fill missing)
        rawDims = rawOutput.get("dimension_scores", {})
        sanitisedDims = _sanitiseDimensionScores(rawDims)

        # Clamp score_preview to [1, 10]
        rawScore = rawOutput.get("score_preview", 5)
        scorePreview = max(1, min(10, int(rawScore)))

        feedback = CoachingFeedback(
            answer_index=answerIndex,
            feedback_text=str(rawOutput.get("feedback_text", "")).strip()
                          or "Good effort. Focus on adding more specific examples.",
            score_preview=scorePreview,
            strengths=list(rawOutput.get("strengths", []))[:3],
            improvements=list(rawOutput.get("improvements", []))[:3],
            dimension_scores=sanitisedDims,
        )
        coachingFeedback.append(feedback.model_dump())

    except Exception as exc:
        logger.warning("liveCoachAgent: Pydantic validation failed — using fallback. %s", exc)
        stepLog.append(f"[liveCoachAgent] Validation error: {exc}. Using fallback.")
        coachingFeedback.append(_buildFallbackFeedback(answerIndex))
        return {"coaching_feedback": coachingFeedback, "step_log": stepLog}

    stepLog.append(
        f"[liveCoachAgent] Coaching complete. "
        f"score_preview={scorePreview} | "
        f"dims={sanitisedDims}"
    )

    return {
        "coaching_feedback": coachingFeedback,
        "step_log": stepLog,
    }
