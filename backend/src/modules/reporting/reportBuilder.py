# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/reporting/reportBuilder.py
#
# Assembles final scores, metrics, and LLM-generated narrative into an InterviewReport.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from typing import Dict

from src.graph.sessionState import InterviewSession
from src.schemas.reportSchema import InterviewReport, DimensionScore
from src.core.llmClient import callLlm

logger = logging.getLogger(__name__)

def buildReport(state: InterviewSession, dimensionScores: Dict[str, DimensionScore]) -> InterviewReport:
    """
    Assembles all scores + metrics + LLM-generated narrative into InterviewReport.
    Records interview_mode and interview_length in report for context.
    Narrative sections generated via LLM.
    """
    logger.info("Building final InterviewReport for session %s", state.get("session_id"))
    
    # 1. Calculate overall score (average of all dimension scores)
    scores = [d.score for d in dimensionScores.values()]
    overallScore = round(sum(scores) / len(scores), 1) if scores else 5.0
    
    # 2. Extract context to prompt LLM for narratives
    scoreContext = "\n".join([f"{k}: {v.score}/10.0 - {v.rationale}" for k, v in dimensionScores.items()])
    
    systemPrompt = (
        "You are an expert technical hiring manager summarizing an interview performance.\n"
        "Return a JSON object matching this schema exactly:\n"
        "{\n"
        '  "executive_summary": "High-level summary (3-4 sentences)",\n'
        '  "top_strengths": ["Strength 1", "Strength 2", "Strength 3"],\n'
        '  "areas_for_improvement": ["Area 1", "Area 2"],\n'
        '  "recommended_next_steps": "Actionable advice for their prep (2 sentences)"\n'
        "}\n"
        "Be extremely objective, direct, and actionable."
    )
    
    prompt = (
        f"Candidate Role: {state.get('role_category')}\n"
        f"Interview Mode: {state.get('interview_mode')}\n"
        f"Interview Length: {state.get('interview_length')}\n"
        f"Overall Composite Score: {overallScore}/10.0\n\n"
        f"Dimension Scores & Rationale:\n{scoreContext}\n"
    )
    
    try:
        result = callLlm(prompt=prompt, systemPrompt=systemPrompt, temperature=0.3, jsonMode=True)
    except Exception as e:
        logger.error("Failed to generate report narrative: %s", e)
        result = {}

    return InterviewReport(
        session_id=state.get("session_id", "unknown"),
        candidate_id=state.get("candidate_id", "unknown"),
        interview_mode=state.get("interview_mode", "mixed"),
        interview_length=state.get("interview_length", "medium"),
        overall_score=overallScore,
        dimension_scores=dimensionScores,
        executive_summary=result.get("executive_summary", "Summary unavailable due to generation error."),
        top_strengths=result.get("top_strengths", ["Unavailable"]),
        areas_for_improvement=result.get("areas_for_improvement", ["Unavailable"]),
        recommended_next_steps=result.get("recommended_next_steps", "Continue practicing.")
    )
