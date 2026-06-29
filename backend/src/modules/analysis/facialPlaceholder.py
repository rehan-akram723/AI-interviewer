# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/analysis/facialPlaceholder.py
#
# Processes MediaPipe telemetry JSON for a single interview answer turn.
#
# Production: Parses and aggregates per-frame boolean/float flags into turn-level 
#             metrics (eye_contact_percentage, avg_blink_rate_per_minute, etc.)
# Demo mode:  Returns a FacialMetrics struct with all metrics set to None.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from typing import Optional

from src.core.appConfig import settings
from src.schemas.analysisSchema import FacialMetrics

logger = logging.getLogger(__name__)

def processFacialData(
    mediapipeJson: Optional[dict],
    answerIndex: int,
    durationSeconds: Optional[float] = None
) -> FacialMetrics:
    """
    Production: Receives MediaPipe JSON from frontend, computes turn-level engagement metrics.
    Demo mode:  Returns FacialMetrics with all fields None, demo_mode=True.
    
    Args:
        mediapipeJson: Dictionary containing frontend telemetry. Expected to have
                       a "frames" list of dicts: 
                       {"lookingAtCamera": bool, "blinkDetected": bool, "headJitter": float}
        answerIndex: Index of the answer.
        durationSeconds: Duration of the answer to calculate per-minute rates.

    Returns:
        FacialMetrics struct.
    """
    if settings.is_demo or mediapipeJson is None:
        if settings.is_production and mediapipeJson is None:
            logger.warning("processFacialData [production]: mediapipeJson is None. Bypassing.")
            
        return FacialMetrics(
            answer_index=answerIndex,
            eye_contact_percentage=None,
            avg_blink_rate_per_minute=None,
            head_movement_score=None,
            engagement_score=None,
            demo_mode=True
        )

    frames = mediapipeJson.get("frames", [])
    if not frames:
        logger.warning("processFacialData [production]: 'frames' array empty in mediapipeJson.")
        return FacialMetrics(
            answer_index=answerIndex,
            demo_mode=True
        )

    # Duration fallback (guess based on 30 FPS if not provided)
    duration = durationSeconds if durationSeconds and durationSeconds > 0 else (len(frames) / 30.0)
    if duration <= 0:
        duration = 1.0

    # 1. Eye contact percentage
    lookingCount = sum(1 for f in frames if f.get("lookingAtCamera") is True)
    eyeContactPercent = (lookingCount / len(frames)) * 100.0

    # 2. Blink rate per minute
    # Count rising edges (False -> True) to count distinct blinks
    blinkCount = 0
    prevBlink = False
    for f in frames:
        currentBlink = f.get("blinkDetected") is True
        if currentBlink and not prevBlink:
            blinkCount += 1
        prevBlink = currentBlink
        
    blinkRate = (blinkCount / duration) * 60.0

    # 3. Head movement score (scale 0-10)
    # Assumes frontend sends headJitter typically in [0.0, 1.0] range
    jitters = [f.get("headJitter", 0.0) for f in frames]
    avgJitter = sum(jitters) / len(jitters) if jitters else 0.0
    headMovementScore = min(10.0, max(0.0, avgJitter * 10.0))

    # 4. Composite Engagement Score (scale 1-10)
    # Simple heuristic: eye contact is highly engaging, excessive head movement detracts.
    baseEngagement = (eyeContactPercent / 100.0) * 8.0  # Up to 8 points from eye contact
    # Add 2 points if head movement is stable and natural (score ~ 2-5)
    movementBonus = 2.0 if 1.0 <= headMovementScore <= 6.0 else 0.0
    engagementScore = min(10.0, max(1.0, baseEngagement + movementBonus))

    return FacialMetrics(
        answer_index=answerIndex,
        eye_contact_percentage=round(eyeContactPercent, 1),
        avg_blink_rate_per_minute=round(blinkRate, 1),
        head_movement_score=round(headMovementScore, 1),
        engagement_score=round(engagementScore, 1),
        demo_mode=False
    )
