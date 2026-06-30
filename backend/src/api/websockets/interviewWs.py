# ─────────────────────────────────────────────────────────────────────────────
# backend/src/api/websockets/interviewWs.py
#
# Interview WebSocket Server — Live coaching and difficulty telemetry
#
# Provides a full-duplex WebSocket room for an active interview session.
# While the client HTTP POSTs audio to /answer, the backend pushes live
# JSON coaching frames (from liveCoachAgent) and difficulty adjustments
# (from difficultyCalibratorAgent) to the frontend via this socket.
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.modules.interviewEngine.sessionManager import sessionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSockets"])

# ── Connection Registry ────────────────────────────────────────────────────────
# Maps sessionId -> active WebSocket instance
# Allows background agents (which only know the sessionId) to push data to the client.
_activeConnections: Dict[str, WebSocket] = {}


# ── Internal Push Interface (Used by Agents) ───────────────────────────────────

def pushToClientSync(sessionId: str, message: dict) -> None:
    """
    Synchronous wrapper to push a JSON message to a connected WebSocket client.
    Agents (which run in a thread pool and cannot await directly) call this.
    """
    ws = _activeConnections.get(sessionId)
    if not ws:
        # Client not connected, or drop occurred. The frame is safely ignored.
        # It's already in the session state JSON anyway.
        return

    # Schedule the coroutine on the main event loop safely from the worker thread
    try:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(ws.send_json(message), loop)
    except Exception as exc:
        logger.warning(
            "Failed to schedule WebSocket push for session %s: %s",
            sessionId, exc
        )


# ── Route ──────────────────────────────────────────────────────────────────────

@router.websocket("/ws/sessions/{sessionId}")
async def interviewWebsocket(websocket: WebSocket, sessionId: str):
    """
    Full-duplex WebSocket endpoint for an interview session.
    """
    await websocket.accept()

    # Guard: Session must exist
    session = sessionManager.getSession(sessionId)
    if session is None:
        session = await sessionManager.loadSessionAsync(sessionId)
    if session is None:
        await websocket.send_json({"type": "error", "message": "Session not found."})
        await websocket.close(code=1008)
        return

    # Register connection
    _activeConnections[sessionId] = websocket
    logger.info("WebSocket connected for session %s", sessionId)

    try:
        # Keep-alive loop. We accept inbound text messages (e.g. pings or frontend telemetry)
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                # Currently only handling ping/pong for keepalive.
                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.debug("Received non-JSON text on WS %s: %s", sessionId, data)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally for session %s", sessionId)
    except Exception as exc:
        logger.error("WebSocket connection dropped for session %s: %s", sessionId, exc)
    finally:
        # Always clean up the connection registry
        if sessionId in _activeConnections:
            del _activeConnections[sessionId]
        logger.debug("WebSocket cleanup complete for session %s", sessionId)
