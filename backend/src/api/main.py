# ─────────────────────────────────────────────────────────────────────────────
# backend/src/api/main.py
#
# FastAPI application entry point.
#
# Responsibilities:
#   • Create the FastAPI app instance with lifespan handler.
#   • Configure logging via src.core.logger on startup.
#   • Register CORS middleware using settings.cors_origins.
#   • Register global exception handlers for AppBaseException subclasses.
#   • Mount all API routers (to be added in Milestone B).
#
# Run (from backend/ directory):
#   uvicorn src.api.main:app --reload
# ─────────────────────────────────────────────────────────────────────────────

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.appConfig import settings
from src.core.logger import configureLogging
from src.core.exceptions import AppBaseException

logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Runs startup logic before the first request and teardown after shutdown.
    """
    # ── Startup ────────────────────────────────────────────────────────────────
    configureLogging()
    logger.info(
        "%s v%s starting | mode=%s",
        settings.app_name,
        settings.app_version,
        settings.app_mode,
    )
    yield
    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("%s shutting down.", settings.app_name)


# ── App Instance ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Multimodal AI interview simulator. "
        "Conducts adaptive voice-driven interviews and generates structured PDF reports."
    ),
    lifespan=lifespan,
)


# ── CORS Middleware ────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ───────────────────────────────────────────────────

@app.exception_handler(AppBaseException)
async def appExceptionHandler(request: Request, exc: AppBaseException) -> JSONResponse:
    """
    Converts any AppBaseException subclass into a consistent JSON error response.

    Response body:
    {
        "error":   "SESSION_NOT_FOUND",
        "message": "Session 'abc-123' not found."
    }
    """
    logger.warning(
        "AppException [%s] %s | path=%s",
        exc.errorCode,
        exc.message,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.statusCode,
        content={"error": exc.errorCode, "message": exc.message},
    )


# ── Health Endpoint ────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["Health"])
def healthCheck() -> dict:
    """Returns the current application health and mode."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "mode": settings.app_mode,
    }


# ── Routers (Milestone B — will be mounted here) ───────────────────────────────
# from src.api.routes.setup import router as setupRouter
# from src.api.routes.interview import router as interviewRouter
# from src.api.routes.report import router as reportRouter
# from src.api.routes.candidates import router as candidatesRouter
# from src.api.routes.comparison import router as comparisonRouter
#
# app.include_router(setupRouter,       prefix="/api")
# app.include_router(interviewRouter,   prefix="/api")
# app.include_router(reportRouter,      prefix="/api")
# app.include_router(candidatesRouter,  prefix="/api")
# app.include_router(comparisonRouter,  prefix="/api")
