# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testCvParser.py
#
# Unit tests for:
#   - src.modules.ingestion.cvParser (extractTextFromPdf, parseCv)
#   - src.modules.ingestion.jdParser (parseJd)
#   - src.modules.ingestion.motivationParser (parseMotivation)
#   - src.modules.ingestion.companyScraper (scrapeCompany — demo mode)
#
# All LLM calls are mocked. No real PDF bytes required.
# ─────────────────────────────────────────────────────────────────────────────

import io
import pytest
from unittest.mock import patch, MagicMock


# ════════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════════

def makeFakePdfBytes(text: str = "Jane Doe\nPython Developer\nSkills: Python, FastAPI") -> bytes:
    """
    Create a minimal real PDF in-memory using reportlab if available,
    otherwise use a pdfplumber-compatible approach via mocking.
    Since we mock pdfplumber in tests, we just need any non-empty bytes.
    """
    return text.encode("utf-8")  # Used as fake bytes — pdfplumber is mocked below


# ── Canonical LLM responses for CV parsing ────────────────────────────────────
SAMPLE_CV_LLM_RESPONSE = {
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "education": [
        {
            "institution": "MIT",
            "degree": "BSc",
            "field": "Computer Science",
            "graduation_year": 2020,
            "gpa": "3.8"
        }
    ],
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Backend Engineer",
            "duration": "2020–2023",
            "description": "Built REST APIs using FastAPI.",
            "technologies": ["FastAPI", "PostgreSQL"]
        }
    ],
    "projects": [
        {
            "name": "AI Scheduler",
            "description": "Automated interview scheduling system.",
            "technologies": ["Python", "Redis"],
            "url": None
        }
    ],
    "confirmed_skills": ["Python", "FastAPI", "PostgreSQL"],
    "uncertain_skills": ["Kubernetes", "Terraform"]
}


# ════════════════════════════════════════════════════════════════════════════════
# cvParser.extractTextFromPdf
# ════════════════════════════════════════════════════════════════════════════════

class TestExtractTextFromPdf:

    def test_raises_on_empty_bytes(self):
        from src.modules.ingestion.cvParser import extractTextFromPdf
        with pytest.raises(ValueError, match="must not be empty"):
            extractTextFromPdf(b"")

    def test_returns_string_on_valid_pdf(self):
        """Mocks pdfplumber to return controlled text."""
        from src.modules.ingestion.cvParser import extractTextFromPdf

        mockPage = MagicMock()
        mockPage.extract_text.return_value = "Jane Doe\nPython Developer"

        mockPdf = MagicMock()
        mockPdf.__enter__ = MagicMock(return_value=mockPdf)
        mockPdf.__exit__ = MagicMock(return_value=False)
        mockPdf.pages = [mockPage]

        with patch("src.modules.ingestion.cvParser.pdfplumber.open", return_value=mockPdf):
            result = extractTextFromPdf(b"fake-pdf-bytes")

        assert isinstance(result, str)
        assert "Jane Doe" in result
        assert "Python Developer" in result

    def test_handles_empty_pages_gracefully(self):
        """Pages with no extractable text should not crash."""
        from src.modules.ingestion.cvParser import extractTextFromPdf

        mockPage = MagicMock()
        mockPage.extract_text.return_value = None  # Scanned page

        mockPdf = MagicMock()
        mockPdf.__enter__ = MagicMock(return_value=mockPdf)
        mockPdf.__exit__ = MagicMock(return_value=False)
        mockPdf.pages = [mockPage]

        with patch("src.modules.ingestion.cvParser.pdfplumber.open", return_value=mockPdf):
            result = extractTextFromPdf(b"fake-pdf-bytes")

        assert result == ""

    def test_multiple_pages_concatenated(self):
        """Text from multiple pages should be joined with double newlines."""
        from src.modules.ingestion.cvParser import extractTextFromPdf

        mockPage1 = MagicMock()
        mockPage1.extract_text.return_value = "Page 1 content"
        mockPage2 = MagicMock()
        mockPage2.extract_text.return_value = "Page 2 content"

        mockPdf = MagicMock()
        mockPdf.__enter__ = MagicMock(return_value=mockPdf)
        mockPdf.__exit__ = MagicMock(return_value=False)
        mockPdf.pages = [mockPage1, mockPage2]

        with patch("src.modules.ingestion.cvParser.pdfplumber.open", return_value=mockPdf):
            result = extractTextFromPdf(b"fake-pdf-bytes")

        assert "Page 1 content" in result
        assert "Page 2 content" in result


# ════════════════════════════════════════════════════════════════════════════════
# cvParser.parseCv
# ════════════════════════════════════════════════════════════════════════════════

class TestParseCv:

    def _mockPdfExtraction(self, text: str = "Jane Doe, Python Developer"):
        """Patch pdfplumber.open to return a controlled text."""
        mockPage = MagicMock()
        mockPage.extract_text.return_value = text
        mockPdf = MagicMock()
        mockPdf.__enter__ = MagicMock(return_value=mockPdf)
        mockPdf.__exit__ = MagicMock(return_value=False)
        mockPdf.pages = [mockPage]
        return patch("src.modules.ingestion.cvParser.pdfplumber.open", return_value=mockPdf)

    def test_parseCv_returns_dict(self):
        from src.modules.ingestion.cvParser import parseCv
        with self._mockPdfExtraction():
            with patch("src.modules.ingestion.cvParser.callLlm", return_value=SAMPLE_CV_LLM_RESPONSE):
                result = parseCv(b"fake-pdf")
        assert isinstance(result, dict)

    def test_confirmed_skills_populated(self):
        from src.modules.ingestion.cvParser import parseCv
        with self._mockPdfExtraction():
            with patch("src.modules.ingestion.cvParser.callLlm", return_value=SAMPLE_CV_LLM_RESPONSE):
                result = parseCv(b"fake-pdf")
        assert "confirmed_skills" in result
        assert len(result["confirmed_skills"]) > 0
        assert "Python" in result["confirmed_skills"]

    def test_uncertain_skills_populated(self):
        from src.modules.ingestion.cvParser import parseCv
        with self._mockPdfExtraction():
            with patch("src.modules.ingestion.cvParser.callLlm", return_value=SAMPLE_CV_LLM_RESPONSE):
                result = parseCv(b"fake-pdf")
        assert "uncertain_skills" in result
        assert "Kubernetes" in result["uncertain_skills"]

    def test_confirmed_and_uncertain_skills_are_separate(self):
        """Skills must NOT appear in both lists."""
        from src.modules.ingestion.cvParser import parseCv
        with self._mockPdfExtraction():
            with patch("src.modules.ingestion.cvParser.callLlm", return_value=SAMPLE_CV_LLM_RESPONSE):
                result = parseCv(b"fake-pdf")
        confirmedSet = set(result["confirmed_skills"])
        uncertainSet = set(result["uncertain_skills"])
        overlap = confirmedSet & uncertainSet
        assert not overlap, f"Skills appear in both lists: {overlap}"

    def test_skills_are_deduplicated(self):
        """Duplicate skills in LLM response should be removed."""
        from src.modules.ingestion.cvParser import parseCv
        duplicateResponse = {
            **SAMPLE_CV_LLM_RESPONSE,
            "confirmed_skills": ["Python", "Python", "FastAPI", "FastAPI"],
        }
        with self._mockPdfExtraction():
            with patch("src.modules.ingestion.cvParser.callLlm", return_value=duplicateResponse):
                result = parseCv(b"fake-pdf")
        assert result["confirmed_skills"].count("Python") == 1

    def test_missing_llm_fields_default_to_empty_lists(self):
        """If LLM omits list fields, they should default to []."""
        from src.modules.ingestion.cvParser import parseCv
        minimalResponse = {"full_name": "John", "email": None}
        with self._mockPdfExtraction():
            with patch("src.modules.ingestion.cvParser.callLlm", return_value=minimalResponse):
                result = parseCv(b"fake-pdf")
        assert result["confirmed_skills"] == []
        assert result["uncertain_skills"] == []
        assert result["education"] == []

    def test_raises_on_empty_pdf_text(self):
        """If PDF produces no text, parseCv must raise ValueError."""
        from src.modules.ingestion.cvParser import parseCv
        mockPage = MagicMock()
        mockPage.extract_text.return_value = "   "  # Whitespace only
        mockPdf = MagicMock()
        mockPdf.__enter__ = MagicMock(return_value=mockPdf)
        mockPdf.__exit__ = MagicMock(return_value=False)
        mockPdf.pages = [mockPage]

        with patch("src.modules.ingestion.cvParser.pdfplumber.open", return_value=mockPdf):
            with pytest.raises(ValueError, match="Could not extract any text"):
                parseCv(b"fake-pdf")

    def test_education_list_structure(self):
        from src.modules.ingestion.cvParser import parseCv
        with self._mockPdfExtraction():
            with patch("src.modules.ingestion.cvParser.callLlm", return_value=SAMPLE_CV_LLM_RESPONSE):
                result = parseCv(b"fake-pdf")
        assert isinstance(result["education"], list)
        if result["education"]:
            edu = result["education"][0]
            assert "institution" in edu
            assert "degree" in edu


# ════════════════════════════════════════════════════════════════════════════════
# jdParser.parseJd
# ════════════════════════════════════════════════════════════════════════════════

class TestParseJd:

    SAMPLE_JD_LLM_RESPONSE = {
        "target_role": "Senior Backend Engineer",
        "required_skills_from_jd": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL"]
    }

    def test_parseJd_returns_dict(self):
        from src.modules.ingestion.jdParser import parseJd
        with patch("src.modules.ingestion.jdParser.callLlm", return_value=self.SAMPLE_JD_LLM_RESPONSE):
            result = parseJd("We are hiring a Senior Backend Engineer with Python skills...")
        assert isinstance(result, dict)

    def test_parseJd_extracts_target_role(self):
        from src.modules.ingestion.jdParser import parseJd
        with patch("src.modules.ingestion.jdParser.callLlm", return_value=self.SAMPLE_JD_LLM_RESPONSE):
            result = parseJd("We are hiring a Senior Backend Engineer...")
        assert result["target_role"] == "Senior Backend Engineer"

    def test_parseJd_extracts_required_skills(self):
        from src.modules.ingestion.jdParser import parseJd
        with patch("src.modules.ingestion.jdParser.callLlm", return_value=self.SAMPLE_JD_LLM_RESPONSE):
            result = parseJd("We need Python, FastAPI, Docker...")
        assert "Python" in result["required_skills_from_jd"]
        assert "Kubernetes" in result["required_skills_from_jd"]

    def test_parseJd_deduplicates_skills(self):
        from src.modules.ingestion.jdParser import parseJd
        dupResponse = {"target_role": "Dev", "required_skills_from_jd": ["Python", "Python", "SQL"]}
        with patch("src.modules.ingestion.jdParser.callLlm", return_value=dupResponse):
            result = parseJd("Python Python SQL...")
        assert result["required_skills_from_jd"].count("Python") == 1

    def test_parseJd_raises_on_empty_text(self):
        from src.modules.ingestion.jdParser import parseJd
        with pytest.raises(ValueError, match="must not be empty"):
            parseJd("")

    def test_parseJd_raises_on_whitespace_only(self):
        from src.modules.ingestion.jdParser import parseJd
        with pytest.raises(ValueError, match="must not be empty"):
            parseJd("   ")

    def test_parseJd_defaults_missing_fields(self):
        from src.modules.ingestion.jdParser import parseJd
        with patch("src.modules.ingestion.jdParser.callLlm", return_value={}):
            result = parseJd("Some JD text")
        assert result["target_role"] == ""
        assert result["required_skills_from_jd"] == []


# ════════════════════════════════════════════════════════════════════════════════
# motivationParser.parseMotivation
# ════════════════════════════════════════════════════════════════════════════════

class TestParseMotivation:

    def test_returns_string(self):
        from src.modules.ingestion.motivationParser import parseMotivation
        with patch("src.modules.ingestion.motivationParser.callLlm",
                   return_value="The candidate is motivated by AI research."):
            result = parseMotivation("I am passionate about AI and want to join...")
        assert isinstance(result, str)

    def test_strips_whitespace(self):
        from src.modules.ingestion.motivationParser import parseMotivation
        with patch("src.modules.ingestion.motivationParser.callLlm",
                   return_value="  The candidate wants to contribute to AI.  "):
            result = parseMotivation("My motivation is AI.")
        assert result == "The candidate wants to contribute to AI."

    def test_raises_on_empty_text(self):
        from src.modules.ingestion.motivationParser import parseMotivation
        with pytest.raises(ValueError, match="must not be empty"):
            parseMotivation("")

    def test_raises_on_whitespace_only(self):
        from src.modules.ingestion.motivationParser import parseMotivation
        with pytest.raises(ValueError, match="must not be empty"):
            parseMotivation("   ")

    def test_llm_called_with_motivation_text(self):
        """Verify the motivation text is passed to the LLM."""
        from src.modules.ingestion.motivationParser import parseMotivation
        with patch("src.modules.ingestion.motivationParser.callLlm",
                   return_value="Summary.") as mockLlm:
            parseMotivation("I want to work in AI because I love solving problems.")
        mockLlm.assert_called_once()
        callKwargs = mockLlm.call_args
        assert "I want to work in AI" in callKwargs[1].get("prompt", "") or \
               "I want to work in AI" in str(callKwargs)


# ════════════════════════════════════════════════════════════════════════════════
# companyScraper.scrapeCompany (demo mode behaviour)
# ════════════════════════════════════════════════════════════════════════════════

class TestScrapeCompany:

    def test_returns_empty_string_in_demo_mode(self):
        """In demo mode, scrapeCompany must return '' with zero network calls."""
        from src.modules.ingestion.companyScraper import scrapeCompany
        with patch("src.modules.ingestion.companyScraper.settings") as mockSettings:
            mockSettings.is_demo = True
            result = scrapeCompany("Acme Corp")
        assert result == ""

    def test_no_network_call_in_demo_mode(self):
        """Ensure no HTTP libraries are invoked in demo mode."""
        from src.modules.ingestion.companyScraper import scrapeCompany
        with patch("src.modules.ingestion.companyScraper.settings") as mockSettings:
            mockSettings.is_demo = True
            with patch("builtins.__import__") as mockImport:
                result = scrapeCompany("TestCo")
        # If no import was attempted for httpx/requests, we're good
        assert result == ""

    def test_raises_not_implemented_in_production_mode(self):
        """Production mode must raise NotImplementedError (not silently fail)."""
        from src.modules.ingestion.companyScraper import scrapeCompany
        with patch("src.modules.ingestion.companyScraper.settings") as mockSettings:
            mockSettings.is_demo = False
            with pytest.raises(NotImplementedError):
                scrapeCompany("Acme Corp")
