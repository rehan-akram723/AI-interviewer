# ─────────────────────────────────────────────────────────────────────────────
# backend/src/agents/difficultyCalibratorAgent.py
#
# Difficulty Calibrator Agent — LangGraph node function
#
# Pure algorithmic adjustment — zero LLM calls. This agent reads the per-dimension
# scores from the last 1–2 coaching feedback objects and applies explicit
# multi-axis rules to update the difficulty profile.
#
# Calibration rules (from manifest §5.7):
#   Rule 1 — High performance: relevance ≥ 7 AND depth ≥ 7
#             → difficulty_level += 1 (increases technical pressure)
#   Rule 2 — Low clarity:      clarity ≤ 4
#             → shift toward structured behavioral (dimension["clarity"] += 1, clamped)
#             → NOTE: does NOT change difficulty_level directly — signals format shift
#   Rule 3 — Low confidence:   confidence ≤ 3
#             → difficulty_level -= 1 (reduce cognitive load temporarily)
#   Rule 4 — Strong structure: structure ≥ 8
#             → sets "suggest_followup" flag = True (signals FollowUpAgent to probe deeper)
#   Rule 5 — Low overall:      avg(all 5 dimensions) < 4
#             → difficulty_level -= 1 (regardless of individual dims)
#
# Clamping: ALL adjustments are clamped to [1, 5].
#
# Composite difficulty_level is ALSO updated as the floor of the mean of all
# difficulty_dimensions values — this prevents the level and dimensions drifting apart.
#
# LangGraph contract:
#   Input:  Full InterviewSession state dict
#   Output: Partial dict:
#           {
#               "difficulty_level":      int (1-5),
#               "difficulty_dimensions": dict (5 keys, each int 1-5),
#               "suggest_followup":      bool (flag for FollowUpAgent),
#               "step_log":              list (appended)
#           }
#
# Exports: difficultyCalibratorAgent
# ─────────────────────────────────────────────────────────────────────────────

import logging
import math

from src.api.websockets.interviewWs import pushToClientSync

logger = logging.getLogger(__name__)

# ── Dimension score thresholds (from manifest) ────────────────────────────────
_HIGH_RELEVANCE_THRESHOLD = 7
_HIGH_DEPTH_THRESHOLD = 7
_LOW_CLARITY_THRESHOLD = 4
_LOW_CONFIDENCE_THRESHOLD = 3
_STRONG_STRUCTURE_THRESHOLD = 8
_LOW_OVERALL_THRESHOLD = 4.0     # avg < this → reduce difficulty

# ── Difficulty bounds ─────────────────────────────────────────────────────────
_MIN_DIFFICULTY = 1
_MAX_DIFFICULTY = 5

# ── Difficulty dimension keys (must match sessionState) ───────────────────────
_DIFFICULTY_DIMENSIONS = ("relevance", "clarity", "depth", "confidence", "structure")


def _clamp(value: int) -> int:
    """Clamp an integer to the [1, 5] difficulty bounds."""
    return max(_MIN_DIFFICULTY, min(_MAX_DIFFICULTY, value))


def _clampScore(value: int, lo: int = 1, hi: int = 10) -> int:
    """Clamp to [1, 10] for coaching dimension scores."""
    return max(lo, min(hi, value))


def _extractDimScores(feedbackObj: dict) -> dict:
    """
    Safely extract dimension_scores from a CoachingFeedback dict.
    Returns a dict with all 5 keys guaranteed, defaulting missing values to 5.
    """
    rawDims = feedbackObj.get("dimension_scores", {})
    return {
        dim: _clampScore(int(rawDims.get(dim, 5)))
        for dim in _DIFFICULTY_DIMENSIONS
    }


def _computeAverageDimScore(dimScores: dict) -> float:
    """Return the arithmetic mean of all 5 dimension scores."""
    values = [dimScores.get(dim, 5) for dim in _DIFFICULTY_DIMENSIONS]
    return sum(values) / len(values)


def difficultyCalibratorAgent(state: dict) -> dict:
    """
    LangGraph node: Difficulty Calibrator Agent.

    Reads from state:
        state["coaching_feedback"]    — list of CoachingFeedback dicts
        state["difficulty_level"]     — current composite difficulty (1-5)
        state["difficulty_dimensions"]— current per-dimension difficulty map

    Returns:
        {
            "difficulty_level":      int,
            "difficulty_dimensions": dict,
            "suggest_followup":      bool,
            "step_log":              list
        }
    """
    stepLog = list(state.get("step_log", []))
    coachingFeedback: list = state.get("coaching_feedback", [])
    currentLevel: int = state.get("difficulty_level", 2)
    currentDims: dict = dict(state.get("difficulty_dimensions", {
        "relevance": 2, "clarity": 2, "depth": 2, "confidence": 2, "structure": 2,
    }))

    suggestFollowup: bool = False

    # ── 1. Guard: need at least one feedback entry ─────────────────────────────
    if not coachingFeedback:
        stepLog.append(
            "[difficultyCalibratorAgent] No coaching feedback available — "
            "difficulty unchanged."
        )
        return {
            "difficulty_level": currentLevel,
            "difficulty_dimensions": currentDims,
            "suggest_followup": False,
            "step_log": stepLog,
        }

    # ── 2. Read last 1–2 feedback entries ─────────────────────────────────────
    # Use the most recent entry for Rules 2–4 (immediate signal).
    # Average the last 2 for Rule 1 (sustained high performance trigger).
    recentFeedback = coachingFeedback[-2:]  # List of 1 or 2 feedback dicts
    lastFeedback = coachingFeedback[-1]

    lastDims = _extractDimScores(lastFeedback)

    # Average dimensions across last 2 turns for trending signals
    if len(recentFeedback) == 2:
        prevDims = _extractDimScores(recentFeedback[0])
        trendDims = {
            dim: (lastDims[dim] + prevDims[dim]) / 2
            for dim in _DIFFICULTY_DIMENSIONS
        }
    else:
        trendDims = {dim: float(lastDims[dim]) for dim in _DIFFICULTY_DIMENSIONS}

    newLevel = currentLevel
    adjustments = []

    # ── 3. Rule 1: High relevance + high depth (trending) → increase difficulty ─
    if trendDims["relevance"] >= _HIGH_RELEVANCE_THRESHOLD and trendDims["depth"] >= _HIGH_DEPTH_THRESHOLD:
        newLevel += 1
        adjustments.append(
            f"Rule1(+1): trending relevance={trendDims['relevance']:.1f}, "
            f"depth={trendDims['depth']:.1f} both ≥ {_HIGH_RELEVANCE_THRESHOLD}"
        )

    # ── 4. Rule 2: Low clarity → nudge clarity dimension upward (format shift signal) ─
    if lastDims["clarity"] <= _LOW_CLARITY_THRESHOLD:
        # Don't change difficulty_level — signal a format shift toward behavioral
        # Nudge the clarity difficulty dimension DOWN (easier, more structured questions)
        currentDims["clarity"] = _clamp(currentDims.get("clarity", 2) - 1)
        adjustments.append(
            f"Rule2(clarity-dim): last clarity score={lastDims['clarity']} "
            f"≤ {_LOW_CLARITY_THRESHOLD} → behavioral format shift, "
            f"clarity_dim→{currentDims['clarity']}"
        )

    # ── 5. Rule 3: Low confidence → reduce overall difficulty ──────────────────
    if lastDims["confidence"] <= _LOW_CONFIDENCE_THRESHOLD:
        newLevel -= 1
        adjustments.append(
            f"Rule3(-1): last confidence={lastDims['confidence']} "
            f"≤ {_LOW_CONFIDENCE_THRESHOLD}"
        )

    # ── 6. Rule 4: Strong STAR structure → suggest deeper follow-up ────────────
    if lastDims["structure"] >= _STRONG_STRUCTURE_THRESHOLD:
        suggestFollowup = True
        adjustments.append(
            f"Rule4(followup): last structure={lastDims['structure']} "
            f"≥ {_STRONG_STRUCTURE_THRESHOLD} → probe deeper"
        )

    # ── 7. Rule 5: Low overall average → reduce difficulty ────────────────────
    overallAvg = _computeAverageDimScore(lastDims)
    if overallAvg < _LOW_OVERALL_THRESHOLD:
        newLevel -= 1
        adjustments.append(
            f"Rule5(-1): overall avg={overallAvg:.2f} < {_LOW_OVERALL_THRESHOLD}"
        )

    # ── 8. Clamp composite difficulty level ───────────────────────────────────
    newLevel = _clamp(newLevel)

    # ── 9. Update difficulty_dimensions based on latest scores ─────────────────
    # Each dimension in difficulty_dimensions tracks the QUESTION difficulty asked
    # at that cognitive axis, not the answer score. We map:
    #   - High answer score on a dim → raise that difficulty dimension next turn
    #   - Low answer score on a dim  → lower that difficulty dimension next turn
    # Scale: answer scores are 1-10; difficulty dims are 1-5.
    # Map: answer_score > 6 → dim + 1; answer_score < 5 → dim - 1; else unchanged.
    for dim in _DIFFICULTY_DIMENSIONS:
        answerDimScore = lastDims[dim]
        currentDimVal = currentDims.get(dim, 2)
        if answerDimScore > 6:
            currentDims[dim] = _clamp(currentDimVal + 1)
        elif answerDimScore < 5:
            currentDims[dim] = _clamp(currentDimVal - 1)
        else:
            currentDims[dim] = currentDimVal  # No change in neutral band

    # ── 10. Recalculate composite level as floor(mean of dims) ─────────────────
    # This prevents the composite level and dimensions from drifting apart over time.
    dimMean = sum(currentDims.values()) / len(currentDims)
    compositeFromDims = max(_MIN_DIFFICULTY, min(_MAX_DIFFICULTY, math.floor(dimMean)))

    # Blend: rule-based adjustment (70%) + dimension mean (30%).
    # At boundary values (1 or 5), the rule-adjusted level is authoritative —
    # blending must never erode a hard ceiling/floor caused by explicit rules.
    if newLevel == _MAX_DIFFICULTY:
        # At ceiling: don't let low dims pull us below ceiling
        finalLevel = _MAX_DIFFICULTY
    elif newLevel == _MIN_DIFFICULTY:
        # At floor: don't let high dims push us above floor
        finalLevel = _MIN_DIFFICULTY
    else:
        # Mid-range: blend normally
        blendedLevel = round(0.7 * newLevel + 0.3 * compositeFromDims)
        finalLevel = _clamp(blendedLevel)

    if adjustments:
        stepLog.append(
            f"[difficultyCalibratorAgent] Adjustments: {' | '.join(adjustments)}"
        )

    stepLog.append(
        f"[difficultyCalibratorAgent] "
        f"difficulty_level {currentLevel}→{finalLevel} | "
        f"dims={currentDims} | suggest_followup={suggestFollowup}"
    )

    # Push to client immediately
    sessionId = state.get("session_id")
    if sessionId:
        pushToClientSync(
            sessionId,
            {
                "type": "difficulty_update",
                "payload": {
                    "difficultyLevel": finalLevel,
                    "difficultyDimensions": currentDims,
                }
            }
        )

    return {
        "difficulty_level": finalLevel,
        "difficulty_dimensions": currentDims,
        "suggest_followup": suggestFollowup,
        "step_log": stepLog,
    }
