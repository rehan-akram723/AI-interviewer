# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testSessionManager.py
#
# Unit tests for src.modules.interviewEngine.sessionManager
#
# All disk I/O uses pytest's tmp_path fixture — zero writes to real ./data/.
# Tests cover:
#   1. Session creation (in-memory state)
#   2. Session persistence and loading from disk
#   3. Candidate persistence and loading from disk
#   4. Candidate ↔ Session linkage
#   5. Ephemeral field stripping before disk writes
#   6. In-memory store operations (update, setStatus, remove)
#   7. Async variants (saveSessionAsync, loadSessionAsync, saveCandidateAsync)
#   8. Edge cases (missing files, invalid status, double-link)
# ─────────────────────────────────────────────────────────────────────────────

import json
import uuid
import pytest
from pathlib import Path

from src.modules.interviewEngine.sessionManager import SessionManager, _stripEphemeralFields


# ════════════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def manager(tmp_path):
    """
    SessionManager instance with isolated tmp directories.
    Never writes to real ./data/ directories.
    """
    return SessionManager(
        candidateStoragePath=str(tmp_path / "candidates"),
        sessionStoragePath=str(tmp_path / "sessions"),
        reportStoragePath=str(tmp_path / "reports"),
    )


@pytest.fixture
def sampleCandidateId():
    return str(uuid.uuid4())


@pytest.fixture
def sampleSession(manager, sampleCandidateId):
    """A freshly created session in memory."""
    return manager.createSession(
        candidateId=sampleCandidateId,
        interviewLength="medium",
        interviewMode="mixed",
        targetCompany="Acme Corp",
    )


@pytest.fixture
def sampleCandidateData(sampleCandidateId):
    return {
        "candidate_id": sampleCandidateId,
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "education": [],
        "experience": [],
        "projects": [],
        "confirmed_skills": ["Python", "FastAPI"],
        "uncertain_skills": ["Kubernetes"],
        "motivation": "Excited about AI.",
        "target_role": "Backend Engineer",
        "target_company": "Acme Corp",
        "required_skills_from_jd": ["Python", "Docker"],
        "skills_gap": ["Docker"],
        "session_ids": [],
        "created_at": "2026-01-01T00:00:00Z",
    }


# ════════════════════════════════════════════════════════════════════════════════
# Session Creation — in-memory
# ════════════════════════════════════════════════════════════════════════════════

class TestSessionCreation:

    def test_createSession_returns_dict(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        assert isinstance(session, dict)

    def test_createSession_has_session_id(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        assert "session_id" in session
        assert session["session_id"]  # Non-empty string

    def test_createSession_session_id_is_uuid(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        # Should not raise if it's a valid UUID
        parsed = uuid.UUID(session["session_id"])
        assert str(parsed) == session["session_id"]

    def test_createSession_candidate_id_preserved(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        assert session["candidate_id"] == sampleCandidateId

    def test_createSession_interview_length_stored(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId, interviewLength="long")
        assert session["interview_length"] == "long"

    def test_createSession_interview_mode_stored(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId, interviewMode="technical")
        assert session["interview_mode"] == "technical"

    def test_createSession_status_is_setting_up(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        assert session["status"] == "setting_up"

    def test_createSession_phase_is_icebreaker(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        assert session["current_phase"] == "icebreaker"

    def test_createSession_difficulty_starts_at_2(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        assert session["difficulty_level"] == 2

    def test_createSession_all_lists_are_empty(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        for field in ["question_plan", "asked_questions", "answers",
                      "coaching_feedback", "audio_metrics_per_answer", "transcript"]:
            assert session[field] == [], f"Field '{field}' should be empty list"

    def test_createSession_optional_fields_are_none(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        assert session["final_report"] is None
        assert session["pdf_path"] is None
        assert session["error"] is None

    def test_createSession_stored_in_memory(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        sessionId = session["session_id"]
        assert manager.getSession(sessionId) is not None

    def test_createSession_two_sessions_have_unique_ids(self, manager, sampleCandidateId):
        s1 = manager.createSession(candidateId=sampleCandidateId)
        s2 = manager.createSession(candidateId=sampleCandidateId)
        assert s1["session_id"] != s2["session_id"]

    def test_createSession_step_log_has_entry(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        assert len(session["step_log"]) >= 1
        assert any("sessionManager" in entry for entry in session["step_log"])

    def test_createSession_difficulty_dimensions_all_present(self, manager, sampleCandidateId):
        session = manager.createSession(candidateId=sampleCandidateId)
        dims = session["difficulty_dimensions"]
        for dim in ["relevance", "clarity", "depth", "confidence", "structure"]:
            assert dim in dims, f"Dimension '{dim}' missing from difficulty_dimensions"
            assert 1 <= dims[dim] <= 5


# ════════════════════════════════════════════════════════════════════════════════
# In-Memory Operations
# ════════════════════════════════════════════════════════════════════════════════

class TestInMemoryOperations:

    def test_getSession_returns_session(self, manager, sampleSession):
        retrieved = manager.getSession(sampleSession["session_id"])
        assert retrieved is not None
        assert retrieved["session_id"] == sampleSession["session_id"]

    def test_getSession_returns_none_for_unknown_id(self, manager):
        assert manager.getSession("nonexistent-id") is None

    def test_updateSession_merges_partial_dict(self, manager, sampleSession):
        sessionId = sampleSession["session_id"]
        manager.updateSession(sessionId, {"current_phase": "cv_deep_dive"})
        updated = manager.getSession(sessionId)
        assert updated["current_phase"] == "cv_deep_dive"

    def test_updateSession_does_not_overwrite_other_fields(self, manager, sampleSession):
        sessionId = sampleSession["session_id"]
        originalMode = sampleSession["interview_mode"]
        manager.updateSession(sessionId, {"current_phase": "cv_deep_dive"})
        assert manager.getSession(sessionId)["interview_mode"] == originalMode

    def test_updateSession_raises_on_unknown_session(self, manager):
        with pytest.raises(KeyError):
            manager.updateSession("nonexistent", {"status": "ready"})

    def test_setSessionStatus_updates_status(self, manager, sampleSession):
        sessionId = sampleSession["session_id"]
        manager.setSessionStatus(sessionId, "ready")
        assert manager.getSession(sessionId)["status"] == "ready"

    def test_setSessionStatus_sets_error_message(self, manager, sampleSession):
        sessionId = sampleSession["session_id"]
        manager.setSessionStatus(sessionId, "error", error="LLM timeout")
        session = manager.getSession(sessionId)
        assert session["status"] == "error"
        assert session["error"] == "LLM timeout"

    def test_setSessionStatus_raises_on_invalid_status(self, manager, sampleSession):
        with pytest.raises(ValueError, match="Invalid status"):
            manager.setSessionStatus(sampleSession["session_id"], "cooking")

    def test_setSessionStatus_raises_on_unknown_session(self, manager):
        with pytest.raises(KeyError):
            manager.setSessionStatus("ghost-session", "ready")

    def test_removeFromMemory_removes_session(self, manager, sampleSession):
        sessionId = sampleSession["session_id"]
        manager.removeFromMemory(sessionId)
        assert manager.getSession(sessionId) is None

    def test_removeFromMemory_is_silent_on_unknown_id(self, manager):
        # Should not raise
        manager.removeFromMemory("never-existed")

    def test_getActiveSessionIds_returns_list(self, manager, sampleSession):
        ids = manager.getActiveSessionIds()
        assert isinstance(ids, list)
        assert sampleSession["session_id"] in ids


# ════════════════════════════════════════════════════════════════════════════════
# Ephemeral Field Stripping
# ════════════════════════════════════════════════════════════════════════════════

class TestEphemeralFieldStripping:

    def test_strips_underscore_prefixed_fields(self):
        session = {
            "session_id": "abc",
            "_cv_bytes": b"raw bytes",
            "_jd_text": "job description",
            "status": "setting_up",
        }
        stripped = _stripEphemeralFields(session)
        assert "_cv_bytes" not in stripped
        assert "_jd_text" not in stripped

    def test_preserves_non_ephemeral_fields(self):
        session = {
            "session_id": "abc",
            "_cv_bytes": b"bytes",
            "status": "setting_up",
            "interview_mode": "mixed",
        }
        stripped = _stripEphemeralFields(session)
        assert "session_id" in stripped
        assert "status" in stripped
        assert "interview_mode" in stripped

    def test_does_not_mutate_original(self):
        session = {"session_id": "abc", "_cv_bytes": b"bytes"}
        _stripEphemeralFields(session)
        assert "_cv_bytes" in session  # Original unchanged

    def test_empty_session_returns_empty_dict(self):
        assert _stripEphemeralFields({}) == {}

    def test_session_with_no_ephemeral_fields_returned_unchanged(self):
        session = {"session_id": "abc", "status": "ready"}
        stripped = _stripEphemeralFields(session)
        assert stripped == session


# ════════════════════════════════════════════════════════════════════════════════
# Session Disk Persistence
# ════════════════════════════════════════════════════════════════════════════════

class TestSessionDiskPersistence:

    def test_saveSession_creates_json_file(self, manager, sampleSession):
        manager.saveSession(sampleSession)
        sessionId = sampleSession["session_id"]
        filePath = Path(manager._sessionDir) / f"{sessionId}.json"
        assert filePath.exists()

    def test_saveSession_writes_valid_json(self, manager, sampleSession):
        manager.saveSession(sampleSession)
        sessionId = sampleSession["session_id"]
        filePath = Path(manager._sessionDir) / f"{sessionId}.json"
        data = json.loads(filePath.read_text(encoding="utf-8"))
        assert data["session_id"] == sessionId

    def test_saveSession_strips_ephemeral_fields(self, manager, sampleSession):
        sampleSession["_cv_bytes"] = b"should not be saved"
        manager.saveSession(sampleSession)
        sessionId = sampleSession["session_id"]
        filePath = Path(manager._sessionDir) / f"{sessionId}.json"
        data = json.loads(filePath.read_text(encoding="utf-8"))
        assert "_cv_bytes" not in data

    def test_saveSession_returns_file_path_string(self, manager, sampleSession):
        result = manager.saveSession(sampleSession)
        assert isinstance(result, str)
        assert sampleSession["session_id"] in result

    def test_loadSession_returns_dict(self, manager, sampleSession):
        manager.saveSession(sampleSession)
        sessionId = sampleSession["session_id"]
        manager.removeFromMemory(sessionId)
        loaded = manager.loadSession(sessionId)
        assert isinstance(loaded, dict)

    def test_loadSession_restores_session_id(self, manager, sampleSession):
        manager.saveSession(sampleSession)
        sessionId = sampleSession["session_id"]
        manager.removeFromMemory(sessionId)
        loaded = manager.loadSession(sessionId)
        assert loaded["session_id"] == sessionId

    def test_loadSession_loads_into_memory(self, manager, sampleSession):
        manager.saveSession(sampleSession)
        sessionId = sampleSession["session_id"]
        manager.removeFromMemory(sessionId)
        manager.loadSession(sessionId)
        assert manager.getSession(sessionId) is not None

    def test_loadSession_returns_none_for_missing_file(self, manager):
        result = manager.loadSession("does-not-exist")
        assert result is None

    def test_sessionExists_true_after_save(self, manager, sampleSession):
        manager.saveSession(sampleSession)
        assert manager.sessionExists(sampleSession["session_id"]) is True

    def test_sessionExists_false_before_save(self, manager, sampleCandidateId):
        assert manager.sessionExists("never-saved") is False

    def test_save_and_load_preserves_all_required_fields(self, manager, sampleSession):
        manager.saveSession(sampleSession)
        sessionId = sampleSession["session_id"]
        manager.removeFromMemory(sessionId)
        loaded = manager.loadSession(sessionId)

        requiredFields = [
            "session_id", "candidate_id", "created_at", "app_mode",
            "interview_length", "interview_mode", "candidate", "company_context",
            "question_plan", "role_category", "current_phase",
            "current_question_index", "asked_questions", "answers",
            "coaching_feedback", "difficulty_level", "difficulty_dimensions",
            "audio_metrics_per_answer", "facial_metrics_summary", "transcript",
            "final_report", "pdf_path", "status", "error", "step_log",
        ]
        for field in requiredFields:
            assert field in loaded, f"Field '{field}' missing after save/load cycle"

    def test_overwrite_existing_session_on_second_save(self, manager, sampleSession):
        """Saving a modified session should overwrite the previous file."""
        sessionId = sampleSession["session_id"]
        manager.saveSession(sampleSession)

        manager.updateSession(sessionId, {"current_phase": "cv_deep_dive"})
        manager.saveSession(manager.getSession(sessionId))

        manager.removeFromMemory(sessionId)
        loaded = manager.loadSession(sessionId)
        assert loaded["current_phase"] == "cv_deep_dive"


# ════════════════════════════════════════════════════════════════════════════════
# Candidate Disk Persistence
# ════════════════════════════════════════════════════════════════════════════════

class TestCandidateDiskPersistence:

    def test_saveCandidate_creates_json_file(self, manager, sampleCandidateData):
        manager.saveCandidate(sampleCandidateData)
        candidateId = sampleCandidateData["candidate_id"]
        filePath = Path(manager._candidateDir) / f"{candidateId}.json"
        assert filePath.exists()

    def test_saveCandidate_returns_file_path_string(self, manager, sampleCandidateData):
        result = manager.saveCandidate(sampleCandidateData)
        assert isinstance(result, str)
        assert sampleCandidateData["candidate_id"] in result

    def test_loadCandidate_returns_dict(self, manager, sampleCandidateData):
        manager.saveCandidate(sampleCandidateData)
        loaded = manager.loadCandidate(sampleCandidateData["candidate_id"])
        assert isinstance(loaded, dict)

    def test_loadCandidate_restores_full_name(self, manager, sampleCandidateData):
        manager.saveCandidate(sampleCandidateData)
        loaded = manager.loadCandidate(sampleCandidateData["candidate_id"])
        assert loaded["full_name"] == "Jane Doe"

    def test_loadCandidate_restores_confirmed_skills(self, manager, sampleCandidateData):
        manager.saveCandidate(sampleCandidateData)
        loaded = manager.loadCandidate(sampleCandidateData["candidate_id"])
        assert "Python" in loaded["confirmed_skills"]

    def test_loadCandidate_returns_none_for_missing_file(self, manager):
        assert manager.loadCandidate("nonexistent-candidate") is None

    def test_candidateExists_true_after_save(self, manager, sampleCandidateData):
        manager.saveCandidate(sampleCandidateData)
        assert manager.candidateExists(sampleCandidateData["candidate_id"]) is True

    def test_candidateExists_false_before_save(self, manager):
        assert manager.candidateExists("never-saved") is False


# ════════════════════════════════════════════════════════════════════════════════
# Candidate ↔ Session Linkage
# ════════════════════════════════════════════════════════════════════════════════

class TestCandidateSessionLinkage:

    def test_linkSessionToCandidate_appends_session_id(
        self, manager, sampleCandidateData
    ):
        manager.saveCandidate(sampleCandidateData)
        candidateId = sampleCandidateData["candidate_id"]
        newSessionId = str(uuid.uuid4())

        manager.linkSessionToCandidate(candidateId, newSessionId)
        candidateSessions = manager.listCandidateSessions(candidateId)
        assert newSessionId in candidateSessions

    def test_linkSessionToCandidate_multiple_sessions(
        self, manager, sampleCandidateData
    ):
        """One candidate can have multiple linked sessions."""
        manager.saveCandidate(sampleCandidateData)
        candidateId = sampleCandidateData["candidate_id"]

        session1Id = str(uuid.uuid4())
        session2Id = str(uuid.uuid4())
        session3Id = str(uuid.uuid4())

        manager.linkSessionToCandidate(candidateId, session1Id)
        manager.linkSessionToCandidate(candidateId, session2Id)
        manager.linkSessionToCandidate(candidateId, session3Id)

        sessions = manager.listCandidateSessions(candidateId)
        assert session1Id in sessions
        assert session2Id in sessions
        assert session3Id in sessions
        assert len(sessions) >= 3

    def test_linkSessionToCandidate_does_not_duplicate(
        self, manager, sampleCandidateData
    ):
        """Linking the same session twice should not create duplicates."""
        manager.saveCandidate(sampleCandidateData)
        candidateId = sampleCandidateData["candidate_id"]
        sessionId = str(uuid.uuid4())

        manager.linkSessionToCandidate(candidateId, sessionId)
        manager.linkSessionToCandidate(candidateId, sessionId)  # Second call

        sessions = manager.listCandidateSessions(candidateId)
        assert sessions.count(sessionId) == 1

    def test_linkSessionToCandidate_noop_if_candidate_not_on_disk(self, manager):
        """If candidate doesn't exist yet, linkage is a silent no-op."""
        # Should not raise
        manager.linkSessionToCandidate("ghost-candidate", str(uuid.uuid4()))

    def test_listCandidateSessions_returns_empty_for_unknown_candidate(self, manager):
        result = manager.listCandidateSessions("unknown-candidate")
        assert result == []

    def test_listCandidateSessions_returns_list(self, manager, sampleCandidateData):
        manager.saveCandidate(sampleCandidateData)
        result = manager.listCandidateSessions(sampleCandidateData["candidate_id"])
        assert isinstance(result, list)


# ════════════════════════════════════════════════════════════════════════════════
# Report Persistence
# ════════════════════════════════════════════════════════════════════════════════

class TestReportPersistence:

    def test_saveReport_creates_file(self, manager, sampleSession):
        reportData = {
            "session_id": sampleSession["session_id"],
            "candidate_id": sampleSession["candidate_id"],
            "overall_score": 7.5,
            "demo_mode": True,
        }
        manager.saveReport(reportData)
        filePath = Path(manager._reportDir) / f"{sampleSession['session_id']}.json"
        assert filePath.exists()

    def test_loadReport_returns_none_for_missing_report(self, manager):
        assert manager.loadReport("no-report-here") is None

    def test_loadReport_returns_dict_after_save(self, manager, sampleSession):
        reportData = {"session_id": sampleSession["session_id"], "overall_score": 8.0}
        manager.saveReport(reportData)
        loaded = manager.loadReport(sampleSession["session_id"])
        assert isinstance(loaded, dict)
        assert loaded["overall_score"] == 8.0


# ════════════════════════════════════════════════════════════════════════════════
# Async Operations
# ════════════════════════════════════════════════════════════════════════════════

class TestAsyncOperations:

    async def test_saveSessionAsync_creates_file(self, manager, sampleSession):
        await manager.saveSessionAsync(sampleSession)
        sessionId = sampleSession["session_id"]
        filePath = Path(manager._sessionDir) / f"{sessionId}.json"
        assert filePath.exists()

    async def test_loadSessionAsync_returns_dict(self, manager, sampleSession):
        await manager.saveSessionAsync(sampleSession)
        sessionId = sampleSession["session_id"]
        manager.removeFromMemory(sessionId)
        loaded = await manager.loadSessionAsync(sessionId)
        assert isinstance(loaded, dict)
        assert loaded["session_id"] == sessionId

    async def test_loadSessionAsync_returns_none_for_missing_file(self, manager):
        result = await manager.loadSessionAsync("ghost-session")
        assert result is None

    async def test_saveCandidateAsync_creates_file(self, manager, sampleCandidateData):
        await manager.saveCandidateAsync(sampleCandidateData)
        candidateId = sampleCandidateData["candidate_id"]
        filePath = Path(manager._candidateDir) / f"{candidateId}.json"
        assert filePath.exists()

    async def test_loadCandidateAsync_returns_dict(self, manager, sampleCandidateData):
        await manager.saveCandidateAsync(sampleCandidateData)
        loaded = await manager.loadCandidateAsync(sampleCandidateData["candidate_id"])
        assert isinstance(loaded, dict)
        assert loaded["full_name"] == "Jane Doe"

    async def test_async_session_strips_ephemeral_fields(self, manager, sampleSession):
        sampleSession["_cv_bytes"] = b"should not be saved"
        await manager.saveSessionAsync(sampleSession)
        sessionId = sampleSession["session_id"]
        filePath = Path(manager._sessionDir) / f"{sessionId}.json"
        data = json.loads(filePath.read_text())
        assert "_cv_bytes" not in data
