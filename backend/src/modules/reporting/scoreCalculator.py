# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/reporting/scoreCalculator.py
#
# Generates quantitative scores and qualitative narratives for all 6 tracking dimensions.
# Enforces strict boundaries (e.g. Resume Hallucination Protection for technical relevance).
# ─────────────────────────────────────────────────────────────────────────────

import logging
import json
from typing import Dict

from src.graph.sessionState import InterviewSession
from src.schemas.reportSchema import DimensionScore
from src.core.llmClient import callLlm

logger = logging.getLogger(__name__)

def _callDimensionLlm(dimensionName: str, promptData: str) -> DimensionScore:
    """Helper to consistently invoke LLM and parse the DimensionScore schema."""
    systemPrompt = (
        f"You are an expert technical interviewer evaluating a candidate on: {dimensionName}.\n"
        "Return a JSON object matching this schema:\n"
        "{\n"
        '  "score": float (1.0 to 10.0),\n'
        '  "evidence": [list of specific facts/metrics justifying the score],\n'
        '  "rationale": "Narrative explanation connecting evidence to score"\n'
        "}\n"
        "Be extremely objective and use specific examples from the provided data."
    )
    
    try:
        result = callLlm(
            prompt=promptData,
            systemPrompt=systemPrompt,
            temperature=0.2,
            jsonMode=True
        )
        return DimensionScore(
            score=float(result.get("score", 5.0)),
            evidence=result.get("evidence", []),
            rationale=result.get("rationale", "No rationale provided.")
        )
    except Exception as e:
        logger.error("Failed to calculate dimension %s: %s", dimensionName, e)
        return DimensionScore(
            score=5.0,
            evidence=["Failed to generate analysis."],
            rationale="An error occurred during evaluation."
        )


def calculateCommunicationClarity(state: InterviewSession) -> DimensionScore:
    metrics = state.get("audio_metrics_per_answer", [])
    feedbacks = state.get("coaching_feedback", [])
    
    avgWpm = sum(m.get("words_per_minute") or 0.0 for m in metrics) / max(1, len(metrics))
    totalFillers = sum(m.get("filler_word_count", 0) for m in metrics)
    clarityScores = [f.get("dimension_scores", {}).get("clarity", 5) for f in feedbacks]
    
    prompt = (
        f"Audio Metrics:\n- Average WPM: {avgWpm:.1f}\n- Total Filler Words: {totalFillers}\n"
        f"Live Clarity Scores from Coach: {clarityScores}\n"
        "Evaluate the candidate's communication clarity."
    )
    return _callDimensionLlm("Communication Clarity", prompt)


def calculateTechnicalRelevance(state: InterviewSession) -> DimensionScore:
    # Resume Hallucination Protection: STRICTLY use confirmed_skills only
    candidate = state.get("candidate", {})
    confirmedSkills = candidate.get("confirmed_skills", [])
    # Intentionally ignoring candidate.get("uncertain_skills")
    
    qaPairs = []
    for i, q in enumerate(state.get("asked_questions", [])):
        ans = next((a for a in state.get("answers", []) if a.get("question_index") == q.get("index")), None)
        if ans:
            qaPairs.append(f"Q: {q.get('text')}\nA: {ans.get('text')}")
            
    prompt = (
        f"Confirmed Skills of Candidate (DO NOT invent or evaluate unlisted skills):\n{confirmedSkills}\n\n"
        f"Interview Q&A:\n" + "\n---\n".join(qaPairs) + "\n\n"
        "Evaluate the technical relevance of their answers against their confirmed skills. "
        "Did they actually demonstrate these skills in their answers?"
    )
    return _callDimensionLlm("Technical Relevance", prompt)


def calculateProblemSolving(state: InterviewSession) -> DimensionScore:
    qaPairs = []
    for q in state.get("asked_questions", []):
        ans = next((a for a in state.get("answers", []) if a.get("question_index") == q.get("index")), None)
        if ans:
            qaPairs.append(f"Q: {q.get('text')}\nA: {ans.get('text')}")
            
    prompt = (
        "Evaluate the candidate's problem solving skills based on these answers:\n"
        + "\n---\n".join(qaPairs) + "\n"
        "Look for logical structured thinking, handling of constraints, and clear technical reasoning."
    )
    return _callDimensionLlm("Problem Solving", prompt)


def calculateMotivationFit(state: InterviewSession) -> DimensionScore:
    companyContext = state.get("company_context", "")
    qaPairs = []
    for q in state.get("asked_questions", []):
        if q.get("phase") in ["icebreaker", "closing"] or q.get("category") == "motivational":
            ans = next((a for a in state.get("answers", []) if a.get("question_index") == q.get("index")), None)
            if ans:
                qaPairs.append(f"Q: {q.get('text')}\nA: {ans.get('text')}")
            
    prompt = (
        f"Company Context:\n{companyContext}\n\n"
        "Evaluate motivation and culture fit based on these motivational answers:\n"
        + "\n---\n".join(qaPairs)
    )
    return _callDimensionLlm("Motivation & Culture Fit", prompt)


def calculateConfidence(state: InterviewSession) -> DimensionScore:
    metrics = state.get("audio_metrics_per_answer", [])
    feedbacks = state.get("coaching_feedback", [])
    
    avgEnergy = sum(m.get("voice_energy_level") or 0.0 for m in metrics) / max(1, len(metrics))
    confScores = [f.get("dimension_scores", {}).get("confidence", 5) for f in feedbacks]
    
    prompt = (
        f"Average Voice Energy Level: {avgEnergy:.2f} (0.0 to 1.0 scale)\n"
        f"Live Confidence Scores from Coach: {confScores}\n"
        "Evaluate the candidate's confidence."
    )
    return _callDimensionLlm("Confidence", prompt)


def calculateListeningComprehension(state: InterviewSession) -> DimensionScore:
    feedbacks = state.get("coaching_feedback", [])
    relScores = [f.get("dimension_scores", {}).get("relevance", 5) for f in feedbacks]
    
    prompt = (
        f"Live Answer Relevance Scores from Coach: {relScores}\n"
        "Evaluate the candidate's listening comprehension. High relevance means they answered the actual question asked."
    )
    return _callDimensionLlm("Listening Comprehension", prompt)


def calculateAllScores(state: InterviewSession) -> Dict[str, DimensionScore]:
    """Runs all 6 dimension calculators, returns dict of DimensionScore objects."""
    logger.info("Starting dimension score calculations for session %s", state.get("session_id"))
    
    return {
        "communication_clarity": calculateCommunicationClarity(state),
        "technical_relevance": calculateTechnicalRelevance(state),
        "problem_solving": calculateProblemSolving(state),
        "motivation_fit": calculateMotivationFit(state),
        "confidence": calculateConfidence(state),
        "listening_comprehension": calculateListeningComprehension(state),
    }
