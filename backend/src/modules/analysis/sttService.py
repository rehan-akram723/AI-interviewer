# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/analysis/sttService.py
#
# Speech-to-Text Service — Whisper (production) / Text passthrough (demo)
#
# Public interface:
#   transcribe(audioBytes: bytes | None, textInput: str | None) -> str
#
# Mode behaviour:
#   demo:       Returns textInput directly. Zero imports from the `whisper`
#               package, zero model allocations, zero disk I/O.
#   production: Lazily loads the OpenAI Whisper model on first real audio call.
#               The loaded model object is cached at module level as _whisperModel
#               so subsequent calls in the same process are instant.
#               Whisper requires a file path — audio bytes are written to a
#               tempfile, transcribed, and the temp file is deleted.
#
# Lazy-load rationale:
#   Whisper's base model is ~150 MB; medium is ~1.5 GB on GPU. Loading at
#   module import time would make every test and dev server startup extremely
#   slow. Lazy loading ensures the model is only initialized on the FIRST live
#   interview answer, not on startup or unit test collection.
#
# Return contract:
#   Always a plain str. Empty string on empty/None inputs.
#   The caller (FollowUpAgent / API route) stores this in Answer.text.
#
# Exports: transcribe, getWhisperModel (for testing)
# ─────────────────────────────────────────────────────────────────────────────

import logging
import os
import tempfile
from typing import Optional, Any

from src.core.appConfig import settings

logger = logging.getLogger(__name__)

# ── Module-level Whisper model singleton ──────────────────────────────────────
# Populated on the first production transcribe() call. Never touched in demo mode.
_whisperModel: Optional[Any] = None


def getWhisperModel() -> Any:
    """
    Lazily load and cache the Whisper model.

    Called only in production mode and only on first use.
    Subsequent calls return the cached instance immediately.

    The model size is controlled by settings.whisper_model_size:
        "base"   → ~150 MB,  fast,  lower accuracy
        "small"  → ~460 MB,  good tradeoff
        "medium" → ~1.5 GB,  high accuracy  (recommended for RTX 4060)
        "large"  → ~3 GB,    best accuracy, requires more VRAM

    Returns:
        Loaded whisper model object.

    Raises:
        ImportError: If the `openai-whisper` package is not installed.
        RuntimeError: If Whisper fails to load the model.
    """
    global _whisperModel
    if _whisperModel is not None:
        return _whisperModel

    try:
        import whisper  # type: ignore[import]  # production-only dependency
    except ImportError as exc:
        raise ImportError(
            "openai-whisper is not installed. "
            "Install it with: pip install openai-whisper\n"
            "This package is only required in production mode."
        ) from exc

    modelSize = settings.whisper_model_size or "base"
    logger.info(
        "sttService: Loading Whisper model '%s'. "
        "This may take a moment on first call...",
        modelSize,
    )

    try:
        _whisperModel = whisper.load_model(modelSize)
        logger.info("sttService: Whisper '%s' model loaded and cached.", modelSize)
    except Exception as exc:
        raise RuntimeError(
            f"sttService: Failed to load Whisper model '{modelSize}': {exc}"
        ) from exc

    return _whisperModel


def transcribe(
    audioBytes: Optional[bytes],
    textInput: Optional[str],
) -> str:
    """
    Transcribe audio or pass through typed text, depending on APP_MODE.

    Args:
        audioBytes: Raw audio file bytes (WAV, MP3, WebM, etc.).
                    Used only in production mode.
                    Pass None in demo mode — it is never read.
        textInput:  Typed text string submitted by the candidate.
                    Used in demo mode as the direct transcript.
                    Also used as fallback in production if audioBytes is None.

    Returns:
        Transcript string. Empty string if both inputs are empty/None.

    Design invariant:
        This function NEVER touches the whisper package in demo mode.
        No import, no model load, no file I/O. The demo branch executes
        in under 1 microsecond.
    """
    # ── Demo mode: immediate passthrough ──────────────────────────────────────
    if settings.is_demo:
        transcript = (textInput or "").strip()
        logger.debug("sttService [demo]: passthrough '%s...'", transcript[:40])
        return transcript

    # ── Production mode ───────────────────────────────────────────────────────

    # Safety fallback: if no audio provided, use typed input
    if not audioBytes:
        logger.warning(
            "sttService [production]: audioBytes is empty — "
            "falling back to textInput passthrough."
        )
        return (textInput or "").strip()

    # Whisper requires a file path — write bytes to a named temp file
    tmpFile = None
    try:
        # suffix=".wav" helps Whisper auto-detect format; works with WebM/MP3 too
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
            prefix="stt_",
        ) as tmpFile:
            tmpFilePath = tmpFile.name
            tmpFile.write(audioBytes)

        logger.debug(
            "sttService [production]: Transcribing audio (%d bytes) from %s...",
            len(audioBytes),
            tmpFilePath,
        )

        model = getWhisperModel()

        # fp16=False: disable half-precision for CPU compatibility
        # language=None: auto-detect language
        result: dict = model.transcribe(tmpFilePath, fp16=False, language=None)
        transcript = result.get("text", "").strip()

        logger.info(
            "sttService [production]: Transcription complete. "
            "'%s...' (%d chars)",
            transcript[:50],
            len(transcript),
        )
        return transcript

    except Exception as exc:
        logger.error("sttService [production]: Transcription failed: %s", exc)
        # Graceful fallback to typed input rather than crashing the interview
        fallback = (textInput or "").strip()
        if fallback:
            logger.warning(
                "sttService [production]: Using textInput fallback: '%s...'",
                fallback[:50],
            )
        return fallback

    finally:
        # Always clean up the temp file regardless of success or failure
        if tmpFile is not None and os.path.exists(tmpFilePath):
            try:
                os.remove(tmpFilePath)
            except OSError as cleanupErr:
                logger.warning(
                    "sttService: Failed to delete temp file %s: %s",
                    tmpFilePath,
                    cleanupErr,
                )
