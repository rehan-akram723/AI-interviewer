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

    # ── 1. Parse Inputs Concurrently ──────────────────────────────────────────
    cvBytes: Optional[bytes] = state.get("cv_bytes_input")
    if not cvBytes:
        raise ValueError("cvParserAgent: cv_bytes_input not found in state. Cannot parse CV.")

    jdText: str = state.get("jd_text_input", "")
    motivationText: str = state.get("motivation_text_input", "")

    # DEMO SHORTCUT: Bypass LLM to save tokens and avoid crashes in demo mode
    cvRawText = ""
    try:
        cvRawText = cvBytes.decode("utf-8").strip()
    except Exception:
        pass

    if cvRawText.startswith("REHAN AKRAM") and "AI/ML Engineer" in jdText:
        stepLog.append("[cvParserAgent] DETECTED QUICK START DEMO. Bypassing LLM parsing to save tokens.")
        cvData = {
            "full_name": "Rehan Akram",
            "email": "rehan.akram@outlook.com",
            "education": [{"institution": "FAST NUCES", "degree": "Bachelor of Science", "field": "Computer Science", "graduation_year": 2027, "gpa": ""}],
            "experience": [
                {"company": "AVN Monitoring System", "role": "C++ Developer", "duration": "", "description": "Engineered a real-time Airspace Violation Notification product.", "technologies": ["C++", "POSIX threads", "IPC"]},
                {"company": "Full-Stack Application Development", "role": "Lead Developer", "duration": "", "description": "Robust full-stack application using Java Spring Boot and MySQL.", "technologies": ["Java", "Spring Boot", "MySQL"]}
            ],
            "projects": [],
            "confirmed_skills": ["Java", "Spring Boot", "MySQL", "C++", "C", "RISC-V Assembly", "UX", "Product Design", "Git", "VS Code", "Linux", "IntelliJ IDEA", "Unity", "C#"],
            "uncertain_skills": []
        }
        jdData = {
            "target_role": "AI/ML Engineer",
            "required_skills_from_jd": ["Machine Learning", "Python", "Scalable Architecture", "Full-stack development"]
        }
        motivation = motivationText
    else:
        import concurrent.futures

        def _doCv():
            return parseCv(cvBytes)
            
        def _doJd():
            return parseJd(jdText) if jdText.strip() else {}
            
        def _doMotivation():
            return parseMotivation(motivationText) if motivationText.strip() else ""

        stepLog.append("[cvParserAgent] Spawning threads for concurrent parsing...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futureCv = executor.submit(_doCv)
            futureJd = executor.submit(_doJd)
            futureMot = executor.submit(_doMotivation)
            
            cvData = futureCv.result()
            jdData = futureJd.result()
            motivation = futureMot.result()

        stepLog.append(
            f"[cvParserAgent] Concurrent parsing complete. "
            f"CV skills: {len(cvData.get('confirmed_skills', []))} confirmed."
        )

    targetRole = jdData.get("target_role", "")
    requiredSkillsFromJd = jdData.get("required_skills_from_jd", [])

    # ── 2. Compute Skills Gap ─────────────────────────────────────────────────
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
