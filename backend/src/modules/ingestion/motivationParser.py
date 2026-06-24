# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/ingestion/motivationParser.py
#
# Motivation Letter Parser — LLM-driven summarisation
#
# Condenses a raw motivation letter into 2-3 concise sentences capturing
# the candidate's core motivation for the role and company.
#
# Exports: parseMotivation
# ─────────────────────────────────────────────────────────────────────────────

from src.core.llmClient import callLlm


_MOTIVATION_SYSTEM_PROMPT = """\
You are a precise text summarisation engine. Summarise motivation letters \
into concise, first-person summaries that capture the candidate's core motivation.
"""

_MOTIVATION_PROMPT_TEMPLATE = """\
Summarise this motivation letter into exactly 2-3 sentences.

RULES:
- Write in third person (e.g., "The candidate is motivated by...")
- Focus on WHY the candidate wants this role and this company specifically.
- Be concrete. Avoid vague filler phrases like "passionate about technology".
- Do not add information not present in the letter.
- Return ONLY the summary text. No labels, no JSON, no markdown.

MOTIVATION LETTER:
---
{motivationText}
---
"""


def parseMotivation(motivationText: str) -> str:
    """
    Summarise a raw motivation letter into 2-3 concise sentences.

    Args:
        motivationText: Raw motivation letter text.

    Returns:
        A 2-3 sentence concise motivation summary string.

    Raises:
        ValueError: If motivationText is empty.
    """
    if not motivationText or not motivationText.strip():
        raise ValueError("motivationText must not be empty.")

    prompt = _MOTIVATION_PROMPT_TEMPLATE.format(motivationText=motivationText.strip())

    summary: str = callLlm(
        prompt=prompt,
        systemPrompt=_MOTIVATION_SYSTEM_PROMPT,
        temperature=0.3,   # Slightly higher for natural sentence generation
        maxTokens=256,
        jsonMode=False,    # Plain text output, not JSON
    )

    return summary.strip()
