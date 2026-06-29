# ─────────────────────────────────────────────────────────────────────────────
# backend/src/schemas/reportSchema.py
#
# Pydantic models for the final Interview Report and cross-session Progress Comparisons.
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class DimensionScore(BaseModel):
    """
    A calculated score and narrative for a single evaluation dimension.
    """
    score: float = Field(ge=1.0, le=10.0)
    """Numeric score from 1.0 to 10.0."""

    evidence: List[str] = Field(default_factory=list)
    """Hard data points justifying the score (e.g., filler word counts, missing STAR)."""

    rationale: str
    """LLM-generated narrative connecting the evidence to the final score."""


class InterviewReport(BaseModel):
    """
    The final finalized structured output for a completed interview session.
    """
    session_id: str
    candidate_id: str
    interview_mode: str
    interview_length: str

    overall_score: float = Field(ge=1.0, le=10.0)
    """Composite score across all dimensions."""

    dimension_scores: Dict[str, DimensionScore]
    """
    Map of dimension names to scores. Keys typically include:
    communication_clarity, technical_relevance, problem_solving,
    motivation_fit, confidence, listening_comprehension.
    """

    executive_summary: str
    """High-level summary of the candidate's performance."""

    top_strengths: List[str]
    """3-5 key strengths demonstrated."""

    areas_for_improvement: List[str]
    """1-3 critical areas to work on."""

    recommended_next_steps: str
    """Actionable advice for the candidate's prep."""


class ProgressComparison(BaseModel):
    """
    Delta analysis between two InterviewReport instances.
    """
    overall_score_delta: float
    """Difference in overall score (current - previous). Positive means improvement."""

    dimension_deltas: Dict[str, float]
    """Difference per dimension (current - previous)."""

    strengths_improved: List[str]
    """Areas where the candidate showed marked improvement."""

    weaknesses_improved: List[str]
    """Previous weaknesses that were addressed successfully."""

    regressions_detected: List[str]
    """Areas that worsened compared to the previous session."""

    comparison_narrative: str
    """LLM-generated 3-4 sentence summary of the progress."""
