# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/ingestion/cvParser.py
#
# CV Parser — PDF text extraction + LLM-driven structured extraction
#
# Responsibilities:
#   1. Extract raw text from PDF bytes using pdfplumber
#   2. Call LLM to extract structured CandidateProfile fields
#   3. Strictly classify skills as confirmed vs uncertain
#
# Hallucination protection rule (enforced in the prompt):
#   confirmed_skills → skills EXPLICITLY listed in the CV (e.g., "Python" in skills section)
#   uncertain_skills → skills INFERRED from context (e.g., "AWS" mentioned in a job desc sentence)
#
# Exports: extractTextFromPdf, parseCv
# ─────────────────────────────────────────────────────────────────────────────

import io
import json
from typing import Optional

import pdfplumber

from src.core.llmClient import callLlm


# ── Extraction Prompt ──────────────────────────────────────────────────────────
_CV_EXTRACTION_SYSTEM_PROMPT = """\
You are a precise CV data extraction engine. Your job is to parse a candidate's \
CV and return a structured JSON object. You must follow every rule exactly.
"""

_CV_EXTRACTION_PROMPT_TEMPLATE = """\
Extract the following fields from this CV and return them as a single valid JSON object.

STRICT RULES:
1. confirmed_skills: ONLY skills that are EXPLICITLY listed by name in the CV
   (e.g., in a "Skills" section, or clearly stated as a technology used).
   Examples: "Python", "React", "PostgreSQL" — if they appear verbatim.
2. uncertain_skills: Skills you can INFER from context but are NOT explicitly stated.
   Example: If they worked at AWS but never listed cloud skills explicitly.
3. Do NOT invent information. If a field is missing, use null or an empty list.
4. Return ONLY valid JSON. No markdown, no explanation.

REQUIRED OUTPUT SCHEMA:
{{
  "full_name": "string or null",
  "email": "string or null",
  "education": [
    {{
      "institution": "string",
      "degree": "string",
      "field": "string",
      "graduation_year": integer or null,
      "gpa": "string or null"
    }}
  ],
  "experience": [
    {{
      "company": "string",
      "role": "string",
      "duration": "string",
      "description": "string",
      "technologies": ["list of explicitly mentioned technologies"]
    }}
  ],
  "projects": [
    {{
      "name": "string",
      "description": "string",
      "technologies": ["list of explicitly mentioned technologies"],
      "url": "string or null"
    }}
  ],
  "confirmed_skills": ["skills EXPLICITLY named in a skills section or equivalent"],
  "uncertain_skills": ["skills INFERRED from job descriptions or context only"]
}}

CV TEXT TO PARSE:
---
{cvText}
---
"""


def extractTextFromPdf(pdfBytes: bytes) -> str:
    """
    Extract all text from a PDF given as raw bytes using pdfplumber.

    Args:
        pdfBytes: Raw bytes of the PDF file.

    Returns:
        Concatenated text from all pages, separated by newlines.
        Returns empty string if the PDF has no extractable text.

    Raises:
        ValueError: If pdfBytes is empty or cannot be opened as a PDF.
    """
    if not pdfBytes:
        raise ValueError("pdfBytes must not be empty.")

    extractedPages = []
    try:
        with pdfplumber.open(io.BytesIO(pdfBytes)) as pdf:
            for page in pdf.pages:
                pageText = page.extract_text()
                if pageText:
                    extractedPages.append(pageText.strip())
        return "\n\n".join(extractedPages)
    except Exception:
        # Fallback to plain text if it's not a valid PDF
        try:
            return pdfBytes.decode('utf-8')
        except Exception:
            raise ValueError("Could not parse file as PDF or plain text.")


def parseCv(pdfBytes: bytes) -> dict:
    """
    Parse a CV PDF into a structured dict matching the CandidateProfile schema.

    Pipeline:
        1. Extract raw text from PDF via pdfplumber
        2. Send text to LLM with strict skill-classification prompt
        3. Return parsed dict (skills split into confirmed + uncertain)

    Args:
        pdfBytes: Raw bytes of the uploaded CV PDF.

    Returns:
        dict with keys matching CandidateProfile fields:
        full_name, email, education, experience, projects,
        confirmed_skills, uncertain_skills.

    Raises:
        ValueError: If PDF text extraction produces empty output.
        ValueError: If LLM response cannot be parsed as valid JSON.
    """
    cvText = extractTextFromPdf(pdfBytes)
    if not cvText.strip():
        raise ValueError(
            "Could not extract any text from the PDF. "
            "Ensure the CV is a text-based PDF (not a scanned image)."
        )

    prompt = _CV_EXTRACTION_PROMPT_TEMPLATE.format(cvText=cvText)

    parsed: dict = callLlm(
        prompt=prompt,
        systemPrompt=_CV_EXTRACTION_SYSTEM_PROMPT,
        temperature=0.1,  # Very low — extraction must be deterministic
        maxTokens=3000,
        jsonMode=True,
    )

    # Normalise: ensure list fields are present even if LLM omits them
    parsed.setdefault("education", [])
    parsed.setdefault("experience", [])
    parsed.setdefault("projects", [])
    parsed.setdefault("confirmed_skills", [])
    parsed.setdefault("uncertain_skills", [])

    # Strip and deduplicate skill lists
    parsed["confirmed_skills"] = list(dict.fromkeys(
        s.strip() for s in parsed.get("confirmed_skills", []) if s and s.strip()
    ))
    parsed["uncertain_skills"] = list(dict.fromkeys(
        s.strip() for s in parsed.get("uncertain_skills", []) if s and s.strip()
    ))

    return parsed
