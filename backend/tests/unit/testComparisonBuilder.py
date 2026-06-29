# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testComparisonBuilder.py
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch

from src.schemas.reportSchema import InterviewReport, DimensionScore
from src.modules.reporting.comparisonBuilder import buildComparison

def makeMockReport(overall: float, comms: float, tech: float) -> InterviewReport:
    return InterviewReport(
        session_id="session_id",
        candidate_id="cand_id",
        interview_mode="mixed",
        interview_length="medium",
        overall_score=overall,
        dimension_scores={
            "communication_clarity": DimensionScore(score=comms, rationale=""),
            "technical_relevance": DimensionScore(score=tech, rationale="")
        },
        executive_summary="Summary",
        top_strengths=["Strength A"],
        areas_for_improvement=["Needs work on X"],
        recommended_next_steps="Practice more."
    )

class TestComparisonBuilder:
    @patch("src.modules.reporting.comparisonBuilder.callLlm")
    def test_build_comparison_flags_regressions_and_improvements(self, mockCallLlm):
        mockCallLlm.return_value = {"comparison_narrative": "Good progress."}
        
        # Previous: Overall 5.0, Comms 6.0, Tech 8.0
        prev = makeMockReport(5.0, 6.0, 8.0)
        
        # Current: Overall 7.0, Comms 8.0 (improved by 2), Tech 6.5 (dropped by 1.5)
        curr = makeMockReport(7.0, 8.0, 6.5)
        
        comp = buildComparison(prev, curr)
        
        assert comp.overall_score_delta == 2.0
        assert comp.dimension_deltas["communication_clarity"] == 2.0
        assert comp.dimension_deltas["technical_relevance"] == -1.5
        
        # Check improvements list
        assert any("communication_clarity" in s and "improved" in s for s in comp.strengths_improved)
        
        # Check regressions list
        assert any("technical_relevance" in s and "dropped" in s for s in comp.regressions_detected)
        
        assert comp.comparison_narrative == "Good progress."
