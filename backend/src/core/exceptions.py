# ─────────────────────────────────────────────────────────────────────────────
# backend/src/core/exceptions.py
#
# Custom exception hierarchy for the AI Interviewer backend.
#
# Architecture pattern:
#   • All custom exceptions inherit from AppBaseException, which carries a
#     machine-readable errorCode and a human-readable message.
#   • FastAPI exception handlers (registered in main.py) catch AppBaseException
#     subclasses and convert them into consistent JSON error responses.
#   • Agents and modules raise these exceptions; API routes let them propagate
#     to the exception handlers — no manual try/except in routes needed.
#
# Naming convention:
#   • Class names: PascalCase ending in "Error" or "Exception"
#   • errorCode values: SCREAMING_SNAKE_CASE strings (used in API error bodies)
#
# Usage (in any module):
#   from src.core.exceptions import SessionNotFoundError
#   raise SessionNotFoundError(sessionId="abc-123")
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional


# ── Base Exception ─────────────────────────────────────────────────────────────

class AppBaseException(Exception):
    """
    Root of the custom exception hierarchy.

    All domain-specific exceptions extend this class. FastAPI exception handlers
    catch AppBaseException to produce uniform JSON error responses.

    Attributes:
        message:   Human-readable description of the error.
        errorCode: Machine-readable identifier (e.g. "SESSION_NOT_FOUND").
                   Used by the frontend to display localised error messages.
        statusCode: Suggested HTTP status code for the API response.
    """

    def __init__(
        self,
        message: str,
        errorCode: str = "INTERNAL_ERROR",
        statusCode: int = 500,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.errorCode: str = errorCode
        self.statusCode: int = statusCode

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"errorCode={self.errorCode!r}, "
            f"message={self.message!r})"
        )


# ── Session Exceptions ─────────────────────────────────────────────────────────

class SessionNotFoundError(AppBaseException):
    """
    Raised when a session ID is provided but no matching session exists on disk.

    Typical trigger: GET /api/sessions/{sessionId}/... with a stale or invalid ID.
    """

    def __init__(self, sessionId: str) -> None:
        super().__init__(
            message=f"Session '{sessionId}' not found.",
            errorCode="SESSION_NOT_FOUND",
            statusCode=404,
        )
        self.sessionId: str = sessionId


class SessionNotReadyError(AppBaseException):
    """
    Raised when an interview action is requested on a session that has not
    completed the setup phase yet (status != "ready").

    Typical trigger: Submitting an answer before the setup graph has finished.
    """

    def __init__(self, sessionId: str, currentStatus: str) -> None:
        super().__init__(
            message=(
                f"Session '{sessionId}' is not ready for interview actions. "
                f"Current status: '{currentStatus}'."
            ),
            errorCode="SESSION_NOT_READY",
            statusCode=409,
        )
        self.sessionId: str = sessionId
        self.currentStatus: str = currentStatus


class SessionAlreadyCompletedError(AppBaseException):
    """
    Raised when an answer is submitted to an already-completed session.
    """

    def __init__(self, sessionId: str) -> None:
        super().__init__(
            message=f"Session '{sessionId}' has already been completed. No further answers accepted.",
            errorCode="SESSION_ALREADY_COMPLETED",
            statusCode=409,
        )
        self.sessionId: str = sessionId


# ── Candidate Exceptions ───────────────────────────────────────────────────────

class CandidateNotFoundError(AppBaseException):
    """
    Raised when a candidate ID is provided but no matching profile exists on disk.
    """

    def __init__(self, candidateId: str) -> None:
        super().__init__(
            message=f"Candidate '{candidateId}' not found.",
            errorCode="CANDIDATE_NOT_FOUND",
            statusCode=404,
        )
        self.candidateId: str = candidateId


# ── File / Upload Exceptions ───────────────────────────────────────────────────

class InvalidMimeTypeError(AppBaseException):
    """
    Raised when an uploaded file has an unsupported MIME type.

    Typical trigger: Uploading a .docx file where only .pdf is accepted.

    Attributes:
        receivedMime: The MIME type that was actually received.
        allowedMimes: List of MIME types that are accepted.
    """

    def __init__(self, receivedMime: str, allowedMimes: list[str]) -> None:
        allowed = ", ".join(allowedMimes)
        super().__init__(
            message=(
                f"Unsupported file type '{receivedMime}'. "
                f"Allowed types: {allowed}."
            ),
            errorCode="INVALID_MIME_TYPE",
            statusCode=415,
        )
        self.receivedMime: str = receivedMime
        self.allowedMimes: list[str] = allowedMimes


class FileTooLargeError(AppBaseException):
    """
    Raised when an uploaded file exceeds the maximum allowed size.

    Attributes:
        receivedBytes: Size of the rejected file in bytes.
        maxBytes:      Maximum allowed size in bytes.
    """

    def __init__(self, receivedBytes: int, maxBytes: int) -> None:
        super().__init__(
            message=(
                f"Uploaded file is {receivedBytes:,} bytes, "
                f"which exceeds the {maxBytes:,}-byte limit."
            ),
            errorCode="FILE_TOO_LARGE",
            statusCode=413,
        )
        self.receivedBytes: int = receivedBytes
        self.maxBytes: int = maxBytes


class CvParsingError(AppBaseException):
    """
    Raised when the CV parser cannot extract meaningful structured data from
    the uploaded document (corrupted PDF, encrypted, scanned image, etc.).
    """

    def __init__(self, detail: Optional[str] = None) -> None:
        msg = "Failed to parse the uploaded CV."
        if detail:
            msg += f" Detail: {detail}"
        super().__init__(
            message=msg,
            errorCode="CV_PARSING_FAILED",
            statusCode=422,
        )


# ── LLM / Agent Exceptions ─────────────────────────────────────────────────────

class LLMTimeoutError(AppBaseException):
    """
    Raised when an LLM API call exceeds its timeout budget.

    Typical trigger: OpenRouter rate-limiting or network latency spike.

    Attributes:
        agentName:      Name of the agent that initiated the call.
        timeoutSeconds: The timeout threshold that was breached.
    """

    def __init__(self, agentName: str, timeoutSeconds: float) -> None:
        super().__init__(
            message=(
                f"LLM call from '{agentName}' timed out after {timeoutSeconds:.1f}s. "
                "Please retry."
            ),
            errorCode="LLM_TIMEOUT",
            statusCode=504,
        )
        self.agentName: str = agentName
        self.timeoutSeconds: float = timeoutSeconds


class LLMResponseParseError(AppBaseException):
    """
    Raised when the LLM returns a response that cannot be parsed as the
    expected JSON schema.

    Attributes:
        agentName:   Name of the agent that received the malformed response.
        rawResponse: The raw LLM output that failed to parse (truncated for safety).
    """

    def __init__(self, agentName: str, rawResponse: str) -> None:
        preview = rawResponse[:200] if len(rawResponse) > 200 else rawResponse
        super().__init__(
            message=(
                f"'{agentName}' received a non-parseable LLM response. "
                f"Preview: {preview!r}"
            ),
            errorCode="LLM_PARSE_ERROR",
            statusCode=502,
        )
        self.agentName: str = agentName
        self.rawResponse: str = rawResponse


# ── Report Exceptions ──────────────────────────────────────────────────────────

class ReportNotFoundError(AppBaseException):
    """
    Raised when a report is requested for a session that has not yet completed
    report generation (final_report is None).
    """

    def __init__(self, sessionId: str) -> None:
        super().__init__(
            message=(
                f"No report available for session '{sessionId}'. "
                "The interview may not be complete yet."
            ),
            errorCode="REPORT_NOT_FOUND",
            statusCode=404,
        )
        self.sessionId: str = sessionId


class PdfGenerationError(AppBaseException):
    """
    Raised when WeasyPrint fails to generate the PDF report.
    """

    def __init__(self, sessionId: str, detail: Optional[str] = None) -> None:
        msg = f"PDF generation failed for session '{sessionId}'."
        if detail:
            msg += f" Detail: {detail}"
        super().__init__(
            message=msg,
            errorCode="PDF_GENERATION_FAILED",
            statusCode=500,
        )
        self.sessionId: str = sessionId


# ── Pipeline Exceptions ────────────────────────────────────────────────────────

class PipelineError(AppBaseException):
    """
    Raised when an agent fails during concurrent pipeline execution.
    
    Attributes:
        agentName: The name of the agent that failed.
        originalException: The original exception that was raised.
    """

    def __init__(self, agentName: str, originalException: Exception) -> None:
        super().__init__(
            message=f"Agent '{agentName}' failed in pipeline: {str(originalException)}",
            errorCode="PIPELINE_ERROR",
            statusCode=500,
        )
        self.agentName: str = agentName
        self.originalException: Exception = originalException
