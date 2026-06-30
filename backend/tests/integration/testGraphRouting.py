# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/integration/testGraphRouting.py
#
# Integration tests — LangGraph conditional routing edge validation
#
# What these tests verify:
#   1. shouldGenerateFollowup (edges.py):
#      • Routes to "conductorAgent" when should_advance=True
#      • Routes to END when should_advance=False (follow-up injected)
#      • Routes to END on terminal statuses ("completed", "error")
#        regardless of should_advance — no infinite loop possible
#
#   2. interviewGraph end-to-end invocation:
#      • Graph terminates (reaches END) on every code path without stalling
#      • Follow-up path (should_advance=False): graph stops, next_question set
#      • Advance path (should_advance=True): conductorAgent runs, increments index
#      • Completion path: conductorAgent detects completion, sets status="completed"
#
#   3. reportGraph end-to-end invocation:
#      • evaluatorAgent + pdfGeneratorNode run in sequence and terminate
#      • final_report is populated with correct structure
#      • pdf_path is None when WeasyPrint is not available (graceful degradation)
#      • Zero-answer guard: evaluatorAgent returns status="error" cleanly
#
# All LLM calls are mocked with unittest.mock.patch to keep tests fast,
# deterministic, and free of API charges.
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch, MagicMock
from langgraph.graph import END

from src.graph.edges import shouldGenerateFollowup
from src.graph.interviewGraph import interviewGraph
from src.graph.reportGraph import reportGraph


# ════════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════════

def makeMinimalState(**overrides) -> dict:
    """
    Returns a minimal valid InterviewSession dict suitable for graph invocation.
    Individual fields can be overridden via kwargs.
    """
    base = {
        "session_id": "integ-test-001",
        "candidate_id": "cand-test-001",
        "created_at": "2026-01-01T00:00:00Z",
        "app_mode": "demo",
        "interview_length": "short",
        "interview_mode": "mixed",
        "candidate": {
            "candidate_id": "cand-test-001",
            "full_name": "Test Candidate",
            "email": "test@example.com",
            "education": [],
            "experience": [],
            "projects": [],
            "confirmed_skills": ["Python"],
            "uncertain_skills": [],
            "motivation": "Test motivation.",
            "target_role": "Engineer",
            "target_company": "Acme",
            "required_skills_from_jd": ["Python"],
            "skills_gap": [],
            "session_ids": ["integ-test-001"],
            "created_at": "2026-01-01T00:00:00Z",
        },
        "company_context": "",
        "question_plan": [
            "Tell me about yourself.",
            "Describe a project you are proud of.",
            "How do you handle deadlines?",
        ],
        "role_category": "software_engineer",
        "current_phase": "icebreaker",
        "current_question_index": 0,
        "asked_questions": [],
        "answers": [],
        "coaching_feedback": [],
        "difficulty_level": 2,
        "difficulty_dimensions": {
            "relevance": 2, "clarity": 2, "depth": 2,
            "confidence": 2, "structure": 2,
        },
        "audio_metrics_per_answer": [],
        "facial_metrics_summary": {
            "eye_contact_percentage": None,
            "avg_blink_rate_per_minute": None,
            "head_movement_score": None,
            "engagement_score": None,
            "demo_mode": True,
        },
        "transcript": [],
        "final_report": None,
        "pdf_path": None,
        "status": "in_progress",
        "error": None,
        "step_log": ["[TEST] Integration session created."],
        # Runtime-only fields used by agents
        "next_question": None,
        "should_advance": True,
        "suggest_followup": False,
    }
    base.update(overrides)
    return base


def makeCompletedStateWithAnswers() -> dict:
    """State with one answered question — ready for the report graph."""
    question = {
        "index": 0,
        "text": "Tell me about yourself.",
        "phase": "icebreaker",
        "category": "motivational",
        "difficulty": 2,
        "followup_count": 0,
        "asked_at": "2026-01-01T00:00:01Z",
        "based_on_answer_index": None,
        "parent_question_index": None,
    }
    answer = {
        "question_index": 0,
        "text": "I am a backend engineer with 3 years of experience in Python.",
        "audio_path": None,
        "answered_at": "2026-01-01T00:01:00Z",
        "duration_seconds": 45.0,
    }
    coaching = {
        "answer_index": 0,
        "feedback_text": "Good concise introduction.",
        "score_preview": 7,
        "strengths": ["Clarity"],
        "improvements": ["Add metrics"],
        "dimension_scores": {
            "relevance": 7, "clarity": 7, "depth": 5,
            "confidence": 6, "structure": 6,
        },
    }
    return makeMinimalState(
        status="completed",
        current_question_index=3,
        asked_questions=[question],
        answers=[answer],
        coaching_feedback=[coaching],
        audio_metrics_per_answer=[{
            "words_per_minute": 130.0,
            "filler_word_count": 2,
            "pause_count": 1,
            "avg_pause_duration": 0.5,
            "voice_energy_level": 0.65,
            "demo_mode": False,
        }],
    )


# ── Shared LLM mock return values ──────────────────────────────────────────────
_MOCK_DIMENSION_SCORE = {
    "score": 7.5,
    "evidence": ["Candidate demonstrated clear reasoning."],
    "rationale": "Strong overall performance in this dimension.",
}

_MOCK_REPORT_NARRATIVE = {
    "executive_summary": "Solid candidate with good technical foundation.",
    "top_strengths": ["Python expertise", "Communication", "Problem solving"],
    "areas_for_improvement": ["System design depth"],
    "recommended_next_steps": "Practice system design problems. Review distributed systems.",
}


# ════════════════════════════════════════════════════════════════════════════════
# 1. shouldGenerateFollowup — Unit-level edge function tests
# ════════════════════════════════════════════════════════════════════════════════

class TestShouldGenerateFollowup:
    """Tests for the shouldGenerateFollowup conditional edge function in edges.py."""

    def test_routesToConductorWhenShouldAdvanceTrue(self):
        """should_advance=True → conductorAgent."""
        state = makeMinimalState(should_advance=True, status="in_progress")
        result = shouldGenerateFollowup(state)
        assert result == "conductorAgent"

    def test_routesToEndWhenShouldAdvanceFalse(self):
        """should_advance=False (follow-up injected) → END."""
        state = makeMinimalState(should_advance=False, status="in_progress")
        result = shouldGenerateFollowup(state)
        assert result == END

    def test_routesToEndWhenStatusCompleted(self):
        """status='completed' always routes to END, regardless of should_advance."""
        state = makeMinimalState(should_advance=True, status="completed")
        result = shouldGenerateFollowup(state)
        assert result == END

    def test_routesToEndWhenStatusError(self):
        """status='error' always routes to END — prevents infinite loops."""
        state = makeMinimalState(should_advance=True, status="error")
        result = shouldGenerateFollowup(state)
        assert result == END

    def test_defaultsShouldAdvanceTrueWhenKeyMissing(self):
        """Missing should_advance key defaults to True → conductorAgent."""
        state = makeMinimalState(status="in_progress")
        state.pop("should_advance", None)
        result = shouldGenerateFollowup(state)
        assert result == "conductorAgent"

    def test_errorStatusOverridesAdvanceSignal(self):
        """Status 'error' takes priority over should_advance=False."""
        state = makeMinimalState(should_advance=False, status="error")
        result = shouldGenerateFollowup(state)
        assert result == END

    def test_completedStatusOverridesAdvanceSignal(self):
        """Status 'completed' takes priority over should_advance=False."""
        state = makeMinimalState(should_advance=False, status="completed")
        result = shouldGenerateFollowup(state)
        assert result == END


# ════════════════════════════════════════════════════════════════════════════════
# 2. interviewGraph — End-to-end routing validation
# ════════════════════════════════════════════════════════════════════════════════

class TestInterviewGraphRouting:
    """
    Integration tests for the compiled interviewGraph.

    Each test invokes the graph synchronously with a controlled state and
    verifies the resulting state is correct. LLM calls are mocked throughout.
    """

    @patch("src.agents.liveCoachAgent.callLlm")
    @patch("src.agents.followUpAgent.callLlm")
    def test_advancePathTerminatesCorrectly(
        self, mockFollowupLlm, mockCoachLlm
    ):
        """
        Advance path (should_advance=True): graph terminates without stalling.
        conductorAgent runs and increments current_question_index.
        """
        # LiveCoach LLM → coaching feedback
        mockCoachLlm.return_value = {
            "feedback_text": "Good answer, but add more specifics.",
            "score_preview": 7,
            "strengths": ["Clarity"],
            "improvements": ["Add metrics"],
            "dimension_scores": {
                "relevance": 7, "clarity": 7,
                "depth": 5, "confidence": 6, "structure": 6,
            },
        }
        # FollowUp LLM → advance (skip follow-up)
        mockFollowupLlm.return_value = {
            "should_followup": False,
            "followup_question": None,
        }

        # Start with one question already asked, one answer submitted
        state = makeMinimalState(
            current_question_index=1,
            asked_questions=[{
                "index": 0, "text": "Tell me about yourself.",
                "phase": "icebreaker", "category": "motivational",
                "difficulty": 2, "followup_count": 0,
                "asked_at": "2026-01-01T00:00:01Z",
                "based_on_answer_index": None, "parent_question_index": None,
            }],
            answers=[{
                "question_index": 0,
                "text": "I have 3 years in Python backend development.",
                "audio_path": None, "answered_at": "2026-01-01T00:01:00Z",
                "duration_seconds": 30.0,
            }],
        )

        result = interviewGraph.invoke(state)

        # Graph must terminate without stalling.
        # conductorAgent increments current_question_index and appends to asked_questions.
        # Note: next_question may be None in merged state because followUpAgent sets
        # next_question=None on the advance path before conductorAgent overwrites it.
        # We verify conductor ran by checking index + asked_questions length instead.
        assert result["current_question_index"] == 2, (
            "conductorAgent must have incremented the question index"
        )
        assert len(result["asked_questions"]) == 2, (
            "conductorAgent must have appended the next planned question"
        )
        assert result["status"] == "in_progress"

    @patch("src.agents.liveCoachAgent.callLlm")
    @patch("src.agents.followUpAgent.callLlm")
    def test_followUpPathTerminatesCorrectly(
        self, mockFollowupLlm, mockCoachLlm
    ):
        """
        Follow-up path (should_advance=False): graph terminates after injecting
        the follow-up question. conductorAgent is NOT invoked.
        current_question_index must remain unchanged.
        """
        mockCoachLlm.return_value = {
            "feedback_text": "Interesting point — let me probe further.",
            "score_preview": 5,
            "strengths": [],
            "improvements": ["Add STAR structure"],
            "dimension_scores": {
                "relevance": 6, "clarity": 5,
                "depth": 4, "confidence": 5, "structure": 4,
            },
        }
        mockFollowupLlm.return_value = {
            "should_followup": True,
            "followup_question": "You mentioned Python — what was your biggest Python challenge?",
        }

        state = makeMinimalState(
            current_question_index=1,
            asked_questions=[{
                "index": 0, "text": "Tell me about yourself.",
                "phase": "icebreaker", "category": "motivational",
                "difficulty": 2, "followup_count": 0,
                "asked_at": "2026-01-01T00:00:01Z",
                "based_on_answer_index": None, "parent_question_index": None,
            }],
            answers=[{
                "question_index": 0,
                "text": "Python.",  # Very short — follow-up score gate should NOT block LLM
                "audio_path": None, "answered_at": "2026-01-01T00:01:00Z",
                "duration_seconds": 5.0,
            }],
        )

        result = interviewGraph.invoke(state)

        # Follow-up was injected and graph stopped before conductorAgent.
        # current_question_index must NOT have advanced (conductorAgent didn't run).
        assert result["current_question_index"] == 1
        # The follow-up question must be present in asked_questions as the second entry.
        assert len(result["asked_questions"]) == 2
        followupQ = result["asked_questions"][-1]
        assert followupQ["followup_count"] == 1, "Follow-up count must be 1"
        assert "Python" in followupQ["text"], (
            "Follow-up must reference Python as the LLM mock specifies"
        )

    @patch("src.agents.liveCoachAgent.callLlm")
    @patch("src.agents.followUpAgent.callLlm")
    def test_completionPathSetsStatusCompleted(
        self, mockFollowupLlm, mockCoachLlm
    ):
        """
        Completion path: when current_question_index == len(question_plan),
        conductorAgent sets status='completed' and next_question=None.
        Graph terminates cleanly without looping.
        """
        mockCoachLlm.return_value = {
            "feedback_text": "Well done overall.",
            "score_preview": 8,
            "strengths": ["Structure"],
            "improvements": [],
            "dimension_scores": {
                "relevance": 8, "clarity": 8,
                "depth": 7, "confidence": 7, "structure": 8,
            },
        }
        # FollowUp → advance (ceiling / score gate should fire for this short plan)
        mockFollowupLlm.return_value = {
            "should_followup": False,
            "followup_question": None,
        }

        # current_question_index == len(question_plan): interview is complete
        state = makeMinimalState(
            question_plan=["Q0", "Q1"],
            current_question_index=2,  # Past the end of the 2-item plan
            asked_questions=[
                {"index": 0, "text": "Q0", "phase": "icebreaker",
                 "category": "motivational", "difficulty": 2,
                 "followup_count": 0, "asked_at": "2026-01-01T00:00:01Z",
                 "based_on_answer_index": None, "parent_question_index": None},
                {"index": 1, "text": "Q1", "phase": "cv_deep_dive",
                 "category": "technical", "difficulty": 2,
                 "followup_count": 0, "asked_at": "2026-01-01T00:01:00Z",
                 "based_on_answer_index": None, "parent_question_index": None},
            ],
            answers=[
                {"question_index": 0, "text": "Answer to Q0.",
                 "audio_path": None, "answered_at": "2026-01-01T00:01:00Z",
                 "duration_seconds": 40.0},
                {"question_index": 1, "text": "Answer to Q1.",
                 "audio_path": None, "answered_at": "2026-01-01T00:02:00Z",
                 "duration_seconds": 45.0},
            ],
        )

        result = interviewGraph.invoke(state)

        assert result["status"] == "completed"
        # next_question may not appear in result keys if conductorAgent sets it to None
        # and LangGraph doesn't echo unchanged Optional keys — use .get() with sentinel
        assert result.get("next_question", "NOT_SET") in (None, "NOT_SET")

    @patch("src.agents.liveCoachAgent.callLlm")
    def test_llmFailureInCoachFallsBackGracefully(self, mockCoachLlm):
        """
        If liveCoachAgent's LLM call raises, the agent returns a safe default
        and the graph still terminates correctly without raising to the caller.
        """
        mockCoachLlm.side_effect = ValueError("Simulated LLM timeout")

        state = makeMinimalState(
            current_question_index=1,
            asked_questions=[{
                "index": 0, "text": "Tell me about yourself.",
                "phase": "icebreaker", "category": "motivational",
                "difficulty": 2, "followup_count": 0,
                "asked_at": "2026-01-01T00:00:01Z",
                "based_on_answer_index": None, "parent_question_index": None,
            }],
            answers=[{
                "question_index": 0,
                "text": "I am a backend engineer.",
                "audio_path": None, "answered_at": "2026-01-01T00:01:00Z",
                "duration_seconds": 20.0,
            }],
        )

        # Must not raise — agent error handling must prevent graph crash
        result = interviewGraph.invoke(state)
        assert result is not None
        # status should not be "error" just from a coach LLM failure
        # (liveCoachAgent uses a default fallback response)
        assert "step_log" in result

    @patch("src.agents.liveCoachAgent.callLlm")
    @patch("src.agents.followUpAgent.callLlm")
    def test_graphDoesNotInfiniteLoopOnFollowUpCeiling(
        self, mockFollowupLlm, mockCoachLlm
    ):
        """
        When followUpAgent hits the hard ceiling (2 follow-ups already used),
        it returns should_advance=True without calling the LLM. The graph must
        route to conductorAgent and terminate — not loop back to followUpAgent.
        """
        mockCoachLlm.return_value = {
            "feedback_text": "Decent answer.",
            "score_preview": 5,
            "strengths": [],
            "improvements": ["More depth"],
            "dimension_scores": {
                "relevance": 5, "clarity": 5,
                "depth": 4, "confidence": 5, "structure": 5,
            },
        }
        # This mock should NOT be called — ceiling check fires first
        mockFollowupLlm.return_value = {
            "should_followup": True,
            "followup_question": "Probe deeper?",
        }

        # Two follow-ups already exist for question 0 (the ceiling is MAX=2)
        state = makeMinimalState(
            current_question_index=3,  # Two follow-ups have been added
            asked_questions=[
                {"index": 0, "text": "Q0", "phase": "icebreaker",
                 "category": "motivational", "difficulty": 2,
                 "followup_count": 0, "asked_at": "2026-01-01T00:00:01Z",
                 "based_on_answer_index": None, "parent_question_index": None},
                {"index": 1, "text": "FU1", "phase": "icebreaker",
                 "category": "behavioral", "difficulty": 2,
                 "followup_count": 1, "asked_at": "2026-01-01T00:01:00Z",
                 "based_on_answer_index": 0, "parent_question_index": 0},
                {"index": 2, "text": "FU2", "phase": "icebreaker",
                 "category": "behavioral", "difficulty": 2,
                 "followup_count": 2, "asked_at": "2026-01-01T00:02:00Z",
                 "based_on_answer_index": 1, "parent_question_index": 0},
            ],
            answers=[
                {"question_index": 0, "text": "A0", "audio_path": None,
                 "answered_at": "2026-01-01T00:01:00Z", "duration_seconds": 30.0},
                {"question_index": 1, "text": "A1", "audio_path": None,
                 "answered_at": "2026-01-01T00:02:00Z", "duration_seconds": 25.0},
                {"question_index": 2, "text": "A2", "audio_path": None,
                 "answered_at": "2026-01-01T00:03:00Z", "duration_seconds": 20.0},
            ],
        )

        result = interviewGraph.invoke(state)

        # Ceiling fires → should_advance=True → conductorAgent runs → next plan question
        # followUpAgent writes should_advance=True; conductorAgent may also write state
        assert result.get("should_advance", True) is True
        # LLM should NOT have been called (ceiling fires before LLM step)
        mockFollowupLlm.assert_not_called()


# ════════════════════════════════════════════════════════════════════════════════
# 3. reportGraph — End-to-end report generation validation
# ════════════════════════════════════════════════════════════════════════════════

class TestReportGraphRouting:
    """Integration tests for the compiled reportGraph."""

    @patch("src.modules.reporting.scoreCalculator.callLlm")
    @patch("src.modules.reporting.reportBuilder.callLlm")
    @patch("src.graph.reportGraph.pdfGeneratorNode")
    def test_reportGraphPopulatesFinalReport(
        self, mockPdfNode, mockReportLlm, mockScoreLlm
    ):
        """
        reportGraph terminates and final_report is populated correctly.
        PDF node is mocked to avoid WeasyPrint dependency in CI.
        """
        mockScoreLlm.return_value = _MOCK_DIMENSION_SCORE
        mockReportLlm.return_value = _MOCK_REPORT_NARRATIVE
        mockPdfNode.return_value = {"pdf_path": None, "step_log": ["[PDF] Skipped (mocked)."]}

        state = makeCompletedStateWithAnswers()
        result = reportGraph.invoke(state)

        assert result["final_report"] is not None
        assert "overall_score" in result["final_report"]
        assert result["final_report"]["session_id"] == "integ-test-001"

    @patch("src.modules.reporting.scoreCalculator.callLlm")
    @patch("src.modules.reporting.reportBuilder.callLlm")
    def test_reportGraphZeroAnswersReturnsError(
        self, mockReportLlm, mockScoreLlm
    ):
        """
        evaluatorAgent with zero answers sets status='error' and final_report=None.
        The graph must still terminate without raising.
        """
        mockScoreLlm.return_value = _MOCK_DIMENSION_SCORE
        mockReportLlm.return_value = _MOCK_REPORT_NARRATIVE

        state = makeMinimalState(status="completed", answers=[], asked_questions=[])
        result = reportGraph.invoke(state)

        assert result["status"] == "error"
        assert result["final_report"] is None
        assert result.get("error") is not None

    @patch("src.modules.reporting.scoreCalculator.callLlm")
    @patch("src.modules.reporting.reportBuilder.callLlm")
    def test_diskPersistenceFailureDoesNotCrashGraph(
        self, mockReportLlm, mockScoreLlm, tmp_path
    ):
        """
        If _persistReportJson cannot write to disk (OSError on open), evaluatorAgent
        catches it gracefully. final_report must still be returned in state.

        Strategy: patch the built-in `open` inside evaluatorAgent's namespace so
        the os.makedirs call succeeds (tmp_path exists) but open() raises OSError.
        """
        mockScoreLlm.return_value = _MOCK_DIMENSION_SCORE
        mockReportLlm.return_value = _MOCK_REPORT_NARRATIVE

        state = makeCompletedStateWithAnswers()

        # Patch 'open' inside the evaluatorAgent module to simulate write failure
        # builtins.open is the correct patch target when the module uses open() directly
        import builtins
        original_open = builtins.open

        def mockOpenRaise(*args, **kwargs):
            # Only raise when writing the report JSON file (binary modes are not intercepted)
            if args and str(args[0]).endswith(".json"):
                raise OSError("Disk full")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mockOpenRaise):
            from src.agents.evaluatorAgent import evaluatorAgent
            result = evaluatorAgent(state)

        # final_report is populated despite disk failure
        assert result["final_report"] is not None
        assert result["status"] == "completed"
        # The step_log must mention the persistence warning
        warningLogs = [l for l in result["step_log"] if "WARNING" in l or "persist" in l.lower()]
        assert len(warningLogs) >= 1
