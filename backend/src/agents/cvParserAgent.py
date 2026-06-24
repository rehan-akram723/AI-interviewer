# ─────────────────────────────────────────────────────────────────────────────
# backend/src/agents/cvParserAgent.py
#
# CV Parser Agent — LangGraph node function
#
# Orchestrates the full ingestion pipeline for a single setup turn:
#   1. Parse CV PDF → confirmed_skills + uncertain_skills + education/exp/projects
#   2. Parse JD text → target_role + required_skills_from_jd
#   3. Parse motivation letter → concise motivation summary
#   4. Compute skills_gap = required_skills_from_jd - confirmed_skills
#      (uncertain_skills NEVER close the skills gap)
#   5. Assemble and validate CandidateProfile
#   6. Return partial state dict for LangGraph merge
#
# LangGraph contract:
#   Input:  Full InterviewSession state dict
#   Output: Partial dict — only the keys this agent modifies
#           {"candidate": {...}, "step_log": [...appended]}
#
# Exports: cvParserAgent
# ─────────────────────────────────────────────────────────────────────────────

import uuid
from datetime import datetime, timezone
from typing import Optional

from src.schemas.candidateSchema import CandidateProfile
from src.modules.ingestion.cvParser import parseCv
from src.modules.ingestion.jdParser import parseJd
from src.modules.ingestion.motivationParser import parseMotivation


def cvParserAgent(state: dict) -> dict:
    """
    LangGraph node: Ingestion agent — CV + JD + motivation parsing.

    Reads from state:
        state["session_id"]     — for step_log attribution
        state["_cv_bytes"]      — raw PDF bytes (set by API route before invoking graph)
        state["_jd_text"]       — raw JD text
        state["_motivation_text"] — raw motivation letter text
        state["candidate"]["target_company"] — user-provided company name

    Note: _cv_bytes, _jd_text, _motivation_text are ephemeral state fields
    set by the API route. They are not part of the persisted InterviewSession
    contract but are needed to pass raw data into the graph.

    Returns:
        {
            "candidate": <CandidateProfile as dict>,
            "step_log": <existing log + new entries>
        }
    """
    stepLog = list(state.get("step_log", []))
    stepLog.append("[cvParserAgent] Starting CV + JD + motivation parsing.")

    # ── 1. Parse CV ──────────────────────────────────────────────────────────
    cvBytes: Optional[bytes] = state.get("_cv_bytes")
    if not cvBytes:
        raise ValueError("cvParserAgent: _cv_bytes not found in state. Cannot parse CV.")

    stepLog.append("[cvParserAgent] Extracting text from CV PDF...")
    cvData = parseCv(cvBytes)
    stepLog.append(
        f"[cvParserAgent] CV parsed. "
        f"confirmed_skills={len(cvData.get('confirmed_skills', []))}, "
        f"uncertain_skills={len(cvData.get('uncertain_skills', []))}"
    )

    # ── 2. Parse JD ──────────────────────────────────────────────────────────
    jdText: str = state.get("_jd_text", "")
    if jdText.strip():
        stepLog.append("[cvParserAgent] Parsing job description...")
        jdData = parseJd(jdText)
        targetRole = jdData.get("target_role", "")
        requiredSkillsFromJd = jdData.get("required_skills_from_jd", [])
        stepLog.append(
            f"[cvParserAgent] JD parsed. role='{targetRole}', "
            f"required_skills={len(requiredSkillsFromJd)}"
        )
    else:
        stepLog.append("[cvParserAgent] No JD text provided — skipping JD parsing.")
        targetRole = ""
        requiredSkillsFromJd = []

    # ── 3. Parse Motivation ───────────────────────────────────────────────────
    motivationText: str = state.get("_motivation_text", "")
    if motivationText.strip():
        stepLog.append("[cvParserAgent] Summarising motivation letter...")
        motivation = parseMotivation(motivationText)
        stepLog.append("[cvParserAgent] Motivation letter summarised.")
    else:
        stepLog.append("[cvParserAgent] No motivation text provided — using empty string.")
        motivation = ""

    # ── 4. Compute Skills Gap ─────────────────────────────────────────────────
    # CRITICAL: Only confirmed_skills close the gap. uncertain_skills are excluded.
    confirmedSkillsLower = {s.lower() for s in cvData.get("confirmed_skills", [])}
    skillsGap = [
        skill for skill in requiredSkillsFromJd
        if skill.lower() not in confirmedSkillsLower
    ]
    stepLog.append(
        f"[cvParserAgent] Skills gap computed: {len(skillsGap)} gap skills "
        f"(from confirmed_skills only)."
    )

    # ── 5. Retrieve existing candidate_id or use the one from state ───────────
    existingCandidateId = (
        state.get("candidate", {}).get("candidate_id")
        or state.get("candidate_id")
        or str(uuid.uuid4())
    )

    # ── 6. Assemble CandidateProfile ──────────────────────────────────────────
    candidateData = {
        "candidate_id": existingCandidateId,
        "full_name": cvData.get("full_name") or "",
        "email": cvData.get("email"),
        "education": cvData.get("education", []),
        "experience": cvData.get("experience", []),
        "projects": cvData.get("projects", []),
        "confirmed_skills": cvData.get("confirmed_skills", []),
        "uncertain_skills": cvData.get("uncertain_skills", []),
        "motivation": motivation,
        "target_role": targetRole,
        "target_company": state.get("candidate", {}).get("target_company", ""),
        "required_skills_from_jd": requiredSkillsFromJd,
        "skills_gap": skillsGap,
        "session_ids": state.get("candidate", {}).get("session_ids", [state.get("session_id", "")]),
        "created_at": state.get("candidate", {}).get("created_at", datetime.now(timezone.utc).isoformat()),
    }

    # Validate via Pydantic before returning
    validatedProfile = CandidateProfile(**candidateData)
    stepLog.append(
        f"[cvParserAgent] CandidateProfile validated. "
        f"candidate_id={validatedProfile.candidate_id}"
    )

    return {
        "candidate": validatedProfile.model_dump(),
        "step_log": stepLog,
    }
