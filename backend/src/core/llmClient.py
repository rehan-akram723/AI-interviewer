# ─────────────────────────────────────────────────────────────────────────────
# backend/src/core/llmClient.py
#
# Shared LLM Client — OpenRouter via OpenAI-compatible API
#
# Architecture pattern:
#   • Single function `callLlm(prompt, systemPrompt, ...)` used by ALL agents.
#   • All agents import and call this function — no agent instantiates its own client.
#   • Tests mock this function with `unittest.mock.patch("src.core.llmClient.callLlm")`
#     to avoid real API calls and control LLM outputs deterministically.
#   • JSON mode: when `jsonMode=True`, the function instructs the LLM to return
#     only valid JSON and attempts to parse + return the parsed dict.
#
# Usage:
#   from src.core.llmClient import callLlm
#   result = callLlm(prompt="Extract skills from this CV: ...", jsonMode=True)
# ─────────────────────────────────────────────────────────────────────────────

import json
import re
from typing import Optional, Union
from openai import OpenAI

from src.core.appConfig import settings


# ── OpenRouter client (OpenAI-compatible) ──────────────────────────────────────
# Instantiated once at module load. All agents reuse this client.
_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key or "no-key-set",
)

# System prompt used when no custom system prompt is provided
_DEFAULT_SYSTEM_PROMPT = (
    "You are a precise AI assistant. Follow instructions exactly. "
    "Return only what is explicitly requested."
)


def callLlm(
    prompt: str,
    systemPrompt: str = _DEFAULT_SYSTEM_PROMPT,
    model: Optional[str] = None,
    temperature: float = 0.2,
    maxTokens: int = 2048,
    jsonMode: bool = False,
) -> Union[str, dict]:
    """
    Call the LLM via OpenRouter (OpenAI-compatible API).

    Args:
        prompt:       The user-turn message content.
        systemPrompt: The system-turn message. Defaults to a precise assistant persona.
        model:        Override the model. Defaults to settings.openrouter_model.
        temperature:  Sampling temperature. Low (0.2) for structured extraction.
        maxTokens:    Maximum tokens to generate.
        jsonMode:     If True, instructs the model to return valid JSON only,
                      then parses and returns a dict. Raises ValueError on parse failure.

    Returns:
        str if jsonMode=False, dict if jsonMode=True.

    Raises:
        ValueError: If jsonMode=True and the LLM response cannot be parsed as JSON.
        openai.OpenAIError: If the API call fails.
    """
    selectedModel = model or settings.openrouter_model

    messages = [
        {"role": "system", "content": systemPrompt},
        {"role": "user", "content": prompt},
    ]

    # When requesting JSON, strengthen the instruction
    if jsonMode:
        messages[0]["content"] = (
            systemPrompt
            + "\n\nCRITICAL: Your response MUST be valid JSON only. "
            "No markdown, no explanation, no code fences. Raw JSON only."
        )

    response = _client.chat.completions.create(
        model=selectedModel,
        messages=messages,
        temperature=temperature,
        max_tokens=maxTokens,
    )

    rawText = response.choices[0].message.content or ""

    if not jsonMode:
        return rawText.strip()

    # ── JSON parsing with cleanup ──────────────────────────────────────────────
    # Some models wrap output in ```json ... ``` even when told not to.
    cleaned = rawText.strip()
    # Strip markdown code fences if present
    fencePattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(fencePattern, cleaned, re.MULTILINE)
    if match:
        cleaned = match.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned non-JSON output.\n"
            f"Model: {selectedModel}\n"
            f"Raw response: {rawText[:500]}\n"
            f"Parse error: {e}"
        ) from e
