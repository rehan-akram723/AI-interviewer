# ─────────────────────────────────────────────────────────────────────────────
# backend/src/core/logger.py
#
# Standardised logging configuration for the AI Interviewer backend.
#
# Architecture pattern:
#   • Call configureLogging() ONCE at app startup (in main.py).
#   • Every module creates its own child logger with logging.getLogger(__name__).
#   • Never call configureLogging() from inside an agent or module — startup only.
#   • getLogger() is a lightweight helper that returns a named logger guaranteed
#     to be a child of the root logger configured here.
#
# Log format:
#   2026-01-01 12:00:00,123 | INFO     | src.agents.conductorAgent | message
#
# Usage (in any module):
#   import logging
#   logger = logging.getLogger(__name__)
#   logger.info("Processing session %s", session_id)
#
# Usage (in main.py once at startup):
#   from src.core.logger import configureLogging
#   configureLogging()
# ─────────────────────────────────────────────────────────────────────────────

import logging
import sys
from typing import Optional


# ── Log format ─────────────────────────────────────────────────────────────────
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configureLogging(level: int = logging.INFO, logFile: Optional[str] = None) -> None:
    """
    Configure the root logger for the entire application.

    Must be called once at application startup (in main.py lifespan event or
    before the first Uvicorn worker starts). Subsequent calls are idempotent —
    if handlers are already present on the root logger, this function returns
    immediately without adding duplicates.

    Args:
        level:   Logging level for all handlers. Defaults to INFO.
                 Use logging.DEBUG during development, logging.WARNING in production.
        logFile: Optional filesystem path to write log output to in addition to stdout.
                 When None (default), logs only go to stdout.

    Side effects:
        Attaches a StreamHandler (stdout) and optionally a FileHandler to the
        root logger. Sets the formatter on both handlers.
    """
    rootLogger = logging.getLogger()

    # Idempotency guard — do not add handlers more than once
    if rootLogger.handlers:
        return

    rootLogger.setLevel(level)
    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # ── Stdout handler (always present) ───────────────────────────────────────
    stdoutHandler = logging.StreamHandler(sys.stdout)
    stdoutHandler.setLevel(level)
    stdoutHandler.setFormatter(formatter)
    rootLogger.addHandler(stdoutHandler)

    # ── File handler (optional) ────────────────────────────────────────────────
    if logFile:
        try:
            fileHandler = logging.FileHandler(logFile, encoding="utf-8")
            fileHandler.setLevel(level)
            fileHandler.setFormatter(formatter)
            rootLogger.addHandler(fileHandler)
        except OSError as exc:
            # Log to stdout if file handler cannot be created — do not crash startup
            rootLogger.warning(
                "logger: Could not attach file handler to '%s': %s", logFile, exc
            )

    rootLogger.info(
        "Logging initialised | level=%s | file=%s",
        logging.getLevelName(level),
        logFile or "none",
    )


def getLogger(name: str) -> logging.Logger:
    """
    Convenience wrapper around logging.getLogger(name).

    Exists so modules can import from one place instead of mixing
    `import logging; logger = logging.getLogger(__name__)` everywhere.
    Both patterns are equivalent — use whichever is clearer.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A named Logger instance.
    """
    return logging.getLogger(name)
