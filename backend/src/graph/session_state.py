# ─────────────────────────────────────────────────────────────────────────────
# backend/src/graph/session_state.py
#
# THE CENTRAL CONTRACT — InterviewSession TypedDict
#
# This is the single shared state object that flows through every LangGraph
# node (agent). Every module reads from it and writes back a subset of fields.
#
# Architecture pattern:
#   • TypedDict (not Pydantic) because LangGraph passes raw dicts between nodes.
#   • Agents return a dict with ONLY the keys they modify; LangGraph merges it.
#   • Adding new fields REQUIRES updating this manifest first. No exceptions.
#
# Field groups:
#   Identity          — session/candidate UUIDs, timestamps, mode flag
#   Configuration     — interview_length, interview_mode
#   Module 1 Output   — parsed candidate, company context, question plan
#   Module 2 Output   — live interview state (phases, Q&A, coaching, difficulty)
#   Module 3 Output   — multimodal analysis metrics
#   Module 4 Output   — final report + PDF path
#   System Fields     — status, error, step audit log
# ─────────────────────────────────────────────────────────────────────────────

from typing import TypedDict, List, Optional, Literal


# ── Forward-declared type aliases (imported from schemas at runtime) ──────────
# These are typed as dict here to keep this file dependency-free during import.
# Agents and graph nodes use the actual Pydantic models; the TypedDict uses
# dict to stay compatible with LangGraph's serialisation pipeline.
CandidateProfileDict = dict
QuestionDict = dict
AnswerDict = dict
CoachingFeedbackDict = dict
AudioMetricsDict = dict
FacialMetricsDict = dict
InterviewReportDict = dict


class InterviewSession(TypedDict):
    """
    Central shared state object for the AI Interviewer pipeline.

    Flows through every LangGraph node. Each agent reads relevant fields
    and returns a dict of only the fields it modifies — LangGraph merges
    the partial update back into the full state automatically.

    All field groups are documented with their originating module so you can
    trace exactly which agent is responsible for each piece of data.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    session_id: str
    """UUID generated at session initialisation. Immutable after creation."""

    candidate_id: str
    """UUID linking this session to a persistent CandidateProfile JSON file."""

    created_at: str
    """ISO 8601 timestamp — when the session was first created."""

    app_mode: Literal["demo", "production"]
    """Copied from settings.app_mode at session init. Gates all paid API calls."""

    # ── Interview Configuration ────────────────────────────────────────────────
    interview_length: Literal["short", "medium", "long"]
    """
    Controls total question count and phase sizes:
      short:  5–7  questions  (~5–10 min)
      medium: 10–15 questions (~15–25 min)
      long:   18–25 questions (~30–45 min)
    """

    interview_mode: Literal[
        "mixed", "technical", "behavioral", "hr_culture_fit", "system_design"
    ]
    """
    Controls question type distribution across the interview:
      technical:      80% technical, 20% behavioral
      behavioral:     80% behavioral, 20% technical
      hr_culture_fit: 70% culture/motivation, 30% behavioral
      system_design:  90% system design, 10% behavioral
      mixed:          balanced across all types
    """

    # ── Module 1 Output: Ingestion ─────────────────────────────────────────────
    candidate: CandidateProfileDict
    """
    Parsed from CV + JD + motivation letter by the CV Parser Agent.
    Contains confirmed_skills (high-confidence) and uncertain_skills (inferred).
    Only confirmed_skills drive technical questioning and scoring.
    """

    company_context: str
    """
    Output from the Company Research Agent after consuming RetrievedDocuments.
    Empty string ("") in demo mode — skipped cleanly, no placeholder hallucination.
    """

    question_plan: List[str]
    """
    Ordered question roadmap designed by the Interview Planner Agent.
    Phase-aware: icebreaker → cv_deep_dive → dynamic_followup → closing.
    """

    role_category: str
    """
    Detected role category used to load the matching question bank.
    Examples: "software_engineer", "data_scientist", "product_manager"
    """

    # ── Module 2 Output: Interview Engine ─────────────────────────────────────
    current_phase: Literal[
        "icebreaker", "cv_deep_dive", "dynamic_followup", "closing"
    ]
    """Current interview phase. Transitions are managed by the flow controller."""

    current_question_index: int
    """0-based index into asked_questions. Incremented after each answer."""

    asked_questions: List[QuestionDict]
    """Full chronological history of all Question objects asked in this session."""

    answers: List[AnswerDict]
    """Full chronological history of all Answer objects. Parallel to asked_questions."""

    coaching_feedback: List[CoachingFeedbackDict]
    """
    One CoachingFeedback per answer, generated by the Live Coach Agent.
    Delivered immediately via WebSocket to the frontend coaching sidebar.
    """

    difficulty_level: int
    """
    Overall difficulty level 1–5. Adjusted by the Difficulty Calibrator Agent
    after each answer based on composite performance signals.
    """

    difficulty_dimensions: dict
    """
    Per-dimension difficulty tracking:
      {
        "relevance": int,    # 1-5
        "clarity": int,      # 1-5
        "depth": int,        # 1-5
        "confidence": int,   # 1-5
        "structure": int     # 1-5
      }
    Allows independent calibration per skill axis. All values clamped 1–5.
    """

    # ── Module 3 Output: Analysis ──────────────────────────────────────────────
    audio_metrics_per_answer: List[AudioMetricsDict]
    """
    One AudioMetrics dict per answer turn.
    Computed by librosa in production. Contains WPM, filler words, pauses, energy.
    demo_mode=True when audio analysis is skipped.
    """

    facial_metrics_summary: FacialMetricsDict
    """
    Single FacialMetrics dict aggregated over the entire interview session.
    Populated from MediaPipe.js data sent by the frontend (production only).
    demo_mode=True when facial analysis is skipped.
    """

    transcript: List[str]
    """
    Raw STT text per answer turn (one string per turn).
    In demo mode: contains the typed answer text directly.
    In production: Whisper transcription output.
    """

    # ── Module 4 Output: Report ────────────────────────────────────────────────
    final_report: Optional[InterviewReportDict]
    """
    None until the report generation phase completes.
    Populated by the Evaluator Agent. Stored as JSON at data/reports/{session_id}.json
    """

    pdf_path: Optional[str]
    """
    Filesystem path to the generated PDF report.
    None until pdf_generator.py completes. Example: ./data/reports/{session_id}.pdf
    """

    # ── System Fields ──────────────────────────────────────────────────────────
    status: Literal[
        "setting_up", "ready", "in_progress", "completed", "error"
    ]
    """
    Lifecycle state of the session:
      setting_up  → setup_graph is running (CV parse, company research, planning)
      ready       → setup complete, interview can begin
      in_progress → interview is live
      completed   → all questions answered, report available
      error       → unrecoverable failure; check the error field
    """

    error: Optional[str]
    """
    Error message if status == "error". None otherwise.
    Always set before transitioning status to "error".
    """

    step_log: List[str]
    """
    Append-only audit trail of agent actions. Each agent appends timestamped
    entries. Format: "[AGENT_NAME] <action description>"
    Used for debugging, transparency, and the setup progress UI.
    """
