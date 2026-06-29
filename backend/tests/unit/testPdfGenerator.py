# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testPdfGenerator.py
# ─────────────────────────────────────────────────────────────────────────────

import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch

from src.schemas.reportSchema import InterviewReport, DimensionScore, ProgressComparison
from src.modules.reporting.pdfGenerator import generatePdf, generateComparisonPdf

def makeMockReport() -> InterviewReport:
    return InterviewReport(
        session_id="session-456",
        candidate_id="cand-789",
        interview_mode="technical",
        interview_length="short",
        overall_score=8.5,
        dimension_scores={
            "communication_clarity": DimensionScore(
                score=9.0, 
                evidence=["Spoke clearly", "Good pacing"], 
                rationale="Candidate demonstrated strong verbal skills."
            ),
            "problem_solving": DimensionScore(
                score=8.0, 
                evidence=["Used STAR method"], 
                rationale="Solid structural approach to algorithms."
            )
        },
        executive_summary="An excellent technical candidate.",
        top_strengths=["Clear communication", "System design"],
        areas_for_improvement=["Needs more cloud experience"],
        recommended_next_steps="Review AWS architecture patterns."
    )

def makeMockComparison() -> ProgressComparison:
    return ProgressComparison(
        overall_score_delta=1.5,
        dimension_deltas={
            "communication_clarity": 1.0,
            "problem_solving": 2.0,
            "technical_relevance": -0.5
        },
        strengths_improved=["Communication structure became much better."],
        weaknesses_improved=["Addressed prior weakness: No eye contact."],
        regressions_detected=["Technical depth dropped slightly on cloud questions."],
        comparison_narrative="Overall, a massive improvement from the first session."
    )


class TestPdfGenerator:
    def test_generate_pdf_creates_file(self):
        report = makeMockReport()
        
        # Mock weasyprint module
        mock_weasyprint = MagicMock()
        mock_html_instance = MagicMock()
        
        def write_mock_pdf(out_path):
            with open(out_path, "wb") as f:
                f.write(b"%PDF-mock-data-1000-bytes" + b"0" * 1000)
                
        mock_html_instance.write_pdf.side_effect = write_mock_pdf
        mock_weasyprint.HTML.return_value = mock_html_instance
        
        with tempfile.TemporaryDirectory() as tmpdir:
            outPath = os.path.join(tmpdir, "test_report.pdf")
            
            with patch.dict("sys.modules", {"weasyprint": mock_weasyprint}):
                # Execute
                resultPath = generatePdf(report, outPath)
                
                # Verify file exists and is not empty
                assert os.path.exists(resultPath)
                assert os.path.getsize(resultPath) > 1000  # Should be a decent size PDF
                
                # Verify PDF magic number/header
                with open(resultPath, "rb") as f:
                    header = f.read(4)
                    assert header == b"%PDF"

    def test_generate_comparison_pdf_creates_file(self):
        comparison = makeMockComparison()
        
        # Mock weasyprint module
        mock_weasyprint = MagicMock()
        mock_html_instance = MagicMock()
        
        def write_mock_pdf(out_path):
            with open(out_path, "wb") as f:
                f.write(b"%PDF-mock-data-1000-bytes" + b"0" * 1000)
                
        mock_html_instance.write_pdf.side_effect = write_mock_pdf
        mock_weasyprint.HTML.return_value = mock_html_instance
        
        with tempfile.TemporaryDirectory() as tmpdir:
            outPath = os.path.join(tmpdir, "test_comparison.pdf")
            
            with patch.dict("sys.modules", {"weasyprint": mock_weasyprint}):
                # Execute
                resultPath = generateComparisonPdf(comparison, outPath)
                
                # Verify file exists and is not empty
                assert os.path.exists(resultPath)
                assert os.path.getsize(resultPath) > 1000
                
                # Verify PDF magic number/header
                with open(resultPath, "rb") as f:
                    header = f.read(4)
                    assert header == b"%PDF"
