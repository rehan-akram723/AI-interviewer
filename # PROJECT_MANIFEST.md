# PROJECT_MANIFEST.md
# AI Interview Simulator — Multimodal Multi-Agent System

> **Blueprint Version:** 2.0.0
> **Status:** Active Development
> **Architecture:** Module-by-module, frontend last, contracts-first

---

## Table of Contents

1. [Project Summary](#1-project-summary)
2. [Repository Structure](#2-repository-structure)
3. [Session State — The Central Contract](#3-session-state--the-central-contract)
4. [Data Flow](#4-data-flow)
5. [Interface Definitions](#5-interface-definitions-the-contracts)
6. [Module Breakdown & Implementation Requirements](#6-module-breakdown--implementation-requirements)
7. [Demo Mode Reference](#7-demo-mode-reference)
8. [Appendix](#8-appendix)

---

## 1. Project Summary

### Goal
A multimodal AI interview simulator that ingests a candidate's CV, job description, company name, and motivation letter — then conducts a fully adaptive, voice-driven interview with live coaching feedback, facial engagement tracking, and speaking pattern analysis. At the end it generates a structured PDF performance report. The system uses multiple specialized agents orchestrated via LangGraph, with a clean demo mode that substitutes all paid APIs for free alternatives during development.

Candidates may complete multiple interview sessions and compare their performance across attempts.

### Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Orchestration** | LangGraph 0.2+ | Multi-agent session state machine |
| **LLM** | OpenRouter (free tier: Llama 3.3 70B / DeepSeek V4 Flash) | All agent reasoning |
| **Backend** | FastAPI | REST + WebSocket API |
| **Frontend** | React + Tailwind CSS | Camera, mic, real-time UI |
| **STT (production)** | Local Whisper (RTX 4060) | Speech-to-text, zero cost |
| **STT (demo)** | Text input box | Free substitute |
| **TTS (production)** | ElevenLabs free tier → OpenAI TTS | AI interviewer voice |
| **TTS (demo)** | Browser Web Speech API / text display | Free substitute |
| **Facial Analysis (prod)** | MediaPipe.js (client-side) | Eye contact, engagement |
| **Facial Analysis (demo)** | Skipped, placeholder returned | Free substitute |
| **Audio Analysis** | librosa (local) | Pace, filler words, pauses |
| **PDF Reports** | WeasyPrint | Structured performance reports |
| **Persistence** | JSON files on disk | Candidate profiles, sessions, reports |
| **Config** | Pydantic Settings + python-dotenv | APP_MODE flag + env vars |
| **Testing** | pytest + pytest-asyncio | Unit and integration tests |
| **Deployment** | Render (backend) + Vercel (frontend) | Free tier hosting |

### Key Architecture Pattern
**Module-by-module, contracts-first, frontend last.**

All modules share a single `InterviewSession` state object defined before any code is written. Each module is built completely and tested in isolation before the next begins. The React frontend is written last, against a fully complete and tested backend. No module is revisited after the frontend connects.

### Demo Mode
A single `APP_MODE=demo` flag in `.env` substitutes all paid/media APIs:
- TTS → text displayed on screen
- STT → typed text input
- Facial analysis → skipped, placeholder metrics returned
- LLM → OpenRouter free tier (already free, no change)

---

## 2. Repository Structure

```
ai-interviewer/
│
├── backend/                                    # All Python backend code
│   │
│   ├── src/
│   │   │
│   │   ├── agents/                             # LangGraph agent implementations
│   │   │   ├── __init__.py
│   │   │   ├── cv_parser_agent.py              # Extracts structured profile from CV + JD
│   │   │   ├── company_research_agent.py       # Consumes retrieved docs, summarises company context
│   │   │   ├── interview_planner_agent.py      # Designs question roadmap (length + mode aware)
│   │   │   ├── conductor_agent.py              # Asks questions, manages flow
│   │   │   ├── followup_agent.py               # Generates dynamic follow-ups (max 2 per question)
│   │   │   ├── live_coach_agent.py             # Real-time feedback on each answer
│   │   │   ├── difficulty_calibrator_agent.py  # Dimension-aware difficulty adjustment
│   │   │   └── evaluator_agent.py              # Final scoring across all dimensions
│   │   │
│   │   ├── graph/                              # LangGraph graph definitions
│   │   │   ├── __init__.py
│   │   │   ├── session_state.py                # InterviewSession TypedDict — central contract
│   │   │   ├── setup_graph.py                  # Setup phase graph (CV → plan)
│   │   │   ├── interview_graph.py              # Live interview phase graph
│   │   │   ├── report_graph.py                 # Report generation graph
│   │   │   └── edges.py                        # Conditional routing logic
│   │   │
│   │   ├── modules/                            # The 4 core build modules
│   │   │   ├── __init__.py
│   │   │   ├── ingestion/                      # Module 1 — CV + JD + Company
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cv_parser.py
│   │   │   │   ├── jd_parser.py
│   │   │   │   ├── motivation_parser.py
│   │   │   │   └── company_scraper.py
│   │   │   │
│   │   │   ├── retrieval/                      # NEW — Retrieval layer for company research
│   │   │   │   ├── __init__.py
│   │   │   │   ├── retriever.py                # Base retriever interface
│   │   │   │   └── company_retriever.py        # Company-specific retrieval logic
│   │   │   │
│   │   │   ├── interview_engine/               # Module 2 — Agent orchestration
│   │   │   │   ├── __init__.py
│   │   │   │   ├── question_bank.py            # Role-specific + mode-specific base questions
│   │   │   │   ├── session_manager.py          # Manages active interview sessions
│   │   │   │   └── flow_controller.py          # Phase transitions (icebreaker→CV→followup)
│   │   │   │
│   │   │   ├── analysis/                       # Module 3 — Multimodal analysis
│   │   │   │   ├── __init__.py
│   │   │   │   ├── stt_service.py              # Whisper local / demo text passthrough
│   │   │   │   ├── tts_service.py              # ElevenLabs / Web Speech / text display
│   │   │   │   ├── audio_analyzer.py           # librosa: pace, filler words, pauses
│   │   │   │   └── facial_placeholder.py       # Receives MediaPipe data from frontend
│   │   │   │
│   │   │   └── reporting/                      # Module 4 — Report generation
│   │   │       ├── __init__.py
│   │   │       ├── score_calculator.py         # Aggregates all dimension scores
│   │   │       ├── report_builder.py           # Structures report content
│   │   │       ├── comparison_builder.py       # NEW — Builds ProgressComparison across sessions
│   │   │       ├── pdf_generator.py            # WeasyPrint PDF output
│   │   │       └── templates/
│   │   │           ├── report.html             # HTML template for PDF
│   │   │           └── comparison.html         # NEW — HTML template for comparison report
│   │   │
│   │   ├── api/                                # FastAPI application
│   │   │   ├── __init__.py
│   │   │   ├── main.py                         # FastAPI app entry point
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── setup.py                    # POST /setup — upload docs, init session
│   │   │   │   ├── interview.py                # POST /interview/answer, GET /interview/question
│   │   │   │   ├── report.py                   # GET /report/{session_id}
│   │   │   │   ├── candidates.py               # NEW — GET /candidates, GET /candidates/{id}/sessions
│   │   │   │   ├── comparison.py               # NEW — GET /compare?session_a=&session_b=
│   │   │   │   └── health.py                   # GET /health
│   │   │   ├── websockets/
│   │   │   │   ├── __init__.py
│   │   │   │   └── interview_ws.py             # WebSocket for real-time coaching
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       └── cors.py
│   │   │
│   │   ├── schemas/                            # Pydantic data contracts
│   │   │   ├── __init__.py
│   │   │   ├── candidate.py                    # CandidateProfile, ParsedCV, ParsedJD
│   │   │   ├── interview.py                    # Question, Answer, CoachingFeedback
│   │   │   ├── analysis.py                     # AudioMetrics, FacialMetrics
│   │   │   ├── report.py                       # DimensionScore, InterviewReport, ProgressComparison
│   │   │   ├── request.py                      # All API request models
│   │   │   └── response.py                     # All API response models
│   │   │
│   │   └── core/                               # Shared utilities
│   │       ├── __init__.py
│   │       ├── config.py                       # Settings + APP_MODE + is_demo property
│   │       ├── logger.py
│   │       └── exceptions.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_cv_parser.py
│   │   │   ├── test_jd_parser.py
│   │   │   ├── test_company_scraper.py
│   │   │   ├── test_company_retriever.py       # NEW
│   │   │   ├── test_question_bank.py
│   │   │   ├── test_session_manager.py
│   │   │   ├── test_stt_service.py
│   │   │   ├── test_tts_service.py
│   │   │   ├── test_audio_analyzer.py
│   │   │   ├── test_score_calculator.py
│   │   │   ├── test_comparison_builder.py      # NEW
│   │   │   └── test_pdf_generator.py
│   │   └── integration/
│   │       ├── test_setup_flow.py
│   │       ├── test_interview_flow.py
│   │       ├── test_report_flow.py
│   │       └── test_comparison_flow.py         # NEW
│   │
│   ├── scripts/
│   │   ├── seed_question_bank.py               # Populate role-specific question banks
│   │   └── evaluate_session.py                 # Run benchmark interview sessions
│   │
│   ├── data/
│   │   ├── candidates/                         # Persistent CandidateProfile JSON files
│   │   ├── sessions/                           # InterviewSession JSON files (one per attempt)
│   │   └── reports/                            # InterviewReport JSON + PDF files
│   │
│   ├── .env.example
│   ├── .gitignore
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── frontend/                                   # React application (built last)
│   │
│   ├── src/
│   │   ├── components/
│   │   │   ├── setup/
│   │   │   │   ├── UploadPanel.jsx             # CV, JD, motivation letter upload
│   │   │   │   ├── InterviewConfig.jsx         # NEW — length + mode selectors
│   │   │   │   └── SetupProgress.jsx           # Shows agent setup progress
│   │   │   ├── interview/
│   │   │   │   ├── InterviewRoom.jsx           # Main interview screen
│   │   │   │   ├── QuestionDisplay.jsx         # Shows current question (text always)
│   │   │   │   ├── AnswerInput.jsx             # Mic recorder OR text box (demo mode)
│   │   │   │   ├── CoachingSidebar.jsx         # Live feedback panel
│   │   │   │   ├── CameraFeed.jsx              # Webcam + MediaPipe overlay
│   │   │   │   └── ProgressBar.jsx             # Interview phase indicator
│   │   │   ├── report/
│   │   │   │   ├── ReportViewer.jsx            # Structured score display
│   │   │   │   ├── ComparisonViewer.jsx        # NEW — side-by-side session comparison
│   │   │   │   └── DownloadButton.jsx          # PDF download
│   │   │   └── history/
│   │   │       └── SessionHistory.jsx          # NEW — lists past sessions per candidate
│   │   │
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js                 # WS connection for live coaching
│   │   │   ├── useMediaPipe.js                 # Facial analysis hook
│   │   │   └── useAudioRecorder.js             # Mic capture hook
│   │   │
│   │   ├── services/
│   │   │   └── api.js                          # All HTTP calls to FastAPI
│   │   │
│   │   ├── context/
│   │   │   └── SessionContext.jsx              # Session ID + mode shared state
│   │   │
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   ├── evaluation.md
│   └── diagrams/
│       ├── agent_flow.png
│       └── session_state_flow.png
│
└── PROJECT_MANIFEST.md
```

---

## 3. Session State — The Central Contract

> **This is the most important section in the entire manifest.**
> Every module reads from and writes to this object.
> It is defined here, in full, before any module is built.
> No module may add fields to this object without updating this manifest first.

```python
# backend/src/graph/session_state.py

from typing import TypedDict, List, Optional, Literal
from src.schemas.candidate import CandidateProfile
from src.schemas.interview import Question, Answer, CoachingFeedback
from src.schemas.analysis import AudioMetrics, FacialMetrics
from src.schemas.report import InterviewReport

class InterviewSession(TypedDict):

    # ── Identity ──────────────────────────────────────────────────
    session_id: str                         # UUID, generated at setup
    candidate_id: str                       # UUID, links session to CandidateProfile
    created_at: str                         # ISO timestamp
    app_mode: Literal["demo", "production"] # Copied from settings at session init

    # ── Interview Configuration ────────────────────────────────────
    interview_length: Literal["short", "medium", "long"]
    interview_mode: Literal[
        "mixed", "technical", "behavioral", "hr_culture_fit", "system_design"
    ]

    # ── Module 1 Output: Ingestion ────────────────────────────────
    candidate: CandidateProfile             # Parsed from CV + JD + motivation letter
    company_context: str                    # Output from Company Research Agent (or "" in demo)
    question_plan: List[str]                # Ordered question roadmap from planner agent
    role_category: str                      # "software_engineer" | "data_scientist" | etc.

    # ── Module 2 Output: Interview Engine ─────────────────────────
    current_phase: Literal[
        "icebreaker", "cv_deep_dive", "dynamic_followup", "closing"
    ]
    current_question_index: int             # 0-based index into asked_questions
    asked_questions: List[Question]         # Full history of questions asked
    answers: List[Answer]                   # Full history of candidate answers
    coaching_feedback: List[CoachingFeedback]  # One per answer, from live coach agent
    difficulty_level: int                   # 1-5, adjusted by calibrator agent
    difficulty_dimensions: dict             # Per-dimension scores: relevance, clarity, depth, confidence, structure

    # ── Module 3 Output: Analysis ─────────────────────────────────
    audio_metrics_per_answer: List[AudioMetrics]  # One per answer
    facial_metrics_summary: FacialMetrics          # Aggregated over whole interview
    transcript: List[str]                          # Raw STT text per answer turn

    # ── Module 4 Output: Report ───────────────────────────────────
    final_report: Optional[InterviewReport]        # None until report phase
    pdf_path: Optional[str]                        # Path to generated PDF

    # ── System Fields ─────────────────────────────────────────────
    status: Literal[
        "setting_up", "ready", "in_progress", "completed", "error"
    ]
    error: Optional[str]
    step_log: List[str]                     # Audit trail of agent actions
```

### Persistent Data Structures

These are stored as JSON files on disk and are distinct from the in-flight `InterviewSession`.

```python
# backend/src/schemas/candidate.py (additional persistent models)

class CandidateProfile(BaseModel):
    candidate_id: str                       # UUID, stable across sessions
    full_name: str
    email: Optional[str]
    education: List[Education]
    experience: List[Experience]
    projects: List[Project]
    confirmed_skills: List[str]             # Confidently extracted from CV
    uncertain_skills: List[str]             # Inferred with low confidence — not used in evaluation
    motivation: str
    target_role: str
    target_company: str
    required_skills_from_jd: List[str]
    skills_gap: List[str]
    session_ids: List[str]                  # All InterviewSession IDs for this candidate
    created_at: str

# backend/src/schemas/report.py (additional persistent model)

class InterviewReport(BaseModel):
    session_id: str
    candidate_id: str
    # ... (full schema in Section 5.4)
```

**Relationship model:**

```
CandidateProfile (persistent, one per candidate)
├── InterviewSession 1
│   └── InterviewReport 1
├── InterviewSession 2
│   └── InterviewReport 2
└── InterviewSession N
    └── InterviewReport N
```

Each entity is persisted as a JSON file under `data/candidates/`, `data/sessions/`, and `data/reports/` respectively. No SQL database is used.

---

## 4. Data Flow

```
[User] → visits React app
    │
    ▼
[Setup Screen]
    │  Uploads: CV (PDF), Job Description (PDF/text),
    │           Company Name (text), Motivation Letter (text)
    │  Selects: Interview Length (short / medium / long)
    │           Interview Mode (mixed / technical / behavioral / hr_culture_fit / system_design)
    │
    │  POST /setup  { files + metadata + interview_length + interview_mode }
    ▼
[FastAPI: setup.py route]
    │  Creates candidate_id (UUID) or retrieves existing candidate
    │  Creates session_id (UUID)
    │  Initialises InterviewSession with status="setting_up"
    │  Invokes setup_graph
    ▼
[Setup Graph — LangGraph]
    │
    ├──► [CV Parser Agent]
    │       Extracts: name, education, confirmed_skills, uncertain_skills, experience, projects
    │       confirmed_skills: high-confidence extraction
    │       uncertain_skills: inferred / low-confidence — logged but not used for evaluation
    │       Output: session["candidate"]
    │
    ├──► [JD + Motivation Parser]
    │       Extracts: required skills, responsibilities, candidate's stated motivation
    │       Output: updates session["candidate"] with JD context
    │
    ├──► [Company Retriever]  ← NEW dedicated retrieval layer
    │       Searches company website, retrieves summary + recent news
    │       Returns structured RetrievedDocuments object
    │       Demo mode: returns empty document set immediately
    │
    ├──► [Company Research Agent]  ← consumes retrieved documents, no direct web access
    │       Input: RetrievedDocuments from retriever
    │       Summarises company context, extracts interview-relevant information
    │       Output: session["company_context"]
    │
    └──► [Interview Planner Agent]
            Reads: interview_length + interview_mode + candidate + company_context
            Designs personalised question roadmap with phase-aware question counts
            Selects role_category → loads role-specific + mode-specific question bank
            Output: session["question_plan"], session["role_category"]
            Status → "ready"
    │
    ▼
[FastAPI returns session_id to frontend]
    │
    ▼
[Interview Screen loads]
    │  Frontend opens WebSocket connection for live coaching
    │  Camera initialises MediaPipe.js (production) or shows placeholder (demo)
    │  Mic initialises recorder (production) or shows text box (demo)
    │
    ▼ (user clicks "Start Interview")
    │
    │  GET /interview/question?session_id=...
    ▼
[Conductor Agent]
    │  Determines next question from plan + current_phase + difficulty_level
    │  Returns Question object
    │
    ▼
[Frontend displays question]
    │  Production: ElevenLabs speaks the question
    │  Demo: question text displayed on screen
    │
    ▼ (user answers)
    │
    │  Production: Whisper transcribes mic audio
    │  Demo: user types answer into text box
    │
    │  POST /interview/answer { session_id, answer_text, audio_data?, facial_data? }
    ▼
[FastAPI: interview.py route]
    │  Stores Answer in session["answers"]
    │  Invokes live analysis pipeline — all steps run concurrently within this turn:
    │
    ├──► [Audio Analyzer] — runs on answer audio (or skipped in demo)
    │       Measures: WPM, filler word count, pause duration, energy
    │       Output: AudioMetrics → appended to session["audio_metrics_per_answer"]
    │
    ├──► [Live Coach Agent] — runs on answer text
    │       LLM evaluates: relevance, clarity, depth, STAR structure
    │       Returns 1-3 sentences of actionable feedback
    │       Output: CoachingFeedback → appended to session["coaching_feedback"]
    │       Sent immediately via WebSocket to frontend sidebar (real-time delivery)
    │
    ├──► [Difficulty Calibrator Agent]  ← dimension-aware
    │       Reads per-dimension scores from last answers
    │       Adjusts difficulty_dimensions independently
    │       Examples:
    │         High relevance + high depth → increase technical difficulty
    │         Low clarity → ask more structured behavioral questions
    │         Low confidence → temporarily reduce difficulty
    │         Strong STAR structure → generate deeper follow-up
    │       Output: session["difficulty_level"], session["difficulty_dimensions"]
    │
    └──► [Follow-Up Agent]  ← safeguarded
            Tracks followup_count per parent question (max: 2)
            If followup_count < 2: decides whether to follow up or advance
            If followup_count == 2: automatically advances to next planned question
            Output: next Question → session["asked_questions"]

    Concurrent outputs per answer turn:
    - coaching_feedback (WebSocket, real-time)
    - difficulty_level update (WebSocket)
    - next question (API response)
    - TTS audio for next question (API response)
    - audio + analysis metrics (stored in session)
    │
    ▼
[Frontend receives next question + coaching feedback simultaneously]
    │  Coaching appears in sidebar
    │  Next question spoken/displayed
    │
    ▼ (interview ends — all phases complete)
    │
    │  POST /report/generate { session_id }
    ▼
[Report Graph — LangGraph]
    │
    ├──► [Evaluator Agent]
    │       Scores all answers across 6 dimensions (see schemas)
    │       Each DimensionScore includes: score, feedback, evidence, rationale
    │       Only confirmed_skills used for technical scoring
    │       Aggregates audio + facial metrics
    │       Records interview_length + interview_mode in report
    │       Output: session["final_report"]
    │
    └──► [PDF Generator]
            Renders report.html template with scores + feedback
            Saves PDF to disk
            Output: session["pdf_path"]
    │
    ▼
[Frontend: Report Screen]
    │  Displays structured scores with evidence + rationale per dimension
    │  Download PDF button
    │  Option to compare with previous sessions (if candidate has history)
    │
    ▼
[User downloads report / views comparison]
```

---

## 5. Interface Definitions (The "Contracts")

---

### 5.1 `backend/src/schemas/candidate.py`

```python
from pydantic import BaseModel
from typing import List, Optional

class Education(BaseModel):
    institution: str
    degree: str
    field: str
    graduation_year: Optional[int]
    gpa: Optional[str]

class Experience(BaseModel):
    company: str
    role: str
    duration: str
    description: str
    technologies: List[str]

class Project(BaseModel):
    name: str
    description: str
    technologies: List[str]
    url: Optional[str]

class CandidateProfile(BaseModel):
    candidate_id: str               # UUID, stable across sessions
    full_name: str
    email: Optional[str]
    education: List[Education]
    experience: List[Experience]
    projects: List[Project]
    confirmed_skills: List[str]     # High-confidence CV extraction
    uncertain_skills: List[str]     # Inferred / low-confidence; logged only, not used in evaluation
    motivation: str                 # From motivation letter
    target_role: str                # From JD
    target_company: str             # User-provided
    required_skills_from_jd: List[str]
    skills_gap: List[str]           # Skills in JD not found in confirmed_skills
    session_ids: List[str]          # All session IDs linked to this candidate
    created_at: str                 # ISO timestamp
```

- **Input:** Raw PDF bytes (CV) + raw text (JD, motivation letter, company name)
- **Output:** Validated `CandidateProfile` object
- **Dependencies:** pydantic

> **Hallucination Protection:** The CV parser must explicitly classify each extracted skill as `confirmed` (directly stated in CV) or `uncertain` (inferred). Only `confirmed_skills` drive technical questioning, skill gap analysis, and technical scoring. `uncertain_skills` are stored for logging purposes only.

---

### 5.2 `backend/src/schemas/interview.py`

```python
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class Question(BaseModel):
    index: int
    text: str
    phase: Literal["icebreaker", "cv_deep_dive", "dynamic_followup", "closing"]
    category: str                # "behavioral" | "technical" | "motivational" | "situational" | "system_design"
    difficulty: int              # 1-5
    based_on_answer_index: Optional[int]  # If follow-up, which answer triggered it
    parent_question_index: Optional[int]  # Index of the original question (for follow-up tracking)
    followup_count: int          # How many follow-ups have been generated for parent question (0 for originals)
    asked_at: str                # ISO timestamp

class Answer(BaseModel):
    question_index: int
    text: str                    # Transcribed or typed text
    audio_path: Optional[str]    # Path to audio file (None in demo mode)
    answered_at: str             # ISO timestamp
    duration_seconds: Optional[float]

class CoachingFeedback(BaseModel):
    answer_index: int
    feedback_text: str           # 1-3 sentences, actionable
    score_preview: int           # 1-10, quick signal for the user
    strengths: List[str]         # What they did well
    improvements: List[str]      # What to improve
    dimension_scores: dict       # Per-dimension breakdown: relevance, clarity, depth, confidence, structure
```

- **Input:** Agent outputs during live interview
- **Output:** Typed objects stored in `InterviewSession`
- **Dependencies:** pydantic

> **Follow-Up Safeguard:** `followup_count` is tracked per original question. The Follow-Up Agent will not generate a follow-up once `followup_count == 2`. The Conductor Agent automatically advances to the next planned question at that point. `max_followups_per_question = 2` is a hard system constant.

---

### 5.3 `backend/src/schemas/analysis.py`

```python
from pydantic import BaseModel
from typing import Optional, List

class AudioMetrics(BaseModel):
    answer_index: int
    words_per_minute: Optional[float]
    filler_word_count: int                  # "um", "uh", "like", "you know"
    filler_words_detected: List[str]        # Actual instances found
    avg_pause_duration_seconds: Optional[float]
    longest_pause_seconds: Optional[float]
    voice_energy_level: Optional[float]     # librosa RMS energy, normalised 0-1
    demo_mode: bool                         # True if metrics not computed

class FacialMetrics(BaseModel):
    eye_contact_percentage: Optional[float] # % of time looking at camera
    avg_blink_rate_per_minute: Optional[float]
    head_movement_score: Optional[float]    # 0-1, lower = more stable
    engagement_score: Optional[float]       # Composite 0-100
    demo_mode: bool                         # True if metrics not computed
```

- **Input:** Audio bytes (librosa) + MediaPipe JSON data from frontend
- **Output:** Typed metrics objects
- **Dependencies:** pydantic, librosa (production)

---

### 5.4 `backend/src/schemas/report.py`

```python
from pydantic import BaseModel
from typing import List, Optional

class DimensionScore(BaseModel):
    name: str                    # e.g. "Communication Clarity"
    score: int                   # 1-10
    max_score: int               # 10
    feedback: str                # 2-3 sentences explaining the score
    evidence: List[str]          # Specific quotes or metrics that led to this score
    rationale: str               # Narrative explaining the reasoning behind the score

class InterviewReport(BaseModel):
    session_id: str
    candidate_id: str
    candidate_name: str
    target_role: str
    target_company: str
    interview_date: str

    # Interview configuration (recorded for context)
    interview_mode: str          # "mixed" | "technical" | "behavioral" | "hr_culture_fit" | "system_design"
    interview_length: str        # "short" | "medium" | "long"

    # Dimension scores — each includes score, feedback, evidence, rationale
    communication_clarity: DimensionScore
    technical_relevance: DimensionScore
    problem_solving: DimensionScore
    motivation_fit: DimensionScore
    confidence: DimensionScore
    listening_comprehension: DimensionScore

    # Aggregated metrics
    overall_score: float                    # Average of all dimension scores
    total_questions_asked: int
    total_duration_minutes: float
    avg_words_per_minute: Optional[float]
    total_filler_words: int
    eye_contact_percentage: Optional[float]

    # Narrative sections
    executive_summary: str                  # 3-4 sentence overview
    top_strengths: List[str]               # 3 bullet points
    areas_for_improvement: List[str]       # 3 bullet points
    recommended_next_steps: List[str]      # 3 actionable items

    # Per-question breakdown
    question_scores: List[DimensionScore]  # One per answer

    demo_mode: bool

class ProgressComparison(BaseModel):
    """
    Comparison between two completed InterviewSessions for the same candidate.
    """
    candidate_id: str
    previous_session_id: str
    current_session_id: str
    previous_interview_date: str
    current_interview_date: str

    # Score deltas (positive = improvement, negative = regression)
    overall_score_delta: float
    communication_delta: float
    technical_delta: float
    confidence_delta: float
    motivation_delta: float
    problem_solving_delta: float
    listening_delta: float

    # Qualitative change tracking
    strengths_improved: List[str]          # Dimensions or areas showing improvement
    weaknesses_improved: List[str]         # Previously weak areas that improved
    regressions_detected: List[str]        # Areas that declined since previous session

    # Narrative
    comparison_summary: str               # LLM-generated 3-4 sentence comparison narrative
```

> **Evaluation Traceability:** Every `DimensionScore` now includes `evidence` (concrete observations such as filler word counts, STAR structure detection, answer length metrics) and `rationale` (a narrative explanation connecting the evidence to the score). Users should always understand why a score was assigned.

---

### 5.5 `backend/src/schemas/retrieval.py` *(NEW)*

```python
from pydantic import BaseModel
from typing import List, Optional

class RetrievedDocument(BaseModel):
    source: str                  # URL or description of source
    content: str                 # Raw retrieved text
    doc_type: str                # "website" | "news" | "summary" | "placeholder"
    retrieved_at: str            # ISO timestamp

class RetrievedDocuments(BaseModel):
    company_name: str
    documents: List[RetrievedDocument]
    demo_mode: bool
```

---

### 5.6 `backend/src/core/config.py`

```python
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # Mode control — this gates ALL paid API calls
    app_mode: Literal["demo", "production"] = "demo"

    # LLM
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # TTS (production only)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # STT (production only — local Whisper path)
    whisper_model_size: str = "base"       # "base" | "small" | "medium"

    # App
    app_name: str = "AI Interviewer"
    app_version: str = "2.0.0"
    candidate_storage_path: str = "./data/candidates"
    session_storage_path: str = "./data/sessions"
    report_storage_path: str = "./data/reports"
    pdf_output_path: str = "./data/reports"
    cors_origins: list = ["http://localhost:5173"]

    # Interview constraints
    max_followups_per_question: int = 2    # Hard limit on follow-up chains

    class Config:
        env_file = ".env"

    @property
    def is_demo(self) -> bool:
        return self.app_mode == "demo"

settings = Settings()
```

---

### 5.7 Agent Contracts

#### `cv_parser_agent(state: InterviewSession) -> dict`
```
Input:  state["session_id"], raw CV bytes stored at session init
Action: LLM extracts structured profile from PDF text
        Classifies each skill as confirmed (explicit in CV) or uncertain (inferred)
        Computes skills_gap using confirmed_skills only
Output: {"candidate": CandidateProfile, "step_log": [...]}
Demo:   Identical — LLM still runs (OpenRouter free)
```

#### `company_retriever(company_name: str) -> RetrievedDocuments`
```
Input:  company_name string
Action: Searches company website (homepage, about page)
        Retrieves recent news articles
        Returns structured RetrievedDocuments
Demo:   Returns RetrievedDocuments(documents=[], demo_mode=True) immediately
Note:   This is a retrieval function, not an LLM agent. No reasoning performed here.
```

#### `company_research_agent(state: InterviewSession) -> dict`
```
Input:  RetrievedDocuments (from retriever), state["candidate"]["target_company"]
Action: LLM reads retrieved documents, summarises company context
        Extracts interview-relevant info (culture, mission, recent events)
        The LLM does NOT perform retrieval — it only reasons over supplied documents
Output: {"company_context": str, "step_log": [...]}
Demo:   Returns {"company_context": "", "step_log": ["demo: company research skipped"]}
```

#### `interview_planner_agent(state: InterviewSession) -> dict`
```
Input:  state["candidate"], state["company_context"],
        state["interview_length"], state["interview_mode"]
Action: LLM designs question roadmap based on length + mode
        interview_length determines total question count and phase sizes
        interview_mode determines question type distribution:
          technical:      80% technical, 20% behavioral
          behavioral:     80% behavioral, 20% technical
          hr_culture_fit: 70% culture/motivation, 30% behavioral
          system_design:  90% system design, 10% behavioral
          mixed:          balanced across all types
        Selects role_category → loads appropriate question bank
Output: {"question_plan": [...], "role_category": str, "step_log": [...]}
Demo:   Identical — LLM still runs
```

**Interview length targets:**

| Length | Total Questions | Icebreaker | CV Deep Dive | Dynamic / Follow-up | Closing | Approx Duration |
|---|---|---|---|---|---|---|
| short | 5–7 | 1 | 2 | 2 | 1 | 5–10 min |
| medium | 10–15 | 2–3 | 4–5 | 4–5 | 2 | 15–25 min |
| long | 18–25 | 3–4 | 7–8 | 7–8 | 3 | 30–45 min |

#### `conductor_agent(state: InterviewSession) -> dict`
```
Input:  Full session state
Action: Determines next question based on:
        - current_phase
        - current_question_index
        - difficulty_level + difficulty_dimensions
        - question_plan
        - interview_mode (influences question category selection)
Output: {"next_question": Question, "step_log": [...]}
Demo:   Identical
```

#### `followup_agent(state: InterviewSession) -> dict`
```
Input:  state["answers"][-1] (last answer), state["question_plan"],
        current question's followup_count
Action: If followup_count >= max_followups_per_question (2):
          Automatically signal advance — no LLM call made
        Else:
          LLM decides: follow up on this answer OR advance plan
          If follow-up: generates contextual question referencing the answer
Output: {"next_question": Question, "followup_count": int, "step_log": [...]}
Demo:   Identical
```

#### `live_coach_agent(state: InterviewSession) -> dict`
```
Input:  state["answers"][-1], state["asked_questions"][-1]
Action: LLM evaluates answer on: relevance, clarity, depth, confidence, STAR structure
        Returns per-dimension scores + 1-3 sentences of actionable real-time feedback
Output: {"coaching_feedback": CoachingFeedback, "step_log": [...]}
        Immediately pushed via WebSocket to frontend
Demo:   Identical
```

#### `difficulty_calibrator_agent(state: InterviewSession) -> dict`
```
Input:  state["coaching_feedback"][-2:] (last 2 per-dimension scores)
Action: Dimension-aware adjustment rules:
          High relevance + high depth  → increase technical difficulty
          Low clarity                  → shift to more structured behavioral questions
          Low confidence               → temporarily reduce difficulty
          Strong STAR structure        → generate deeper follow-up questions
        Overall difficulty_level is also updated as a composite signal.
        All adjustments clamped between 1 and 5.
Output: {"difficulty_level": int, "difficulty_dimensions": dict, "step_log": [...]}
Demo:   Identical
```

#### `evaluator_agent(state: InterviewSession) -> dict`
```
Input:  Full completed InterviewSession
Action: LLM scores all 6 dimensions based on full answer history
        Each DimensionScore includes score + feedback + evidence + rationale
        Only confirmed_skills used for technical dimension scoring
        Records interview_mode and interview_length in report
        Aggregates audio + facial metrics into report
Output: {"final_report": InterviewReport, "step_log": [...]}
Demo:   Runs identically but report flags demo_mode=True
        Facial/audio scores shown as None with explanatory note
```

---

### 5.8 API Endpoint Contracts

#### `POST /setup`
```
Request (multipart/form-data):
  cv_file:          PDF file
  jd_text:          string
  company_name:     string
  motivation_text:  string
  interview_length: "short" | "medium" | "long"         (default: "medium")
  interview_mode:   "mixed" | "technical" | "behavioral"
                    | "hr_culture_fit" | "system_design" (default: "mixed")

Response:
  {
    "session_id": "uuid-string",
    "candidate_id": "uuid-string",
    "status": "setting_up",
    "estimated_wait_seconds": 15
  }
```

#### `GET /setup/status?session_id=`
```
Response:
  {
    "session_id": "...",
    "candidate_id": "...",
    "status": "setting_up" | "ready" | "error",
    "candidate_name": "...",           # available once parsing done
    "question_count": 14,              # available once planning done
    "role_category": "...",
    "interview_length": "medium",
    "interview_mode": "technical",
    "error": null
  }
```

#### `GET /interview/question?session_id=`
```
Response:
  {
    "question": {
      "index": 3,
      "text": "Tell me about the multi-agent project on your CV...",
      "phase": "cv_deep_dive",
      "category": "technical",
      "difficulty": 3,
      "followup_count": 0
    },
    "audio_url": "/tts/question_3.mp3" | null,   # null in demo mode
    "interview_complete": false
  }
```

#### `POST /interview/answer`
```
Request (multipart/form-data):
  session_id:     string
  answer_text:    string    # typed (demo) or STT transcription (production)
  audio_file:     optional  # raw audio (production only)
  facial_data:    optional  # JSON from MediaPipe (production only)

Response:
  {
    "answer_received": true,
    "coaching_feedback": {
      "feedback_text": "...",
      "score_preview": 7,
      "strengths": ["..."],
      "improvements": ["..."],
      "dimension_scores": {
        "relevance": 7, "clarity": 5, "depth": 6, "confidence": 6, "structure": 4
      }
    },
    "next_question_ready": true
  }
```

#### `POST /report/generate`
```
Request: { "session_id": "..." }
Response:
  {
    "session_id": "...",
    "status": "generating" | "ready",
    "report_url": "/report/{session_id}",
    "pdf_download_url": "/report/{session_id}/pdf"
  }
```

#### `GET /report/{session_id}`
```
Response: Full InterviewReport JSON object
```

#### `GET /report/{session_id}/pdf`
```
Response: PDF file download (application/pdf)
```

#### `GET /candidates/{candidate_id}/sessions` *(NEW)*
```
Response:
  {
    "candidate_id": "...",
    "candidate_name": "...",
    "sessions": [
      {
        "session_id": "...",
        "interview_date": "...",
        "interview_mode": "technical",
        "interview_length": "medium",
        "overall_score": 6.2,
        "status": "completed"
      },
      ...
    ]
  }
```

#### `GET /compare?session_a={id}&session_b={id}` *(NEW)*
```
Response: ProgressComparison JSON object
```

#### `GET /compare/{session_a}/{session_b}/pdf` *(NEW)*
```
Response: PDF comparison report download (application/pdf)
```

#### `WebSocket /ws/interview/{session_id}`
```
Server pushes after each answer is processed:
  {
    "type": "coaching_feedback",
    "data": CoachingFeedback
  }
  {
    "type": "difficulty_update",
    "data": { "new_level": 4, "dimensions": {...} }
  }
  {
    "type": "interview_complete",
    "data": { "total_questions": 14 }
  }
```

---

## 6. Module Breakdown & Implementation Requirements

---

### Module 1 — Ingestion
**Goal:** Parse all uploaded documents into a structured `CandidateProfile`, with confirmed/uncertain skill classification and a dedicated retrieval layer for company research.
**Duration:** Week 2–3
**Depends on:** Nothing (first module)

#### Files to Create

**`backend/src/modules/ingestion/cv_parser.py`**
```python
import pdfplumber
from src.schemas.candidate import CandidateProfile
from src.core.config import settings

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF bytes using pdfplumber."""
    ...

def parse_cv(pdf_bytes: bytes) -> dict:
    """
    Input:  Raw PDF bytes
    Action: Extract text → call LLM with extraction prompt
            LLM returns structured JSON matching CandidateProfile fields
            Skills are classified into confirmed_skills and uncertain_skills:
              confirmed_skills: skills explicitly listed or clearly demonstrated
              uncertain_skills: skills inferred from context with low confidence
    Output: dict matching CandidateProfile schema
    Prompt: "Extract the following fields from this CV in JSON format:
             full_name, email, education[], experience[], projects[],
             confirmed_skills[], uncertain_skills[]
             confirmed_skills: only skills explicitly stated in the CV
             uncertain_skills: skills you inferred but are not certain about
             Return ONLY valid JSON, no explanation."
    """
    ...

# Exports: parse_cv, extract_text_from_pdf
```

**`backend/src/modules/ingestion/jd_parser.py`**
```python
def parse_jd(jd_text: str) -> dict:
    """
    Input:  Raw job description text
    Action: LLM extracts target_role, required_skills_from_jd
    Output: {"target_role": str, "required_skills_from_jd": List[str]}
    """
    ...

# Exports: parse_jd
```

**`backend/src/modules/ingestion/motivation_parser.py`**
```python
def parse_motivation(motivation_text: str) -> str:
    """
    Input:  Raw motivation letter text
    Action: LLM summarises core motivation into 2-3 sentences
    Output: str — concise motivation summary
    """
    ...

# Exports: parse_motivation
```

**`backend/src/modules/ingestion/company_scraper.py`**
```python
from src.core.config import settings

def scrape_company(company_name: str) -> str:
    """
    Production: Web search company name, scrape top result + Wikipedia summary
                Returns 200-300 word company context string
    Demo mode:  Returns "" immediately, no network call
    Note: This is the legacy scraper — the new retrieval layer in
          modules/retrieval/company_retriever.py supersedes this for
          structured retrieval. This file may be kept for simple fallback use.
    """
    if settings.is_demo:
        return ""
    ...

# Exports: scrape_company
```

**`backend/src/modules/retrieval/retriever.py`** *(NEW)*
```python
from src.schemas.retrieval import RetrievedDocuments

class BaseRetriever:
    """
    Abstract base retriever interface.
    Concrete implementations return RetrievedDocuments.
    The LLM never calls retrieval directly — retrieval is always a separate step.
    """
    def retrieve(self, query: str) -> RetrievedDocuments:
        raise NotImplementedError

# Exports: BaseRetriever
```

**`backend/src/modules/retrieval/company_retriever.py`** *(NEW)*
```python
from src.modules.retrieval.retriever import BaseRetriever
from src.schemas.retrieval import RetrievedDocuments, RetrievedDocument
from src.core.config import settings

class CompanyRetriever(BaseRetriever):
    """
    Retrieves structured company information before passing to Company Research Agent.

    Production responsibilities:
    - Search company website (homepage, about page)
    - Retrieve recent news / press releases
    - Return structured RetrievedDocuments with sources

    Demo mode:
    - Returns empty RetrievedDocuments immediately (no network call)

    The Company Research Agent consumes this output.
    The LLM in the agent is never expected to pretend it searched the web.
    """

    def retrieve(self, company_name: str) -> RetrievedDocuments:
        if settings.is_demo:
            return RetrievedDocuments(
                company_name=company_name,
                documents=[],
                demo_mode=True
            )
        # Web search + scrape logic here
        # Returns list of RetrievedDocument objects
        ...

company_retriever = CompanyRetriever()  # Singleton

# Exports: company_retriever, CompanyRetriever
```

**`backend/src/agents/cv_parser_agent.py`**
```python
from src.graph.session_state import InterviewSession
from src.modules.ingestion.cv_parser import parse_cv
from src.modules.ingestion.jd_parser import parse_jd
from src.modules.ingestion.motivation_parser import parse_motivation
from src.schemas.candidate import CandidateProfile

def cv_parser_agent(state: InterviewSession) -> dict:
    """
    Orchestrates all ingestion parsers.
    Skill gap computed using confirmed_skills only (not uncertain_skills).
    Returns fully populated CandidateProfile.
    """
    ...

# Exports: cv_parser_agent
```

**`backend/src/agents/company_research_agent.py`**
```python
from src.graph.session_state import InterviewSession
from src.modules.retrieval.company_retriever import company_retriever

def company_research_agent(state: InterviewSession) -> dict:
    """
    Step 1: Call company_retriever to fetch documents (no LLM here)
    Step 2: Pass retrieved documents to LLM for summarisation and reasoning
    The LLM reads the documents — it does not search the web itself.
    """
    retrieved = company_retriever.retrieve(state["candidate"]["target_company"])
    # LLM summarisation of retrieved.documents here
    ...

# Exports: company_research_agent
```

**`backend/tests/unit/test_cv_parser.py`**
```python
def test_extract_text_from_pdf(): ...
def test_parse_cv_returns_valid_profile(): ...
def test_confirmed_skills_populated(): ...
def test_uncertain_skills_populated(): ...
def test_skills_gap_uses_confirmed_skills_only(): ...
def test_parse_jd_extracts_required_skills(): ...
def test_scrape_company_returns_empty_in_demo_mode(): ...
```

**`backend/tests/unit/test_company_retriever.py`** *(NEW)*
```python
def test_retriever_returns_empty_in_demo_mode(): ...
def test_retriever_returns_retrieved_documents_schema(): ...
def test_company_research_agent_receives_documents(): ...
def test_llm_not_called_in_retrieval_step(): ...
```

**`backend/tests/integration/test_setup_flow.py`**
```python
def test_full_setup_flow_demo_mode(): ...
def test_setup_route_returns_session_id_and_candidate_id(): ...
def test_setup_status_reaches_ready(): ...
def test_interview_length_stored_in_session(): ...
def test_interview_mode_stored_in_session(): ...
```

> ✅ **Module 1 Done When:**
> - `pytest tests/unit/test_cv_parser.py` passes
> - A sample CV PDF produces a valid `CandidateProfile` with confirmed/uncertain skills classified
> - Demo mode returns empty company context and empty retrieval documents without network calls
> - Company Research Agent correctly consumes RetrievedDocuments (not calling retrieval itself)
> - `interview_length` and `interview_mode` are correctly stored in session state

---

### Module 2 — Interview Engine
**Goal:** Full agent-driven interview loop with mode-aware planning, dimension-aware difficulty calibration, follow-up safeguards, and interview length selection. Terminal-testable without UI.
**Duration:** Week 4–6
**Depends on:** Module 1 (`CandidateProfile` in session state)

#### Files to Create

**`backend/src/modules/interview_engine/question_bank.py`**
```python
# Role-specific and mode-specific curated question sets
# Prevents 100% LLM reliance for base questions

QUESTION_BANK = {
    "software_engineer": {
        "icebreaker": [
            "Tell me about yourself and your journey into software engineering.",
            "Why are you interested in this role at {company}?",
            "Where do you see yourself in 5 years?"
        ],
        "technical": [
            "Walk me through the most technically challenging project on your CV.",
            "How do you approach debugging a complex production issue?",
        ],
        "behavioral": [
            "Tell me about a time you disagreed with a technical decision.",
        ],
        "system_design": [
            "Design a URL shortener. Walk me through your approach.",
            "How would you design a distributed logging service?",
        ]
    },
    "data_scientist": { ... },
    "product_manager": { ... },
    "business_analyst": { ... },
    "ml_engineer": {
        "technical": [
            "Walk me through how you would deploy a model to production.",
            "How do you detect and handle data drift in a live ML system?",
        ],
        "system_design": [
            "Design a recommendation system for an e-commerce platform.",
            "How would you design an experimentation platform for ML models?",
        ],
        ...
    }
}

# Mode-specific question type distributions
MODE_DISTRIBUTIONS = {
    "mixed":          {"technical": 0.35, "behavioral": 0.35, "motivational": 0.20, "situational": 0.10},
    "technical":      {"technical": 0.80, "behavioral": 0.15, "motivational": 0.05, "situational": 0.00},
    "behavioral":     {"technical": 0.10, "behavioral": 0.80, "motivational": 0.05, "situational": 0.05},
    "hr_culture_fit": {"technical": 0.00, "behavioral": 0.30, "motivational": 0.60, "situational": 0.10},
    "system_design":  {"technical": 0.05, "behavioral": 0.05, "motivational": 0.00, "system_design": 0.90},
}

def get_base_questions(role_category: str, phase: str, mode: str) -> list:
    """Returns base questions for a role + phase + mode combination."""
    ...

def detect_role_category(target_role: str) -> str:
    """
    Maps free-text job title to one of 5 role categories.
    Uses LLM for ambiguous cases.
    """
    ...

# Exports: get_base_questions, detect_role_category, QUESTION_BANK, MODE_DISTRIBUTIONS
```

**`backend/src/modules/interview_engine/session_manager.py`**
```python
import json
import os
from src.graph.session_state import InterviewSession
from src.schemas.candidate import CandidateProfile
from src.core.config import settings

class SessionManager:
    """
    Manages active interview sessions in memory + persists to disk.
    In-memory dict for fast access during live interview.
    JSON file on disk for recovery + history.

    CandidateProfiles, InterviewSessions, and InterviewReports are stored
    in separate directories. One candidate may have many sessions.
    """

    def __init__(self):
        self._sessions: dict[str, InterviewSession] = {}
        self._candidates: dict[str, CandidateProfile] = {}

    # Session operations
    def create_session(self, session_id: str, initial_state: InterviewSession) -> None: ...
    def get_session(self, session_id: str) -> InterviewSession: ...
    def update_session(self, session_id: str, updates: dict) -> InterviewSession: ...

    # Candidate operations
    def create_candidate(self, candidate: CandidateProfile) -> None: ...
    def get_candidate(self, candidate_id: str) -> CandidateProfile: ...
    def get_candidate_sessions(self, candidate_id: str) -> list[str]: ...

    def list_sessions(self) -> list[str]: ...

session_manager = SessionManager()  # Singleton

# Exports: session_manager, SessionManager
```

**`backend/src/modules/interview_engine/flow_controller.py`**
```python
from src.graph.session_state import InterviewSession
from typing import Literal

# Hard system constant
MAX_FOLLOWUPS_PER_QUESTION = 2

def get_current_phase(state: InterviewSession) -> str:
    """
    Determines interview phase based on question index + plan.
    Phase boundaries are dynamic based on interview_length:
      short:  0     → icebreaker, 1-2 → cv_deep_dive, 3-4 → dynamic_followup, 5-6 → closing
      medium: 0-2   → icebreaker, 3-7 → cv_deep_dive, 8-12 → dynamic_followup, 13+ → closing
      long:   0-3   → icebreaker, 4-11 → cv_deep_dive, 12-19 → dynamic_followup, 20+ → closing
    """
    ...

def is_interview_complete(state: InterviewSession) -> bool:
    """Returns True when all planned questions have been asked + answered."""
    ...

def should_followup(state: InterviewSession) -> bool:
    """
    Returns True if:
    - followup_count for current question < MAX_FOLLOWUPS_PER_QUESTION
    - AND (last answer score < 5 OR answer contained an expandable claim)
    Returns False automatically if followup_count >= MAX_FOLLOWUPS_PER_QUESTION.
    """
    ...

def get_followup_count(state: InterviewSession, question_index: int) -> int:
    """Returns the number of follow-ups generated for a given question index."""
    ...

# Exports: get_current_phase, is_interview_complete, should_followup, get_followup_count, MAX_FOLLOWUPS_PER_QUESTION
```

**`backend/src/agents/conductor_agent.py`**
```python
from src.graph.session_state import InterviewSession
from src.modules.interview_engine.flow_controller import get_current_phase
from src.modules.interview_engine.question_bank import get_base_questions

def conductor_agent(state: InterviewSession) -> dict:
    """
    Core question delivery agent.
    Selects next question based on phase, difficulty, plan, and interview_mode.
    Applies difficulty modifier to question phrasing via LLM.
    Returns Question object with followup_count=0 for new questions.
    """
    ...
```

**`backend/src/agents/followup_agent.py`**
```python
from src.modules.interview_engine.flow_controller import MAX_FOLLOWUPS_PER_QUESTION

FOLLOWUP_PROMPT = """
The candidate just answered this question:
Q: {question}
A: {answer}

Their answer score was {score}/10.

Decide:
1. If the answer mentioned a specific project, technology, or claim worth probing → generate a follow-up question
2. Otherwise → return null (we will move to the next planned question)

If generating a follow-up, it must directly reference something the candidate said.
Return JSON: {"should_followup": bool, "followup_question": str | null}
"""

def followup_agent(state: InterviewSession) -> dict:
    """
    Enforces follow-up limit: if current question already has MAX_FOLLOWUPS_PER_QUESTION
    follow-ups (2), skip LLM call and signal advance immediately.
    Otherwise, generates a context-aware follow-up or signals to advance the plan.
    """
    ...
```

**`backend/src/agents/live_coach_agent.py`**
```python
COACH_PROMPT = """
You are a professional interview coach providing real-time feedback.
The candidate just answered:
Q: {question}
A: {answer}

Evaluate on:
- Relevance (did they answer what was asked?)
- Clarity (was it easy to follow?)
- Depth (enough detail without rambling?)
- Confidence (did they sound assured?)
- Structure (did they use STAR or a logical flow?)

Return JSON:
{
  "feedback_text": "2-3 sentence actionable feedback",
  "score_preview": 1-10,
  "strengths": ["..."],
  "improvements": ["..."],
  "dimension_scores": {
    "relevance": 1-10,
    "clarity": 1-10,
    "depth": 1-10,
    "confidence": 1-10,
    "structure": 1-10
  }
}
"""

def live_coach_agent(state: InterviewSession) -> dict:
    """
    Runs immediately after each answer.
    Result is pushed to frontend via WebSocket before next question loads.
    Returns per-dimension scores for use by difficulty calibrator.
    """
    ...
```

**`backend/src/agents/difficulty_calibrator_agent.py`**
```python
def difficulty_calibrator_agent(state: InterviewSession) -> dict:
    """
    Dimension-aware difficulty adjustment.

    Reads dimension_scores from last 2 coaching feedback objects.

    Rules:
    - High relevance + high depth  → difficulty_level += 1 (max 5)
    - Low clarity                  → shift toward structured behavioral questions
    - Low confidence               → difficulty_level -= 1 (min 1)
    - Strong STAR structure        → signal deeper follow-up generation
    - Low overall (avg < 4)        → difficulty_level -= 1

    Updates both difficulty_level (composite) and difficulty_dimensions (per-axis).
    """
    ...
```

**`backend/src/graph/interview_graph.py`**
```python
from langgraph.graph import StateGraph, END
from src.graph.session_state import InterviewSession
from src.graph.edges import should_generate_followup

def build_interview_graph():
    """
    Per-answer graph: runs after each answer submission.
    audio_analyzer → live_coach → difficulty_calibrator → followup_or_advance

    All nodes within this graph run concurrently where possible.
    WebSocket push of coaching_feedback occurs as soon as live_coach completes,
    without waiting for difficulty calibration or follow-up decision.
    """
    graph = StateGraph(InterviewSession)
    # nodes + edges here
    return graph.compile()
```

**`backend/src/api/websockets/interview_ws.py`**
```python
from fastapi import WebSocket
from src.modules.interview_engine.session_manager import session_manager

async def interview_websocket(websocket: WebSocket, session_id: str):
    """
    Maintains persistent WS connection per interview session.
    Receives coaching feedback + difficulty updates from agent pipeline.
    Pushes coaching_feedback immediately when available (before follow-up decision).
    Pushes difficulty_update after calibration completes.
    """
    await websocket.accept()
    ...
```

> ✅ **Module 2 Done When:**
> - Terminal script runs a full interview loop using typed input for short, medium, and long length
> - Follow-up agent never generates more than 2 follow-ups per question
> - Dimension-aware difficulty calibration fires correctly based on per-dimension scores
> - Conductor generates correct question distribution for each interview_mode
> - Candidate–session relationship persists correctly across multiple sessions
> - WebSocket pushes coaching feedback in < 2 seconds after answer received

---

### Module 3 — Analysis
**Goal:** Audio analysis + STT + TTS + facial metric handling, all with clean demo substitutes.
**Duration:** Week 7–9
**Depends on:** Module 2 (slots into answer pipeline)

#### Files to Create

**`backend/src/modules/analysis/stt_service.py`**
```python
from src.core.config import settings

def transcribe(audio_bytes: bytes | None, text_input: str | None) -> str:
    """
    Production: Loads Whisper model, transcribes audio_bytes
                Returns transcript string with word-level timestamps available
    Demo mode:  Returns text_input directly (no Whisper loaded)
    """
    if settings.is_demo:
        return text_input or ""
    ...

# Exports: transcribe
```

**`backend/src/modules/analysis/tts_service.py`**
```python
from src.core.config import settings

def speak(text: str) -> dict:
    """
    Production: Calls ElevenLabs API, returns audio bytes + URL
    Demo mode:  Returns {"mode": "text", "content": text, "audio_url": None}
    Frontend handles both: plays audio OR displays text depending on mode field.
    """
    if settings.is_demo:
        return {"mode": "text", "content": text, "audio_url": None}
    ...

# Exports: speak
```

**`backend/src/modules/analysis/audio_analyzer.py`**
```python
from src.schemas.analysis import AudioMetrics
from src.core.config import settings

FILLER_WORDS = ["um", "uh", "like", "you know", "basically", "literally", "sort of"]

def analyze_audio(audio_bytes: bytes | None, transcript: str, answer_index: int) -> AudioMetrics:
    """
    Production: Uses librosa for energy/pace, transcript for filler words
    Demo mode:  Returns AudioMetrics with all Optional fields as None, demo_mode=True

    Computes:
    - words_per_minute: word count / duration
    - filler_word_count: count FILLER_WORDS in transcript (works in both modes)
    - avg_pause_duration: from librosa silence detection
    - voice_energy_level: RMS energy normalised 0-1
    """
    if settings.is_demo:
        filler_count = sum(transcript.lower().count(fw) for fw in FILLER_WORDS)
        return AudioMetrics(
            answer_index=answer_index,
            words_per_minute=None,
            filler_word_count=filler_count,
            filler_words_detected=[fw for fw in FILLER_WORDS if fw in transcript.lower()],
            avg_pause_duration_seconds=None,
            longest_pause_seconds=None,
            voice_energy_level=None,
            demo_mode=True
        )
    ...

# Exports: analyze_audio
```

**`backend/src/modules/analysis/facial_placeholder.py`**
```python
from src.schemas.analysis import FacialMetrics
from src.core.config import settings

def process_facial_data(mediapipe_json: dict | None) -> FacialMetrics:
    """
    Production: Receives MediaPipe JSON from frontend, computes engagement metrics
    Demo mode:  Returns FacialMetrics with all fields None, demo_mode=True
    """
    if settings.is_demo or mediapipe_json is None:
        return FacialMetrics(
            eye_contact_percentage=None,
            avg_blink_rate_per_minute=None,
            head_movement_score=None,
            engagement_score=None,
            demo_mode=True
        )
    ...

# Exports: process_facial_data
```

> ✅ **Module 3 Done When:**
> - `APP_MODE=demo` → STT returns typed text, TTS returns text dict, audio analyzer returns partial metrics, facial returns placeholder
> - `APP_MODE=production` → Whisper transcribes audio correctly, ElevenLabs returns audio, librosa extracts WPM + filler words
> - All services tested in both modes

---

### Module 4 — Reporting
**Goal:** Transform completed `InterviewSession` into a scored, structured PDF report with traceable evidence and rationale. Support cross-session progress comparison.
**Duration:** Week 10–11
**Depends on:** Modules 1–3 (full session state)

#### Files to Create

**`backend/src/modules/reporting/score_calculator.py`**
```python
from src.graph.session_state import InterviewSession
from src.schemas.report import DimensionScore

def calculate_communication_clarity(state: InterviewSession) -> DimensionScore:
    """
    Uses: coaching_feedback dimension scores (clarity, structure) + audio_metrics (WPM, filler words)
    Evidence: e.g. "18 filler words detected", "STAR structure missing in 2 answers"
    Rationale: narrative explanation connecting evidence to score
    """
    ...

def calculate_technical_relevance(state: InterviewSession) -> DimensionScore:
    """
    Uses: answer content vs required_skills_from_jd
          Only confirmed_skills are considered — uncertain_skills are excluded
    Evidence: which required skills were demonstrated
    Rationale: explains skill coverage and gaps
    """
    ...

def calculate_problem_solving(state: InterviewSession) -> DimensionScore: ...
def calculate_motivation_fit(state: InterviewSession) -> DimensionScore: ...
def calculate_confidence(state: InterviewSession) -> DimensionScore: ...
def calculate_listening_comprehension(state: InterviewSession) -> DimensionScore: ...

def calculate_all_scores(state: InterviewSession) -> dict:
    """Runs all 6 dimension calculators, returns dict of DimensionScore objects."""
    ...

# Exports: calculate_all_scores
```

**`backend/src/modules/reporting/report_builder.py`**
```python
from src.graph.session_state import InterviewSession
from src.schemas.report import InterviewReport

def build_report(state: InterviewSession, dimension_scores: dict) -> InterviewReport:
    """
    Assembles all scores + metrics + LLM-generated narrative into InterviewReport.
    Records interview_mode and interview_length in report for context.
    Narrative sections generated via LLM.
    """
    ...

# Exports: build_report
```

**`backend/src/modules/reporting/comparison_builder.py`** *(NEW)*
```python
from src.schemas.report import InterviewReport, ProgressComparison

def build_comparison(
    previous_report: InterviewReport,
    current_report: InterviewReport
) -> ProgressComparison:
    """
    Computes score deltas across all dimensions.
    Identifies improvements, areas still requiring work, and regressions.
    Generates a comparison narrative via LLM.

    Example output:
      overall_score_delta: +1.2
      communication_delta: +1.3
      confidence_delta: +1.8
      regressions_detected: ["Technical depth", "Answer structure"]
    """
    ...

# Exports: build_comparison
```

**`backend/src/modules/reporting/pdf_generator.py`**
```python
from weasyprint import HTML
from src.schemas.report import InterviewReport, ProgressComparison
import os

def generate_pdf(report: InterviewReport, output_path: str) -> str:
    """
    Renders report.html template with report data using Jinja2.
    Converts HTML → PDF using WeasyPrint.
    Returns full file path.
    """
    ...

def generate_comparison_pdf(comparison: ProgressComparison, output_path: str) -> str:
    """
    Renders comparison.html template with ProgressComparison data.
    Returns full file path.
    """
    ...

# Exports: generate_pdf, generate_comparison_pdf
```

**`backend/src/modules/reporting/templates/report.html`**
```html
<!-- Jinja2 template for PDF report -->
<!-- Sections:
  - Header: candidate name, role, company, date
  - Interview Configuration: Mode, Length, Questions Asked, Duration
  - Overall Score
  - 6 Dimension Score Cards: each shows score, feedback, evidence list, rationale paragraph
  - Per-question breakdown
  - Audio metrics
  - Facial metrics (if production)
  - Narrative sections: executive summary, strengths, improvements, next steps
  - Footer: demo mode notice if applicable
-->
```

**`backend/src/modules/reporting/templates/comparison.html`** *(NEW)*
```html
<!-- Jinja2 template for progress comparison PDF report -->
<!-- Sections:
  - Header: candidate name, Session A vs Session B
  - Overall Score Comparison (side-by-side)
  - Per-dimension delta table (positive deltas in green, negative in red)
  - Improvements list
  - Areas Still Requiring Work list
  - Regressions Detected list
  - Comparison narrative paragraph
-->
```

**`backend/src/agents/evaluator_agent.py`**
```python
from src.graph.session_state import InterviewSession
from src.modules.reporting.score_calculator import calculate_all_scores
from src.modules.reporting.report_builder import build_report

def evaluator_agent(state: InterviewSession) -> dict:
    """
    Final agent. Runs once at interview completion.
    Calculates all scores → builds report → sets session status to "completed"
    Each DimensionScore includes evidence + rationale for full traceability.
    Only confirmed_skills used for technical scoring.
    """
    scores = calculate_all_scores(state)
    report = build_report(state, scores)
    return {
        "final_report": report,
        "status": "completed",
        "step_log": [*state["step_log"], "evaluator_agent: report generated"]
    }
```

**`backend/tests/unit/test_comparison_builder.py`** *(NEW)*
```python
def test_positive_delta_detected(): ...
def test_negative_delta_detected(): ...
def test_regressions_identified(): ...
def test_comparison_narrative_generated(): ...
def test_comparison_pdf_renders(): ...
```

> ✅ **Module 4 Done When:**
> - Given a complete mock `InterviewSession`, generates a valid `InterviewReport` with evidence + rationale on every DimensionScore
> - PDF renders correctly with interview_mode + interview_length in the configuration section
> - Given two mock InterviewReports, `build_comparison` returns a valid `ProgressComparison` with correct deltas
> - Comparison PDF renders correctly
> - Demo mode report clearly marks facial/audio sections as "unavailable in demo mode"
> - `pytest tests/unit/test_score_calculator.py`, `test_pdf_generator.py`, `test_comparison_builder.py` pass

---

### Module 5 — Frontend (React)
**Goal:** Complete, polished UI connecting to the fully finished backend.
**Duration:** Week 12–14
**Depends on:** ALL backend modules complete and tested

> ⚠️ **This module starts ONLY when all 4 backend modules are done.**
> Every API endpoint must be tested and stable before a single React component is written.

#### Files to Create

**`frontend/src/services/api.js`**
```javascript
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const setupInterview = async (formData) => {
    // POST /setup with multipart form data (includes interview_length + interview_mode)
    // Returns { session_id, candidate_id, status }
};

export const getSetupStatus = async (sessionId) => {
    // GET /setup/status?session_id=
};

export const getNextQuestion = async (sessionId) => {
    // GET /interview/question?session_id=
};

export const submitAnswer = async (sessionId, answerText, audioBlob, facialData) => {
    // POST /interview/answer
};

export const generateReport = async (sessionId) => {
    // POST /report/generate
};

export const getReport = async (sessionId) => {
    // GET /report/{session_id}
};

export const getCandidateSessions = async (candidateId) => {
    // GET /candidates/{candidate_id}/sessions
};

export const compareReports = async (sessionA, sessionB) => {
    // GET /compare?session_a=&session_b=
};
```

**`frontend/src/components/setup/InterviewConfig.jsx`** *(NEW)*
```javascript
// Renders two selectors during setup:
//   Interview Length: short / medium / long  (default: medium)
//   Interview Mode: mixed / technical / behavioral / hr_culture_fit / system_design  (default: mixed)
// Values submitted as part of POST /setup form data
```

**`frontend/src/components/history/SessionHistory.jsx`** *(NEW)*
```javascript
// Lists all past sessions for a candidate
// Shows: date, mode, length, overall score, status
// Provides links to view individual reports
// Provides "Compare" button to select two sessions for ProgressComparison view
```

**`frontend/src/components/report/ComparisonViewer.jsx`** *(NEW)*
```javascript
// Renders a ProgressComparison side-by-side:
// Left column: previous session scores
// Right column: current session scores
// Center: delta indicators (green arrows up, red arrows down)
// Bottom: improvements, regressions, narrative summary
// Download button for comparison PDF
```

**`frontend/src/hooks/useWebSocket.js`**
```javascript
export const useWebSocket = (sessionId) => {
    // Connects to WS /ws/interview/{session_id}
    // Returns: { coachingFeedback, difficultyLevel, difficultyDimensions, isConnected }
    // Handles reconnection on drop
};
```

**`frontend/src/hooks/useMediaPipe.js`**
```javascript
export const useMediaPipe = (videoRef, isDemo) => {
    // If isDemo: returns null immediately, no MediaPipe loaded
    // If production: loads MediaPipe, runs face mesh on video stream
    // Returns: { facialData, isReady }
    // facialData sent with each answer submission
};
```

**`frontend/src/hooks/useAudioRecorder.js`**
```javascript
export const useAudioRecorder = (isDemo) => {
    // If isDemo: returns null, no mic access requested
    // If production: manages mic recording lifecycle
    // Returns: { startRecording, stopRecording, audioBlob, isRecording }
};
```

**`frontend/src/context/SessionContext.jsx`**
```javascript
// Global state: session_id, candidate_id, app_mode, candidate_name,
//               current_phase, interview_length, interview_mode
// Shared across all screens via React Context
```

**`frontend/src/components/interview/InterviewRoom.jsx`**
```javascript
// Main interview screen layout:
// Left: CameraFeed (production) or placeholder (demo)
// Center: QuestionDisplay + AnswerInput
// Right: CoachingSidebar (live feedback via WS, includes per-dimension scores)
// Bottom: ProgressBar showing phase + question count
```

**`frontend/src/components/interview/AnswerInput.jsx`**
```javascript
// Production: mic button → records audio → submits blob
// Demo: text area + submit button → submits typed text
// Determined by SessionContext.app_mode
```

> ✅ **Module 5 Done When:**
> - Full interview flow works end-to-end in browser in demo mode
> - Interview length and mode selectors work at setup; values reflected in session
> - Full interview flow works in production mode with real mic/camera
> - Follow-up limit (2 per question) is visible to user via progress indicators
> - Report screen displays all 6 dimension scores with evidence + rationale + PDF download
> - Session history screen lists past sessions for a candidate
> - Comparison screen renders ProgressComparison correctly for any two completed sessions
> - App deployed to Vercel (frontend) + Render (backend)

---

## 7. Demo Mode Reference

### Environment Variables

```bash
# .env — Demo Mode (development)
APP_MODE=demo
OPENROUTER_API_KEY=your_key   # Still needed — but uses free models
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free

# .env — Production Mode (demo recording / public deployment)
APP_MODE=production
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=your_voice_id
WHISPER_MODEL_SIZE=base
```

### Demo Mode Substitution Table

| Feature | Production Behaviour | Demo Substitute | Cost Saved |
|---|---|---|---|
| TTS | ElevenLabs API call | `{"mode": "text", "content": question}` | ~$0.005/session |
| STT | Whisper mic transcription | Text input field in UI | $0 (Whisper is local anyway) |
| Camera / Facial | MediaPipe.js face mesh | Camera hidden, placeholder metrics returned | $0 |
| Company retriever | Web search + scrape | Returns empty RetrievedDocuments immediately | API call skipped |
| Company research agent | Summarises retrieved documents | Returns "" immediately | LLM call skipped |
| LLM calls | OpenRouter free models | Same — no change | Already free |
| Audio analysis | librosa full analysis | Filler word count from text only | Compute saved |

### Switching Modes

```bash
# Development (all APIs free, fast iteration)
APP_MODE=demo uvicorn src.api.main:app --reload

# Recording demo video (full production quality)
APP_MODE=production uvicorn src.api.main:app --reload
```

### Frontend Demo Mode Banner

When `app_mode === "demo"` the UI shows:

```
┌──────────────────────────────────────────────────────────┐
│  🧪 Demo Mode — Camera/mic disabled. Type your answers.  │
└──────────────────────────────────────────────────────────┘
```

All other UI is identical. The interview experience is fully testable.

---

## 8. Appendix

### Full Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_MODE` | ✅ | `demo` | `demo` or `production` |
| `OPENROUTER_API_KEY` | ✅ | — | OpenRouter API key |
| `OPENROUTER_MODEL` | ❌ | `meta-llama/llama-3.3-70b-instruct:free` | LLM model slug |
| `ELEVENLABS_API_KEY` | Prod only | — | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | Prod only | — | Voice ID for interviewer |
| `WHISPER_MODEL_SIZE` | Prod only | `base` | Whisper model size |
| `CANDIDATE_STORAGE_PATH` | ❌ | `./data/candidates` | Where candidate JSON files live |
| `SESSION_STORAGE_PATH` | ❌ | `./data/sessions` | Where session JSON files live |
| `REPORT_STORAGE_PATH` | ❌ | `./data/reports` | Where report JSON + PDF files live |
| `PDF_OUTPUT_PATH` | ❌ | `./data/reports` | Where generated PDFs are saved |

### Key Commands

```bash
# Backend setup
cd backend
python -m venv env && source env/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in your keys

# Run backend
uvicorn src.api.main:app --reload

# Run tests
pytest tests/ -v

# Frontend setup
cd frontend
npm install
npm run dev
```

### Cost Summary

| Component | Cost |
|---|---|
| LLM (OpenRouter free tier) | $0 |
| STT (local Whisper) | $0 |
| TTS in demo mode | $0 |
| TTS in production (ElevenLabs free) | $0 (10k chars/month) |
| MediaPipe.js | $0 |
| librosa | $0 |
| PDF generation (WeasyPrint) | $0 |
| **Total dev + demo cost** | **$0** |
| **Per session (public deployment)** | **~$0.11** |

### Module Build Order (Non-Negotiable)

```
Week 1:     Manifest + contracts (this document)
Week 2-3:   Module 1 — Ingestion (+ retrieval layer)
Week 4-6:   Module 2 — Interview Engine
Week 7-9:   Module 3 — Analysis
Week 10-11: Module 4 — Reporting (+ comparison builder)
Week 12-14: Module 5 — Frontend (+ history + comparison UI)
Week 15:    Polish, deployment, README, demo video
```

### What Changed in v2.0.0

| # | Change | Impact |
|---|---|---|
| 1 | Candidate–Session–Report separation | Candidate has stable ID; sessions + reports linked to it |
| 2 | Interview progress tracking | `ProgressComparison` schema + comparison builder + comparison PDF + comparison API endpoint |
| 3 | Retrieval layer for company research | `modules/retrieval/` added; LLM no longer pretends to search the web |
| 4 | Dimension-aware difficulty calibration | `difficulty_calibrator_agent` uses 5 independent axes instead of a single average |
| 5 | Evaluation traceability | `DimensionScore` now requires `evidence` list + `rationale` string |
| 6 | Follow-up safeguard | `max_followups_per_question = 2`; tracked via `followup_count` on `Question` |
| 7 | Resume hallucination protection | `confirmed_skills` vs `uncertain_skills` split; only confirmed used in evaluation |
| 8 | Interview length selection | `interview_length` field: short / medium / long with defined question count targets |
| 9 | Multiple outputs per turn | Architecture explicitly supports concurrent coaching, calibration, and question generation |
| 10 | Interview mode selection | `interview_mode` field: mixed / technical / behavioral / hr_culture_fit / system_design |

---

*This manifest is the single source of truth. No module begins until the previous one passes its completion criteria. The frontend does not start until all 4 backend modules are complete.*
