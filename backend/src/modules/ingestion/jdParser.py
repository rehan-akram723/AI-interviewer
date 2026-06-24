# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/ingestion/jdParser.py
#
# Job Description Parser — LLM-driven extraction of role + required skills
#
# Exports: parseJd
# ─────────────────────────────────────────────────────────────────────────────

from src.core.llmClient import callLlm


_JD_SYSTEM_PROMPT = """\
You are a precise job description parser. Extract structured information \
from job postings and return only valid JSON.
"""

_JD_PROMPT_TEMPLATE = """\
Parse this job description and return a JSON object with exactly these two fields:

{{
  "target_role": "the exact job title from the posting (string)",
  "required_skills_from_jd": ["list of all technical and soft skills listed as required or preferred"]
}}

RULES:
- target_role: Use the job title as written in the posting. If ambiguous, use the most prominent title.
- required_skills_from_jd: Include ALL skills mentioned as required, preferred, or desired.
  Include both technical skills (Python, AWS, SQL) and soft skills (communication, leadership).
- Do NOT infer skills not mentioned. Extract only what is explicitly stated.
- Return ONLY valid JSON. No markdown, no explanation.

JOB DESCRIPTION:
---
{jdText}
---
"""


def parseJd(jdText: str) -> dict:
    """
    Extract structured role and skills data from a raw job description.

    Args:
        jdText: Raw job description text (plain text or pasted from a job board).

    Returns:
        dict with keys:
            target_role: str — the job title
            required_skills_from_jd: List[str] — all required/preferred skills

    Raises:
        ValueError: If jdText is empty.
        ValueError: If LLM response cannot be parsed as valid JSON.
    """
    if not jdText or not jdText.strip():
        raise ValueError("jdText must not be empty.")

    prompt = _JD_PROMPT_TEMPLATE.format(jdText=jdText.strip())

    parsed: dict = callLlm(
        prompt=prompt,
        systemPrompt=_JD_SYSTEM_PROMPT,
        temperature=0.1,
        maxTokens=1024,
        jsonMode=True,
    )

    # Normalise
    parsed.setdefault("target_role", "")
    parsed.setdefault("required_skills_from_jd", [])

    # Clean skill list
    parsed["required_skills_from_jd"] = list(dict.fromkeys(
        s.strip() for s in parsed.get("required_skills_from_jd", []) if s and s.strip()
    ))

    return parsed
