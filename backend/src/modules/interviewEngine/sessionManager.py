# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/interviewEngine/sessionManager.py
#
# Session Manager — In-memory store + JSON disk persistence
#
# Responsibilities:
#   1. Maintain an in-memory dict of active InterviewSession states for fast
#      access during live interviews (avoids disk reads on every question turn).
#   2. Persist sessions, candidates, and reports to separate JSON files on disk
#      under the paths configured in appConfig.
#   3. Manage the one-to-many linkage: CandidateProfile.session_ids → [session_id, ...]
#   4. Provide both synchronous (for tests, scripts) and async (for FastAPI routes)
#      versions of read/write operations.
#   5. Strip ephemeral runtime-only fields (prefixed with "_") before any disk write.
#
# Directory layout (relative to backend/):
#   ./data/candidates/{candidate_id}.json   — CandidateProfile
#   ./data/sessions/{session_id}.json       — InterviewSession snapshot
#   ./data/reports/{session_id}.json        — InterviewReport
#
# Exports: SessionManager, sessionManager (singleton)
# ─────────────────────────────────────────────────────────────────────────────

import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiofiles

from src.core.appConfig import settings

logger = logging.getLogger(__name__)

# ── Fields that must never be written to disk ──────────────────────────────────
# These carry raw bytes or large runtime blobs that are only needed in-flight.
_EPHEMERAL_FIELD_PREFIXES = ("_",)
_EPHEMERAL_EXACT_KEYS = {"cv_bytes_input", "jd_text_input", "motivation_text_input"}

# ── Valid session status transitions ──────────────────────────────────────────
_VALID_STATUSES = {"setting_up", "ready", "in_progress", "completed", "error"}

def _stripEphemeralFields(session: dict) -> dict:
    """
    Return a shallow copy of the session dict with all ephemeral runtime fields
    removed. Ephemeral fields are identified by:
      - A leading underscore in the key (e.g. _runtime_blob), OR
      - Membership in _EPHEMERAL_EXACT_KEYS (e.g. cv_bytes_input)

    This is called before every disk write — never persist raw PDF bytes, etc.
    """
    return {
        k: v for k, v in session.items()
        if not k.startswith("_") and k not in _EPHEMERAL_EXACT_KEYS
    }


class SessionManager:
    """
    Manages the full lifecycle of InterviewSession and CandidateProfile objects.

    In-memory layer:
        Fast dict lookup for active sessions during a live interview. Avoids
        disk I/O on the critical path (each question/answer turn).

    Disk persistence layer:
        Each entity is a single JSON file named by its UUID.
        Writes are atomic: write to a temp file then rename.

    Candidate ↔ Session linkage:
        CandidateProfile.session_ids is the authoritative list.
        When a new session is created or linked, the candidate JSON is updated.
    """

    def __init__(
        self,
        candidateStoragePath: Optional[str] = None,
        sessionStoragePath: Optional[str] = None,
        reportStoragePath: Optional[str] = None,
    ):
        """
        Args:
            candidateStoragePath: Override the candidates directory (useful for tests).
            sessionStoragePath:   Override the sessions directory.
            reportStoragePath:    Override the reports directory.

        If not provided, the paths from appConfig.settings are used.
        """
        self._activeSessions: dict[str, dict] = {}

        self._candidateDir = Path(
            candidateStoragePath or settings.candidate_storage_path
        )
        self._sessionDir = Path(
            sessionStoragePath or settings.session_storage_path
        )
        self._reportDir = Path(
            reportStoragePath or settings.report_storage_path
        )

    # ── Directory Setup ────────────────────────────────────────────────────────

    def ensureDirectories(self) -> None:
        """Create all storage directories if they do not already exist."""
        self._candidateDir.mkdir(parents=True, exist_ok=True)
        self._sessionDir.mkdir(parents=True, exist_ok=True)
        self._reportDir.mkdir(parents=True, exist_ok=True)
        logger.debug(
            "Storage directories ensured: candidates=%s, sessions=%s, reports=%s",
            self._candidateDir, self._sessionDir, self._reportDir,
        )

    # ── Private Path Helpers ───────────────────────────────────────────────────

    def _getSessionPath(self, sessionId: str) -> Path:
        return self._sessionDir / f"{sessionId}.json"

    def _getCandidatePath(self, candidateId: str) -> Path:
        return self._candidateDir / f"{candidateId}.json"

    def _getReportPath(self, sessionId: str) -> Path:
        return self._reportDir / f"{sessionId}.json"

    # ── Session Creation ───────────────────────────────────────────────────────

    def createSession(
        self,
        candidateId: str,
        interviewLength: str = "medium",
        interviewMode: str = "mixed",
        targetCompany: str = "",
        appMode: Optional[str] = None,
    ) -> dict:
        """
        Create a new InterviewSession dict, store it in memory, and return it.

        This initialises ALL fields of the InterviewSession TypedDict to safe
        defaults. The LangGraph setup graph will fill in the Module 1 fields
        (candidate, company_context, question_plan) via agent nodes.

        Args:
            candidateId:    UUID string for the candidate (stable across sessions).
            interviewLength: "short" | "medium" | "long".
            interviewMode:   "mixed" | "technical" | "behavioral" | "hr_culture_fit" | "system_design".
            targetCompany:   Company name provided by the user at setup.
            appMode:         Override app mode (defaults to settings.app_mode).

        Returns:
            Fully initialised InterviewSession dict stored in memory.
        """
        sessionId = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        resolvedAppMode = appMode or settings.app_mode

        session: dict = {
            # ── Identity ──────────────────────────────────────────────────────
            "session_id": sessionId,
            "candidate_id": candidateId,
            "created_at": now,
            "app_mode": resolvedAppMode,

            # ── Interview Configuration ────────────────────────────────────────
            "interview_length": interviewLength,
            "interview_mode": interviewMode,

            # ── Module 1 Outputs (populated by setup graph) ───────────────────
            "candidate": {
                "candidate_id": candidateId,
                "full_name": "",
                "email": None,
                "education": [],
                "experience": [],
                "projects": [],
                "confirmed_skills": [],
                "uncertain_skills": [],
                "motivation": "",
                "target_role": "",
                "target_company": targetCompany,
                "required_skills_from_jd": [],
                "skills_gap": [],
                "session_ids": [sessionId],
                "created_at": now,
            },
            "company_context": "",
            "question_plan": [],
            "role_category": "",

            # ── Module 2 Outputs (populated during interview) ─────────────────
            "current_phase": "icebreaker",
            "current_question_index": 0,
            "asked_questions": [],
            "answers": [],
            "coaching_feedback": [],
            "difficulty_level": 2,
            "difficulty_dimensions": {
                "relevance": 2,
                "clarity": 2,
                "depth": 2,
                "confidence": 2,
                "structure": 2,
            },

            # ── Module 3 Outputs ───────────────────────────────────────────────
            "audio_metrics_per_answer": [],
            "facial_metrics_summary": {
                "eye_contact_percentage": None,
                "avg_blink_rate_per_minute": None,
                "head_movement_score": None,
                "engagement_score": None,
                "demo_mode": resolvedAppMode == "demo",
            },
            "transcript": [],

            # ── Module 4 Outputs ───────────────────────────────────────────────
            "final_report": None,
            "pdf_path": None,

            # ── System Fields ──────────────────────────────────────────────────
            "status": "setting_up",
            "error": None,
            "step_log": [f"[sessionManager] Session {sessionId} created at {now}."],
        }

        self._activeSessions[sessionId] = session
        logger.info("Created session %s for candidate %s", sessionId, candidateId)
        return session

    # ── In-Memory Access ───────────────────────────────────────────────────────

    def getSession(self, sessionId: str) -> Optional[dict]:
        """
        Retrieve a session from the in-memory store.

        Returns None if the session is not loaded (call loadSession to fetch from disk).
        """
        return self._activeSessions.get(sessionId)

    def updateSession(self, sessionId: str, updates: dict) -> dict:
        """
        Apply a partial update dict to an in-memory session (LangGraph merge pattern).

        Args:
            sessionId: The session to update.
            updates:   Partial dict of fields to update. Only specified keys are changed.

        Returns:
            The updated full session dict.

        Raises:
            KeyError: If sessionId is not in the in-memory store.
        """
        if sessionId not in self._activeSessions:
            raise KeyError(
                f"Session '{sessionId}' is not in memory. "
                "Call loadSession() first or createSession() to initialise."
            )
        self._activeSessions[sessionId].update(updates)
        return self._activeSessions[sessionId]

    def setSessionStatus(self, sessionId: str, status: str, error: Optional[str] = None) -> None:
        """
        Update the status field of an in-memory session.

        Args:
            sessionId: Target session.
            status:    New status value. Must be one of the valid status literals.
            error:     Optional error message (required when status == "error").

        Raises:
            ValueError: If status is not a valid value.
            KeyError:   If session is not in memory.
        """
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {_VALID_STATUSES}"
            )
        if sessionId not in self._activeSessions:
            raise KeyError(f"Session '{sessionId}' is not in memory.")
        self._activeSessions[sessionId]["status"] = status
        if error is not None:
            self._activeSessions[sessionId]["error"] = error
        logger.debug("Session %s status → %s", sessionId, status)

    def removeFromMemory(self, sessionId: str) -> None:
        """
        Remove a session from the in-memory store (call after persisting to disk).
        Silently does nothing if the session is not loaded.
        """
        self._activeSessions.pop(sessionId, None)

    def getActiveSessionIds(self) -> list:
        """Return list of all session IDs currently held in memory."""
        return list(self._activeSessions.keys())

    # ── Sync Disk Persistence — Sessions ──────────────────────────────────────

    def saveSession(self, session: dict) -> str:
        """
        Persist a session dict to disk as a JSON file.
        Ephemeral fields (prefixed with "_") are stripped before writing.

        Args:
            session: The InterviewSession dict to persist.

        Returns:
            Absolute path string of the written file.
        """
        self.ensureDirectories()
        sessionId = session["session_id"]
        diskData = _stripEphemeralFields(session)
        filePath = self._getSessionPath(sessionId)

        # Atomic write: write to temp then rename
        tmpPath = filePath.with_suffix(".tmp")
        tmpPath.write_text(json.dumps(diskData, indent=2, default=str), encoding="utf-8")
        tmpPath.replace(filePath)  # replace() is atomic and overwrites on Windows

        logger.debug("Session %s persisted to %s", sessionId, filePath)
        return str(filePath)

    def loadSession(self, sessionId: str) -> Optional[dict]:
        """
        Load a session from disk into the in-memory store and return it.

        Returns None if the file does not exist.
        """
        filePath = self._getSessionPath(sessionId)
        if not filePath.exists():
            logger.debug("Session file not found: %s", filePath)
            return None

        data = json.loads(filePath.read_text(encoding="utf-8"))
        self._activeSessions[sessionId] = data
        logger.debug("Session %s loaded from disk into memory", sessionId)
        return data

    def sessionExists(self, sessionId: str) -> bool:
        """Return True if the session JSON file exists on disk."""
        return self._getSessionPath(sessionId).exists()

    # ── Sync Disk Persistence — Candidates ────────────────────────────────────

    def saveCandidate(self, candidateData: dict) -> str:
        """
        Persist a CandidateProfile dict to disk.

        Args:
            candidateData: Dict matching CandidateProfile schema.

        Returns:
            Absolute path string of the written file.
        """
        self.ensureDirectories()
        candidateId = candidateData["candidate_id"]
        filePath = self._getCandidatePath(candidateId)

        tmpPath = filePath.with_suffix(".tmp")
        tmpPath.write_text(json.dumps(candidateData, indent=2, default=str), encoding="utf-8")
        tmpPath.replace(filePath)

        logger.debug("Candidate %s persisted to %s", candidateId, filePath)
        return str(filePath)

    def loadCandidate(self, candidateId: str) -> Optional[dict]:
        """Load a CandidateProfile from disk. Returns None if not found."""
        filePath = self._getCandidatePath(candidateId)
        if not filePath.exists():
            logger.debug("Candidate file not found: %s", filePath)
            return None
        return json.loads(filePath.read_text(encoding="utf-8"))

    def candidateExists(self, candidateId: str) -> bool:
        """Return True if the candidate JSON file exists on disk."""
        return self._getCandidatePath(candidateId).exists()

    # ── Candidate ↔ Session Linkage ────────────────────────────────────────────

    def linkSessionToCandidate(self, candidateId: str, sessionId: str) -> None:
        """
        Append a sessionId to the candidate's session_ids list and re-save.

        If the candidate does not exist yet on disk (first session ever), this
        is a no-op — the session will be linked when the candidate is first saved
        via saveCandidate() with the session_id already in session_ids.

        Args:
            candidateId: The stable candidate UUID.
            sessionId:   The new session UUID to append.
        """
        candidateData = self.loadCandidate(candidateId)
        if candidateData is None:
            logger.debug(
                "Candidate %s not found on disk — linkage will occur at first saveCandidate()",
                candidateId,
            )
            return

        existingIds: list = candidateData.get("session_ids", [])
        if sessionId not in existingIds:
            existingIds.append(sessionId)
            candidateData["session_ids"] = existingIds
            self.saveCandidate(candidateData)
            logger.info(
                "Linked session %s to candidate %s (%d total sessions)",
                sessionId, candidateId, len(existingIds),
            )

    def listCandidateSessions(self, candidateId: str) -> list:
        """
        Return the list of session_ids for a candidate, loaded from disk.

        Returns an empty list if the candidate does not exist.
        """
        candidateData = self.loadCandidate(candidateId)
        if candidateData is None:
            return []
        return candidateData.get("session_ids", [])

    # ── Sync Disk Persistence — Reports ───────────────────────────────────────

    def saveReport(self, reportData: dict) -> str:
        """
        Persist an InterviewReport dict to disk.

        Args:
            reportData: Dict matching InterviewReport schema.

        Returns:
            Absolute path string of the written file.
        """
        self.ensureDirectories()
        sessionId = reportData["session_id"]
        filePath = self._getReportPath(sessionId)

        tmpPath = filePath.with_suffix(".tmp")
        tmpPath.write_text(json.dumps(reportData, indent=2, default=str), encoding="utf-8")
        tmpPath.replace(filePath)

        logger.debug("Report for session %s persisted to %s", sessionId, filePath)
        return str(filePath)

    def loadReport(self, sessionId: str) -> Optional[dict]:
        """Load an InterviewReport from disk. Returns None if not found."""
        filePath = self._getReportPath(sessionId)
        if not filePath.exists():
            return None
        return json.loads(filePath.read_text(encoding="utf-8"))

    # ── Async Wrappers (for FastAPI routes) ────────────────────────────────────

    async def saveSessionAsync(self, session: dict) -> str:
        """Async version of saveSession using aiofiles."""
        self.ensureDirectories()
        sessionId = session["session_id"]
        diskData = _stripEphemeralFields(session)
        filePath = self._getSessionPath(sessionId)
        tmpPath = filePath.with_suffix(".tmp")

        async with aiofiles.open(str(tmpPath), mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(diskData, indent=2, default=str))

        tmpPath.replace(filePath)
        return str(filePath)

    async def loadSessionAsync(self, sessionId: str) -> Optional[dict]:
        """Async version of loadSession."""
        filePath = self._getSessionPath(sessionId)
        if not filePath.exists():
            return None

        async with aiofiles.open(str(filePath), mode="r", encoding="utf-8") as f:
            content = await f.read()

        data = json.loads(content)
        self._activeSessions[sessionId] = data
        return data

    async def saveCandidateAsync(self, candidateData: dict) -> str:
        """Async version of saveCandidate."""
        self.ensureDirectories()
        candidateId = candidateData["candidate_id"]
        filePath = self._getCandidatePath(candidateId)
        tmpPath = filePath.with_suffix(".tmp")

        async with aiofiles.open(str(tmpPath), mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(candidateData, indent=2, default=str))

        tmpPath.replace(filePath)
        return str(filePath)

    async def loadCandidateAsync(self, candidateId: str) -> Optional[dict]:
        """Async version of loadCandidate."""
        filePath = self._getCandidatePath(candidateId)
        if not filePath.exists():
            return None

        async with aiofiles.open(str(filePath), mode="r", encoding="utf-8") as f:
            content = await f.read()

        return json.loads(content)


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this everywhere. Never instantiate SessionManager() again in application code.
# Tests should instantiate their own SessionManager with tmp_path overrides.
sessionManager = SessionManager()
