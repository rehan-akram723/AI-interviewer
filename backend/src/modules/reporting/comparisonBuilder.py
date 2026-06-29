# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/reporting/comparisonBuilder.py
#
# Generates a ProgressComparison between two InterviewReports.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from typing import Dict

from src.schemas.reportSchema import InterviewReport, ProgressComparison
from src.core.llmClient import callLlm

logger = logging.getLogger(__name__)

def buildComparison(previousReport: InterviewReport, currentReport: InterviewReport) -> ProgressComparison:
    """
    Computes score deltas across all dimensions.
    Identifies improvements, areas still requiring work, and regressions.
    Generates a comparison narrative via LLM.
    """
    logger.info(
        "Building progress comparison between sessions %s and %s", 
        previousReport.session_id, currentReport.session_id
    )
    
    overallDelta = round(currentReport.overall_score - previousReport.overall_score, 2)
    
    dimensionDeltas: Dict[str, float] = {}
    for dimName, currScoreObj in currentReport.dimension_scores.items():
        prevScoreObj = previousReport.dimension_scores.get(dimName)
        if prevScoreObj:
            delta = currScoreObj.score - prevScoreObj.score
            dimensionDeltas[dimName] = round(delta, 2)
        else:
            dimensionDeltas[dimName] = 0.0
            
    # Simple mathematical analysis to populate lists
    regressions = []
    strengthsImproved = []
    
    for dimName, delta in dimensionDeltas.items():
        if delta <= -1.0:
            regressions.append(f"{dimName} score dropped by {-delta:.1f} points.")
        elif delta >= 1.0:
            strengthsImproved.append(f"{dimName} score improved by {delta:.1f} points.")
            
    weaknessesImproved = []
    for prevWeakness in previousReport.areas_for_improvement:
        if prevWeakness not in currentReport.areas_for_improvement:
            # Simplistic matching, usually the LLM refines this in the narrative
            weaknessesImproved.append(f"Addressed prior weakness: {prevWeakness}")
            
    # LLM narrative generation
    systemPrompt = (
        "You are an expert technical coach reviewing a candidate's progress across two interview sessions.\n"
        "Return a JSON object matching this schema exactly:\n"
        "{\n"
        '  "comparison_narrative": "A concise 3-4 sentence summary of their progress, mentioning regressions if any."\n'
        "}\n"
    )
    
    prompt = (
        f"Overall Score Delta: {'+' if overallDelta > 0 else ''}{overallDelta:.1f}\n"
        f"Dimension Deltas: {dimensionDeltas}\n"
        f"Previous Weaknesses: {previousReport.areas_for_improvement}\n"
        f"Current Weaknesses: {currentReport.areas_for_improvement}\n"
        f"Detected Regressions: {regressions}\n"
        f"Detected Improvements: {strengthsImproved}\n\n"
        "Write the 3-4 sentence summary."
    )
    
    try:
        result = callLlm(prompt=prompt, systemPrompt=systemPrompt, temperature=0.3, jsonMode=True)
    except Exception as e:
        logger.error("Failed to generate comparison narrative: %s", e)
        result = {}

    return ProgressComparison(
        overall_score_delta=overallDelta,
        dimension_deltas=dimensionDeltas,
        strengths_improved=strengthsImproved,
        weaknesses_improved=weaknessesImproved,
        regressions_detected=regressions,
        comparison_narrative=result.get("comparison_narrative", "Comparison narrative unavailable.")
    )
