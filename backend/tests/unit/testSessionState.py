# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testSessionState.py
#
# Unit tests for backend/src/graph/sessionState.py
#
# Tests verify:
#   1. InterviewSession TypedDict has all required keys from the manifest
#   2. The conftest minimal_session fixture passes structural validation
#   3. Key type constraints are correct
#   4. Status and phase literals match the manifest values
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from typing import get_type_hints


class TestInterviewSessionStructure:
    """Verify that the InterviewSession TypedDict contains all manifest-required keys."""

    REQUIRED_IDENTITY_KEYS = {
        "session_id", "candidate_id", "created_at", "app_mode"
    }

    REQUIRED_CONFIG_KEYS = {
        "interview_length", "interview_mode"
    }

    REQUIRED_MODULE1_KEYS = {
        "candidate", "company_context", "question_plan", "role_category"
    }

    REQUIRED_MODULE2_KEYS = {
        "current_phase", "current_question_index", "asked_questions",
        "answers", "coaching_feedback", "difficulty_level", "difficulty_dimensions"
    }

    REQUIRED_MODULE3_KEYS = {
        "audio_metrics_per_answer", "facial_metrics_summary", "transcript"
    }

    REQUIRED_MODULE4_KEYS = {
        "final_report", "pdf_path"
    }

    REQUIRED_SYSTEM_KEYS = {
        "status", "error", "step_log"
    }

    def _get_all_keys(self) -> set:
        from src.graph.sessionState import InterviewSession
        hints = get_type_hints(InterviewSession)
        return set(hints.keys())

    def test_identity_keys_present(self):
        keys = self._get_all_keys()
        assert self.REQUIRED_IDENTITY_KEYS.issubset(keys), (
            f"Missing identity keys: {self.REQUIRED_IDENTITY_KEYS - keys}"
        )

    def test_config_keys_present(self):
        keys = self._get_all_keys()
        assert self.REQUIRED_CONFIG_KEYS.issubset(keys), (
            f"Missing config keys: {self.REQUIRED_CONFIG_KEYS - keys}"
        )

    def test_module1_keys_present(self):
        keys = self._get_all_keys()
        assert self.REQUIRED_MODULE1_KEYS.issubset(keys), (
            f"Missing Module 1 keys: {self.REQUIRED_MODULE1_KEYS - keys}"
        )

    def test_module2_keys_present(self):
        keys = self._get_all_keys()
        assert self.REQUIRED_MODULE2_KEYS.issubset(keys), (
            f"Missing Module 2 keys: {self.REQUIRED_MODULE2_KEYS - keys}"
        )

    def test_module3_keys_present(self):
        keys = self._get_all_keys()
        assert self.REQUIRED_MODULE3_KEYS.issubset(keys), (
            f"Missing Module 3 keys: {self.REQUIRED_MODULE3_KEYS - keys}"
        )

    def test_module4_keys_present(self):
        keys = self._get_all_keys()
        assert self.REQUIRED_MODULE4_KEYS.issubset(keys), (
            f"Missing Module 4 keys: {self.REQUIRED_MODULE4_KEYS - keys}"
        )

    def test_system_keys_present(self):
        keys = self._get_all_keys()
        assert self.REQUIRED_SYSTEM_KEYS.issubset(keys), (
            f"Missing system keys: {self.REQUIRED_SYSTEM_KEYS - keys}"
        )

    def test_total_key_count(self):
        """Ensures no keys were silently dropped. Update this if manifest adds fields."""
        keys = self._get_all_keys()
        expectedMinimum = (
            len(self.REQUIRED_IDENTITY_KEYS) +
            len(self.REQUIRED_CONFIG_KEYS) +
            len(self.REQUIRED_MODULE1_KEYS) +
            len(self.REQUIRED_MODULE2_KEYS) +
            len(self.REQUIRED_MODULE3_KEYS) +
            len(self.REQUIRED_MODULE4_KEYS) +
            len(self.REQUIRED_SYSTEM_KEYS)
        )
        assert len(keys) >= expectedMinimum


class TestMinimalSessionFixture:
    """Verify the conftest minimal_session fixture matches the TypedDict contract."""

    def test_all_typed_dict_keys_in_fixture(self, minimal_session):
        """Every key defined in InterviewSession must exist in the fixture."""
        from src.graph.sessionState import InterviewSession
        requiredKeys = set(get_type_hints(InterviewSession).keys())
        fixtureKeys = set(minimal_session.keys())
        missing = requiredKeys - fixtureKeys
        assert not missing, f"Fixture is missing these InterviewSession keys: {missing}"

    def test_app_mode_is_demo(self, minimal_session):
        assert minimal_session["app_mode"] == "demo"

    def test_status_is_valid(self, minimal_session):
        validStatuses = {"setting_up", "ready", "in_progress", "completed", "error"}
        assert minimal_session["status"] in validStatuses

    def test_current_phase_is_valid(self, minimal_session):
        validPhases = {"icebreaker", "cv_deep_dive", "dynamic_followup", "closing"}
        assert minimal_session["current_phase"] in validPhases

    def test_interview_length_is_valid(self, minimal_session):
        validLengths = {"short", "medium", "long"}
        assert minimal_session["interview_length"] in validLengths

    def test_interview_mode_is_valid(self, minimal_session):
        validModes = {"mixed", "technical", "behavioral", "hr_culture_fit", "system_design"}
        assert minimal_session["interview_mode"] in validModes

    def test_difficulty_dimensions_has_all_keys(self, minimal_session):
        """difficulty_dimensions must track all 5 scoring dimensions."""
        dims = minimal_session["difficulty_dimensions"]
        requiredDims = {"relevance", "clarity", "depth", "confidence", "structure"}
        assert requiredDims.issubset(set(dims.keys()))

    def test_difficulty_level_in_range(self, minimal_session):
        level = minimal_session["difficulty_level"]
        assert 1 <= level <= 5

    def test_lists_are_lists(self, minimal_session):
        listFields = [
            "question_plan", "asked_questions", "answers",
            "coaching_feedback", "audio_metrics_per_answer",
            "transcript", "step_log",
        ]
        for field in listFields:
            assert isinstance(minimal_session[field], list), (
                f"Field '{field}' must be a list, got {type(minimal_session[field])}"
            )

    def test_optional_fields_are_none_initially(self, minimal_session):
        assert minimal_session["final_report"] is None
        assert minimal_session["pdf_path"] is None
        assert minimal_session["error"] is None

    def test_candidate_has_confirmed_skills(self, minimal_session):
        candidate = minimal_session["candidate"]
        assert "confirmed_skills" in candidate
        assert isinstance(candidate["confirmed_skills"], list)

    def test_candidate_has_uncertain_skills(self, minimal_session):
        """uncertain_skills must exist even if empty — they're stored for logging."""
        candidate = minimal_session["candidate"]
        assert "uncertain_skills" in candidate
        assert isinstance(candidate["uncertain_skills"], list)
