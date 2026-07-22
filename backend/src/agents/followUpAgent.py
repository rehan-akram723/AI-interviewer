# ─────────────────────────────────────────────────────────────────────────────
# backend/src/agents/followUpAgent.py
#
# Follow-Up Agent — LangGraph node function
#
# Enforces the absolute system guardrail on follow-up chains and then
# uses the LLM to decide whether to probe the last answer further or advance.
#
# Decision pipeline (strictly in this order):
#
#   1. HARD CEILING CHECK (no LLM):
#      - Determine the parent_question_index of the last question asked.
#      - Count all follow-ups already generated for that parent.
#      - If followup_count >= MAX_FOLLOWUPS_PER_QUESTION (2):
#            → signal "advance" immediately, no LLM call.
#
#   2. CALIBRATOR SIGNAL CHECK (no LLM):
#      - If state["suggest_followup"] is True (DifficultyCalibrator flagged strong STAR):
#            → proactively go to LLM to probe deeper.
#
#   3. COACH SCORE GATE (no LLM):
#      - If the last coaching score_preview >= 7 AND answer word count >= 50:
#            → skip LLM call, signal "advance" (the answer was good enough)
#
#   4. LLM FOLLOW-UP DECISION:
#      - Call LLM with the last Q+A pair and score.
#      - LLM returns {should_followup: bool, followup_question: str | null}.
#      - If should_followup=True and followup_question is non-empty:
#            → Build a new Question schema with incremented followup_count.
#            → Inject it as the NEXT question to be delivered.
#      - If should_followup=False or followup_question is empty:
#            → signal "advance".
#
# State key "should_advance":
#   True  → interviewGraph routes to conductorAgent (next planned question)
#   False → interviewGraph routes back into the loop (follow-up delivered already)
#
# LangGraph contract:
#   Input:  Full InterviewSession state dict
#   Output: Partial dict:
#           {
#               "next_question":         dict | None  (Question if follow-up generated)
#               "asked_questions":       list          (appended if follow-up generated)
#               "should_advance":        bool
#               "step_log":              list
#           }
#
# Exports: followUpAgent
# ─────────────────────────────────────────────────────────────────────────────

import logging
from datetime import datetime, timezone

from src.core.llmClient import callLlm
from src.modules.interviewEngine.flowController import (
    getFollowupCount,
    MAX_FOLLOWUPS_PER_QUESTION,
    MAX_FOLLOWUPS_BY_LENGTH,
)
from src.schemas.interviewSchema import Question

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────────
_FOLLOWUP_SYSTEM_PROMPT = """\
You are an expert interviewer deciding whether to probe an answer more deeply \
or move on to the next planned question. Be decisive. Reference specific things \
the candidate said. Return only valid JSON.\
"""

# ── Follow-up decision prompt ─────────────────────────────────────────────────
_FOLLOWUP_PROMPT_TEMPLATE = """\
The candidate just answered an interview question.

QUESTION:
{question}

CANDIDATE'S ANSWER:
{answer}

COACHING SCORE: {score}/10

INTERVIEW CONTEXT:
Role: {roleCategory}
Phase: {phase}
Difficulty: {difficultyLevel}/5

TOPICS ALREADY COVERED IN THIS SESSION (do NOT ask about any of these again):
{coveredTopics}

Decide whether to generate a follow-up question or advance to the next planned question.

Generate a follow-up question ONLY IF the candidate:
1. Mentioned a specific project, technology, decision, or event worth exploring deeper.
2. Made a claim that would benefit from a concrete example ("Tell me more about X you mentioned").
3. Gave an answer that was short or vague on a key technical point.

Do NOT generate a follow-up if:
- The answer was comprehensive and self-contained.
- The candidate already gave concrete examples with results.
- A follow-up would feel repetitive given the interview context.
- The topic overlaps with any question in the TOPICS ALREADY COVERED list above.

If generating a follow-up: the question MUST directly reference something they said.
Bad: "Tell me more about your experience."
Good: "You mentioned refactoring the authentication layer — what specific design pattern did you use?"

Return JSON only:
{{
  "should_followup": true | false,
  "followup_question": "The follow-up question text here" | null
}}
"""

# ── Score / word count gates ───────────────────────────────────────────────────
_GOOD_SCORE_GATE = 7      # score_preview >= this AND word_count >= below → advance
_GOOD_WORD_COUNT_GATE = 50


def followUpAgent(state: dict) -> dict:
    """
    LangGraph node: Follow-Up Agent.

    Reads from state:
        state["asked_questions"]  — list of Question dicts
        state["answers"]          — list of Answer dicts
        state["coaching_feedback"]— list of CoachingFeedback dicts
        state["suggest_followup"] — bool flag from DifficultyCalibrator (Rule 4)
        state["role_category"]    — role category string
        state["difficulty_level"] — current difficulty int

    Returns:
        {
            "next_question":   dict | None,
            "asked_questions": list,
            "should_advance":  bool,
            "step_log":        list
        }
    """
    stepLog = list(state.get("step_log", []))
    askedQuestions: list = list(state.get("asked_questions", []))
    answers: list = state.get("answers", [])
    coachingFeedback: list = state.get("coaching_feedback", [])
    suggestFollowup: bool = state.get("suggest_followup", False)
    roleCategory: str = state.get("role_category", "software_engineer")
    difficultyLevel: int = state.get("difficulty_level", 2)

    # ── Guards: no follow-up possible if no questions or answers exist ─────────
    if not askedQuestions or not answers:
        stepLog.append("[followUpAgent] No questions/answers — advancing plan.")
        return {
            "next_question": None,
            "asked_questions": askedQuestions,
            "should_advance": True,
            "step_log": stepLog,
        }

    lastQuestion: dict = askedQuestions[-1]
    lastAnswer: dict = answers[-1]
    answerText: str = lastAnswer.get("text", "").strip()

    # Determine the parent question index for follow-up counting
    # If the last question itself was a follow-up, look at its parent
    parentIdx: int = lastQuestion.get("parent_question_index")
    if parentIdx is None:
        parentIdx = lastQuestion.get("index", 0)

    # ── STEP 1: HARD CEILING CHECK (length-aware) ─────────────────────────────
    interviewLength: str = state.get("interview_length", "medium")
    lengthCeiling = MAX_FOLLOWUPS_BY_LENGTH.get(interviewLength, MAX_FOLLOWUPS_PER_QUESTION)
    followupsUsed = getFollowupCount(state, parentIdx)
    if followupsUsed >= lengthCeiling:
        stepLog.append(
            f"[followUpAgent] Hard ceiling reached: {followupsUsed}/{lengthCeiling} "
            f"follow-ups for question {parentIdx} (length={interviewLength}). Advancing plan."
        )
        return {
            "next_question": None,
            "asked_questions": askedQuestions,
            "should_advance": True,
            "step_log": stepLog,
        }

    # ── STEP 2: SCORE GATE (skip LLM if answer was strong enough) ─────────────
    lastScore: int = 10
    if coachingFeedback:
        lastScore = coachingFeedback[-1].get("score_preview", 10)

    wordCount = len(answerText.split())

    # Only skip if calibrator did NOT flag suggest_followup
    if (not suggestFollowup
            and lastScore >= _GOOD_SCORE_GATE
            and wordCount >= _GOOD_WORD_COUNT_GATE):
        stepLog.append(
            f"[followUpAgent] Score gate cleared: score={lastScore} ≥ {_GOOD_SCORE_GATE}, "
            f"words={wordCount} ≥ {_GOOD_WORD_COUNT_GATE}. Advancing plan. No LLM call."
        )
        return {
            "next_question": None,
            "asked_questions": askedQuestions,
            "should_advance": True,
            "step_log": stepLog,
        }

    # ── STEP 3: LLM DECISION ───────────────────────────────────────────────────
    questionText: str = lastQuestion.get("text", "")
    questionPhase: str = lastQuestion.get("phase", "cv_deep_dive")

    # Build a compact history of all questions already asked to inject into prompt
    coveredTopics = "\n".join(
        f"  - Q{i+1}: {q.get('text', '')[:100]}"
        for i, q in enumerate(askedQuestions[:-1])  # exclude the current question
    ) or "  (None yet — this is the first question)"

    if suggestFollowup:
        stepLog.append(
            "[followUpAgent] DifficultyCalibrator flagged strong structure — "
            "probing deeper via LLM."
        )
    else:
        stepLog.append(
            f"[followUpAgent] Score={lastScore}, words={wordCount} — consulting LLM."
        )

    prompt = _FOLLOWUP_PROMPT_TEMPLATE.format(
        question=questionText or "(Question not recorded)",
        answer=answerText or "(No answer text)",
        score=lastScore,
        roleCategory=roleCategory,
        phase=questionPhase,
        difficultyLevel=difficultyLevel,
        coveredTopics=coveredTopics,
    )

    try:
        rawOutput = callLlm(
            prompt=prompt,
            systemPrompt=_FOLLOWUP_SYSTEM_PROMPT,
            temperature=0.3,
            maxTokens=400,
            jsonMode=True,
        )
    except Exception as exc:
        logger.warning("followUpAgent: LLM call failed — advancing plan. Error: %s", exc)
        stepLog.append(f"[followUpAgent] LLM error: {exc}. Advancing plan.")
        return {
            "next_question": None,
            "asked_questions": askedQuestions,
            "should_advance": True,
            "step_log": stepLog,
        }

    # ── STEP 4: Parse LLM output ──────────────────────────────────────────────
    if not isinstance(rawOutput, dict):
        stepLog.append("[followUpAgent] Unexpected LLM output — advancing plan.")
        return {
            "next_question": None,
            "asked_questions": askedQuestions,
            "should_advance": True,
            "step_log": stepLog,
        }

    shouldFollowup: bool = bool(rawOutput.get("should_followup", False))
    followupQuestionText: str = str(rawOutput.get("followup_question") or "").strip()

    if not shouldFollowup or not followupQuestionText:
        stepLog.append(
            f"[followUpAgent] LLM decided: advance plan "
            f"(should_followup={shouldFollowup})."
        )
        return {
            "next_question": None,
            "asked_questions": askedQuestions,
            "should_advance": True,
            "step_log": stepLog,
        }

    # ── STEP 5: Build the follow-up Question object ───────────────────────────
    newFollowupCount = followupsUsed + 1
    newQuestionIndex = len(askedQuestions)  # Next position in the sequence
    answerIdx = lastAnswer.get("question_index", len(answers) - 1)
    now = datetime.now(timezone.utc).isoformat()

    followupQuestion = Question(
        index=newQuestionIndex,
        text=followupQuestionText,
        phase=questionPhase,          # Follow-ups inherit the parent's phase
        category="behavioral",        # Follow-ups are always exploratory/behavioral
        difficulty=difficultyLevel,
        parent_question_index=parentIdx,
        based_on_answer_index=answerIdx,
        followup_count=newFollowupCount,
        asked_at=now,
    )
    followupDict = followupQuestion.model_dump()
    askedQuestions.append(followupDict)

    stepLog.append(
        f"[followUpAgent] Follow-up #{newFollowupCount} generated for "
        f"question {parentIdx}: \"{followupQuestionText[:60]}...\""
        if len(followupQuestionText) > 60 else
        f"[followUpAgent] Follow-up #{newFollowupCount} generated for "
        f"question {parentIdx}: \"{followupQuestionText}\""
    )

    return {
        "next_question": followupDict,
        "asked_questions": askedQuestions,
        "should_advance": False,  # Do NOT advance — deliver follow-up next
        "step_log": stepLog,
    }
