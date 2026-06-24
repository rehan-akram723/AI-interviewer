# ─────────────────────────────────────────────────────────────────────────────
# backend/src/core/config.py
#
# Application Settings — Pydantic Settings + python-dotenv
#
# Architecture pattern:
#   • BaseSettings auto-reads all values from the .env file in the project root.
#   • Every module imports the `settings` singleton — never re-instantiate Settings.
#   • The `is_demo` property is the SINGLE gate for all paid API calls. No module
#     should check app_mode == "demo" directly; always use `settings.is_demo`.
#   • Storage paths are relative to the backend/ directory where uvicorn runs.
#     In production deployment they can be overridden via env vars.
#
# Usage:
#   from src.core.config import settings
#   if settings.is_demo:
#       return placeholder_result()
# ─────────────────────────────────────────────────────────────────────────────

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Literal, List


class Settings(BaseSettings):
    """
    Singleton settings object loaded from the .env file.

    All attributes map directly to environment variable names (case-insensitive).
    Pydantic-settings handles type coercion automatically.

    Critical rule: Never instantiate Settings() more than once.
    Import the `settings` singleton exported at the bottom of this file.
    """

    # ── Mode Control ──────────────────────────────────────────────────────────
    app_mode: Literal["demo", "production"] = "demo"
    """
    Master feature flag. Controls ALL paid API calls across every module:
      demo:       OpenRouter LLM (free) + text I/O only. No Whisper, ElevenLabs, MediaPipe.
      production: Full pipeline — Whisper STT, ElevenLabs TTS, MediaPipe facial analysis.
    """

    # ── LLM — OpenRouter ─────────────────────────────────────────────────────
    openrouter_api_key: str = ""
    """OpenRouter API key. Required for LLM calls even in demo mode (free tier)."""

    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    """Default model. Free tier models: llama-3.3-70b-instruct:free, deepseek-r1:free"""

    # ── TTS — ElevenLabs (production only) ───────────────────────────────────
    elevenlabs_api_key: str = ""
    """ElevenLabs API key. Only used when app_mode == "production"."""

    elevenlabs_voice_id: str = ""
    """ElevenLabs voice ID for the AI interviewer persona."""

    # ── STT — Whisper (production only, local GPU) ────────────────────────────
    whisper_model_size: str = "base"
    """Whisper model size: "base" | "small" | "medium" | "large". RTX 4060 recommended: "medium"."""

    # ── App Identity ──────────────────────────────────────────────────────────
    app_name: str = "AI Interviewer"
    app_version: str = "2.0.0"

    # ── Storage Paths (relative to backend/ working directory) ────────────────
    candidate_storage_path: str = "./data/candidates"
    """Directory where CandidateProfile JSON files are persisted."""

    session_storage_path: str = "./data/sessions"
    """Directory where InterviewSession JSON snapshots are persisted."""

    report_storage_path: str = "./data/reports"
    """Directory where InterviewReport JSON files are persisted."""

    pdf_output_path: str = "./data/reports"
    """Directory where generated PDF reports are saved. Same as report_storage_path by default."""

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:5173"]
    """Allowed CORS origins. Add your production frontend URL here for deployment."""

    # ── Interview Constraints ─────────────────────────────────────────────────
    max_followups_per_question: int = 2
    """
    Hard limit on follow-up question chains per original question.
    The Follow-Up Agent enforces this — once followup_count == 2,
    it signals the Conductor to advance to the next planned question.
    This is a system constant; do not adjust without updating the manifest.
    """

    # ── Pydantic-Settings Configuration ───────────────────────────────────────
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    # ── Computed Properties ────────────────────────────────────────────────────
    @property
    def is_demo(self) -> bool:
        """
        Universal demo-mode gate. Import this instead of checking app_mode directly.

        Usage pattern in every module:
            if settings.is_demo:
                return demo_placeholder_result()
            # production path below
        """
        return self.app_mode == "demo"

    @property
    def is_production(self) -> bool:
        """Convenience inverse of is_demo."""
        return self.app_mode == "production"


# ── Singleton Export ───────────────────────────────────────────────────────────
# Import this object everywhere. Never call Settings() again.
settings = Settings()
