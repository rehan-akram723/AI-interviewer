# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/analysis/ttsService.py
#
# Text-to-Speech Service — ElevenLabs (production) / Text display (demo)
#
# Public interface:
#   speak(text: str) -> dict
#
# Return contract (both modes):
#   {
#     "mode":       "text" | "audio",
#     "content":    str,          -- text content (demo) or audio_url (production)
#     "audioUrl":   str | None,   -- None in demo, served URL in production
#     "audioBytes": bytes | None, -- None in demo, raw MP3 bytes in production
#   }
#
# Mode behaviour:
#   demo:       Returns immediately with mode="text". No HTTP call, no API key needed.
#               The frontend checks mode == "text" and displays the text in the
#               coaching sidebar instead of attempting audio playback.
#
#   production: Calls the ElevenLabs REST API synchronously using httpx.
#               Returns mode="audio" with raw MP3 bytes + a placeholder audio_url.
#               The API route is responsible for saving the bytes to a temp file
#               and serving the file URL back to the frontend.
#
# ElevenLabs API:
#   Endpoint: POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
#   Headers:  xi-api-key: {elevenlabs_api_key}
#             Content-Type: application/json
#             Accept: audio/mpeg
#   Body:     {"text": "...", "model_id": "eleven_monolingual_v1",
#              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
#   Response: MP3 audio bytes (binary)
#
# Client caching:
#   The httpx.Client is lazily initialised on first production call and cached
#   at module level. This avoids connection overhead on subsequent questions.
#   The client is configured with a 20-second timeout — ElevenLabs free tier
#   can be slow under load.
#
# Exports: speak, getTtsClient (for testing)
# ─────────────────────────────────────────────────────────────────────────────

import logging
from typing import Optional, Any

from src.core.appConfig import settings

logger = logging.getLogger(__name__)

# ── ElevenLabs API constants ───────────────────────────────────────────────────
_ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
_ELEVENLABS_MODEL_ID = "eleven_monolingual_v1"
_DEFAULT_VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
}
_REQUEST_TIMEOUT_SECONDS = 20

# ── Module-level httpx client singleton ───────────────────────────────────────
# Populated on the first production speak() call. Never touched in demo mode.
_ttsClient: Optional[Any] = None


def getTtsClient() -> Any:
    """
    Lazily initialise and cache the httpx sync client for ElevenLabs.

    Called only in production mode and only on first use.

    Returns:
        Configured httpx.Client instance.

    Raises:
        ImportError: If httpx is not installed (should always be present).
        ValueError:  If elevenlabs_api_key or elevenlabs_voice_id is not set.
    """
    global _ttsClient
    if _ttsClient is not None:
        return _ttsClient

    try:
        import httpx  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "httpx is not installed. Install it with: pip install httpx"
        ) from exc

    if not settings.elevenlabs_api_key:
        raise ValueError(
            "ttsService: ELEVENLABS_API_KEY is not set in .env. "
            "This is required in production mode."
        )
    if not settings.elevenlabs_voice_id:
        raise ValueError(
            "ttsService: ELEVENLABS_VOICE_ID is not set in .env. "
            "This is required in production mode."
        )

    _ttsClient = httpx.Client(
        base_url=_ELEVENLABS_BASE_URL,
        headers={
            "xi-api-key": settings.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    logger.info("ttsService: ElevenLabs httpx client initialised and cached.")
    return _ttsClient


def speak(text: str) -> dict:
    """
    Convert text to speech or return the text directly for display.

    Args:
        text: The question or feedback text to be spoken.
              Must be a non-empty string. If empty, returns a safe empty response.

    Returns:
        {
            "mode":       "text" | "audio",
            "content":    str,          -- the original text (always included)
            "audioUrl":   str | None,   -- None in demo; URL path in production
            "audioBytes": bytes | None, -- None in demo; MP3 bytes in production
        }

    The frontend inspects "mode" to decide how to render:
        "text"  → display text in the question card / coaching sidebar
        "audio" → play the audioUrl via the HTML Audio API

    Design invariant:
        This function NEVER makes an HTTP call in demo mode.
        No httpx import, no network I/O, no API key validation.
        The demo branch executes in under 1 microsecond.
    """
    # Normalise input
    safeText = (text or "").strip()

    # ── Demo mode: immediate text passthrough ─────────────────────────────────
    if settings.is_demo:
        logger.debug("ttsService [demo]: returning text display for '%s...'", safeText[:40])
        return {
            "mode": "text",
            "content": safeText,
            "audioUrl": None,
            "audioBytes": None,
        }

    # ── Production mode ───────────────────────────────────────────────────────

    if not safeText:
        logger.warning("ttsService [production]: received empty text — skipping TTS.")
        return {
            "mode": "text",
            "content": "",
            "audioUrl": None,
            "audioBytes": None,
        }

    voiceId = settings.elevenlabs_voice_id
    endpoint = f"/text-to-speech/{voiceId}"

    requestBody = {
        "text": safeText,
        "model_id": _ELEVENLABS_MODEL_ID,
        "voice_settings": _DEFAULT_VOICE_SETTINGS,
    }

    logger.debug(
        "ttsService [production]: Calling ElevenLabs for %d chars of text...",
        len(safeText),
    )

    try:
        client = getTtsClient()
        response = client.post(endpoint, json=requestBody)
        response.raise_for_status()

        audioBytes: bytes = response.content

        logger.info(
            "ttsService [production]: Received %d bytes of MP3 audio.",
            len(audioBytes),
        )

        # The actual URL path is determined by the API route that saves the file.
        # We return a placeholder that the route replaces with the served path.
        return {
            "mode": "audio",
            "content": safeText,           # Always include original text as fallback
            "audioUrl": None,              # API route fills this after saving to disk
            "audioBytes": audioBytes,      # Route saves these bytes and sets audioUrl
        }

    except Exception as exc:
        # Graceful degradation: TTS failure should NOT crash the interview.
        # Fall back to text display mode so the interview can continue.
        logger.error(
            "ttsService [production]: ElevenLabs call failed: %s. "
            "Falling back to text display.",
            exc,
        )
        return {
            "mode": "text",
            "content": safeText,
            "audioUrl": None,
            "audioBytes": None,
        }
