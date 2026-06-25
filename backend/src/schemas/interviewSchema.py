# ─────────────────────────────────────────────────────────────────────────────
# backend/src/schemas/interviewSchema.py
#
# Pydantic models for live interview objects: Question, Answer, CoachingFeedback.
# These are the typed objects stored inside InterviewSession.asked_questions,
# InterviewSession.answers, and InterviewSession.coaching_feedback.
#
# Naming note: Field names are snake_case (JSON-compatible). File/module is camelCase.
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import Optional, Literal, List


class Question(BaseModel):
    """
    A single interview question delivered to the candidate.
    Stored in InterviewSession.asked_questions.
    """
    index: int
    """0-based position in the overall interview sequence."""

    text: str
    """The question text as presented to the candidate."""

    phase: Literal["icebreaker", "cv_deep_dive", "dynamic_followup", "closing"]
    """The interview phase this question belongs to."""

    category: str
    """
    Question type: "behavioral" | "technical" | "motivational" |
                   "situational" | "system_design"
    """

    difficulty: int = Field(ge=1, le=5)
    """Difficulty level at the time this question was asked (1–5)."""

    based_on_answer_index: Optional[int] = None
    """If this is a follow-up, the index of the answer that triggered it."""

    parent_question_index: Optional[int] = None
    """Index of the original (non-follow-up) question this follows from."""

    followup_count: int = 0
    """Number of follow-ups generated for the parent question. 0 for original questions."""

    asked_at: str = ""
    """ISO 8601 timestamp of when this question was delivered."""


class Answer(BaseModel):
    """
    A candidate's answer to a single question.
    Stored in InterviewSession.answers (parallel to asked_questions).
    """
    question_index: int
    """Index of the Question this answer responds to."""

    text: str
    """Transcribed or typed answer text."""

    audio_path: Optional[str] = None
    """Filesystem path to the raw audio recording. None in demo mode."""

    answered_at: str = ""
    """ISO 8601 timestamp of when the answer was submitted."""

    duration_seconds: Optional[float] = None
    """How long the candidate took to answer. None if not measured."""


class CoachingFeedback(BaseModel):
    """
    Real-time coaching feedback generated after each answer by LiveCoachAgent.
    Stored in InterviewSession.coaching_feedback.
    Immediately pushed to the frontend via WebSocket.
    """
    answer_index: int
    """Index of the Answer this feedback responds to."""

    feedback_text: str
    """1–3 sentences of actionable, specific coaching feedback."""

    score_preview: int = Field(ge=1, le=10)
    """Quick 1–10 signal. Used by the frontend coaching sidebar."""

    strengths: List[str] = Field(default_factory=list)
    """What the candidate did well. 1–3 bullet points."""

    improvements: List[str] = Field(default_factory=list)
    """What to improve. 1–3 bullet points."""

    dimension_scores: dict = Field(default_factory=dict)
    """
    Per-dimension breakdown:
    {
        "relevance":  1–10,
        "clarity":    1–10,
        "depth":      1–10,
        "confidence": 1–10,
        "structure":  1–10
    }
    Consumed by DifficultyCalibrator to adjust future question difficulty.
    """
