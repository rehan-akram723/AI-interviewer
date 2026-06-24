# ─────────────────────────────────────────────────────────────────────────────
# backend/src/schemas/candidateSchema.py
#
# Pydantic models for CandidateProfile and its nested types.
# These are the persistent data models stored as JSON under data/candidates/.
#
# Naming note: Field names use snake_case inside Pydantic models because they
# map directly to JSON keys stored on disk and passed in API payloads.
# File/module names use camelCase per project convention.
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import List, Optional


class Education(BaseModel):
    """A single educational entry from the candidate's CV."""
    institution: str
    degree: str
    field: str
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None


class Experience(BaseModel):
    """A single work experience entry from the candidate's CV."""
    company: str
    role: str
    duration: str
    description: str
    technologies: List[str] = Field(default_factory=list)


class Project(BaseModel):
    """A single project entry from the candidate's CV."""
    name: str
    description: str
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class CandidateProfile(BaseModel):
    """
    Persistent candidate entity. One JSON file per candidate under data/candidates/.
    Stable across multiple interview sessions — session_ids grows with each attempt.

    Hallucination Protection:
        confirmed_skills  → explicitly stated in CV. Used for technical scoring.
        uncertain_skills  → inferred/low-confidence. Stored for logging ONLY.
    """
    candidate_id: str
    """UUID, stable across all sessions for this candidate."""

    full_name: str
    email: Optional[str] = None

    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)

    confirmed_skills: List[str] = Field(default_factory=list)
    """High-confidence skills — explicitly listed or clearly demonstrated in CV."""

    uncertain_skills: List[str] = Field(default_factory=list)
    """Low-confidence skills — inferred from context. Not used in evaluation."""

    motivation: str = ""
    """Concise motivation summary extracted from the motivation letter."""

    target_role: str = ""
    """Extracted from the job description."""

    target_company: str = ""
    """Provided directly by the user at setup."""

    required_skills_from_jd: List[str] = Field(default_factory=list)
    """All skills listed as required/preferred in the job description."""

    skills_gap: List[str] = Field(default_factory=list)
    """
    Skills from required_skills_from_jd NOT found in confirmed_skills.
    Computed from confirmed_skills only — uncertain_skills never close the gap.
    """

    session_ids: List[str] = Field(default_factory=list)
    """All InterviewSession IDs linked to this candidate. Grows over time."""

    created_at: str = ""
    """ISO 8601 timestamp of first profile creation."""
