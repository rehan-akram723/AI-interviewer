# ─────────────────────────────────────────────────────────────────────────────
# backend/src/schemas/analysisSchema.py
#
# Pydantic models for multimodal analytics (Audio & Facial).
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import Optional, List


class AudioMetrics(BaseModel):
    """
    Quantitative audio measurements from a single answer.
    Stored in InterviewSession.audio_metrics.
    """
    answer_index: int
    """Index of the Answer these metrics correspond to."""

    words_per_minute: Optional[float] = None
    """Speaking pace. None if duration could not be determined."""

    filler_word_count: int = 0
    """Total occurrences of detected filler words."""

    filler_words_detected: List[str] = Field(default_factory=list)
    """List of specific filler words detected."""

    avg_pause_duration_seconds: Optional[float] = None
    """Average length of silence intervals. None in demo mode."""

    longest_pause_seconds: Optional[float] = None
    """Longest continuous silence. None in demo mode."""

    voice_energy_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    """RMS energy normalized 0-1. None in demo mode."""

    demo_mode: bool = False
    """True if metrics were computed in demo mode (some fields will be None)."""


class FacialMetrics(BaseModel):
    """
    Facial analysis metrics from MediaPipe telemetry for a single answer.
    Stored in InterviewSession.facial_metrics.
    """
    answer_index: int
    """Index of the Answer these metrics correspond to."""

    eye_contact_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    """Time looking at camera. None in demo mode."""

    avg_blink_rate_per_minute: Optional[float] = None
    """Blinks per minute. None in demo mode."""

    head_movement_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    """Aggregated jitter/movement scale. None in demo mode."""

    engagement_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    """Composite engagement rating. None in demo mode."""

    demo_mode: bool = False
    """True if metrics were skipped due to demo mode or missing data."""
