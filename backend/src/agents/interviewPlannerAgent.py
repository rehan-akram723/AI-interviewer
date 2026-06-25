# ─────────────────────────────────────────────────────────────────────────────
# backend/src/agents/interviewPlannerAgent.py
#
# Interview Planner Agent — LangGraph node function
#
# Responsibilities:
#   1. Detect the candidate's role category from their target_role string.
#   2. Load the appropriate base question set from the static question bank.
#   3. Use MODE_DISTRIBUTIONS + LENGTH_TARGETS to calculate exactly how many
#      questions of each category are needed for this interview configuration.
#   4. Call the LLM with the candidate profile + question bank reference to
#      assemble a personalised, ordered question_plan list.
#   5. Validate the plan length against the manifest range for the chosen length.
#   6. Return the plan + detected role_category to the session state.
#
# LangGraph contract:
#   Input:  Full InterviewSession state dict
#   Output: Partial dict — only the keys this agent modifies:
#           {"question_plan": [...], "role_category": str, "step_log": [...appended]}
#
# Exports: interviewPlannerAgent
# ─────────────────────────────────────────────────────────────────────────────

import json
from typing import List

from src.core.llmClient import callLlm
from src.modules.interviewEngine.questionBank import (
    detectRoleCategory,
    getBaseQuestions,
    MODE_DISTRIBUTIONS,
)
from src.modules.interviewEngine.flowController import LENGTH_TARGETS


# ── Length validity ranges (from manifest §5.7) ────────────────────────────────
_LENGTH_RANGES: dict[str, tuple[int, int]] = {
    "short":  (5, 7),
    "medium": (10, 15),
    "long":   (18, 25),
}

# ── System prompt ──────────────────────────────────────────────────────────────
_PLANNER_SYSTEM_PROMPT = """\
You are a senior AI interview planner. Your job is to design a structured, \
personalised interview question sequence. Follow instructions exactly.\
"""

# ── Planning prompt ────────────────────────────────────────────────────────────
_PLANNER_PROMPT_TEMPLATE = """\
Design a personalised interview question plan for this candidate.

CANDIDATE PROFILE:
Name: {fullName}
Target Role: {targetRole}
Target Company: {targetCompany}
Confirmed Skills: {confirmedSkills}
Skills Gap: {skillsGap}
Motivation Summary: {motivation}
Company Context: {companyContext}

INTERVIEW CONFIGURATION:
Interview Length: {interviewLength} (target {targetTotal} questions total)
Interview Mode: {interviewMode}
Role Category: {roleCategory}

QUESTION TYPE DISTRIBUTION FOR THIS MODE:
{modeDistribution}

PHASE STRUCTURE (must follow this order):
1. Icebreaker:         {icebreakerCount} question(s)   — rapport building, background
2. CV Deep Dive:       {cvDeepDiveCount} question(s)   — explore experience and skills
3. Dynamic Follow-up:  {dynamicFollowupCount} question(s) — probe gaps and key claims
4. Closing:            {closingCount} question(s)       — wrap-up, candidate questions

REFERENCE QUESTION BANK (use as inspiration, rephrase and personalise for this candidate):
{questionBankSample}

RULES:
1. Generate EXACTLY {targetTotal} questions total.
2. Personalise each question using the candidate's CV details — mention specific skills,
   companies, or projects where relevant (e.g., "In your role at Acme Corp, you mentioned
   Python APIs — walk me through...").
3. Follow the phase order strictly: all icebreakers first, then cv_deep_dive, etc.
4. For CV Deep Dive and Dynamic Follow-up phases, focus on confirmed_skills and skills_gap.
5. Do NOT repeat the exact wording of any question from the reference bank.
6. Return ONLY a valid JSON array of {targetTotal} question strings. No labels, no markdown.

Example output format:
["Question 1 text here", "Question 2 text here", ...]

Generate the question plan now:
"""


def _buildModeDistributionText(interviewMode: str) -> str:
    """Format the mode distribution as a readable text block for the prompt."""
    dist = MODE_DISTRIBUTIONS.get(interviewMode, MODE_DISTRIBUTIONS["mixed"])
    lines = [
        f"  {category}: {int(ratio * 100)}%"
        for category, ratio in dist.items()
        if ratio > 0
    ]
    return "\n".join(lines)


def _buildQuestionBankSample(roleCategory: str) -> str:
    """
    Build a compact sample from the question bank for the LLM to reference.
    We include 3 questions per relevant phase to give the LLM material to work from
    without overwhelming the context window.
    """
    phases = ["icebreaker", "technical", "behavioral", "system_design"]
    sampleParts = []
    for phase in phases:
        questions = getBaseQuestions(roleCategory, phase)[:3]
        if questions:
            sampleParts.append(f"[{phase.upper()}]")
            for q in questions:
                sampleParts.append(f"  - {q}")
    return "\n".join(sampleParts)


def _validatePlanLength(plan: list, interviewLength: str) -> list:
    """
    Validate the LLM-generated plan falls within the manifest range.
    If the LLM over-generates: truncate to the top of the range.
    If the LLM under-generates: fill remaining slots with generic closing questions.

    Returns the validated (and possibly adjusted) plan.
    """
    minQ, maxQ = _LENGTH_RANGES.get(interviewLength, (5, 25))
    targetQ = LENGTH_TARGETS[interviewLength]["total"]

    if len(plan) > maxQ:
        plan = plan[:maxQ]
    elif len(plan) < minQ:
        # Pad with generic closing questions until we hit minimum
        while len(plan) < minQ:
            plan.append("What questions do you have for us about the role or the team?")

    return plan


def interviewPlannerAgent(state: dict) -> dict:
    """
    LangGraph node: Interview Planner Agent.

    Reads from state:
        state["candidate"]          — CandidateProfile dict (from cvParserAgent)
        state["company_context"]    — Company briefing string (from companyResearchAgent)
        state["interview_length"]   — "short" | "medium" | "long"
        state["interview_mode"]     — "mixed" | "technical" | "behavioral" | ...

    Returns:
        {
            "question_plan":  List[str],   — ordered list of question strings
            "role_category":  str,          — detected role category
            "step_log":       List[str]     — appended entries
        }
    """
    stepLog = list(state.get("step_log", []))
    stepLog.append("[interviewPlannerAgent] Starting question plan generation.")

    candidate: dict = state.get("candidate", {})
    companyContext: str = state.get("company_context", "")
    interviewLength: str = state.get("interview_length", "medium")
    interviewMode: str = state.get("interview_mode", "mixed")

    # ── 1. Detect Role Category ────────────────────────────────────────────────
    targetRole: str = candidate.get("target_role", "")
    roleCategory = detectRoleCategory(targetRole)
    stepLog.append(
        f"[interviewPlannerAgent] Role category detected: '{roleCategory}' "
        f"from title: '{targetRole}'"
    )

    # ── 2. Compute Question Counts per Phase ───────────────────────────────────
    phaseCounts = LENGTH_TARGETS.get(interviewLength, LENGTH_TARGETS["medium"])
    targetTotal = phaseCounts["total"]
    icebreakerCount = phaseCounts["icebreaker"]
    cvDeepDiveCount = phaseCounts["cv_deep_dive"]
    dynamicFollowupCount = phaseCounts["dynamic_followup"]
    closingCount = phaseCounts["closing"]

    stepLog.append(
        f"[interviewPlannerAgent] Plan target: {targetTotal} questions | "
        f"length={interviewLength} | mode={interviewMode}"
    )

    # ── 3. Build Prompt ────────────────────────────────────────────────────────
    confirmedSkills: List[str] = candidate.get("confirmed_skills", [])
    skillsGap: List[str] = candidate.get("skills_gap", [])

    prompt = _PLANNER_PROMPT_TEMPLATE.format(
        fullName=candidate.get("full_name", "Candidate"),
        targetRole=targetRole or "the target role",
        targetCompany=candidate.get("target_company", "the company"),
        confirmedSkills=", ".join(confirmedSkills) if confirmedSkills else "Not specified",
        skillsGap=", ".join(skillsGap) if skillsGap else "None",
        motivation=candidate.get("motivation", "Not provided"),
        companyContext=companyContext or "Company context not available.",
        interviewLength=interviewLength,
        targetTotal=targetTotal,
        interviewMode=interviewMode,
        roleCategory=roleCategory,
        modeDistribution=_buildModeDistributionText(interviewMode),
        icebreakerCount=icebreakerCount,
        cvDeepDiveCount=cvDeepDiveCount,
        dynamicFollowupCount=dynamicFollowupCount,
        closingCount=closingCount,
        questionBankSample=_buildQuestionBankSample(roleCategory),
    )

    # ── 4. Call LLM ────────────────────────────────────────────────────────────
    stepLog.append("[interviewPlannerAgent] Calling LLM to generate question plan...")
    rawOutput = callLlm(
        prompt=prompt,
        systemPrompt=_PLANNER_SYSTEM_PROMPT,
        temperature=0.6,   # Some creativity for personalised phrasing
        maxTokens=3000,
        jsonMode=True,
    )

    # ── 5. Parse and Validate Output ──────────────────────────────────────────
    # LLM should return a JSON array. callLlm(jsonMode=True) gives us a dict or list.
    if isinstance(rawOutput, dict):
        # Some models wrap the array: {"questions": [...]}
        questionPlan: List[str] = (
            rawOutput.get("questions")
            or rawOutput.get("question_plan")
            or rawOutput.get("plan")
            or list(rawOutput.values())[0] if rawOutput else []
        )
    elif isinstance(rawOutput, list):
        questionPlan = rawOutput
    else:
        questionPlan = []
        stepLog.append(
            "[interviewPlannerAgent] WARNING: LLM returned unexpected type "
            f"({type(rawOutput).__name__}). Using empty plan."
        )

    # Flatten nested lists if the LLM returned a list of lists
    flatPlan: List[str] = []
    for item in questionPlan:
        if isinstance(item, list):
            flatPlan.extend(str(q) for q in item)
        else:
            flatPlan.append(str(item))

    # Clean: remove empty strings
    flatPlan = [q.strip() for q in flatPlan if q and q.strip()]

    # Validate and adjust to manifest-compliant length
    validatedPlan = _validatePlanLength(flatPlan, interviewLength)

    stepLog.append(
        f"[interviewPlannerAgent] Plan generated: {len(validatedPlan)} questions "
        f"(target range {_LENGTH_RANGES[interviewLength][0]}–{_LENGTH_RANGES[interviewLength][1]})."
    )

    return {
        "question_plan": validatedPlan,
        "role_category": roleCategory,
        "step_log": stepLog,
    }
